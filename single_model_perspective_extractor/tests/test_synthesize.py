import unittest

from perspective_extractor.models import PerspectiveNote, QuestionCard, ReviewDecision
from perspective_extractor.legacy.synthesize import synthesize_map


class SynthesizeMapTests(unittest.TestCase):
    def test_synthesize_map_preserves_structure_instead_of_flattening(self) -> None:
        question_card = QuestionCard(
            raw_question="How does remote work affect employee productivity?",
            cleaned_question="How does remote work affect employee productivity?",
            actor_entity="remote work",
            outcome_variable="employee productivity",
            domain_hint="business",
            question_id="question_remote_work",
        )
        kept_notes = [
            PerspectiveNote(
                note_id="note_gain",
                axis_id="axis_commute",
                core_claim="Remote work can increase employee productivity by reducing commute fatigue and expanding uninterrupted focus time.",
                reasoning="Commute relief and longer focus blocks can translate into more output.",
                boundary_condition="This perspective weakens in jobs that require constant in-person coordination.",
                evidence_needed=[
                    "Measure productivity before and after remote adoption.",
                    "Measure commute time saved and uninterrupted focus time.",
                ],
                testable_implication="Employees with longer baseline commutes should show larger productivity gains after moving remote.",
                supporting_card_ids=["knowledge_commute", "variable_productivity"],
            ),
            PerspectiveNote(
                note_id="note_gain_child",
                axis_id="axis_commute",
                core_claim="A narrower sub-perspective says remote work helps most when workers can convert commute time into protected deep-work blocks.",
                reasoning="The productivity mechanism depends on how saved time is reallocated rather than on location alone.",
                counterexample="If saved commute time is replaced by fragmented caregiving interruptions, output may not rise.",
                evidence_needed=[
                    "Track whether saved commute time becomes uninterrupted deep-work time.",
                    "Measure output changes for workers with versus without home interruptions.",
                ],
                verification_question="Do productivity gains persist after accounting for how workers actually reallocate saved commute time?",
                supporting_card_ids=["knowledge_commute", "variable_productivity"],
            ),
            PerspectiveNote(
                note_id="note_coordination",
                axis_id="axis_coordination",
                core_claim="Remote work can decrease employee productivity when handoffs, coaching, and rapid coordination become slower.",
                reasoning="Lost visibility and weaker coordination routines can offset focus-time gains.",
                boundary_condition="This perspective is strongest in interdependent teams with weak asynchronous processes.",
                evidence_needed=[
                    "Measure productivity before and after remote adoption.",
                    "Compare teams with stronger versus weaker coordination systems.",
                ],
                testable_implication="Teams with weaker process discipline should show larger productivity declines after moving remote.",
                supporting_card_ids=["knowledge_management", "variable_productivity"],
            ),
            PerspectiveNote(
                note_id="note_selection",
                axis_id="axis_selection",
                core_claim="Remote work effects may reflect selection because already productive workers are more likely to secure flexible arrangements.",
                reasoning="Observed productivity gains may partly come from who gets remote work, not only from remote work itself.",
                boundary_condition="This perspective matters most when remote access is discretionary rather than universal.",
                evidence_needed=[
                    "Measure productivity before and after remote adoption.",
                    "Compare workers with similar baseline performance who do and do not gain remote access.",
                ],
                testable_implication="When remote access is assigned more broadly instead of selectively, average gains should shrink.",
                supporting_card_ids=["knowledge_selection", "variable_productivity"],
            ),
        ]
        review_decisions = [
            ReviewDecision(
                target_note_id="note_merge_candidate",
                action="merge",
                reason="Near-duplicate commute/focus wording should merge into the stronger commute note.",
                merge_target_note_id="note_gain",
            ),
            ReviewDecision(
                target_note_id="note_gain",
                action="keep",
                reason="Distinct mechanism note.",
            ),
            ReviewDecision(
                target_note_id="note_coordination",
                action="keep",
                reason="Distinct coordination note.",
            ),
            ReviewDecision(
                target_note_id="note_selection",
                action="keep",
                reason="Distinct selection note.",
            ),
        ]

        perspective_map = synthesize_map(question_card, kept_notes, review_decisions)

        self.assertEqual(perspective_map.question_id, question_card.question_id)
        self.assertEqual(
            [note.note_id for note in perspective_map.kept_notes],
            ["note_gain", "note_gain_child", "note_coordination", "note_selection"],
        )
        self.assertEqual(perspective_map.merged_groups, [["note_gain", "note_merge_candidate"]])
        self.assertIn(("note_coordination", "note_gain"), perspective_map.competing_perspectives)
        self.assertIn(("note_gain", "note_selection"), perspective_map.compatible_perspectives)
        self.assertEqual(
            perspective_map.axis_hierarchies[0].main_note_id,
            "note_gain",
        )
        self.assertEqual(
            perspective_map.axis_hierarchies[0].sub_perspective_ids,
            ["note_gain_child"],
        )
        gain_branch = next(
            branch for branch in perspective_map.perspective_branches if branch.note_id == "note_gain"
        )
        gain_child_branch = next(
            branch for branch in perspective_map.perspective_branches if branch.note_id == "note_gain_child"
        )
        self.assertEqual(gain_branch.child_note_ids, ["note_gain_child"])
        self.assertTrue(
            any("note_gain_child:" in item for item in gain_child_branch.evidence_disputes)
        )
        self.assertEqual(
            gain_child_branch.counterexamples,
            ["If saved commute time is replaced by fragmented caregiving interruptions, output may not rise."],
        )
        self.assertTrue(
            any(
                "note_gain" in item and "note_coordination" in item
                for item in perspective_map.evidence_contests
            )
        )
        self.assertTrue(any(item.startswith("note_gain:") for item in perspective_map.boundary_cases))
        self.assertIsNotNone(perspective_map.final_summary)
        self.assertIn("Kept note structure:", perspective_map.final_summary)
        self.assertIn("Axis hierarchy:", perspective_map.final_summary)
        self.assertIn("counterexample:", perspective_map.final_summary)
        self.assertIn("evidence dispute:", perspective_map.final_summary)
        self.assertIn("Competing perspectives:", perspective_map.final_summary)
        self.assertIn("Compatible perspectives:", perspective_map.final_summary)
        self.assertIn("Boundary cases:", perspective_map.final_summary)


if __name__ == "__main__":
    unittest.main()
