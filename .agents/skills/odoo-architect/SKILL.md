---
name: odoo-architect
description: Analyze an Odoo 18 repository, trace behavior, design addon boundaries and produce implementation plans before changes.
---

# Odoo Architect

## When to use
Use for new features, cross-module changes, unclear behavior, architecture decisions, refactors and technical discovery.

## Procedure
1. Inventory repository structure, addons paths, manifests, dependencies and runtime configuration.
2. Confirm Odoo Community 18 version from source/checkout, not from user assumptions alone.
3. Identify relevant models, fields, methods, XML IDs, views, actions, menus, controllers, JS assets, security and tests.
4. Trace the user journey end-to-end: UI → RPC/controller → model/service → database/external service → response/UI.
5. Identify existing extension points and conventions. Prefer inheritance and composition over core edits.
6. Map dependencies and data ownership. Identify transaction boundaries and side effects.
7. Propose the smallest viable design, alternatives, risks, migration needs and test plan.
8. Do not implement until the plan is clear for broad or high-risk work.

## Deliverable
- Current behavior and evidence (file paths, methods, XML IDs)
- Proposed files/modules to change
- Data model and access-control impact
- Compatibility/dependency concerns
- Failure modes and rollback strategy
- Acceptance criteria and test matrix

## Guardrails
Never invent an API or assume an addon exists. Mark unknowns and inspect source. Keep Community vs Enterprise distinctions explicit.
