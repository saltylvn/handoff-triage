"""The labeled examples. All synthetic: free-tier content can be used by Google to improve its
products, so no real customer message goes into this set."""

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from triage.domain.models import Category, Submission, Urgency

# Stratified split: the file is grouped by category, so taking 3 of every 10 rows keeps the mix.
# Change the prompt and pick the threshold using dev only. Report results on test only.
_DEV_POSITIONS = frozenset({0, 3, 6})


class Example(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    split: str
    submission: Submission
    category: Category
    urgency: Urgency = "normal"
    sensitive: bool = False
    company: str | None = None
    team_size: int | None = None
    budget_usd: float | None = None
    tags: list[str] = []


def load_dataset(path: Path) -> list[Example]:
    examples: list[Example] = []
    lines = [line for line in path.read_text().splitlines() if line.strip()]
    for index, line in enumerate(lines):
        row = json.loads(line)
        submission = Submission(
            email=row.pop("from"), subject=row.pop("subject"), message=row.pop("message")
        )
        split = "dev" if index % 10 in _DEV_POSITIONS else "test"
        examples.append(Example(submission=submission, split=split, **row))
    return examples
