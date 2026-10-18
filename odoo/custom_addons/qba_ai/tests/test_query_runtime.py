import odoo
from odoo import api, SUPERUSER_ID
odoo.tools.config.parse_config(["-d", "qba"])
registry = odoo.registry("qba")
with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    # 1. Test query lc.002
    print("=== TEST QUERY: 'lc.002' ===")
    wiz_a = env["qba.ai.assistant"].create({"user_query": "lc.002"})
    wiz_a.action_ask_ai()
    print("Status message:", wiz_a.status_message)
    print("Confidence:", wiz_a.confidence_level)
    print("Matched products:", [p.default_code for p in wiz_a.matched_product_ids])
    print("\n--- Performance HTML Snippet ---")
    print(wiz_a.query_perf_html[:400] if wiz_a.query_perf_html else "No perf HTML")
    print("\n--- Matching Explanation HTML Snippet ---")
    print(wiz_a.matching_explanation_html[:500] if wiz_a.matching_explanation_html else "No matching HTML")

    # 2. Test query rang: 10 răng
    print("\n=== TEST QUERY: 'rang: 10 răng' ===")
    wiz_b = env["qba.ai.assistant"].create({"user_query": "rang: 10 răng"})
    wiz_b.action_ask_ai()
    print("Status message:", wiz_b.status_message)
    print("Confidence:", wiz_b.confidence_level)
    print("Matched products:", [p.default_code for p in wiz_b.matched_product_ids])
    print("\n--- Performance HTML Snippet ---")
    print(wiz_b.query_perf_html[:400] if wiz_b.query_perf_html else "No perf HTML")
    print("\n--- Matching Explanation HTML Snippet ---")
    print(wiz_b.matching_explanation_html[:500] if wiz_b.matching_explanation_html else "No matching HTML")

