# 0007. HubSpot OAuth, Slack bot token, encrypted tokens

**Status:** Accepted · 2026-11-04

**Decision.**
- **HubSpot:** OAuth 2.0 authorization-code flow with only the contact read and write scopes. A 30-minute access token refreshes automatically, and once more on a 401.
- **Starting the flow:** a CLI command rather than a public route, so a stranger can't connect their own HubSpot account. The `state` value is single-use, expires, and is stored only as a hash.
- **Slack:** a bot token for one workspace is enough here. Every interaction's signature is verified, and only allow-listed users can approve.
- **Storage:** OAuth tokens are encrypted with AES-256-GCM before they reach the database. Secrets are read in one place (`config.py`) and live only in a git-ignored file.

**Consequences.** This is single-tenant. Serving many customers would need per-customer tokens and a Slack OAuth install flow.
