"""End-to-end pipeline orchestration with a phase-1 primary path and legacy compatibility flow."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import asdict
import json
from pathlib import Path
from datetime import datetime, timezone

from .models import (
    AxisCard,
    CompeteResult,
    ControversyCard,
    DecomposeResult,
    FinalReport,
    KnowledgeCard,
    PerspectiveMap,
    PerspectiveNote,
    PerspectiveRecord,
    PipelineInput,
    PipelineResult,
    QuestionCard,
    ReviewDecision,
    StressResult,
    TraceResult,
    VariableCard,
)
from .decompose import decompose_problem, run_decompose
from .trace import build_trace, run_trace
from .compete import build_competing_mechanisms, run_compete
from .stress import build_stress_test, run_stress
from .final import build_final_report, run_final
from .normalize import normalize_question, normalize_text
from .knowledge import (
    collect_background,
    generate_controversy_cards,
    generate_knowledge_cards,
    generate_variable_cards,
)
from .legacy.review import review_notes as review_note_decisions, review_records
from .legacy.synthesize import synthesize_map, synthesize_summary
from .legacy.axes import generate_axes
from .legacy.expand import expand_axis as expand_axis_note
from .prompts import PromptVariant, resolve_prompt_variant
from .evaluate import EvaluationResult, evaluate_phase1_artifacts
from .improve import PromptPatchBundle, build_prompt_patch_from_failure_flags
from .policy import PolicyVersion


@dataclass(frozen=True, slots=True)
class DecomposeArtifacts:
    """Artifacts produced by problem decomposition."""

    question_card: QuestionCard
    knowledge_cards: list[KnowledgeCard]
    variable_cards: list[VariableCard]
    controversy_cards: list[ControversyCard]


@dataclass(frozen=True, slots=True)
class TraceArtifacts:
    """Artifacts produced while tracing decomposition outputs through a target."""

    trace_target: str
    axis_cards: list[AxisCard]
    perspective_notes: list[PerspectiveNote]


@dataclass(frozen=True, slots=True)
class CompeteArtifacts:
    """Artifacts produced while comparing traced candidates."""

    review_decisions: list[ReviewDecision]
    notes_by_action: dict[str, list[PerspectiveNote]]


@dataclass(frozen=True, slots=True)
class StressArtifacts:
    """Artifacts produced while stress-testing the competing candidates."""

    kept_notes: list[PerspectiveNote]
    merged_notes: list[PerspectiveNote]
    rewrite_notes: list[PerspectiveNote]
    dropped_notes: list[PerspectiveNote]
    perspective_map: PerspectiveMap


@dataclass(frozen=True, slots=True)
class PipelineArtifacts:
    """Full artifact bundle for the new default execution order."""

    decompose_output: DecomposeArtifacts
    trace_output: TraceArtifacts
    compete_output: CompeteArtifacts
    stress_output: StressArtifacts


@dataclass(frozen=True, slots=True)
class Phase1PipelineArtifacts:
    """Artifact bundle for the dedicated phase-1 reasoning path."""

    decompose_result: DecomposeResult
    trace_result: TraceResult
    compete_result: CompeteResult
    stress_result: StressResult
    final_report: FinalReport
    round_evaluations: list[EvaluationResult]
    run_id: str
    output_root: str


def _card_id(card: KnowledgeCard | VariableCard | ControversyCard) -> str:
    if isinstance(card, KnowledgeCard):
        return card.knowledge_id
    if isinstance(card, VariableCard):
        return card.variable_id
    return card.controversy_id


def _card_label(card: KnowledgeCard | VariableCard | ControversyCard) -> str:
    if isinstance(card, KnowledgeCard):
        return card.title
    if isinstance(card, VariableCard):
        return f"{card.variable_role}:{card.name}"
    return card.question


def _unique_card_ids(*card_groups: list[KnowledgeCard | VariableCard | ControversyCard]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for group in card_groups:
        for card in group:
            card_identifier = _card_id(card)
            if card_identifier not in seen:
                seen.add(card_identifier)
                ordered.append(card_identifier)
    return ordered


def _summarize_supporting_cards(
    *,
    knowledge_cards: list[KnowledgeCard] | None = None,
    variable_cards: list[VariableCard] | None = None,
    controversy_cards: list[ControversyCard] | None = None,
) -> list[str]:
    summary: list[str] = []
    for label, cards in (
        ("knowledge", knowledge_cards or []),
        ("variable", variable_cards or []),
        ("controversy", controversy_cards or []),
    ):
        if cards:
            summary.append(
                f"{label} support: " + ", ".join(_card_label(card) for card in cards[:2])
            )
    return summary


def _note_id_for_axis(axis_id: str) -> str:
    """Derive a deterministic note identifier for a given axis identifier."""

    if axis_id.startswith("axis_"):
        return f"note_{axis_id[5:]}"
    return f"note_{axis_id}"


@dataclass(frozen=True, slots=True)
class PipelinePromptConfig:
    """Reserved prompt/lens options for forward-compatible pipeline entrypoints."""

    prompt_variant: PromptVariant | None = None
    lens: PromptVariant | None = None

    @property
    def resolved_prompt_variant(self) -> PromptVariant | None:
        """Return the validated prompt variant selected for this pipeline run."""

        return resolve_prompt_variant(prompt_variant=self.prompt_variant, lens=self.lens)



def _select_axis_context_cards(
    axis_card: AxisCard,
    *,
    knowledge_cards: list[KnowledgeCard] | None = None,
    variable_cards: list[VariableCard] | None = None,
    controversy_cards: list[ControversyCard] | None = None,
) -> list[KnowledgeCard | VariableCard | ControversyCard]:
    """Return only the supporting cards assigned to the current axis."""

    ordered_cards: list[KnowledgeCard | VariableCard | ControversyCard] = [
        *(knowledge_cards or []),
        *(variable_cards or []),
        *(controversy_cards or []),
    ]
    if not axis_card.supporting_card_ids:
        return []

    card_lookup = {_card_id(card): card for card in ordered_cards}
    return [
        card_lookup[card_id]
        for card_id in axis_card.supporting_card_ids
        if card_id in card_lookup
    ]



def expand_axis(
    axis_card: AxisCard,
    question_card: QuestionCard,
    *,
    knowledge_cards: list[KnowledgeCard] | None = None,
    variable_cards: list[VariableCard] | None = None,
    controversy_cards: list[ControversyCard] | None = None,
) -> list[PerspectiveNote]:
    """Expand one axis into an isolated traceable perspective note."""

    note = expand_axis_note(
        question_card,
        axis_card,
        context_cards=_select_axis_context_cards(
            axis_card,
            knowledge_cards=knowledge_cards,
            variable_cards=variable_cards,
            controversy_cards=controversy_cards,
        ),
    )
    note.note_id = _note_id_for_axis(axis_card.axis_id)
    return [note]



def expand_axes(
    axis_cards: list[AxisCard],
    question_card: QuestionCard,
    *,
    knowledge_cards: list[KnowledgeCard] | None = None,
    variable_cards: list[VariableCard] | None = None,
    controversy_cards: list[ControversyCard] | None = None,
) -> list[PerspectiveNote]:
    """Expand all axes independently and return the raw PerspectiveNote list."""

    perspective_notes: list[PerspectiveNote] = []
    for axis_card in axis_cards:
        perspective_notes.extend(
            expand_axis(
                axis_card,
                question_card,
                knowledge_cards=knowledge_cards,
                variable_cards=variable_cards,
                controversy_cards=controversy_cards,
            )
        )
    return perspective_notes



def review_notes(question_card: QuestionCard, notes: list[PerspectiveNote]) -> list[ReviewDecision]:
    """Review expanded notes for overlap, novelty, and rewrite needs."""

    return review_note_decisions(question_card, notes)



def build_perspective_map(
    question_card: QuestionCard,
    kept_notes: list[PerspectiveNote],
    review_decisions: list[ReviewDecision],
) -> PerspectiveMap:
    """Assemble the final perspective map from reviewed notes."""

    return synthesize_map(question_card, kept_notes, review_decisions)



def _partition_notes_by_review_action(
    notes: list[PerspectiveNote],
    review_decisions: list[ReviewDecision],
) -> dict[str, list[PerspectiveNote]]:
    """Group expanded notes by review action for debug-friendly pipeline output."""

    note_lookup = {note.note_id: note for note in notes}
    grouped_notes: dict[str, list[PerspectiveNote]] = {
        "keep": [],
        "merge": [],
        "rewrite": [],
        "drop": [],
    }

    for decision in review_decisions:
        note = note_lookup.get(decision.target_note_id)
        if note is None:
            continue
        grouped_notes[decision.action].append(note)

    return grouped_notes



def decompose(problem_text: str) -> DecomposeArtifacts:
    """Decompose the input problem into normalized cards used by later stages."""

    question_card = normalize_question(problem_text)
    knowledge_cards = generate_knowledge_cards(question_card)
    variable_cards = generate_variable_cards(question_card)
    controversy_cards = generate_controversy_cards(question_card)
    return DecomposeArtifacts(
        question_card=question_card,
        knowledge_cards=knowledge_cards,
        variable_cards=variable_cards,
        controversy_cards=controversy_cards,
    )



def _run_legacy_perspective_flow(decompose_output: DecomposeArtifacts) -> tuple[list[AxisCard], list[PerspectiveNote]]:
    """Compatibility layer that preserves the earlier axis-driven extraction machinery."""

    axis_cards = generate_axes(
        decompose_output.question_card,
        knowledge_cards=decompose_output.knowledge_cards,
        variable_cards=decompose_output.variable_cards,
        controversy_cards=decompose_output.controversy_cards,
    )
    perspective_notes = expand_axes(
        axis_cards,
        decompose_output.question_card,
        knowledge_cards=decompose_output.knowledge_cards,
        variable_cards=decompose_output.variable_cards,
        controversy_cards=decompose_output.controversy_cards,
    )
    return axis_cards, perspective_notes



def trace(decompose_output: DecomposeArtifacts, trace_target: str) -> TraceArtifacts:
    """Trace decomposition artifacts against the selected target.

    The default implementation routes through the legacy axis/note flow so the
    new pipeline order can coexist with existing synthesis components.
    """

    axis_cards, perspective_notes = _run_legacy_perspective_flow(decompose_output)
    return TraceArtifacts(
        trace_target=trace_target,
        axis_cards=axis_cards,
        perspective_notes=perspective_notes,
    )



def compete(
    decompose_output: DecomposeArtifacts,
    trace_output: TraceArtifacts,
) -> CompeteArtifacts:
    """Compare traced candidates and decide which ones compete, merge, or drop."""

    review_decisions = review_notes(
        decompose_output.question_card,
        trace_output.perspective_notes,
    )
    notes_by_action = _partition_notes_by_review_action(
        trace_output.perspective_notes,
        review_decisions,
    )
    return CompeteArtifacts(
        review_decisions=review_decisions,
        notes_by_action=notes_by_action,
    )



def stress(
    decompose_output: DecomposeArtifacts,
    trace_output: TraceArtifacts,
    compete_output: CompeteArtifacts,
) -> StressArtifacts:
    """Stress-test candidate outputs and synthesize the final structured map."""

    kept_notes = compete_output.notes_by_action["keep"]
    perspective_map = build_perspective_map(
        decompose_output.question_card,
        kept_notes,
        review_decisions=compete_output.review_decisions,
    )
    return StressArtifacts(
        kept_notes=kept_notes,
        merged_notes=compete_output.notes_by_action["merge"],
        rewrite_notes=compete_output.notes_by_action["rewrite"],
        dropped_notes=compete_output.notes_by_action["drop"],
        perspective_map=perspective_map,
    )



def final(all_artifacts: PipelineArtifacts) -> PipelineResult:
    """Assemble the final pipeline result from the full artifact bundle."""

    return PipelineResult(
        question_card=all_artifacts.decompose_output.question_card,
        axis_cards=all_artifacts.trace_output.axis_cards,
        knowledge_cards=all_artifacts.decompose_output.knowledge_cards,
        variable_cards=all_artifacts.decompose_output.variable_cards,
        controversy_cards=all_artifacts.decompose_output.controversy_cards,
        perspective_notes=all_artifacts.trace_output.perspective_notes,
        review_decisions=all_artifacts.compete_output.review_decisions,
        kept_notes=all_artifacts.stress_output.kept_notes,
        merged_notes=all_artifacts.stress_output.merged_notes,
        rewrite_notes=all_artifacts.stress_output.rewrite_notes,
        dropped_notes=all_artifacts.stress_output.dropped_notes,
        perspective_map=all_artifacts.stress_output.perspective_map,
    )



def run_pipeline(
    question: str,
    *,
    prompt_variant: PromptVariant | None = None,
    lens: PromptVariant | None = None,
) -> PipelineResult:
    """Run the default decompose→trace→compete→stress→final pipeline.

    The returned ``PipelineResult`` preserves the full stage-by-stage trace while
    keeping the prior axis/note perspective-extraction implementation behind a
    compatibility layer rather than presenting it as the primary reasoning flow.
    """

    PipelinePromptConfig(
        prompt_variant=prompt_variant,
        lens=lens,
    ).resolved_prompt_variant

    decompose_output = decompose(question)
    trace_output = trace(
        decompose_output,
        trace_target=decompose_output.question_card.cleaned_question,
    )
    compete_output = compete(decompose_output, trace_output)
    stress_output = stress(decompose_output, trace_output, compete_output)
    return final(
        PipelineArtifacts(
            decompose_output=decompose_output,
            trace_output=trace_output,
            compete_output=compete_output,
            stress_output=stress_output,
        )
    )


def run_phase1_pipeline(
    problem_text: str,
    *,
    trace_target: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    improve_rounds: int = 1,
    run_id: str | None = None,
    live_run_output_root: str | Path = "examples/out/live_runs",
    policy_version: str | PolicyVersion | None = None,
) -> Phase1PipelineArtifacts:
    """Run the dedicated phase-1 decompose→trace→compete→stress→final path."""

    if improve_rounds < 1:
        raise ValueError("improve_rounds must be >= 1")

    resolved_run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_root = Path(live_run_output_root) / resolved_run_id
    output_root.mkdir(parents=True, exist_ok=True)

    def _save_round_json(round_dir: Path, filename: str, payload: dict[str, object]) -> None:
        round_dir.mkdir(parents=True, exist_ok=True)
        (round_dir / filename).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    use_live_model = model is not None or api_key is not None
    if use_live_model:
        if not model or not api_key:
            raise ValueError("model and api_key are both required for live phase-1 execution")
    current_patch = PromptPatchBundle()
    round_evaluations: list[EvaluationResult] = []
    decompose_result: DecomposeResult | None = None
    trace_result: TraceResult | None = None
    compete_result: CompeteResult | None = None
    stress_result: StressResult | None = None
    final_report: FinalReport | None = None

    for round_index in range(1, improve_rounds + 1):
        round_dir = output_root / f"round_{round_index}"
        if use_live_model:
            decompose_result = run_decompose(
                problem_text,
                model=model,
                api_key=api_key,
                prompt_patch=current_patch.decompose_patch,
                policy_version=policy_version,
            )
            trace_result = run_trace(
                decompose_result,
                trace_target=trace_target,
                model=model,
                api_key=api_key,
                prompt_patch=current_patch.trace_patch,
                policy_version=policy_version,
            )
            compete_result = run_compete(
                decompose_result,
                trace_result,
                model=model,
                api_key=api_key,
                prompt_patch=current_patch.compete_patch,
                policy_version=policy_version,
            )
            stress_result = run_stress(
                decompose_result,
                trace_result,
                compete_result,
                model=model,
                api_key=api_key,
                prompt_patch=current_patch.stress_patch,
                policy_version=policy_version,
            )
            final_report = run_final(
                decompose_result,
                trace_result,
                compete_result,
                stress_result,
                model=model,
                api_key=api_key,
                prompt_patch=current_patch.final_patch,
                policy_version=policy_version,
            )
        else:
            decompose_result = decompose_problem(problem_text)
            trace_result = build_trace(
                decompose_result,
                trace_target=trace_target,
            )
            compete_result = build_competing_mechanisms(
                decompose_result,
                trace_result,
            )
            stress_result = build_stress_test(
                decompose_result,
                trace_result,
                compete_result,
            )
            final_report = build_final_report(
                decompose_result,
                trace_result,
                compete_result,
                stress_result,
            )

        decompose_payload = asdict(decompose_result)
        trace_payload = asdict(trace_result)
        compete_payload = asdict(compete_result)
        stress_payload = asdict(stress_result)
        final_payload = asdict(final_report)
        evaluation = evaluate_phase1_artifacts(
            decompose_artifact=decompose_payload,
            trace_artifact=trace_payload,
            compete_artifact=compete_payload,
            stress_artifact=stress_payload,
            final_artifact=final_payload,
        )
        round_evaluations.append(evaluation)

        _save_round_json(round_dir, "01_decompose.json", decompose_payload)
        _save_round_json(round_dir, "02_trace.json", trace_payload)
        _save_round_json(round_dir, "03_compete.json", compete_payload)
        _save_round_json(round_dir, "04_stress.json", stress_payload)
        _save_round_json(round_dir, "05_final.json", final_payload)
        _save_round_json(round_dir, "06_evaluate.json", evaluation.to_dict())
        next_patch = build_prompt_patch_from_failure_flags(evaluation.failure_flags)
        _save_round_json(round_dir, "07_prompt_patch_for_next_round.json", next_patch.as_dict())
        current_patch = next_patch

    assert decompose_result is not None
    assert trace_result is not None
    assert compete_result is not None
    assert stress_result is not None
    assert final_report is not None

    return Phase1PipelineArtifacts(
        decompose_result=decompose_result,
        trace_result=trace_result,
        compete_result=compete_result,
        stress_result=stress_result,
        final_report=final_report,
        round_evaluations=round_evaluations,
        run_id=resolved_run_id,
        output_root=str(output_root),
    )


class PerspectiveExtractionPipeline:
    """Backward-compatible orchestrator for the legacy perspective-extraction scaffold."""

    def run(
        self,
        pipeline_input: PipelineInput,
        *,
        prompt_variant: PromptVariant | None = None,
        lens: PromptVariant | None = None,
    ) -> list[PerspectiveRecord]:
        normalized_topic = normalize_text(pipeline_input.topic)
        source_text = normalize_text(pipeline_input.source_text)
        background = collect_background(normalized_topic)
        result = run_pipeline(
            normalized_topic,
            prompt_variant=prompt_variant,
            lens=lens,
        )

        records = [
            PerspectiveRecord(
                axis=axis_card.name,
                summary=(
                    f"{len([note for note in result.perspective_notes if note.axis_id == axis_card.axis_id])} note(s) "
                    f"using {len(axis_card.supporting_card_ids)} support card(s) and {len(background)} background item(s)"
                ),
                evidence=[*background, source_text] if source_text else list(background),
            )
            for axis_card in result.axis_cards
        ]
        return review_records(records)

    def summarize(
        self,
        pipeline_input: PipelineInput,
        *,
        prompt_variant: PromptVariant | None = None,
        lens: PromptVariant | None = None,
    ) -> str:
        return synthesize_summary(
            self.run(
                pipeline_input,
                prompt_variant=prompt_variant,
                lens=lens,
            )
        )


__all__ = [
    "CompeteArtifacts",
    "DecomposeArtifacts",
    "Phase1PipelineArtifacts",
    "PerspectiveExtractionPipeline",
    "PipelineArtifacts",
    "PipelinePromptConfig",
    "StressArtifacts",
    "TraceArtifacts",
    "build_perspective_map",
    "compete",
    "decompose",
    "expand_axis",
    "expand_axes",
    "final",
    "generate_axes",
    "review_notes",
    "run_phase1_pipeline",
    "run_pipeline",
    "stress",
    "trace",
]
