import unittest

from perspective_extractor.models import PerspectiveNote, QuestionCard
from perspective_extractor.pipeline import review_notes


class ReviewNotesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.question_card = QuestionCard(
            raw_question="How does remote work affect employee productivity?",
            cleaned_question="How does remote work affect employee productivity?",
            actor_entity="remote work",
            outcome_variable="employee productivity",
            domain_hint="business",
        )

    def test_review_notes_emits_keep_merge_drop_and_rewrite_with_reasons(self) -> None:
        notes = [
            PerspectiveNote(
                note_id="note_keep",
                axis_id="axis_1",
                core_claim=(
                    "Remote work improves employee productivity when it reduces commute fatigue and preserves long focus blocks."
                ),
                reasoning="Focus time and recovered energy can be turned into output.",
                counterexample=(
                    "A counterexample is a team that depends on rapid in-person coordination, so remote work slows handoffs."
                ),
                evidence_needed=[
                    "Compare productivity before and after remote adoption while measuring commute time saved.",
                    "Measure whether uninterrupted focus time rises in remote teams.",
                ],
                testable_implication=(
                    "If commute relief and focus time drive the effect, employees with longer commutes should gain more productivity from remote work."
                ),
                supporting_card_ids=["knowledge_commute", "variable_productivity"],
            ),
            PerspectiveNote(
                note_id="note_merge",
                axis_id="axis_2",
                core_claim=(
                    "Remote work improves employee productivity by reducing commute fatigue and preserving long focus blocks."
                ),
                reasoning="The mechanism is almost the same but carries one extra evidence cue.",
                counterexample=(
                    "A counterexample is a team that depends on rapid in-person coordination, so remote work slows handoffs and can erase the gains."
                ),
                evidence_needed=[
                    "Compare productivity before and after remote adoption while measuring commute time saved.",
                    "Measure whether uninterrupted focus time rises in remote teams.",
                    "Test whether longer baseline commutes predict larger productivity gains under remote work.",
                ],
                testable_implication=(
                    "If commute relief and focus time drive the effect, employees with longer commutes should gain more productivity from remote work."
                ),
                supporting_card_ids=["knowledge_commute", "variable_productivity", "knowledge_travel_time"],
            ),
            PerspectiveNote(
                note_id="note_drop",
                axis_id="axis_3",
                core_claim=(
                    "Remote work improves employee productivity when it reduces commute fatigue and preserves long focus blocks."
                ),
                reasoning="This restates the first note without adding anything.",
                counterexample=(
                    "A counterexample is a team that depends on rapid in-person coordination, so remote work slows handoffs."
                ),
                evidence_needed=[
                    "Compare productivity before and after remote adoption while measuring commute time saved.",
                    "Measure whether uninterrupted focus time rises in remote teams.",
                ],
                testable_implication=(
                    "If commute relief and focus time drive the effect, employees with longer commutes should gain more productivity from remote work."
                ),
                supporting_card_ids=["knowledge_commute", "variable_productivity"],
            ),
            PerspectiveNote(
                note_id="note_distinct",
                axis_id="axis_4",
                core_claim=(
                    "Remote work can reduce employee productivity when managers lose visibility and coordination routines weaken."
                ),
                reasoning="This is a managerial-monitoring lens rather than a commute/focus lens.",
                counterexample=(
                    "A counterexample is an organization with strong asynchronous processes, where visibility loss does not hurt execution."
                ),
                evidence_needed=[
                    "Measure whether manager-employee check-in quality falls after remote adoption.",
                    "Compare productivity changes across teams with weak versus strong coordination systems.",
                ],
                testable_implication=(
                    "If coordination loss is decisive, teams with weaker process discipline should see larger productivity declines under remote work."
                ),
                supporting_card_ids=["knowledge_management", "variable_coordination"],
            ),
            PerspectiveNote(
                note_id="note_rewrite",
                axis_id="axis_5",
                core_claim="Remote work matters in some cases.",
                reasoning="This note is intentionally vague.",
                counterexample="Sometimes other factors matter.",
                evidence_needed=["Need more evidence."],
                testable_implication="Results could differ.",
                supporting_card_ids=["knowledge_generic"],
            ),
        ]

        decisions = review_notes(self.question_card, notes)
        actions = {decision.target_note_id: decision for decision in decisions}

        self.assertEqual(actions["note_keep"].action, "keep")
        self.assertEqual(actions["note_merge"].action, "merge")
        self.assertEqual(actions["note_merge"].merge_target_note_id, "note_keep")
        self.assertEqual(actions["note_drop"].action, "drop")
        self.assertEqual(actions["note_distinct"].action, "keep")
        self.assertEqual(actions["note_rewrite"].action, "rewrite")

        for note_id, decision in actions.items():
            self.assertTrue(decision.reason, note_id)

        self.assertIn("claim", actions["note_merge"].reason)
        self.assertIn("evidence_needed", actions["note_drop"].reason)
        self.assertIn("generic", actions["note_rewrite"].reason)


if __name__ == "__main__":
    unittest.main()
