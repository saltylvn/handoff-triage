# 0006. Gemini free tier, synthetic data only

**Status:** Accepted · 2026-11-04

**Context.** The project should cost nothing to run. Google's pricing page says free-tier content is used to improve its products.

**Decision.** `gemini-3.5-flash-lite` on the free tier, using only synthetic messages with reserved `.example` addresses. The sender's email is not sent to the model. Reports show $0 actual cost, plus the paid-tier equivalent calculated from real token counts.

**Consequences.** A real deployment must move to the paid tier before handling customer data. Free-tier rate limits force pacing, so evals run slowly and answers are cached to avoid spending quota twice.
