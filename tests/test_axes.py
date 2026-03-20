from perspective_extractor.axes import _normalize_axis_name, generate_axes
from perspective_extractor.knowledge import (
    generate_controversy_cards,
    generate_knowledge_cards,
    generate_variable_cards,
)
from perspective_extractor.normalize import normalize_question


QUESTION_CARD = normalize_question("How does remote work affect employee productivity?")
KNOWLEDGE_CARDS = generate_knowledge_cards(QUESTION_CARD)
VARIABLE_CARDS = generate_variable_cards(QUESTION_CARD)
CONTROVERSY_CARDS = generate_controversy_cards(QUESTION_CARD)


def test_generate_axes_count_and_name_uniqueness_invariants() -> None:
    axes = generate_axes(
        QUESTION_CARD,
        knowledge_cards=KNOWLEDGE_CARDS,
        variable_cards=VARIABLE_CARDS,
        controversy_cards=CONTROVERSY_CARDS,
    )

    assert 8 <= len(axes) <= 12
    normalized_names = [_normalize_axis_name(axis.name) for axis in axes]
    assert all(normalized_names)
    assert len(set(normalized_names)) == len(normalized_names)
    assert all(axis.axis_id for axis in axes)
    assert all(axis.axis_type for axis in axes)
    assert all(axis.focus for axis in axes)
    assert all(axis.how_is_it_distinct for axis in axes)
