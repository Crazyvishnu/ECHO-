from datetime import datetime, timezone
from enum import StrEnum
from uuid import uuid4
from pydantic import BaseModel, Field


def now() -> datetime:
    return datetime.now(timezone.utc)


class DecisionStatus(StrEnum):
    PROPOSED = "proposed"
    VALIDATED = "validated"
    LAUNCHED = "launched"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class Assumption(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    statement: str
    confidence: int = Field(ge=0, le=100)
    importance: str
    supporting_evidence: list[str] = []
    contradicting_evidence: list[str] = []
    validation_method: str
    status: str = "unvalidated"


class Risk(BaseModel):
    title: str
    severity: str
    detail: str


class MemoryUsed(BaseModel):
    id: str
    kind: str
    text: str
    impact: str
    source_decision_id: str | None = None


class Analysis(BaseModel):
    confidence: int = Field(ge=0, le=100)
    recommendation: str
    experiments: list[str]
    risks: list[Risk]
    memory_used: list[MemoryUsed] = []
    without_memory: str
    with_memory: str


class DecisionCreate(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(min_length=10, max_length=5000)
    category: str = "Product"
    evidence: list[str] = []
    expected_outcome: str | None = None
    constraints: str | None = None


class Decision(DecisionCreate):
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=now)
    status: DecisionStatus = DecisionStatus.PROPOSED
    assumptions: list[Assumption] = []
    analysis: Analysis | None = None


class OutcomeCreate(BaseModel):
    actual_result: str = Field(min_length=5, max_length=5000)
    metrics: dict[str, str | int | float] = {}
    qualitative_feedback: list[str] = []
    expected_result: str | None = None


class Outcome(OutcomeCreate):
    id: str = Field(default_factory=lambda: str(uuid4()))
    decision_id: str
    created_at: datetime = Field(default_factory=now)
    variance: str
    outcome_status: str = "recorded"


class Lesson(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    lesson: str
    source_decision_id: str
    evidence: str
    confidence: int = Field(ge=0, le=100)
    applicability: str
    created_at: datetime = Field(default_factory=now)


class DebateAgentRole(StrEnum):
    SUPPORTER = "supporter"
    OPPOSER = "opposer"
    JUDGE = "judge"


class DebateTurn(BaseModel):
    agent: DebateAgentRole
    round: int = Field(ge=1)
    argument: str
    strongest_point: str = ""
    weaknesses_found: list[str] = []


class DebateVerdict(BaseModel):
    decision: str  # "proceed" | "do_not_proceed" | "proceed_with_changes"
    confidence: int = Field(ge=0, le=100)
    reasoning: str
    conditions: list[str] = []
    memory_influence: str = ""


class DebateCreate(BaseModel):
    topic: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=5000)
    rounds: int = Field(default=2, ge=1, le=3)


class Debate(DebateCreate):
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=now)
    turns: list[DebateTurn] = []
    verdict: DebateVerdict | None = None
    memory_used: list[MemoryUsed] = []
