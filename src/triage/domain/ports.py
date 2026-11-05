"""What the pipeline needs from outside. Real adapters and test fakes both satisfy these."""

from typing import Protocol

from triage.domain.models import (
    ChatMessage,
    Classification,
    ContactInput,
    ContactResult,
    ExistingContact,
    PostResult,
    Submission,
)


class Classifier(Protocol):
    def classify(self, submission: Submission) -> Classification: ...


class DomainInfo(Protocol):
    def age_days(self, domain: str) -> int | None: ...


class Crm(Protocol):
    def find_contact(self, email: str) -> ExistingContact | None: ...
    def upsert_contact(self, contact: ContactInput) -> ContactResult: ...


class Chat(Protocol):
    def post(self, message: ChatMessage) -> PostResult: ...
    def find_posted(self, item_id: str, kind: str, since: float) -> PostResult | None: ...
    def mark_resolved(self, channel: str, ts: str, text: str) -> None: ...


class ModelOutputError(Exception):
    """The model answered, but not with a valid triage, even after one repair attempt."""
