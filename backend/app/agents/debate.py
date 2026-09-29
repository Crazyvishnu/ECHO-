"""Three-agent debate: SUPPORTER argues for, OPPOSER argues against, JUDGE rules.

Past debate lessons and outcomes are recalled from long-term memory before the
debate starts and the verdict is retained afterwards, so each debate improves
the next one.
"""
import logging

from app.agents.prompts import JUDGE, OPPOSER, SUPPORTER
from app.domain.models import Debate, DebateTurn, MemoryUsed
from app.llm.openai_compatible import OpenAICompatibleLLM
from app.memory.hindsight import MemoryGateway

logger = logging.getLogger(__name__)


def _transcript(turns: list[DebateTurn]) -> str:
    if not turns:
        return "(The debate has not started; you open it.)"
    return "\n".join(f"ROUND {t.round} {t.agent.upper()}: {t.argument}" for t in turns)


def _memories_block(memories: list[MemoryUsed]) -> str:
    if not memories:
        return "No relevant historical memories were found. Argue from the proposal alone."
    return "\n".join(f"- ({m.kind}) {m.text}" for m in memories)


class DebateOrchestrator:
    def __init__(self, memory: MemoryGateway, llm: OpenAICompatibleLLM | None = None) -> None:
        self.memory = memory
        self.llm = llm or OpenAICompatibleLLM()

    async def run(self, topic: str, description: str, rounds: int = 2) -> Debate:
        memories = await self.memory.recall(f"{topic}. {description}")
        debate = Debate(topic=topic, description=description, rounds=rounds, memory_used=memories)
        memories_block = _memories_block(memories)
        proposal = f"TOPIC: {topic}\nPROPOSAL: {description}"

        for round_number in range(1, rounds + 1):
            supporter = await self._speak(
                SUPPORTER, proposal, memories_block, debate.turns, round_number, "supporter",
                fallback=f"Case for: {description} The evidence supplied and any comparable past wins in memory suggest real upside; the weakest point is whether demand survives contact with real users.",
            )
            debate.turns.append(supporter)
            opposer = await self._speak(
                OPPOSER, proposal, memories_block, debate.turns, round_number, "opposer",
                fallback=f"Case against: the proposal rests on unvalidated assumptions. Comparable past attempts in memory (if any) show stated interest often fails to convert; execution and hidden costs are unpriced.",
            )
            debate.turns.append(opposer)

        debate.verdict = await self._judge(proposal, memories_block, debate.turns, memories)
        logger.info("Debate '%s' completed with verdict '%s'", topic, debate.verdict.decision)
        return debate

    async def _speak(
        self, system: str, proposal: str, memories_block: str,
        turns: list[DebateTurn], round_number: int, role: str, fallback: str,
    ) -> DebateTurn:
        result = await self.llm.complete_json(
            system=system,
            user=(f"{proposal}\n\nHISTORICAL MEMORY\n{memories_block}\n\n"
                  f"DEBATE SO FAR\n{_transcript(turns)}\n\nIt is round {round_number}; "
                  f"give your strongest {role} turn now."),
        )
        if result and isinstance(result.get("argument"), str):
            return DebateTurn(
                agent=role,  # type: ignore[arg-type]
                round=round_number,
                argument=str(result["argument"]),
                strongest_point=str(result.get("strongest_point", "")),
                weaknesses_found=[str(w) for w in result.get("weaknesses_found", [])][:4],
            )
        return DebateTurn(agent=role, round=round_number, argument=fallback, strongest_point="")  # type: ignore[arg-type]

    async def _judge(self, proposal: str, memories_block: str, turns: list[DebateTurn], memories: list[MemoryUsed]) -> "object":
        result = await self.llm.complete_json(
            system=JUDGE,
            user=(f"{proposal}\n\nHISTORICAL MEMORY\n{memories_block}\n\nFULL TRANSCRIPT\n{_transcript(turns)}\n\nRule on the debate now."),
        )
        from app.domain.models import DebateVerdict

        if result and isinstance(result.get("decision"), str) and result["decision"] in {"proceed", "proceed_with_changes", "do_not_proceed"}:
            try:
                return DebateVerdict(
                    decision=str(result["decision"]),
                    confidence=max(0, min(100, int(result.get("confidence", 50)))),
                    reasoning=str(result.get("reasoning", "")),
                    conditions=[str(c) for c in result.get("conditions", [])][:4],
                    memory_influence=str(result.get("memory_influence", "")),
                )
            except (TypeError, ValueError):
                pass
        conditions = ["Run a cheap validation of the riskiest assumption before committing build effort."]
        if memories:
            conditions.insert(0, "Review the cited past lessons and address the failure pattern they describe.")
        return DebateVerdict(
            decision="proceed_with_changes",
            confidence=48,
            reasoning="The LLM judge was unavailable, so this is a neutral default: proceed only after the riskiest assumption is validated cheaply.",
            conditions=conditions,
            memory_influence="Historical memory was retrieved; treat cited lessons as conditions to clear.",
        )
