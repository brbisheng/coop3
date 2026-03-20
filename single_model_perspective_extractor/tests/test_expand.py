import unittest

from perspective_extractor.expand import expand_axis
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

    def test_expand_axis_rejects_non_minimal_context_objects(self) -> None:
        with self.assertRaises(TypeError):
            expand_axis(self.question_card, self.axis_card, context_cards=["not a card"])


if __name__ == "__main__":
    unittest.main()
