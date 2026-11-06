---
name: odoo-testing
description: Plan and execute Odoo 18 unit, integration, security, frontend and AI/RAG regression tests.
---

# Odoo Testing Engineer

## Test strategy
- Unit tests for deterministic business rules.
- Odoo transactional tests for ORM behavior and module integration.
- Security tests using users/groups/companies with different permissions.
- Controller/API tests for schemas, auth, errors and idempotency.
- Frontend tests/build checks for OWL behavior where the project supports them.
- AI/RAG evaluation tests for retrieval, grounding, permissions and resilience.
- End-to-end tests only for critical user journeys and real integration contracts.

## Rules
- Read existing test conventions and test tags first.
- Use isolated test databases or disposable environments.
- Keep fixtures small and deterministic.
- Do not call paid/external services in unit tests; use controlled fakes for unit-level behavior and provider sandbox for contract/E2E tests.
- Test failure paths, duplicates, retries, concurrency assumptions and rollback.
- Never mark a test passed unless it ran successfully.
- Report skipped tests and environment blockers separately.

## Odoo test execution
Derive the command from the repository's Docker/entrypoint and Odoo configuration. Common CLI patterns vary by deployment; inspect first. Do not assume container names, database names, addons paths or config paths.
