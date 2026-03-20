from perspective_extractor.models import PerspectiveNote
from perspective_extractor.normalize import normalize_question
from perspective_extractor.review import review_notes


ALLOWED_ACTIONS = {"keep", "merge", "rewrite", "drop"}
QUESTION_CARD = normalize_question("How does remote work affect employee productivity?")


def test_review_decision_actions_stay_within_allowed_set() -> None:
    notes = [
        PerspectiveNote(
            note_id="note_keep",
            axis_id="axis_keep",
            core_claim="Remote work can improve productivity when it increases focus time.",
            reasoning="The note ties a concrete mechanism to the outcome.",
            counterexample="Coordination-heavy teams may lose productivity instead.",
            boundary_condition="This is most relevant when work can be done asynchronously.",
            evidence_needed=[
                "Compare focus time before and after remote adoption.",
                "Measure output changes for coordination-light teams.",
            ],
            testable_implication="Teams with more uninterrupted work should improve more.",
            verification_question="What evidence would show focus time, rather than selection, explains the change?",
        ),
        PerspectiveNote(
            note_id="note_rewrite",
            axis_id="axis_rewrite",
            core_claim="Remote work matters in some cases.",
            reasoning="This is intentionally generic.",
            counterexample="Other factors also matter.",
            boundary_condition="It depends on the setting.",
            evidence_needed=["Need better evidence."],
            testable_implication="Results could differ.",
            verification_question="What evidence matters here?",
        ),
    ]

    decisions = review_notes(QUESTION_CARD, notes)

    assert decisions
    assert {decision.target_note_id for decision in decisions} == {note.note_id for note in notes}
    for decision in decisions:
        assert decision.action in ALLOWED_ACTIONS
        assert decision.reason
        assert decision.verification_question
