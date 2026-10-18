import odoo
from odoo import api, SUPERUSER_ID
odoo.tools.config.parse_config(["-d", "qba"])
registry = odoo.registry("qba")
with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    prod_lc002 = env["product.template"].search([("default_code", "ilike", "LC.002")], limit=1)
    engine = env["qba.spec.matching.engine"]
    res = engine.match_product_to_candidates(prod_lc002.id)
    print("Base Product:", prod_lc002.name, prod_lc002.default_code)
    print("Total candidates:", res["total_candidates"])
    print("Total matches:", res["total_matches"])
    print("Total rejected:", len(res["rejected_candidates"]))
    for m in res["rejected_candidates"]:
        if "LC.007" in (m.get("candidate_code") or ""):
            print(f"Candidate: {m['candidate_name']} ({m['candidate_code']}) - score={m['match_score']} status={m['match_status']} reason={m['status_reason']}")
            for l in m["comparison_lines"]:
                print(f"   Line: {l['spec_code']} ({l['spec_name']}): inp={l['input_val']} cand={l['candidate_val']} status={l['line_status']} hard={l.get('is_hard_constraint')}")

