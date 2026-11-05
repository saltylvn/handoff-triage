# 0003. Five layers against duplicates

**Status:** Accepted · 2026-11-04

**Context.** Retries are essential, but a retry must never create a second record. Delivery across systems is at-least-once, so exactly-once *effects* have to be built.

**Decision.**
1. **Unique idempotency key** on arrival: the sender's event ID, or a hash of normalized content.
2. **Step ledger:** finished steps are skipped on retry.
3. **HubSpot upsert keyed on email:** repeating it updates the same contact.
4. **Tagged Slack messages:** Slack has no idempotency key, so each post carries the item ID in metadata, and a resumed step searches for it before posting.
5. **Compare-and-set approval:** only the first click changes status.

**Alternatives.** "Check whether it exists, then create" has a race between the two calls. Relying on the ledger alone fails when the external write succeeds and the reply is lost.

**Consequences.** Two honest gaps: a person resending the same text with no event ID is treated as a duplicate, and layer 4 depends on Slack's history API being reachable during the retry.
