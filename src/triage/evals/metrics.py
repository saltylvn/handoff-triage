"""Pure scoring, unit tested. Headline: when the system acts alone, how often is it right?"""

from collections import Counter
from dataclasses import dataclass
from statistics import median

from triage.domain.models import Enrichment, Triage, Usage
from triage.domain.routing import Policy, decide_route
from triage.evals.dataset import Example


@dataclass(frozen=True)
class Scored:
    example: Example
    triage: Triage | None  # None: the model never gave a valid answer
    usage: Usage | None


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def percentile(values: list[float], fraction: float) -> float | None:
    """Nearest-rank percentile."""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, -(-len(ordered) * fraction // 1))
    return ordered[int(rank) - 1]


def _same_company(expected: str | None, actual: str | None) -> bool:
    return (expected or "").casefold().strip() == (actual or "").casefold().strip()


def threshold_row(rows: list[Scored], threshold: float) -> dict[str, float | int | None]:
    """Auto means what the router would let through: confident and not flagged sensitive."""
    auto = [
        r for r in rows if r.triage and r.triage.confidence >= threshold and not r.triage.sensitive
    ]
    correct = sum(1 for r in auto if r.triage and r.triage.category == r.example.category)
    missed = sum(1 for r in auto if r.example.sensitive)
    return {
        "threshold": threshold,
        "auto_count": len(auto),
        "auto_rate": _rate(len(auto), len(rows)),
        "auto_precision": _rate(correct, len(auto)),
        "sensitive_auto_handled": missed,
    }


def router_row(rows: list[Scored], threshold: float) -> dict[str, float | int | None]:
    """Replays the real routing rules, not just confidence. Assumes each sender is new and from an
    established domain, because the labeled set has no enrichment data."""
    neutral = Enrichment(
        email_domain="unknown",
        is_free_mail=False,
        domain_age_days=None,
        existing_contact=None,
        degraded=[],
    )
    policy = Policy(confidence_threshold=threshold)
    auto = [r for r in rows if r.triage and not decide_route(r.triage, neutral, policy).needs_human]
    correct = sum(1 for r in auto if r.triage and r.triage.category == r.example.category)
    return {
        "threshold": threshold,
        "auto_count": len(auto),
        "auto_rate": _rate(len(auto), len(rows)),
        "auto_correct": correct,
        "auto_precision": _rate(correct, len(auto)),
        "sensitive_auto_handled": sum(1 for r in auto if r.example.sensitive),
    }


def sweep(rows: list[Scored]) -> list[dict[str, float | int | None]]:
    return [threshold_row(rows, t / 100) for t in range(50, 100, 5)]


def choose_threshold(dev: list[Scored], min_precision: float = 0.95) -> float | None:
    """The threshold automating the most while meeting the bar with no sensitive item handled
    alone. On a tie, the highest: same behavior on dev, with more margin. Chosen on dev so the test
    score stays honest."""
    best: dict[str, float | int | None] | None = None
    for row in sweep(dev):
        precision = row["auto_precision"]
        if precision is None or precision < min_precision or row["sensitive_auto_handled"] != 0:
            continue
        if best is None or row["auto_count"] == best["auto_count"]:
            best = row
    return float(best["threshold"] or 0.0) if best else None


def summarize(rows: list[Scored]) -> dict[str, object]:
    answered = [r for r in rows if r.triage]
    right = [r for r in answered if r.triage and r.triage.category == r.example.category]
    per_category: dict[str, dict[str, float | int | None]] = {}
    for category in sorted({r.example.category for r in rows}):
        actual = [r for r in answered if r.example.category == category]
        predicted = [r for r in answered if r.triage and r.triage.category == category]
        hits = [r for r in actual if r.triage and r.triage.category == category]
        per_category[category] = {
            "support": len(actual),
            "precision": _rate(len(hits), len(predicted)),
            "recall": _rate(len(hits), len(actual)),
        }
    confusion = Counter(
        f"{r.example.category} -> {r.triage.category}"
        for r in answered
        if r.triage and r.triage.category != r.example.category
    )
    sensitive = [r for r in answered if r.example.sensitive]
    usages = [r.usage for r in rows if r.usage]
    latencies = [u.latency_ms for u in usages]
    costs = [u.cost_usd_equivalent for u in usages]

    def field_accuracy(matches: list[bool]) -> float | None:
        return _rate(sum(matches), len(matches))

    return {
        "items": len(rows),
        "invalid_answers": len(rows) - len(answered),
        "category_accuracy": _rate(len(right), len(rows)),
        "urgency_accuracy": field_accuracy(
            [bool(r.triage and r.triage.urgency == r.example.urgency) for r in answered]
        ),
        "sensitive_recall": field_accuracy(
            [bool(r.triage and r.triage.sensitive) for r in sensitive]
        ),
        "company_accuracy": field_accuracy(
            [
                bool(r.triage and _same_company(r.example.company, r.triage.company))
                for r in answered
            ]
        ),
        "team_size_accuracy": field_accuracy(
            [bool(r.triage and r.triage.team_size == r.example.team_size) for r in answered]
        ),
        "budget_accuracy": field_accuracy(
            [bool(r.triage and r.triage.budget_usd == r.example.budget_usd) for r in answered]
        ),
        "per_category": per_category,
        "confusions": dict(confusion.most_common()),
        "latency_ms_p50": median(latencies) if latencies else None,
        "latency_ms_p95": percentile(latencies, 0.95),
        "cost_usd_per_item_paid_equivalent": sum(costs) / len(costs) if costs else None,
        "cost_usd_actual_free_tier": 0.0,
        "input_tokens_mean": sum(u.input_tokens for u in usages) / len(usages) if usages else None,
        "output_tokens_mean": sum(u.output_tokens for u in usages) / len(usages)
        if usages
        else None,
        "threshold_sweep": sweep(rows),
    }
