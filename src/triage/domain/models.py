"""Everything that crosses a trust boundary has a schema here. Type hints alone validate nothing."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Category = Literal["sales_lead", "support", "partnership", "job_seeker", "spam", "other"]
Urgency = Literal["low", "normal", "high"]
Plan = Literal["crm_and_notify", "notify_only", "discard"]
ItemStatus = Literal[
    "queued", "processing", "awaiting_approval", "done", "discarded", "rejected", "failed"
]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Submission(Strict):
    event_id: str | None = Field(default=None, min_length=1, max_length=200)
    email: EmailStr
    name: str | None = Field(default=None, max_length=200)
    company: str | None = Field(default=None, max_length=200)
    subject: str | None = Field(default=None, max_length=300)
    message: str = Field(min_length=1, max_length=10_000)


class Triage(Strict):
    category: Category
    urgency: Urgency
    sensitive: bool  # legal threats, security incidents, data-deletion demands
    confidence: float = Field(ge=0, le=1)
    company: str | None = Field(max_length=200)
    team_size: int | None = Field(ge=1)
    budget_usd: float | None = Field(ge=0)
    summary: str = Field(min_length=1, max_length=500)


class Usage(BaseModel):
    model: str
    prompt_version: str
    input_tokens: int
    output_tokens: int
    cost_usd_equivalent: float  # what these tokens would cost on the paid tier
    latency_ms: float
    attempts: int


class Classification(BaseModel):
    triage: Triage
    usage: Usage | None
    invalid_output: bool = False


class ExistingContact(BaseModel):
    id: str
    lifecycle_stage: str | None


class Enrichment(BaseModel):
    email_domain: str
    is_free_mail: bool
    domain_age_days: int | None
    existing_contact: ExistingContact | None
    degraded: list[str]  # optional lookups that failed; the item still moves on


class Route(BaseModel):
    plan: Plan
    needs_human: bool
    reasons: list[str]
    threshold: float


class ContactInput(BaseModel):
    email: str
    properties: dict[str, str]


class ContactResult(BaseModel):
    id: str
    created: bool


class PostResult(BaseModel):
    ts: str
    recovered: bool = False  # True when a retry found the earlier post instead of posting twice


class ChatMessage(BaseModel):
    item_id: str
    kind: Literal["summary", "approval_request"]
    sender: str
    category: Category
    urgency: Urgency
    confidence: float
    summary: str
    reasons: list[str] = []
    crm_contact_id: str | None = None


class Item(BaseModel):
    id: str
    payload: Submission
    status: ItemStatus
    attempts: int
    approved_by: str | None
