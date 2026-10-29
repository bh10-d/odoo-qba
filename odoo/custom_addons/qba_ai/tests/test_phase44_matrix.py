import os
import json
import time
import odoo
from odoo.api import Environment

def run_matrix_audit():
    odoo.tools.config.parse_config(['-c', '/app/debian/odoo.conf', '-d', 'qba'])
    registry = odoo.registry('qba')
    with registry.cursor() as cr:
        env = Environment(cr, odoo.SUPERUSER_ID, {})
        router = env['qba.query.intent.router']
        engine = env['qba.spec.matching.engine']
        conv_model = env['qba.ai.conversation']
        user = env.ref('base.user_admin')

        results = []

        test_cases = [
            # 1. SKU-only
            {"id": "MAT-01", "name": "SKU-only LC.002", "query": "LC.002", "category": "LC"},
            {"id": "MAT-02", "name": "SKU-only TBUA.046", "query": "TBUA.046", "category": "TBUA"},
            {"id": "MAT-03", "name": "SKU-only BI.087", "query": "BI.087", "category": "BI"},

            # 2. Product name & common aliases
            {"id": "MAT-04", "name": "Name alias: lá côn howo", "query": "lá côn howo", "category": "LC"},
            {"id": "MAT-05", "name": "Name alias: tăm bua sau", "query": "tăm bua sau", "category": "TBUA"},
            {"id": "MAT-06", "name": "Name alias: bi moay ơ", "query": "bi moay ơ", "category": "BI"},

            # 3. Multiple tech parameters in 1 query
            {"id": "MAT-07", "name": "Multi-param: lá côn phi 325 10 răng 8 lò xo", "query": "lá côn phi 325 10 răng 8 lò xo", "category": "LC"},
            {"id": "MAT-08", "name": "Multi-param: lá côn 325 10 răng", "query": "lá côn 325 10 răng", "category": "LC"},
            {"id": "MAT-09", "name": "Multi-param: 325, 10 răng", "query": "325, 10 răng", "category": "LC"},

            # 4. Numeric dimensions with/without units
            {"id": "MAT-10", "name": "With units: 325mm, 10 răng", "query": "325mm, 10 răng", "category": "LC"},
            {"id": "MAT-11", "name": "Without units / comma: 325 10", "query": "325 10", "category": "LC"},

            # 5. Vietnamese technical terms & alternate wording
            {"id": "MAT-12", "name": "Alt term: đĩa ly hợp 325 10 răng", "query": "đĩa ly hợp 325 10 răng", "category": "LC"},
            {"id": "MAT-13", "name": "Alt term: tang trống phanh", "query": "tang trống phanh", "category": "TBUA"},
            {"id": "MAT-14", "name": "Alt term: bạc đạn bánh trước", "query": "bạc đạn bánh trước", "category": "BI"},

            # 6. Missing or ambiguous parameters
            {"id": "MAT-15", "name": "Ambiguous: bare number 325", "query": "325", "category": "None"},
            {"id": "MAT-16", "name": "Ambiguous: punctuation ???", "query": "???", "category": "None"},

            # 7. Cross-category search
            {"id": "MAT-17", "name": "Cross-cat: tăm bua xe howo", "query": "tăm bua xe howo", "category": "TBUA"},
            {"id": "MAT-18", "name": "Cross-cat: bi 3017", "query": "bi 3017", "category": "BI"},

            # 8. Empty results
            {"id": "MAT-19", "name": "Empty search: lá côn phi 999 99 răng", "query": "lá côn phi 999 99 răng", "category": "LC"},
        ]

        print("=== EXECUTING MATRIX CASES ===")
        for tc in test_cases:
            t0 = time.perf_counter()
            route_res = router.route_query(tc["query"])
            t_route = time.perf_counter() - t0

            # Test conversation response
            conv = conv_model.with_user(user).create({
                "name": f"Test {tc['id']}",
                "user_id": user.id,
            })
            t1 = time.perf_counter()
            conv.post_user_message(tc["query"])
            t_total = time.perf_counter() - t1

            last_msg = conv.message_ids.filtered(lambda m: m.role == 'assistant').sorted('id', reverse=True)
            msg = last_msg[0] if last_msg else None

            # Collect results
            parsed_specs = route_res.get("extracted_specs") or {}
            intent = route_res.get("intent")
            target_cat = route_res.get("target_category")
            target_prod = route_res.get("target_product")

            res_info = {
                "id": tc["id"],
                "name": tc["name"],
                "query": tc["query"],
                "expected_cat": tc["category"],
                "parsed_intent": intent,
                "target_cat": target_cat.name if target_cat else None,
                "target_prod": target_prod.default_code if target_prod else None,
                "extracted_specs": {k: v.get("value") for k, v in parsed_specs.items()} if parsed_specs else {},
                "matched_count": len(msg.matched_product_ids) if msg else 0,
                "matched_skus": msg.matched_product_ids.mapped('default_code')[:5] if msg else [],
                "message_type": msg.message_type if msg else None,
                "t_route_ms": round(t_route * 1000, 2),
                "t_total_ms": round(t_total * 1000, 2),
            }
            results.append(res_info)
            print(f"[{tc['id']}] {tc['name']} -> intent={intent}, specs={res_info['extracted_specs']}, matched={res_info['matched_count']}, total={res_info['t_total_ms']}ms")

        # ---------------------------------------------------------------------
        # TEST MULTI-TURN CONVERSATION SCENARIOS
        # ---------------------------------------------------------------------
        print("\n=== EXECUTING MULTI-TURN CONVERSATION SCENARIO ===")
        chain_conv = conv_model.with_user(user).create({
            "name": "Multi-Turn Chain Test",
            "user_id": user.id,
        })

        # Turn 1: lá côn phi 325
        t_start = time.perf_counter()
        chain_conv.post_user_message("lá côn phi 325")
        t_m1 = time.perf_counter() - t_start
        ctx1 = chain_conv._get_search_context()
        m1 = chain_conv.message_ids.filtered(lambda m: m.role == 'assistant').sorted('id', reverse=True)[0]

        # Turn 2: thêm 10 răng
        t_start = time.perf_counter()
        chain_conv.post_user_message("thêm 10 răng")
        t_m2 = time.perf_counter() - t_start
        ctx2 = chain_conv._get_search_context()
        m2 = chain_conv.message_ids.filtered(lambda m: m.role == 'assistant').sorted('id', reverse=True)[0]

        # Turn 3: đổi sang 8 lò xo
        t_start = time.perf_counter()
        chain_conv.post_user_message("đổi sang 8 lò xo")
        t_m3 = time.perf_counter() - t_start
        ctx3 = chain_conv._get_search_context()
        m3 = chain_conv.message_ids.filtered(lambda m: m.role == 'assistant').sorted('id', reverse=True)[0]

        # Turn 4: So sánh với LC.002
        t_start = time.perf_counter()
        chain_conv.post_user_message("So sánh với LC.002")
        t_m4 = time.perf_counter() - t_start
        ctx4 = chain_conv._get_search_context()
        m4 = chain_conv.message_ids.filtered(lambda m: m.role == 'assistant').sorted('id', reverse=True)[0]

        # Turn 5: Unrelated query: tăm bua sau (Must reset LC filters and mode!)
        t_start = time.perf_counter()
        chain_conv.post_user_message("tăm bua sau 1069")
        t_m5 = time.perf_counter() - t_start
        ctx5 = chain_conv._get_search_context()
        m5 = chain_conv.message_ids.filtered(lambda m: m.role == 'assistant').sorted('id', reverse=True)[0]

        chain_res = {
            "turn_1": {"query": "lá côn phi 325", "specs": ctx1.get("specs"), "matched": m1.matched_product_ids.mapped('default_code'), "time_ms": round(t_m1*1000, 2)},
            "turn_2": {"query": "thêm 10 răng", "specs": ctx2.get("specs"), "matched": m2.matched_product_ids.mapped('default_code'), "time_ms": round(t_m2*1000, 2)},
            "turn_3": {"query": "đổi sang 8 lò xo", "specs": ctx3.get("specs"), "matched": m3.matched_product_ids.mapped('default_code'), "time_ms": round(t_m3*1000, 2)},
            "turn_4": {"query": "So sánh với LC.002", "mode": ctx4.get("mode"), "base": ctx4.get("active_product_code"), "msg_type": m4.message_type, "time_ms": round(t_m4*1000, 2)},
            "turn_5": {"query": "tăm bua sau 1069", "cat": ctx5.get("active_category_name"), "specs": ctx5.get("specs"), "mode": ctx5.get("mode"), "time_ms": round(t_m5*1000, 2)},
        }
        print("CHAIN RESULTS:", json.dumps(chain_res, ensure_ascii=False, indent=2))

        # Output JSON result for report
        with open('/app/custom_addons/qba_ai/tests/matrix_results.json', 'w', encoding='utf-8') as f:
            json.dump({"matrix": results, "chain": chain_res}, f, ensure_ascii=False, indent=2)
        print("SAVED /app/custom_addons/qba_ai/tests/matrix_results.json successfully!")

if __name__ == '__main__':
    run_matrix_audit()

