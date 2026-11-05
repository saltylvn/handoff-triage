# 0005. The routing policy is code

**Status:** Accepted · 2026-11-04

**Context.** Form messages are untrusted, and may try to instruct the model. A model's self-reported confidence is also not a calibrated probability.

**Decision.** The model returns structured facts, validated by a strict schema. `domain/routing.py` decides. A person is needed for: confidence below threshold, sensitive content, high value, an urgent existing customer, spam from an existing customer, or a sales lead from a domain under 30 days old. An invalid model reply gets zero confidence, so it goes to a person.

**Alternatives.** Letting the model pick the action directly is simpler, but one successful prompt injection could then cause a write.

**Consequences.** Injection can still skew classification, so the eval set includes injection attempts, and the threshold comes from measurement rather than intuition.
