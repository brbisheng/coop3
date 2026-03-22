from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'single_model_perspective_extractor' / 'src'
DEMOS = ROOT / 'demos'
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(DEMOS) not in sys.path:
    sys.path.insert(0, str(DEMOS))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from perspective_extractor.compete import build_competing_mechanisms
from perspective_extractor.decompose import decompose_problem
from perspective_extractor.final import build_final_report
from perspective_extractor.models import (
    AxisCard,
    CompeteResult,
    ControversyCard,
    DecomposeResult,
    FinalReport,
    KnowledgeCard,
    PerspectiveMap,
    PerspectiveNote,
    QuestionCard,
    ReviewDecision,
    StressResult,
    TraceResult,
    VariableCard,
)
from perspective_extractor.stress import build_stress_test
from perspective_extractor.trace import build_trace


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


@dataclass(slots=True)
class Phase1Scenario:
    problem_text: str
    trace_target: str
    decompose_result: DecomposeResult
    trace_result: TraceResult
    compete_result: CompeteResult
    stress_result: StressResult
    final_report: FinalReport


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
def phase1_sample_problem() -> str:
    return (
        "How could a disruption at the main fuel import terminal force shippers, customs, "
        "and regional distributors to reroute through alternate ports and inland pipeline chokepoints "
        "over the next 30 days?"
    )


@pytest.fixture
def phase1_scenario(phase1_sample_problem: str) -> Phase1Scenario:
    trace_target = "Alternate-port rerouting after a fuel terminal disruption"
    decompose_result = decompose_problem(phase1_sample_problem)
    trace_result = build_trace(decompose_result, trace_target=trace_target)
    compete_result = build_competing_mechanisms(decompose_result, trace_result)
    stress_result = build_stress_test(decompose_result, trace_result, compete_result)
    final_report = build_final_report(
        decompose_result,
        trace_result,
        compete_result,
        stress_result,
    )
    return Phase1Scenario(
        problem_text=phase1_sample_problem,
        trace_target=trace_target,
        decompose_result=decompose_result,
        trace_result=trace_result,
        compete_result=compete_result,
        stress_result=stress_result,
        final_report=final_report,
    )


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
            reason="The note is specific, mechanistic, and distinct.",
            verification_question="What evidence would distinguish this mechanism from selection?",
        ),
        ReviewDecision(
            target_note_id="note_boundary",
            action="keep",
            reason="The note adds a concrete boundary condition the first note does not cover.",
            verification_question="What process evidence would show coordination load is the decisive boundary?",
        ),
        ReviewDecision(
            target_note_id="note_focus_duplicate",
            action="merge",
            reason="This note repeats the same mechanism as note_focus with only wording differences.",
            merge_target_note_id="note_focus",
            verification_question="Does the duplicate add any new evidence need or boundary condition?",
        ),
        ReviewDecision(
            target_note_id="note_vague",
            action="rewrite",
            reason="The note is too generic to survive review without a clearer mechanism and boundary.",
            verification_question="What mechanism and boundary condition would make this note decision-useful?",
        ),
    ]
    perspective_map = PerspectiveMap(
        question_id=question_card.question_id,
        kept_notes=[perspective_notes[0], perspective_notes[1]],
        map_id="map_remote_work",
        merged_groups=[["note_focus", "note_focus_duplicate"]],
        evidence_contests=["note_focus:selection-vs-focus-time"],
        boundary_cases=["note_boundary:coordination-load-threshold"],
        final_summary="Remote work affects productivity through distinct focus and coordination pathways.",
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
