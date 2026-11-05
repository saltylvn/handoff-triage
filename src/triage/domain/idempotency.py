import hashlib
import json

from triage.domain.models import Submission


def _squash(text: str | None) -> str:
    return " ".join((text or "").lower().split())


def idempotency_key(submission: Submission) -> str:
    """Same event, same key. The sender's event ID wins; otherwise a hash of normalized content,
    so a form that resubmits without an ID still dedupes."""
    if submission.event_id:
        return f"event:{submission.event_id}"
    content = json.dumps(
        [submission.email.lower(), _squash(submission.subject), _squash(submission.message)]
    )
    return f"hash:{hashlib.sha256(content.encode()).hexdigest()}"
