# Multi Agent Triage

[![CI](https://github.com/saltylvn/multi_agent_triage/actions/workflows/ci.yml/badge.svg)](https://github.com/saltylvn/multi_agent_triage/actions/workflows/ci.yml)
![Python 3.13](https://img.shields.io/badge/python-3.13-blue)
![Strict mypy](https://img.shields.io/badge/mypy-strict-blue)
![Coverage 95%](https://img.shields.io/badge/coverage-95%25-brightgreen)

**A human-in-the-loop workflow that triages a company's contact form across multiple systems.** Gemini reads each message, an outside API enriches it, and HubSpot and Slack get updated. Anything unsure or risky waits for a person's approval, and retries never create duplicates.

| Measured on 70 held-out messages | Result |
|---|---|
| Handled without a person | **84.3%** |
| Correct when acting alone | **96.6%** |
| Sensitive messages handled without a person | **0 of 4** |
| Cost per message at paid rates | **about $0.00033** |

These are from synthetic test data, so [read the caveats](#evaluation). The workflow has also [run live](#live-run) on HubSpot and Slack test accounts, including a real approval click.

![How it works: a message arrives, AI reads it, rules decide, then it is handled alone or a person approves](docs/assets/flow.png)

> **On the name:** this is one LLM step inside a deterministic workflow across multiple systems, not a set of autonomous agents. That's deliberate, because fixed steps are easier to test, audit and trust.

## Try it in one minute

No accounts or keys needed. This runs the real pipeline against fake services and injects a rate limit, a lost reply, a replayed webhook and a double-clicked approval.

```bash
uv sync
```

```bash
uv run python -m triage.demo
```

To connect the real services, see [docs/setup.md](docs/setup.md). For a guided tour, see [docs/walkthrough.md](docs/walkthrough.md).

## Where to look

| Skill | What to read |
|---|---|
| OAuth 2.0 with token refresh | [adapters/hubspot.py](src/triage/adapters/hubspot.py) |
| Signed webhooks and approval clicks | [infra/signature.py](src/triage/infra/signature.py), [api.py](src/triage/api.py) |
| Retries, backoff and rate limits | [infra/retry.py](src/triage/infra/retry.py) |
| Idempotency and crash recovery | [pipeline.py](src/triage/pipeline.py), [decision 0003](docs/decisions/0003-layered-idempotency.md) |
| LLM output validation and prompt-injection defense | [adapters/gemini.py](src/triage/adapters/gemini.py), [domain/routing.py](src/triage/domain/routing.py) |
| Audit logging | [migrations/0001_init.sql](src/triage/migrations/0001_init.sql) |
| Evals | [evals/metrics.py](src/triage/evals/metrics.py), [dataset](eval/dataset.jsonl), [results](eval/results) |
| Design trade-offs | [decision records](docs/decisions/README.md) |
| Failure testing | [tests/test_pipeline.py](tests/test_pipeline.py) |

## Live run

Run on free HubSpot and Slack test accounts with synthetic messages:

| Scenario | Live result |
|---|---|
| Confident, routine lead | Contact created in HubSpot, one summary in Slack, no person needed |
| Same webhook sent again | Recognized as a duplicate and ignored |
| $250,000 deal | Held for approval even at 1.0 model confidence, with nothing written to HubSpot |
| Person clicks Approve | Signed click accepted, approver logged, contact created, summary posted |
| Invalid email rejected by HubSpot | Set aside as a permanent failure, not retried |
| Unsigned fake click through the public tunnel | Rejected with a 401 |

Every decision is recorded. This is the audit trail from that $250,000 deal, shortened:

```text
07:14:41  system          received
07:14:43  system          classified         sales_lead, confidence 1.0
07:14:43  system          enriched           domain age 11,389 days, not an existing contact
07:14:43  system          routed             needs_human, reason: high_value
07:14:44  system          chat_posted        approval_request
07:14:44  system          awaiting_approval
07:16:19  slack:APPROVER  human_approved
07:16:21  system          crm_upserted       contact created
07:16:21  system          chat_posted        summary
07:16:21  system          completed
```

## Architecture

![Architecture: contact form, API, database and worker, connected to Gemini, RDAP, HubSpot and Slack](docs/assets/architecture.png)

### Full system map

![Full system map: every step from the contact form through the API, database and worker, plus Gemini, RDAP, HubSpot, Slack and the approver](docs/assets/system-map.png)

### Key decisions

| Decision | Why | Trade-off |
|---|---|---|
| [API and worker around a durable queue](docs/decisions/0002-api-worker-durable-queue.md) | Fast replies, and a crash loses no work | One worker on one machine until it moves to Postgres |
| [Five layers against duplicates](docs/decisions/0003-layered-idempotency.md) | Delivery is at-least-once, so effects must be made safe to repeat | More moving parts |
| [Plain HTTP behind interfaces](docs/decisions/0004-ports-adapters-plain-http.md) | Failures are visible and testable without accounts | We maintain more code |
| [Routing rules in code](docs/decisions/0005-routing-policy-in-code.md) | Prompt injection can't directly trigger an action | Rules need manual upkeep |
| [Measured threshold on held-out data](docs/decisions/0008-eval-design.md) | Model confidence is inflated | Small sample |

## Reliability

![Five failures and how the system responds to each](docs/assets/reliability.png)

Items that still fail are set aside, trigger a Slack alert, and can be retried with `python -m triage.requeue` once the cause is fixed. Finished steps are skipped, so nothing repeats.

![Rules flag an item, Slack asks, a person decides, HubSpot is updated](docs/assets/approval.png)

![Every status a message can have](docs/assets/lifecycle.png)

## Evaluation

100 labeled synthetic messages: 30 for tuning, and 70 held out for reporting. The prompt and the 0.90 threshold were set using only the tuning messages.

| Measure, on the 70 held-out messages | Result |
|---|---|
| Handled without a person, all routing rules | **84.3%** (59 of 70) |
| Correct when acting alone | **96.6%** (57 of 59; roughly 88–99% with this sample size) |
| Sensitive messages handled without a person | **0** (all 4 flagged, with no false flags) |
| Category accuracy, all messages | 95.7% |
| Urgency accuracy | 88.6% |
| Company, team size, budget extraction | 100%, 97.1%, 100% |
| Prompt-injection attempts classified correctly | 3 of 3, no inflated values |
| Invalid model replies | 0 of 70 |
| Model latency | 1.0 s median, 7.5 s at the 95th percentile |
| Cost per message | $0 on the free tier; about $0.33 per 1,000 at paid rates |

![Automation rate and accuracy at each confidence threshold](docs/assets/threshold-tradeoff.png)

This chart shows confidence alone, before the business rules:

| Confidence threshold | Handled alone | Correct when alone |
|---|---|---|
| 0.80 | 92.9% | 95.4% |
| 0.85 | 90.0% | 96.8% |
| **0.90 (chosen)** | **88.6%** | **96.8%** |
| 0.95 | 80.0% | 98.2% |

**How to read this:**

- **Small, synthetic sample.** The messages and labels were written with AI assistance for this project, so treat the numbers as indicative. A production claim needs real traffic.
- **Router replay.** The 84.3% applies the real routing rules to saved model answers. It assumes new senders from established domains, because the set has no enrichment data.
- **Confidence is inflated.** The model rated 95 of 100 messages at 0.90 or higher, which is why the threshold is measured and not assumed.
- **Answers can vary.** Temperature is 0, yet tuning-set accuracy moved between 96.7% and 93.3% across two runs of the same prompt.

## Project layout

```
src/triage/
  api.py            webhooks, Slack clicks, OAuth callback
  worker.py         background processing loop
  pipeline.py       the workflow as resumable steps
  store.py          all SQL: queue, ledger, audit log, tokens
  domain/           pure rules and schemas, no network
  adapters/         Gemini, RDAP, HubSpot, Slack
  infra/            retries, HTTP errors, signatures, encryption
  evals/            dataset loader, metrics, runner
hubspot/            the HubSpot OAuth app, as configuration
eval/               labeled examples and results
docs/               walkthrough, setup, decision records, diagrams
```

**Stack:** Python 3.13, FastAPI, Pydantic, httpx, SQLite, Docker, Gemini API, HubSpot CRM API, Slack API.

**Checks:** CI runs a dependency audit, ruff, strict mypy, 83 tests with a coverage gate, the failure demo, and a container start-up test. Coverage leaves out thin entry points and the live eval runner. Run most of it locally with `make check`. Security controls are listed in [SECURITY.md](SECURITY.md).

## Known limitations

- It ran on one machine through a temporary tunnel, and isn't deployed as a service.
- One worker at a time ([the path to Postgres](docs/decisions/0002-api-worker-durable-queue.md)).
- Lost replies and crashes are proven with injected faults, not by breaking the live services.
- The live run covered Approve. Reject is covered by tests.
- There's no data-retention policy, since it handles synthetic data only.
- The free Gemini tier can use submitted content to improve Google's products, so real customer data needs the paid tier.

## What I'd build next

1. Run a pilot on real traffic to replace the synthetic numbers.
2. Calibrate confidence, or replace it with a better signal, since the model's own score separates cases poorly.
3. Move to Postgres with multiple workers, and deploy it.
4. Add monitoring for automation rate, error rate and approval wait time.
