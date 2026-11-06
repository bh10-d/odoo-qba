# Workflow: Feature Delivery

1. **Frame** — define user story, acceptance criteria, out-of-scope items.
2. **Recon** — run `odoo-architect`; inspect actual modules, call paths and Odoo 18 source.
3. **Design** — list model/view/security/API/asset/data changes and risks.
4. **Approve** — ask for confirmation if schema, permissions, external side effects or shared environment may change.
5. **Implement** — invoke backend/frontend/security/integration skills as applicable.
6. **Test** — invoke `odoo-testing`; run focused tests then relevant regression suite.
7. **Review** — invoke `odoo-code-review`; resolve Critical/High findings.
8. **Report** — use implementation report template; list exact commands and outcomes.
