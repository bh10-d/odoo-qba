---
name: odoo-integration
description: Design Odoo 18 controllers, external API clients, webhooks, queues and reliable integrations.
---

# Odoo Integration Engineer

## Design
Define ownership, authentication, request/response schema, idempotency key, retry policy, timeout, rate limits, transaction boundary and observability before coding.

## Rules
- Keep controllers thin; validate input and delegate to model/service methods.
- Use HTTPS and secure secret storage/configuration. Never commit credentials.
- Set connect/read timeouts; bound retries and use exponential backoff with jitter where appropriate.
- Verify webhook signatures and replay protection when provider supports them.
- Make webhook processing idempotent; persist event identity and processing state.
- Acknowledge only after durable acceptance according to provider contract.
- Use queues for slow/retryable work; keep jobs bounded and safe to retry.
- Do not make external calls while holding database locks longer than necessary.
- Redact tokens, personal data and payload secrets from logs.
- Test duplicate, delayed, out-of-order, malformed and failed events.

## Verification
Use provider sandbox/test mode and real contract fixtures. Never simulate a successful production settlement by directly fabricating internal state.
