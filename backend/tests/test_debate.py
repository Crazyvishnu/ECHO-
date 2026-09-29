import pytest

from app.agents.debate import DebateOrchestrator
from app.domain.models import DebateVerdict, MemoryUsed


class FakeMemory:
    def __init__(self, memories=None):
        self.memories = memories or []
        self.retained = []

    async def recall(self, query, limit=8):
        return self.memories[:limit]

    async def retain(self, content, **kwargs):
        self.retained.append((content, kwargs))


class FakeLLM:
    """Scripted LLM: returns queued responses, then fails (exercising fallbacks)."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def complete_json(self, *, system, user):
        self.calls.append((system, user))
        if self.responses:
            return self.responses.pop(0)
        return None


@pytest.mark.asyncio
async def test_debate_runs_all_roles_and_verdict():
    llm = FakeLLM([
        {"argument": "It will work because demand is proven.", "strongest_point": "Proven demand", "weaknesses_found": []},
        {"argument": "It will fail on hidden costs.", "strongest_point": "Hidden costs", "weaknesses_found": ["unpriced migration"]},
        {"argument": "Round two for the proposal.", "strongest_point": "", "weaknesses_found": []},
        {"argument": "Round two against.", "strongest_point": "", "weaknesses_found": []},
        {"decision": "proceed", "confidence": 72, "reasoning": "Supporter carried the evidence burden.", "conditions": ["Ship behind a flag"], "memory_influence": ""},
    ])
    memory = FakeMemory()
    debate = await DebateOrchestrator(memory, llm).run("Launch X", "A test proposal for the debate.", rounds=2)
    assert [t.agent for t in debate.turns] == ["supporter", "opposer", "supporter", "opposer"]
    assert debate.verdict is not None
    assert debate.verdict.decision == "proceed"
    assert debate.verdict.confidence == 72
    assert debate.turns[0].argument == "It will work because demand is proven."


@pytest.mark.asyncio
async def test_debate_falls_back_when_llm_unavailable():
    memory = FakeMemory()
    debate = await DebateOrchestrator(memory, FakeLLM([])).run("Launch Y", "Another proposal description here.", rounds=1)
    assert len(debate.turns) == 2
    assert all("Case" in t.argument for t in debate.turns)
    assert isinstance(debate.verdict, DebateVerdict)
    assert debate.verdict.decision in {"proceed", "proceed_with_changes", "do_not_proceed"}


@pytest.mark.asyncio
async def test_debate_uses_recalled_memory():
    memory = FakeMemory([MemoryUsed(id="m1", kind="experience", text="Similar launch failed", impact="")])
    debate = await DebateOrchestrator(memory, FakeLLM([])).run("Launch Z", "A third proposal for testing.", rounds=1)
    assert debate.memory_used[0].id == "m1"
    # Fallback judge condition should reference past lessons when memories exist
    assert any("lesson" in c.lower() for c in debate.verdict.conditions)
