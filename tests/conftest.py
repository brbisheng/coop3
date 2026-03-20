from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'single_model_perspective_extractor' / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from perspective_extractor.models import (
    AxisCard,
    ControversyCard,
    KnowledgeCard,
    PerspectiveMap,
    PerspectiveNote,
    QuestionCard,
    ReviewDecision,
    VariableCard,
)


@dataclass(slots=True)
class FixedPipelineScenario:
    question_card: QuestionCard
    knowledge_cards: list[KnowledgeCard]
    variable_cards: list[VariableCard]
    controversy_cards: list[ControversyCard]
    axis_cards: list[AxisCard]
    perspective_notes: list[PerspectiveNote]
    review_decisions: list[ReviewDecision]
    perspective_map: PerspectiveMap


class MockPipelineResponder:
    """Deterministic stage responder used to avoid live-model variability in tests."""

    def __init__(self, scenario: FixedPipelineScenario) -> None:
        self.scenario = scenario
        self.call_log: list[str] = []

    def normalize(self, question: str) -> QuestionCard:
        self.call_log.append(f"normalize:{question}")
        return self.scenario.question_card

    def knowledge(self, question_card: QuestionCard) -> list[KnowledgeCard]:
        assert question_card is self.scenario.question_card
        self.call_log.append("knowledge")
        return self.scenario.knowledge_cards

    def variable(self, question_card: QuestionCard) -> list[VariableCard]:
        assert question_card is self.scenario.question_card
        self.call_log.append("variable")
        return self.scenario.variable_cards

    def controversy(self, question_card: QuestionCard) -> list[ControversyCard]:
        assert question_card is self.scenario.question_card
        self.call_log.append("controversy")
        return self.scenario.controversy_cards

    def axes(self, question_card: QuestionCard, **kwargs: object) -> list[AxisCard]:
        assert question_card is self.scenario.question_card
        assert kwargs["knowledge_cards"] is self.scenario.knowledge_cards
        assert kwargs["variable_cards"] is self.scenario.variable_cards
        assert kwargs["controversy_cards"] is self.scenario.controversy_cards
        self.call_log.append("axes")
        return self.scenario.axis_cards

    def expand(self, axis_cards: list[AxisCard], question_card: QuestionCard, **kwargs: object) -> list[PerspectiveNote]:
        assert axis_cards is self.scenario.axis_cards
        assert question_card is self.scenario.question_card
        assert kwargs["knowledge_cards"] is self.scenario.knowledge_cards
        assert kwargs["variable_cards"] is self.scenario.variable_cards
        assert kwargs["controversy_cards"] is self.scenario.controversy_cards
        self.call_log.append("expand")
        return self.scenario.perspective_notes

    def review(self, question_card: QuestionCard, notes: list[PerspectiveNote]) -> list[ReviewDecision]:
        assert question_card is self.scenario.question_card
        assert notes is self.scenario.perspective_notes
        self.call_log.append("review")
        return self.scenario.review_decisions

    def build_map(
        self,
        question_card: QuestionCard,
        kept_notes: list[PerspectiveNote],
        review_decisions: list[ReviewDecision],
    ) -> PerspectiveMap:
        assert question_card is self.scenario.question_card
        assert [note.note_id for note in kept_notes] == ["note_focus", "note_boundary"]
        assert review_decisions is self.scenario.review_decisions
        self.call_log.append("synthesize")
        return self.scenario.perspective_map


@pytest.fixture
def fixed_pipeline_scenario() -> FixedPipelineScenario:
    question_card = QuestionCard(
        question_id="question_remote_work",
        raw_question="How does remote work affect employee productivity?",
        cleaned_question="How does remote work affect employee productivity?",
        actor_entity="remote work",
        outcome_variable="employee productivity",
        domain_hint="business",
        assumptions=["Productivity can be observed at team and individual levels."],
        keywords=["remote work", "productivity"],
        missing_pieces=["Which teams rely on synchronous coordination?"],
    )
    knowledge_cards = [
        KnowledgeCard(
            knowledge_id="knowledge_focus",
            title="Focus-time mechanism",
            content="Remote work can change focus time by reducing office interruptions and commute fatigue.",
        ),
        KnowledgeCard(
            knowledge_id="knowledge_coordination",
            title="Coordination friction",
            content="Remote work can slow handoffs when work depends on rapid synchronous coordination.",
        ),
    ]
    variable_cards = [
        VariableCard(
            variable_id="variable_actor",
            name="remote work intensity",
            variable_role="actor",
            definition="How often work is performed away from the office.",
        ),
        VariableCard(
            variable_id="variable_outcome",
            name="employee productivity",
            variable_role="outcome",
            definition="Observable output, quality, or throughput per worker.",
        ),
        VariableCard(
            variable_id="variable_scope",
            name="coordination load",
            variable_role="constraint",
            definition="How much the work depends on fast interdependent coordination.",
        ),
    ]
    controversy_cards = [
        ControversyCard(
            controversy_id="controversy_selection",
            question="Are observed productivity gains caused by remote work or by worker selection?",
            sides=["causal change", "selection effect"],
        )
    ]
    axis_cards = [
        AxisCard(
            axis_id="axis_focus",
            name="focus-time pathway",
            axis_type="mechanism",
            focus="Track whether regained focus time translates into higher output.",
            how_is_it_distinct="Separates attention and time-allocation mechanisms from coordination constraints.",
            supporting_card_ids=[
                "knowledge_focus",
                "variable_actor",
                "variable_outcome",
            ],
        ),
        AxisCard(
            axis_id="axis_boundary",
            name="coordination boundary",
            axis_type="scope",
            focus="Test when remote work breaks down because coordination load is high.",
            how_is_it_distinct="Focuses on boundary conditions instead of average treatment effects.",
            supporting_card_ids=[
                "knowledge_coordination",
                "variable_scope",
                "controversy_selection",
            ],
        ),
    ]
    perspective_notes = [
        PerspectiveNote(
            note_id="note_focus",
            axis_id="axis_focus",
            core_claim="Remote work can raise productivity when it turns commute savings into sustained focus blocks.",
            reasoning="The mechanism depends on converting time and energy savings into uninterrupted execution time.",
            counterexample="The gain can disappear when workers spend the saved time on fragmented household interruptions.",
            boundary_condition="This note is strongest in roles that can batch deep work with limited coordination overhead.",
            evidence_needed=[
                "Measure whether commute time saved becomes uninterrupted focus time.",
                "Compare output changes for workers with high versus low pre-remote commute burdens.",
            ],
            testable_implication="Workers with longer baseline commutes should gain more productivity after shifting remote.",
            verification_question="Does focus time mediate the productivity change once worker selection is controlled?",
            supporting_card_ids=["knowledge_focus", "variable_actor", "variable_outcome"],
        ),
        PerspectiveNote(
            note_id="note_boundary",
            axis_id="axis_boundary",
            core_claim="Remote work can reduce productivity when coordination-heavy teams lose fast handoffs and managerial visibility.",
            reasoning="Coordination-intensive workflows depend on high-frequency feedback loops that remote settings can slow.",
            counterexample="Teams with strong asynchronous routines may preserve productivity despite remote work.",
            boundary_condition="This note matters most for interdependent teams with weak process discipline.",
            evidence_needed=[
                "Compare output changes across teams with different coordination loads.",
                "Measure whether handoff delay and check-in quality change after moving remote.",
            ],
            testable_implication="Teams with weak asynchronous processes should show larger productivity declines after moving remote.",
            verification_question="When coordination load is high, do handoff delays explain the productivity decline better than selection?",
            supporting_card_ids=["knowledge_coordination", "variable_scope", "controversy_selection"],
        ),
        PerspectiveNote(
            note_id="note_focus_duplicate",
            axis_id="axis_focus",
            core_claim="Remote work can raise productivity when commute savings become longer focus blocks.",
            reasoning="This restates the focus-time mechanism without adding a new structure.",
            counterexample="Fragmented home interruptions can erase the gains.",
            boundary_condition="Applies mostly to work that can be done asynchronously.",
            evidence_needed=[
                "Measure whether commute time saved becomes uninterrupted focus time.",
                "Compare output changes for workers with high versus low pre-remote commute burdens.",
            ],
            testable_implication="Workers with longer baseline commutes should gain more productivity after shifting remote.",
            verification_question="Does focus time mediate the productivity change once worker selection is controlled?",
            supporting_card_ids=["knowledge_focus", "variable_actor", "variable_outcome"],
        ),
        PerspectiveNote(
            note_id="note_vague",
            axis_id="axis_boundary",
            core_claim="Remote work matters in some settings.",
            reasoning="Intentionally generic note used to exercise rewrite handling.",
            counterexample="Other things matter too.",
            boundary_condition="It depends.",
            evidence_needed=["Need better evidence."],
            testable_implication="Results could vary.",
            verification_question="What evidence matters here?",
            supporting_card_ids=["knowledge_coordination"],
        ),
    ]
    review_decisions = [
        ReviewDecision(
            target_note_id="note_focus",
            action="keep",
            reason="Mechanism note remains structurally distinct.",
            verification_question=perspective_notes[0].verification_question,
        ),
        ReviewDecision(
            target_note_id="note_boundary",
            action="keep",
            reason="Boundary-condition note captures a distinct scope lens.",
            verification_question=perspective_notes[1].verification_question,
        ),
        ReviewDecision(
            target_note_id="note_focus_duplicate",
            action="merge",
            reason="Shares the same mechanism, evidence structure, and verification question as note_focus.",
            merge_target_note_id="note_focus",
            verification_question=perspective_notes[2].verification_question,
        ),
        ReviewDecision(
            target_note_id="note_vague",
            action="rewrite",
            reason="Generic note lacks enough anchored structure to keep as-is.",
            verification_question=perspective_notes[3].verification_question,
        ),
    ]
    perspective_map = PerspectiveMap(
        map_id="map_remote_work",
        question_id=question_card.question_id,
        kept_notes=[perspective_notes[0], perspective_notes[1]],
        merged_groups=[["note_focus", "note_focus_duplicate"]],
        evidence_contests=[
            "note_focus vs note_boundary: distinguish time-allocation gains from coordination breakdown losses.",
            f"note_focus: {perspective_notes[0].verification_question}",
            f"note_boundary: {perspective_notes[1].verification_question}",
        ],
        boundary_cases=[
            f"note_focus: {perspective_notes[0].boundary_condition}",
            f"note_boundary: {perspective_notes[1].boundary_condition}",
        ],
        final_summary="Structured summary with two kept notes, one merge, and one rewrite.",
    )
    return FixedPipelineScenario(
        question_card=question_card,
        knowledge_cards=knowledge_cards,
        variable_cards=variable_cards,
        controversy_cards=controversy_cards,
        axis_cards=axis_cards,
        perspective_notes=perspective_notes,
        review_decisions=review_decisions,
        perspective_map=perspective_map,
    )


@pytest.fixture
def mock_pipeline_responder(fixed_pipeline_scenario: FixedPipelineScenario) -> MockPipelineResponder:
    return MockPipelineResponder(fixed_pipeline_scenario)
