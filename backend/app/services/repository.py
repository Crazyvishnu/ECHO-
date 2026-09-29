from app.domain.models import Decision, Outcome, Lesson


class Repository:
    def __init__(self) -> None:
        self.decisions: dict[str, Decision] = {}
        self.outcomes: dict[str, Outcome] = {}
        self.lessons: dict[str, Lesson] = {}

    def add_decision(self, decision: Decision) -> Decision:
        self.decisions[decision.id] = decision
        return decision

    def get_decision(self, decision_id: str) -> Decision | None:
        return self.decisions.get(decision_id)

    def add_outcome(self, outcome: Outcome) -> Outcome:
        self.outcomes[outcome.decision_id] = outcome
        return outcome

    def decision_outcome(self, decision_id: str) -> Outcome | None:
        return self.outcomes.get(decision_id)

    def lessons_for(self, decision_id: str) -> list[Lesson]:
        return [lesson for lesson in self.lessons.values() if lesson.source_decision_id == decision_id]
