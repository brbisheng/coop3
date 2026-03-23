from __future__ import annotations

from dataclasses import fields, is_dataclass
from unittest.mock import patch

import pytest

from perspective_extractor.models import PerspectiveMap
from perspective_extractor.pipeline import expand_axes, run_pipeline
from perspective_extractor.legacy.review import review_notes
from perspective_extractor.legacy.synthesize import synthesize_map


def _required_text_fields(instance: object) -> list[str]:
    missing: list[str] = []
    for field in fields(instance):
        value = getattr(instance, field.name)
        if field.type is str and not value:
            missing.append(field.name)
    return missing


def test_fixed_stage_responses_make_pipeline_order_and_schema_reproducible(
    fixed_pipeline_scenario,
    mock_pipeline_responder,
) -> None:
    with (
        patch("perspective_extractor.pipeline.normalize_question", side_effect=mock_pipeline_responder.normalize),
        patch("perspective_extractor.pipeline.generate_knowledge_cards", side_effect=mock_pipeline_responder.knowledge),
        patch("perspective_extractor.pipeline.generate_variable_cards", side_effect=mock_pipeline_responder.variable),
        patch("perspective_extractor.pipeline.generate_controversy_cards", side_effect=mock_pipeline_responder.controversy),
        patch("perspective_extractor.pipeline.generate_axes", side_effect=mock_pipeline_responder.axes),
        patch("perspective_extractor.pipeline.expand_axes", side_effect=mock_pipeline_responder.expand),
        patch("perspective_extractor.pipeline.review_notes", side_effect=mock_pipeline_responder.review),
        patch("perspective_extractor.pipeline.build_perspective_map", side_effect=mock_pipeline_responder.build_map),
    ):
        result = run_pipeline(fixed_pipeline_scenario.question_card.raw_question)

    assert mock_pipeline_responder.call_log == [
        "normalize:How does remote work affect employee productivity?",
        "knowledge",
        "variable",
        "controversy",
        "axes",
        "expand",
        "review",
        "synthesize",
    ]
    assert result.question_card.question_id == "question_remote_work"
    assert [axis.axis_id for axis in result.axis_cards] == ["axis_focus", "axis_boundary"]
    assert [note.note_id for note in result.perspective_notes] == [
        "note_focus",
        "note_boundary",
        "note_focus_duplicate",
        "note_vague",
    ]
    assert [decision.action for decision in result.review_decisions] == [
        "keep",
        "keep",
        "merge",
        "rewrite",
    ]
    assert [note.note_id for note in result.kept_notes] == ["note_focus", "note_boundary"]
    assert [note.note_id for note in result.merged_notes] == ["note_focus_duplicate"]
    assert [note.note_id for note in result.rewrite_notes] == ["note_vague"]
    assert result.dropped_notes == []
    assert isinstance(result.perspective_map, PerspectiveMap)
    for collection_name in (
        "axis_cards",
        "knowledge_cards",
        "variable_cards",
        "controversy_cards",
        "perspective_notes",
        "review_decisions",
    ):
        assert getattr(result, collection_name), collection_name
    for item in [
        result.question_card,
        *result.axis_cards,
        *result.knowledge_cards,
        *result.variable_cards,
        *result.controversy_cards,
        *result.perspective_notes,
        *result.review_decisions,
        result.perspective_map,
    ]:
        assert is_dataclass(item)
        assert not _required_text_fields(item)


def test_expand_axes_preserves_axis_to_note_mapping_without_model_flakiness(fixed_pipeline_scenario) -> None:
    captured_contexts: list[tuple[str, list[str]]] = []

    def fixed_expand(question_card, axis_card, *, context_cards):
        captured_contexts.append(
            (
                axis_card.axis_id,
                [
                    getattr(card, "knowledge_id", None)
                    or getattr(card, "variable_id", None)
                    or getattr(card, "controversy_id", None)
                    for card in context_cards
                ],
            )
        )
        return fixed_pipeline_scenario.perspective_notes[0].__class__(
            note_id="note_transient",
            axis_id=axis_card.axis_id,
            core_claim=f"claim for {axis_card.axis_id}",
            reasoning="deterministic fixture output",
            supporting_card_ids=[
                getattr(card, "knowledge_id", None)
                or getattr(card, "variable_id", None)
                or getattr(card, "controversy_id", None)
                for card in context_cards
            ],
        )

    with patch("perspective_extractor.pipeline.expand_axis_note", side_effect=fixed_expand):
        notes = expand_axes(
            fixed_pipeline_scenario.axis_cards,
            fixed_pipeline_scenario.question_card,
            knowledge_cards=fixed_pipeline_scenario.knowledge_cards,
            variable_cards=fixed_pipeline_scenario.variable_cards,
            controversy_cards=fixed_pipeline_scenario.controversy_cards,
        )

    assert captured_contexts == [
        ("axis_focus", ["knowledge_focus", "variable_actor", "variable_outcome"]),
        ("axis_boundary", ["knowledge_coordination", "variable_scope", "controversy_selection"]),
    ]
    assert [note.axis_id for note in notes] == ["axis_focus", "axis_boundary"]
    assert [note.note_id for note in notes] == ["note_focus", "note_boundary"]
    assert [note.supporting_card_ids for note in notes] == [
        ["knowledge_focus", "variable_actor", "variable_outcome"],
        ["knowledge_coordination", "variable_scope", "controversy_selection"],
    ]


@pytest.mark.skip(reason="Legacy many-perspectives review/map assertions are no longer a core phase-1 guarantee.")
def test_review_and_synthesis_assert_structure_instead_of_full_text(fixed_pipeline_scenario) -> None:
    decisions = review_notes(
        fixed_pipeline_scenario.question_card,
        fixed_pipeline_scenario.perspective_notes,
    )
    decision_by_note = {decision.target_note_id: decision for decision in decisions}

    assert set(decision_by_note) == {
        "note_focus",
        "note_boundary",
        "note_focus_duplicate",
        "note_vague",
    }
    assert decision_by_note["note_focus"].action in {"keep", "merge"}
    assert decision_by_note["note_boundary"].action in {"keep", "rewrite"}
    assert decision_by_note["note_focus_duplicate"].action in {"merge", "drop"}
    assert decision_by_note["note_vague"].action == "rewrite"
    assert all(decision.verification_question for decision in decisions)

    kept_notes = fixed_pipeline_scenario.perspective_map.kept_notes
    perspective_map = synthesize_map(
        fixed_pipeline_scenario.question_card,
        kept_notes,
        fixed_pipeline_scenario.review_decisions,
    )

    assert perspective_map.question_id == fixed_pipeline_scenario.question_card.question_id
    assert [note.note_id for note in perspective_map.kept_notes] == ["note_focus", "note_boundary"]
    assert all(group[0] in {note.note_id for note in kept_notes} for group in perspective_map.merged_groups)
    assert all(note.note_id and note.axis_id for note in perspective_map.kept_notes)
    assert all(branch.note_id and branch.axis_id and branch.claim for branch in perspective_map.perspective_branches)
    assert all(hierarchy.axis_id and hierarchy.main_note_id for hierarchy in perspective_map.axis_hierarchies)
    assert all(len(pair) == 2 for pair in perspective_map.competing_perspectives)
    assert all(item.split(":", 1)[0].startswith("note_") for item in perspective_map.evidence_contests)
    assert all(item.split(":", 1)[0].startswith("note_") for item in perspective_map.boundary_cases)
    assert perspective_map.final_summary
