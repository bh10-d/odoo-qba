---
name: odoo-backend
description: Implement and debug Odoo 18 Python addons, ORM models, business logic, computed fields, constraints and scheduled jobs.
---

# Odoo Backend Engineer

## Inspect first
Read the target model, its inheritance chain, callers, related fields, views, ACLs, record rules, manifest dependencies and tests. Verify APIs against the installed Odoo 18 source.

## Engineering rules
- Use `_name`, `_inherit`, `_inherits` intentionally; explain delegation vs classical extension where relevant.
- Define fields with correct `required`, `index`, `copy`, `tracking`, `company_dependent`, `compute`, `inverse`, `store` and relation semantics.
- Compute methods must assign values for every record in `self`; declare accurate `@api.depends` and `@api.depends_context`.
- Use `@api.constrains` for invariants that must hold on ORM writes; use SQL constraints only when they are truly database-level and compatible with upgrade/data state.
- Handle multi-record recordsets. Avoid singleton assumptions unless enforced with `ensure_one()`.
- Avoid side effects in compute methods and onchange handlers.
- Use context deliberately; never treat context values as trusted authorization.
- Use batch operations and recordset operations; avoid per-record searches inside loops.
- Preserve company consistency and currency/UoM semantics.
- Use `sudo()` only with a documented authorization boundary and minimal scope.
- Raise user-facing errors with appropriate Odoo exceptions; do not leak stack traces or secrets.
- For cron/jobs, design idempotency, bounded batches, retry behavior and observability.

## Tests
Cover create/read/write/unlink behavior, multi-record calls, constraints, compute dependencies, access rights, company boundaries, transaction rollback and edge cases.
