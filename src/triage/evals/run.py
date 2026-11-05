"""python -m triage.evals.run [--split dev|test|all]

Paced for free-tier rate limits. Each answer is saved as it arrives, so an interrupted run resumes
without spending quota twice. Answers are cached per model and prompt version."""

import argparse
import json
import os
import time
from collections.abc import Iterable
from pathlib import Path

import httpx

from triage.adapters.gemini import PROMPT_VERSION, GeminiClassifier
from triage.domain.models import Classification
from triage.domain.ports import ModelOutputError
from triage.evals.dataset import Example, load_dataset
from triage.evals.metrics import Scored, choose_threshold, summarize, threshold_row
from triage.infra.retry import RetryPolicy

ROOT = Path("eval")
RESULTS = ROOT / "results"


def _cache_path(model: str) -> Path:
    return RESULTS / f"raw-{model}-{PROMPT_VERSION}.jsonl"


def _load_cache(path: Path) -> dict[str, Classification | None]:
    cached: dict[str, Classification | None] = {}
    if path.exists():
        for line in path.read_text().splitlines():
            row = json.loads(line)
            answer = row["answer"]
            cached[row["id"]] = None if answer is None else Classification.model_validate(answer)
    return cached


def collect(
    examples: Iterable[Example], classifier: GeminiClassifier, model: str, min_interval_s: float
) -> list[Scored]:
    path = _cache_path(model)
    cached = _load_cache(path)
    rows: list[Scored] = []
    with path.open("a") as out:
        for example in examples:
            if example.id not in cached:
                started = time.monotonic()
                try:
                    cached[example.id] = classifier.classify(example.submission)
                except ModelOutputError:
                    cached[example.id] = None
                answer = cached[example.id]
                dumped = answer.model_dump() if answer else None
                out.write(json.dumps({"id": example.id, "answer": dumped}) + "\n")
                out.flush()
                print(f"{example.id}: {answer.triage.category if answer else 'invalid'}")
                time.sleep(max(0.0, min_interval_s - (time.monotonic() - started)))
            result = cached[example.id]
            rows.append(
                Scored(example, result.triage if result else None, result.usage if result else None)
            )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-interval", type=float, default=7.0, help="Seconds between calls")
    args = parser.parse_args()
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise SystemExit("Set GEMINI_API_KEY first: sh scripts/set-secret.sh GEMINI_API_KEY")
    model = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
    examples = load_dataset(ROOT / "dataset.jsonl")
    RESULTS.mkdir(parents=True, exist_ok=True)
    classifier = GeminiClassifier(
        httpx.Client(), key, model, RetryPolicy(max_attempts=6, max_wait_s=90.0)
    )
    rows = collect(examples, classifier, model, args.min_interval)
    dev = [r for r in rows if r.example.split == "dev"]
    test = [r for r in rows if r.example.split == "test"]
    threshold = choose_threshold(dev)
    report = {
        "model": model,
        "prompt_version": PROMPT_VERSION,
        "threshold_chosen_on_dev": threshold,
        "test_at_chosen_threshold": threshold_row(test, threshold) if threshold else None,
        "dev": summarize(dev),
        "test": summarize(test),
    }
    (RESULTS / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in list(report)[:4]}, indent=2))


if __name__ == "__main__":
    main()
