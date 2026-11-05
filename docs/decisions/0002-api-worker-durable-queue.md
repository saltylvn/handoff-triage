# 0002. Separate API and worker around a durable queue

**Status:** Accepted · 2026-11-04

**Context.** Senders and Slack expect fast replies (Slack allows 3 seconds), but classification and CRM calls are slow and can fail.

**Decision.** The API verifies, validates, saves and returns 202. A separate worker process claims items from a queue table using a lease, so a crashed worker's item is picked up again. SQLite in WAL mode holds the queue, step ledger, audit log and tokens in one transaction boundary.

**Alternatives.** Redis or SQS with Celery means more infrastructure to run, and a write to the queue and to the database could then disagree. Processing inside the request loses work on a crash and risks timeouts.

**Consequences.** One worker on one machine is the design limit, and the lease has no heartbeat, so it must exceed the longest item (180 seconds). To scale out: move the `Store` class to Postgres with `FOR UPDATE SKIP LOCKED`. All SQL lives in that class, which keeps the move contained.
