---
name: odoo-frontend
description: Build and debug Odoo 18 web client UI using OWL, JavaScript, XML templates, QWeb, assets and services.
---

# Odoo Frontend Engineer

## Inspect first
Find the existing component, template, action, view, asset bundle, service and neighboring implementation. Confirm the exact Odoo 18 conventions in the checked-out source.

## Rules
- Use OWL patterns already present in the target Odoo version.
- Register assets in the correct manifest bundle; verify paths and load order.
- Use services/hooks and reactive state rather than ad-hoc global state.
- Keep components focused; separate data access, state, presentation and business rules.
- Handle asynchronous lifecycle, cancellation/stale responses and component unmounting.
- Handle loading, empty, error, success and permission-denied states.
- Escape/render untrusted content safely; do not inject raw HTML from users or AI responses.
- Do not rely on hidden buttons or frontend checks for authorization.
- Avoid direct DOM manipulation unless a documented integration requires it.
- Keep accessibility, keyboard behavior and responsive layout in scope.

## Verification
Run available JS lint/build checks, inspect browser console/network errors when runtime access exists, and test the UI flow against the actual Odoo 18 server. State clearly when browser verification was not possible.
