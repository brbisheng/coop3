from perspective_extractor.legacy.expand import expand_axis
from perspective_extractor.knowledge import (
    generate_controversy_cards,
    generate_knowledge_cards,
    generate_variable_cards,
)
from perspective_extractor.normalize import normalize_question
from perspective_extractor.legacy.axes import generate_axes


QUESTION_CARD = normalize_question("How does remote work affect employee productivity?")
KNOWLEDGE_CARDS = generate_knowledge_cards(QUESTION_CARD)
VARIABLE_CARDS = generate_variable_cards(QUESTION_CARD)
CONTROVERSY_CARDS = generate_controversy_cards(QUESTION_CARD)
AXIS = generate_axes(
    QUESTION_CARD,
    knowledge_cards=KNOWLEDGE_CARDS,
    variable_cards=VARIABLE_CARDS,
    controversy_cards=CONTROVERSY_CARDS,
)[0]


def test_perspective_note_required_fields_are_complete() -> None:
    note = expand_axis(
        QUESTION_CARD,
        AXIS,
        context_cards=KNOWLEDGE_CARDS + VARIABLE_CARDS + CONTROVERSY_CARDS,
    )

    required_text_fields = (
        "note_id",
        "axis_id",
        "core_claim",
        "reasoning",
        "counterexample",
        "boundary_condition",
        "testable_implication",
        "verification_question",
    )
    for field_name in required_text_fields:
        value = getattr(note, field_name)
        assert isinstance(value, str)
        assert value.strip()

    assert isinstance(note.evidence_needed, list)
    assert note.evidence_needed
    assert isinstance(note.planned_subquestions, list)
    assert isinstance(note.subanswer_trace, list)
    assert len(note.planned_subquestions) == len(note.subanswer_trace)
    assert note.axis_id == AXIS.axis_id
