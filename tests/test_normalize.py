from perspective_extractor.normalize import normalize_question


def test_normalize_returns_required_fields() -> None:
    card = normalize_question("How does remote work affect employee productivity?")

    required_fields = (
        "question_id",
        "raw_question",
        "cleaned_question",
        "actor_entity",
        "outcome_variable",
        "keywords",
        "missing_pieces",
    )

    for field_name in required_fields:
        value = getattr(card, field_name)
        assert value is not None
        if isinstance(value, str):
            assert value.strip()

    assert isinstance(card.assumptions, list)
    assert isinstance(card.keywords, list)
    assert isinstance(card.missing_pieces, list)
    assert len(card.keywords) >= 2
