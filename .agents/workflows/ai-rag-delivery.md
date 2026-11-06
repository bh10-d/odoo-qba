# Workflow: AI/RAG Feature Delivery

1. **Classify query types** — exact ID, fuzzy name, structured attributes, semantic, document, live mutable facts.
2. **Map data authority** — identify Odoo models and external document sources; define source of truth.
3. **Threat model** — user roles, company boundaries, prompt injection, sensitive fields, provider data egress.
4. **Design retrieval** — choose deterministic lookup / SQL filters / semantic / document RAG; avoid vector DB by default until justified.
5. **Design tools** — narrow allowlist, typed arguments, server-side authorization, no arbitrary SQL/shell/Python.
6. **Resilience** — timeout, token limit, retry budget, cache dimensions/TTL, fallback, rate limiting.
7. **Evaluation** — build labeled test cases before tuning; measure recall@k, grounded accuracy, citations, latency and cost.
8. **Implement** — keep model orchestration separate from Odoo business logic and data-access boundaries.
9. **Verify** — test stale price/stock, unauthorized records, injected documents, empty retrieval, provider timeout and malformed output.
10. **Release** — feature flag if appropriate, logs/metrics, rollback path and post-release checks.
