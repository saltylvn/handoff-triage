# 0008. Evals report safety on a held-out test split

**Status:** Accepted · 2026-11-04

**Context.** Overall accuracy hides what matters: errors the system acts on with no person checking.

**Decision.** 100 labeled synthetic examples, split into 30 dev and 70 test by a fixed rule. Prompt changes and threshold selection use dev only; results are reported on test. The headline numbers are precision of auto-handled items, automation rate, and sensitive items handled without a person. Accuracy, field extraction, latency and cost are also reported.

**Consequences.** The set is small, so one error moves test accuracy by about 1.4 points; results should be read as approximate. The messages and labels were written with AI assistance for this project, not drawn from real traffic, so results may flatter the system. Real traffic would be needed for a production claim.
