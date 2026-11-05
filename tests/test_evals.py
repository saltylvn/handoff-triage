from collections import Counter
from pathlib import Path

import pytest

from triage.domain.models import Submission
from triage.evals.chart import render
from triage.evals.dataset import Example, load_dataset
from triage.evals.metrics import (
    Scored,
    choose_threshold,
    percentile,
    router_row,
    summarize,
    sweep,
    threshold_row,
)
from triage.fakes import triage_of

DATASET = Path("eval/dataset.jsonl")


def test_dataset_is_valid_and_split_as_designed() -> None:
    examples = load_dataset(DATASET)
    assert len(examples) == 100
    assert len({e.id for e in examples}) == 100
    assert Counter(e.split for e in examples) == {"dev": 30, "test": 70}
    # Every category is in both splits; adversarial and sensitive cases are represented.
    for split in ("dev", "test"):
        assert len({e.category for e in examples if e.split == split}) == 6
    assert sum("injection" in e.tags for e in examples) >= 3
    assert sum(e.sensitive for e in examples) >= 5


def test_dataset_uses_only_reserved_domains() -> None:
    assert all(e.submission.email.endswith(".example") for e in load_dataset(DATASET))


def example(category: str = "support", sensitive: bool = False) -> Example:
    return Example.model_validate(
        {
            "id": "x",
            "split": "dev",
            "submission": Submission(email="a@x.example", message="m"),
            "category": category,
            "sensitive": sensitive,
        }
    )


def scored(actual: str, predicted: str, confidence: float, sensitive: bool = False) -> Scored:
    triage = triage_of(category=predicted, confidence=confidence, team_size=None, company=None)
    return Scored(example(actual, sensitive), triage, None)


def test_threshold_row_counts_auto_precision() -> None:
    rows = [
        scored("support", "support", 0.95),
        scored("spam", "support", 0.85),
        scored("other", "other", 0.5),
    ]
    assert threshold_row(rows, 0.8)["auto_count"] == 2
    assert threshold_row(rows, 0.8)["auto_precision"] == 0.5
    assert threshold_row(rows, 0.9)["auto_precision"] == 1.0
    assert threshold_row(rows, 0.99)["auto_precision"] is None


def test_choose_threshold_keeps_most_automation_with_most_margin() -> None:
    rows = [scored("support", "support", 0.95), scored("spam", "support", 0.72)]
    assert choose_threshold(rows) == 0.95  # 0.75 through 0.95 auto-handle the same single item


def test_choose_threshold_refuses_sensitive_leak() -> None:
    assert choose_threshold([scored("support", "support", 0.99, sensitive=True)]) is None


def test_summary_counts_invalid_answers_as_wrong() -> None:
    rows = [scored("support", "support", 0.9), Scored(example(), None, None)]
    summary = summarize(rows)
    assert summary["category_accuracy"] == 0.5
    assert summary["invalid_answers"] == 1


def test_full_router_also_applies_the_business_rules() -> None:
    big_deal = triage_of(category="sales_lead", confidence=0.99, team_size=900)
    rows = [scored("support", "support", 0.95), Scored(example("sales_lead"), big_deal, None)]
    assert threshold_row(rows, 0.9)["auto_count"] == 2
    assert router_row(rows, 0.9)["auto_count"] == 1


def test_percentile() -> None:
    assert percentile([], 0.95) is None
    assert percentile([1.0, 2.0, 3.0, 4.0], 0.5) == 2.0
    assert percentile([float(i) for i in range(1, 101)], 0.95) == pytest.approx(95)


def test_chart_renders_every_threshold_and_escapes_text() -> None:
    rows = [scored("support", "support", 0.95), scored("spam", "support", 0.72)]
    svg = render(sweep(rows), "A & B", "subtitle")
    assert svg.startswith("<svg")
    assert "A &amp; B" in svg
    assert "Correct when acting alone at 0.95: 100%" in svg
