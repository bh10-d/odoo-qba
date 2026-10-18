import odoo
from odoo import api, SUPERUSER_ID
odoo.tools.config.parse_config(["-d", "qba"])
registry = odoo.registry("qba")
with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    categ_lc = env["product.category"].search([("name", "ilike", "LC")], limit=1)
    engine = env["qba.spec.matching.engine"]
    input_specs = {"rang": {"value": 10, "uom": "răng"}}
    res = engine.find_matching_products(categ_lc.id, input_specs)
    print("Direct Specs Search 'rang: 10':")
    print("Total candidates:", res["total_candidates"])
    print("Total matches:", res["total_matches"])
    for m in res["ranked_matches"][:3]:
        print(f"Match: {m['candidate_name']} ({m['candidate_code']}) - score={m['match_score']} status={m['match_status']} reason={m['status_reason']}")
        for l in m["comparison_lines"]:
            print(f"   Line: {l['spec_code']} ({l['spec_name']}): inp={l['input_val']} cand={l['candidate_val']} status={l['line_status']}")

