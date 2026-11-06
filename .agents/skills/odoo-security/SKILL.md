---
name: odoo-security
description: Audit and implement Odoo 18 access control, ACLs, record rules, groups, sudo boundaries and company isolation.
---

# Odoo Security Engineer

## Review layers
1. Model ACLs in `ir.model.access.csv`.
2. Record rules and their global/group scope.
3. Groups, implied groups and menu/action visibility.
4. Field-level `groups` restrictions.
5. Controller authentication, authorization, CSRF and input validation.
6. `sudo()`, raw SQL, exports, attachments, computed fields and background jobs.
7. Company context and cross-company relations.

## Rules
- Default deny; grant the minimum operations and records required.
- Menus/views are not security boundaries.
- Review read, create, write and unlink independently.
- Test as representative low-privilege users, not only admin.
- Check whether domains can be bypassed through alternate RPC/controller paths.
- Never trust client-supplied user, company, record IDs or context as authorization.
- For elevated operations, validate the caller's permission before entering a narrowly scoped `sudo()` block.
- Avoid leaking existence of inaccessible records through error messages or timing where practical.

## Required tests
User A cannot read/write User B's protected records; company A cannot access company B records; unauthorized RPC/controller calls fail; allowed role can perform intended actions.
