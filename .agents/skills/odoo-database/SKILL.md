---
name: odoo-database
description: Diagnose Odoo 18 PostgreSQL performance, ORM query patterns, indexes, transactions and safe schema/data migrations.
---

# Odoo Database Engineer

## Diagnose
Use logs and measured query plans/timings. Identify query count, N+1 patterns, row counts, selectivity, lock contention and transaction scope before optimizing.

## Rules
- Prefer ORM and its cache/prefetch behavior for business operations.
- Use `EXPLAIN (ANALYZE, BUFFERS)` only on safe representative data; `ANALYZE` executes the query.
- Add indexes only for demonstrated query patterns; consider write overhead and index size.
- Parameterize SQL. Never interpolate user input into SQL.
- If raw SQL changes ORM-managed data, account for cache invalidation and recomputation using version-correct APIs.
- Avoid long transactions and external network calls inside database transactions.
- Design migrations to be restartable, bounded, observable and safe on partially migrated data.
- Before schema changes, inspect existing data for nulls, duplicates and invalid values.
- Never run destructive SQL on production without explicit approval, verified backup and rollback plan.

## Deliverable
Baseline measurement, bottleneck, proposed change, expected trade-off, migration plan and before/after measurement.
