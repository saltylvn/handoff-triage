# Security

This is a portfolio project that handles synthetic data on test accounts. Please report a problem through GitHub's private vulnerability reporting, or open an issue if it isn't sensitive.

## What's protected and how

| Risk | Control |
|---|---|
| Forged or replayed webhooks | HMAC signature over timestamp and raw body, with a 5-minute window |
| Forged approval clicks | Slack signature check and an allow-list of approvers |
| Double actions | Compare-and-set on approval status |
| Prompt injection | The model only returns schema-checked fields, and plain code decides actions |
| Slack mention injection | All message text is escaped, and user IDs are validated |
| Stolen database file | OAuth tokens encrypted with AES-256-GCM |
| OAuth login forgery | Single-use, expiring `state`, stored only as a hash |
| Connecting someone else's HubSpot account | The flow starts from a CLI command, not a public route |
| Lookup URL tricks | Domains are checked before reaching the RDAP URL |
| Secrets in the repo | Secrets live in a git-ignored file and are read in one module |
| Tampered audit log | Database triggers block updates and deletes |

## Not covered

No data-retention policy, rate limiting on public routes, or production deployment hardening, because it isn't deployed as a service. Real customer data would also need a paid Gemini tier.
