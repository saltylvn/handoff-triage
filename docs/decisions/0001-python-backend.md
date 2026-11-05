# 0001. Python for the whole backend

**Status:** Accepted · 2026-11-04

**Context.** The system is a backend: webhooks, API integrations, a queue and LLM evals. There is no user interface beyond Slack.

**Decision.** Python 3.13, FastAPI, Pydantic, httpx. uv manages dependencies with a lockfile; ruff and strict mypy check the code.

**Alternatives.** TypeScript would work and the owner knows it, but evals and data analysis are more natural in Python, and two languages would add cost with no user-facing benefit.

**Consequences.** TypeScript is reserved for a web dashboard, if one is ever added. The n8n build covers the low-code side, so the project shows both ways of working.
