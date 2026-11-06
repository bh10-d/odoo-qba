# Workflow: Bug Investigation

1. Reproduce with exact steps, user role, company, record state and environment.
2. Capture relevant redacted logs and browser/network errors.
3. Trace UI → RPC/controller → model → database/external service.
4. Form a falsifiable root-cause hypothesis; inspect source before editing.
5. Add a regression test that fails before the fix where feasible.
6. Apply the smallest fix; avoid unrelated refactoring.
7. Run focused and neighboring tests; inspect side effects and permissions.
8. Report root cause, evidence, fix, tests and remaining uncertainty.
