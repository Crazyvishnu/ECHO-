import re
from app.domain.models import Analysis, Assumption, Decision, Lesson, MemoryUsed, Outcome, Risk
from app.agents.prompts import DECISION_ANALYSIS
from app.llm.openai_compatible import OpenAICompatibleLLM
from app.memory.hindsight import MemoryGateway


def _concepts(text: str) -> str:
    return " ".join(re.findall(r"[A-Za-z]{4,}", text.lower())[:24])


class DecisionAgent:
    def __init__(self, memory: MemoryGateway, llm: OpenAICompatibleLLM | None = None) -> None:
        self.memory = memory
        self.llm = llm or OpenAICompatibleLLM()

    def extract_assumptions(self, decision: Decision) -> list[Assumption]:
        topic = decision.title.lower()
        evidence = decision.evidence or ["No direct evidence supplied yet."]
        return [
            Assumption(statement=f"The target audience has a recurring problem that {topic} addresses.", confidence=58, importance="high", supporting_evidence=evidence, contradicting_evidence=[], validation_method="Run 8-12 customer interviews focused on current workarounds."),
            Assumption(statement="Interest will translate into willingness to change behavior or pay.", confidence=42, importance="high", supporting_evidence=evidence, contradicting_evidence=[], validation_method="Test a priced landing page before building the full product."),
            Assumption(statement="The proposed solution is the highest-value way to solve the problem.", confidence=48, importance="medium", supporting_evidence=evidence, contradicting_evidence=[], validation_method="Compare this concept with alternative workflows in a prototype test."),
        ]

    async def analyze(self, decision: Decision) -> Analysis:
        memories = await self.memory.recall(f"{decision.title}. {decision.description}. {_concepts(decision.description)}")
        for memory in memories:
            memory.impact = "This memory changes the confidence and validation sequence because it contains comparable evidence."
        baseline = "Validate the problem with interviews, then build a narrow prototype and measure activation."
        memory_summary = "No relevant historical outcomes were retrieved; keep the first validation focused on the riskiest assumption."
        if memories:
            memory_summary = "Relevant Hindsight memories point to prior evidence. Validate willingness to pay and problem intensity before committing development effort."
        model_result = await self.llm.complete_json(
            system=DECISION_ANALYSIS,
            user=(f"CURRENT DECISION\nTitle: {decision.title}\nDescription: {decision.description}\n"
                  f"Current evidence: {decision.evidence}\nAssumptions: {[a.statement for a in decision.assumptions]}\n"
                  f"HISTORICAL HINDSIGHT MEMORY\n{[m.text for m in memories]}"),
        )
        if model_result:
            try:
                risks = [Risk(**risk) for risk in model_result["risks"]][:3]
                return Analysis(
                    confidence=max(0, min(100, int(model_result["confidence"]))),
                    recommendation=str(model_result["recommendation"]),
                    experiments=[str(item) for item in model_result["experiments"]][:3],
                    risks=risks,
                    memory_used=memories,
                    without_memory=baseline,
                    with_memory=str(model_result["memory_impact"]),
                )
            except (KeyError, TypeError, ValueError):
                pass
        return Analysis(
            confidence=46 if memories else 54,
            recommendation="Validate willingness to pay with a paid smoke test and five problem interviews before allocating a build sprint." if memories else "Run five problem interviews and a narrow prototype test before a build sprint.",
            experiments=["Launch a problem-first landing page with a clear price signal.", "Interview 8 target users about current alternatives and urgency.", "Test the smallest workflow prototype with success metrics agreed in advance."],
            risks=[Risk(title="Weak willingness to pay", severity="high", detail="Stated interest can differ sharply from payment behavior."), Risk(title="Solution-first framing", severity="medium", detail="The chosen format may not address the most urgent workflow."), Risk(title="Evidence gap", severity="medium", detail="Current evidence needs direct behavioral validation.")],
            memory_used=memories, without_memory=baseline, with_memory=memory_summary,
        )

    async def extract_lessons(self, decision: Decision, outcome: Outcome) -> list[Lesson]:
        feedback = " ".join(outcome.qualitative_feedback).lower()
        lessons = [Lesson(lesson="User interest should be validated separately from willingness to pay.", source_decision_id=decision.id, evidence=outcome.actual_result, confidence=90, applicability="Use for any new product concept with early signup or trial signals.")]
        if "job match" in feedback or "matching" in feedback:
            lessons.append(Lesson(lesson="Users signaled stronger demand for job matching than document generation.", source_decision_id=decision.id, evidence="; ".join(outcome.qualitative_feedback), confidence=88, applicability="Prioritize workflow demand before expanding adjacent generation features."))
        return lessons
