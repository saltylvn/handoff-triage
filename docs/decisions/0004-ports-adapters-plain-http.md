# 0004. Ports and adapters over plain HTTP

**Status:** Accepted · 2026-11-04

**Context.** Failure handling is the point of this project, so it must be testable without accounts or network.

**Decision.** The pipeline depends on small interfaces (`domain/ports.py`). Adapters implement them using httpx directly, sharing one retry policy that uses exponential backoff with full jitter and honors `Retry-After`. A wait longer than 15 seconds returns the item to the queue rather than holding the worker.

**Alternatives.** Vendor SDKs are convenient but hide retries and add dependencies. A retry library saves a few lines but makes the queue hand-off harder to see.

**Consequences.** Fakes can inject a lost reply at the exact point it matters. More code is ours to maintain, and API changes reach us directly.
