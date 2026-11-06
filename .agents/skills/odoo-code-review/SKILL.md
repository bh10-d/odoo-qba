---
name: odoo-code-review
description: Perform risk-focused reviews of Odoo 18 addon changes, AI/RAG features and integrations.
---

# Odoo Code Reviewer

Review the diff and surrounding code, not only changed lines.

## Review order
1. Functional correctness and business invariants.
2. Access control, company isolation, `sudo()` and data leakage.
3. Transaction boundaries, idempotency and concurrency.
4. Odoo 18 API compatibility, manifest dependencies and XML IDs.
5. ORM performance, N+1 queries and indexing.
6. OWL lifecycle, state consistency and frontend error handling.
7. AI/RAG grounding, prompt injection, tool permissions and stale data.
8. Test coverage, migration/upgrade safety and maintainability.

## Findings format
For each finding include severity (Critical/High/Medium/Low), exact file/line, concrete failure scenario, impact and minimal remediation.

Do not report style preferences as defects. Do not claim a vulnerability without a plausible exploit path. State areas not verified due to missing runtime or test access.
