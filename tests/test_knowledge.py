from perspective_extractor.knowledge import (
    generate_controversy_cards,
    generate_knowledge_cards,
    generate_variable_cards,
)
from perspective_extractor.normalize import normalize_question


QUESTION_CARD = normalize_question("How does remote work affect employee productivity?")


def test_knowledge_generators_return_structured_cards() -> None:
    knowledge_cards = generate_knowledge_cards(QUESTION_CARD)
    variable_cards = generate_variable_cards(QUESTION_CARD)
    controversy_cards = generate_controversy_cards(QUESTION_CARD)

    assert knowledge_cards
    assert variable_cards
    assert controversy_cards

    for card in knowledge_cards:
        assert card.knowledge_id
        assert card.title
        assert card.content
        assert isinstance(card.evidence_needed, list)

    for card in variable_cards:
        assert card.variable_id
        assert card.name
        assert card.variable_role in {"actor", "state", "decision", "constraint", "outcome"}
        assert card.definition

    for card in controversy_cards:
        assert card.controversy_id
        assert card.question
        assert len(card.sides) >= 2
