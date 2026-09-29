import logging
import asyncio

from fastapi import APIRouter, HTTPException, status
from app.agents.orchestrator import DecisionAgent
from app.agents.debate import DebateOrchestrator
from app.config import settings
from app.domain.models import Decision, DecisionCreate, Debate, DebateCreate, DecisionStatus, Outcome, OutcomeCreate
from app.memory.hindsight import HindsightGateway, MemoryUnavailable
from app.services.repository import Repository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")
repo = Repository()
memory = HindsightGateway()
agent = DecisionAgent(memory)
debate_agent = DebateOrchestrator(memory)
_DEBATES: dict[str, Debate] = {}


def _retain_debate_memory(debate: Debate) -> None:
    """Persist the debate and its verdict to Hindsight so future debates learn from it."""
    turns = "\n".join(f"{t.agent.upper()} (round {t.round}): {t.argument}" for t in debate.turns)
    verdict = debate.verdict
    content = (
        f"DEBATE: {debate.topic}\nPROPOSAL: {debate.description}\n"
        f"TRANSCRIPT:\n{turns}\n"
        f"VERDICT: {verdict.decision} (confidence {verdict.confidence})\n"
        f"REASONING: {verdict.reasoning}\n"
        f"CONDITIONS: {' | '.join(verdict.conditions)}"
    )
    asyncio.create_task(memory.retain(
        content, context="product decision debate",
        document_id=f"debate-{debate.id}",
        metadata={"kind": "debate", "decision": verdict.decision},
    ))
    asyncio.create_task(memory.retain(
        f"DEBATE LESSON: {verdict.reasoning}", context="validated debate lesson",
        document_id=f"debate-lesson-{debate.id}",
        metadata={"kind": "debate_lesson", "decision": verdict.decision},
    ))


async def retain_decision(decision: Decision) -> None:
    await memory.retain(f"DECISION: {decision.title}\nDESCRIPTION: {decision.description}\nASSUMPTIONS: " + " | ".join(a.statement for a in decision.assumptions) + f"\nRECOMMENDATION: {decision.analysis.recommendation if decision.analysis else ''}", context="product decision analysis", document_id=f"decision-{decision.id}", metadata={"kind": "decision", "decision_id": decision.id})


@router.get("/health")
async def health():
    return {"status": "ok", "memory": "configured" if settings.hindsight_api_key else "unavailable"}


@router.get("/decisions")
async def list_decisions():
    return list(repo.decisions.values())


@router.post("/decisions", status_code=status.HTTP_201_CREATED)
async def create_decision(payload: DecisionCreate):
    decision = repo.add_decision(Decision(**payload.model_dump()))
    return decision


@router.get("/decisions/{decision_id}")
async def get_decision(decision_id: str):
    decision = repo.get_decision(decision_id)
    if not decision: raise HTTPException(404, "Decision not found.")
    return {"decision": decision, "outcome": repo.decision_outcome(decision_id), "lessons": repo.lessons_for(decision_id)}


@router.post("/decisions/{decision_id}/analyze")
async def analyze_decision(decision_id: str):
    decision = repo.get_decision(decision_id)
    if not decision: raise HTTPException(404, "Decision not found.")
    decision.assumptions = agent.extract_assumptions(decision)
    try:
        decision.analysis = await agent.analyze(decision)
        await retain_decision(decision)
    except MemoryUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    logger.info("Decision analyzed and stored in Hindsight", extra={"decision_id": decision.id})
    return decision


@router.post("/decisions/{decision_id}/outcome")
async def record_outcome(decision_id: str, payload: OutcomeCreate):
    decision = repo.get_decision(decision_id)
    if not decision: raise HTTPException(404, "Decision not found.")
    if repo.decision_outcome(decision_id): raise HTTPException(409, "An outcome is already recorded for this decision.")
    outcome = Outcome(decision_id=decision_id, variance="Observed outcome compared against the original prediction.", **payload.model_dump())
    lessons = await agent.extract_lessons(decision, outcome)
    try:
        await memory.retain(f"OUTCOME for {decision.title}: {outcome.actual_result}\nMETRICS: {outcome.metrics}\nFEEDBACK: {outcome.qualitative_feedback}", context="product decision outcome", document_id=f"outcome-{decision.id}", metadata={"kind": "outcome", "decision_id": decision.id})
        for lesson in lessons:
            await memory.retain(f"LESSON: {lesson.lesson}\nEVIDENCE: {lesson.evidence}\nAPPLICABILITY: {lesson.applicability}", context="validated decision lesson", document_id=f"lesson-{lesson.id}", metadata={"kind": "lesson", "decision_id": decision.id})
    except MemoryUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    repo.add_outcome(outcome)
    for lesson in lessons: repo.lessons[lesson.id] = lesson
    decision.status = DecisionStatus.COMPLETED
    return {"outcome": outcome, "lessons": lessons}


@router.get("/memory/recent")
async def recent_memory(query: str = "recent product decisions and outcomes"):
    try: return await memory.recall(query)
    except MemoryUnavailable as exc: raise HTTPException(503, str(exc)) from exc


@router.get("/debates")
async def list_debates():
    return list(_DEBATES.values())


@router.post("/debates", status_code=status.HTTP_201_CREATED)
async def create_debate(payload: DebateCreate):
    try:
        debate = await debate_agent.run(payload.topic, payload.description, payload.rounds)
    except MemoryUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    _DEBATES[debate.id] = debate
    _retain_debate_memory(debate)
    logger.info("Debate '%s' stored and retained to Hindsight", debate.topic)
    return debate


@router.post("/demo/load")
async def load_demo():
    decision = repo.add_decision(Decision(title="Launch an AI resume builder for college students", description="Create an AI resume builder for college students seeking internships and first jobs.", evidence=["Students say resume writing is stressful."], expected_outcome="Strong student demand and willingness to pay."))
    decision.assumptions = agent.extract_assumptions(decision)
    decision.analysis = await agent.analyze(decision)
    await retain_decision(decision)
    outcome = Outcome(decision_id=decision.id, actual_result="500 users tried the product but only 8 paid.", metrics={"trials": 500, "paid": 8, "conversion_pct": 1.6}, qualitative_feedback=["Users wanted job matching rather than resume generation."], expected_result="Strong willingness to pay.", variance="High trial activity did not convert into paid demand.")
    lessons = await agent.extract_lessons(decision, outcome)
    await memory.retain(f"OUTCOME for AI Resume Builder: {outcome.actual_result}\nFEEDBACK: {outcome.qualitative_feedback}", context="product decision outcome", document_id=f"outcome-{decision.id}", metadata={"kind": "outcome", "decision_id": decision.id})
    for lesson in lessons:
        await memory.retain(f"LESSON: {lesson.lesson}\nEVIDENCE: {lesson.evidence}", context="validated decision lesson", document_id=f"lesson-{lesson.id}", metadata={"kind": "lesson", "decision_id": decision.id})
        repo.lessons[lesson.id] = lesson
    repo.add_outcome(outcome); decision.status = DecisionStatus.COMPLETED
    return {"decision": decision, "outcome": outcome, "lessons": lessons}
