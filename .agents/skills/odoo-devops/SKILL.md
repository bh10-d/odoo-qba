---
name: odoo-devops
description: Operate Odoo 18 Community development environments with Docker, configuration, logs, backups and safe deployments.
---

# Odoo DevOps Engineer

## Inspect
Read Dockerfiles, compose files, mounted addons, config, environment variable names, health checks, volumes, networks and service dependencies. Never print secret values.

## Rules
- Separate development, test/staging and production configuration.
- Pin versions where reproducibility matters; document upgrade strategy.
- Use health checks and structured logs; redact secrets and personal data.
- Persist PostgreSQL and filestore correctly; understand both are required for recovery.
- Back up database and filestore consistently before upgrades or risky changes.
- Test restore procedures; a backup that has never been restored is unverified.
- Upgrade modules in a disposable/staging database first.
- Do not delete volumes, reset databases, rebuild production state or restart production services without explicit approval.
- Avoid `latest` tags for production dependencies.
- Document resource limits, worker/cron configuration and long-running job behavior.

## Incident workflow
Capture timestamp, affected service, recent changes, relevant redacted logs, health status and reproduction. Prefer reversible mitigation; preserve evidence before cleanup.
