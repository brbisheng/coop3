from perspective_extractor.models import PerspectiveMap
from perspective_extractor.pipeline import run_pipeline


def test_run_pipeline_returns_legal_perspective_map() -> None:
    result = run_pipeline("How does remote work affect employee productivity?")

    assert result.question_card.question_id
    assert 8 <= len(result.axis_cards) <= 12
    assert result.review_decisions
    assert result.perspective_notes
    assert isinstance(result.perspective_map, PerspectiveMap)
    assert result.perspective_map.map_id
    assert result.perspective_map.question_id == result.question_card.question_id
    assert isinstance(result.perspective_map.kept_notes, list)
