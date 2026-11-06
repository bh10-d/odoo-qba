# Odoo Senior Developer Skill Pack
**Target:** Odoo Community 18 · Antigravity / VS Code · Full-stack + AI/RAG

## Purpose
A repository-aware engineering skill pack for safely extending Odoo 18 Community and building AI/RAG features in custom addons.

## Install
1. Copy this directory into your repository, or keep it in a shared skills location supported by your agent.
2. Put `AGENTS.md` at the repository root. For agents that support project rules, import/reference it from their project instruction file.
3. Keep each skill directory intact; each contains a `SKILL.md`.
4. Ask the agent to read `AGENTS.md` first, then invoke the relevant skill for the task.

> Agent skill discovery paths vary. Antigravity and VS Code extensions may use different project-rule and skill-discovery conventions. Verify the configured path in the installed agent; do not assume a folder is auto-discovered.

## Included skills
| Skill | Use |
|---|---|
| `odoo-architect` | Repository reconnaissance, module boundaries, design decisions |
| `odoo-backend` | ORM, models, fields, compute, constraints, business logic |
| `odoo-frontend` | OWL, JS services, XML views, assets, QWeb |
| `odoo-security` | ACL, record rules, groups, company/tenant isolation |
| `odoo-database` | PostgreSQL, ORM query efficiency, indexes, migrations |
| `odoo-integration` | Controllers, external APIs, webhooks, queues |
| `odoo-ai-rag` | Retrieval, embeddings, grounding, tool routing, evaluation |
| `odoo-testing` | Odoo tests, integration tests, regression and test evidence |
| `odoo-code-review` | Risk-focused review, correctness, security, maintainability |
| `odoo-devops` | Docker, environments, logs, backups, deployment safety |

## Recommended activation
- New feature / unclear scope: `odoo-architect`
- Python model or business logic: `odoo-backend`
- OWL / web client: `odoo-frontend`
- Access or multi-company issue: `odoo-security`
- Slow query / data model: `odoo-database`
- API / webhook / external system: `odoo-integration`
- AI assistant / RAG: `odoo-ai-rag`
- Before merge: `odoo-testing` + `odoo-code-review`
- Runtime / deployment: `odoo-devops`

## Non-negotiable operating mode
- Inspect the actual repository and installed Odoo source before making assumptions.
- Treat the checked-out code and its manifest as the authority for this project.
- Never claim a test passed unless it was executed and its output was inspected.
- Never run destructive database, migration, deployment, or external side-effect commands without explicit approval.
- Prefer minimal, reversible changes and explain any unavoidable data migration.
