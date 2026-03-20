import unittest

from perspective_extractor.expand import (
    compose_perspective_note_from_subanswers,
    expand_axis,
    plan_axis_subquestions,
)
from perspective_extractor.models import AxisCard, ControversyCard, KnowledgeCard, PerspectiveNote, QuestionCard, VariableCard


class ExpandAxisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.question_card = QuestionCard(
            raw_question="How does remote work affect employee productivity?",
            cleaned_question="How does remote work affect employee productivity?",
            actor_entity="remote work",
            outcome_variable="employee productivity",
            domain_hint="business",
        )
        self.knowledge_card = KnowledgeCard(title="Mechanism map", content="map likely channels")
        self.variable_card = VariableCard(
            name="employee productivity",
            variable_role="outcome",
            definition="measured output per employee",
        )
        self.controversy_card = ControversyCard(
            question="Is the observed effect causal?",
            sides=["yes", "no"],
        )
        self.axis_card = AxisCard(
            name="causal pathways",
            axis_type="mechanism",
            focus="Map direct and indirect channels linking remote work to employee productivity.",
            how_is_it_distinct="Separates mechanism claims from measurement or value judgments.",
            supporting_card_ids=[
                self.knowledge_card.knowledge_id,
                self.variable_card.variable_id,
                self.controversy_card.controversy_id,
            ],
        )

    def test_plan_axis_subquestions_returns_axis_specific_questions(self) -> None:
        subquestions = plan_axis_subquestions(
            self.question_card,
            self.axis_card,
            context_cards=[self.knowledge_card, self.variable_card, self.controversy_card],
        )

        self.assertGreaterEqual(len(subquestions), 3)
        self.assertLessEqual(len(subquestions), 7)
        self.assertTrue(all("causal pathways" in question or "remote work" in question for question in subquestions))
        self.assertTrue(any("Mechanism map" in question for question in subquestions))
        self.assertTrue(any("employee productivity" in question for question in subquestions))
        self.assertTrue(any("Is the observed effect causal?" in question for question in subquestions))

    def test_compose_perspective_note_from_subanswers_preserves_trace(self) -> None:
        subanswers = [
            (
                "Within the causal pathways axis, which part of the mechanism most directly links remote work to employee productivity?",
                "the decisive pathway is improved coordination quality and reduced commute fatigue",
            ),
            (
                "How should employee productivity be measured or compared so it can test the causal pathways axis instead of a rival explanation?",
                "the measure must compare matched teams over stable time windows",
            ),
            (
                "How would answering 'Is the observed effect causal?' change confidence in the causal pathways axis?",
                "confidence rises if causal evidence rules out selection effects",
            ),
        ]

        note = compose_perspective_note_from_subanswers(
            self.question_card,
            self.axis_card,
            subanswers,
            context_cards=[self.knowledge_card, self.variable_card, self.controversy_card],
        )

        self.assertEqual(note.planned_subquestions, [question for question, _ in subanswers])
        self.assertEqual(len(note.subanswer_trace), len(subanswers))
        self.assertTrue(note.subanswer_trace[0].startswith("Q1:"))
        self.assertTrue(any("Subquestion trace Q1:" in line for line in note.evidence_needed))
        self.assertIn("Derived from subquestions:", note.reasoning)

    def test_expand_axis_returns_single_perspective_note_with_required_fields(self) -> None:
        note = expand_axis(
            self.question_card,
            self.axis_card,
            context_cards=[self.knowledge_card, self.variable_card, self.controversy_card],
        )

        self.assertIsInstance(note, PerspectiveNote)
        self.assertEqual(note.axis_id, self.axis_card.axis_id)
        self.assertTrue(note.core_claim)
        self.assertTrue(note.reasoning)
        self.assertTrue(note.counterexample)
        self.assertTrue(note.boundary_condition)
        self.assertTrue(note.evidence_needed)
        self.assertTrue(note.testable_implication)
        self.assertEqual(note.supporting_card_ids, self.axis_card.supporting_card_ids)
        self.assertGreaterEqual(len(note.planned_subquestions), 3)
        self.assertEqual(len(note.planned_subquestions), len(note.subanswer_trace))

    def test_expand_axis_rejects_non_minimal_context_objects(self) -> None:
        with self.assertRaises(TypeError):
            expand_axis(self.question_card, self.axis_card, context_cards=["not a card"])


if __name__ == "__main__":
    unittest.main()
