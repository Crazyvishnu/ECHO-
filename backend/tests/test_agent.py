import pytest
from app.agents.orchestrator import DecisionAgent
from app.domain.models import Decision, MemoryUsed, Outcome


class ScriptedLLM:
    """Deterministic stand-in so tests do not hit a live LLM."""

    def __init__(self, result=None):
        self.result = result

    async def complete_json(self, *, system, user):
        return self.result


class FakeHindsight:
    def __init__(self, memories=None): self.memories = memories or []; self.retained = []
    async def recall(self, query, limit=8): return self.memories[:limit]
    async def retain(self, content, **kwargs): self.retained.append((content, kwargs))


@pytest.mark.asyncio
async def test_historical_lesson_changes_recommendation():
    memory = MemoryUsed(id="lesson-1", kind="experience", text="Resume-builder had 500 trials but 8 paid; job matching demand was stronger.", impact="", source_decision_id="resume")
    agent = DecisionAgent(FakeHindsight([memory]), ScriptedLLM(result={
        "confidence": 61, "recommendation": "Validate willingness to pay with a paid smoke test before building.",
        "experiments": ["Run a paid smoke test"], "risks": [], "memory_impact": "Prior failure shifts validation first.",
    }))
    decision = Decision(title="AI cover letter generator", description="Build a generation tool because users requested it.")
    decision.assumptions = agent.extract_assumptions(decision)
    analysis = await agent.analyze(decision)
    assert analysis.memory_used[0].id == "lesson-1"
    assert analysis.with_memory != analysis.without_memory
    assert "willingness to pay" in analysis.recommendation.lower()


@pytest.mark.asyncio
async def test_outcome_extracts_job_matching_lesson():
    agent = DecisionAgent(FakeHindsight())
    decision = Decision(title="AI Resume Builder", description="Build resumes for students")
    outcome = Outcome(decision_id=decision.id, actual_result="500 tried; 8 paid", metrics={"paid": 8}, qualitative_feedback=["People wanted job matching instead."], variance="Low conversion")
    lessons = await agent.extract_lessons(decision, outcome)
    assert len(lessons) == 2
    assert any("job matching" in lesson.lesson.lower() for lesson in lessons)
