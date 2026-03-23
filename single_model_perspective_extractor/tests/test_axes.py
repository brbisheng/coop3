import unittest

from perspective_extractor.legacy.axes import _normalize_axis_name, generate_axes
from perspective_extractor.models import ControversyCard, KnowledgeCard, QuestionCard, VariableCard


class AxisGenerationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.question_card = QuestionCard(
            raw_question="How does remote work affect employee productivity?",
            cleaned_question="How does remote work affect employee productivity?",
            actor_entity="remote work",
            outcome_variable="employee productivity",
            domain_hint="business",
            assumptions=["remote work may influence employee productivity."],
            missing_pieces=["population", "timeframe", "comparator"],
        )
        self.knowledge_cards = [
            KnowledgeCard(title="Question framing", content="frame"),
            KnowledgeCard(title="Background facts", content="background"),
            KnowledgeCard(title="Mechanism map", content="mechanisms"),
            KnowledgeCard(title="Conceptual boundaries", content="boundaries"),
        ]
        self.variable_cards = [
            VariableCard(name="remote work", variable_role="actor", definition="actor definition"),
            VariableCard(name="workplace context", variable_role="state", definition="state definition"),
            VariableCard(name="rollout choice", variable_role="decision", definition="decision definition"),
            VariableCard(name="scope constraint", variable_role="constraint", definition="constraint definition"),
            VariableCard(name="employee productivity", variable_role="outcome", definition="outcome definition"),
        ]
        self.controversy_cards = [
            ControversyCard(question="Is the effect causal?", sides=["yes", "no"]),
            ControversyCard(question="Which mechanism dominates?", sides=["direct", "indirect"]),
            ControversyCard(question="How context-dependent are results?", sides=["general", "contingent"]),
        ]

    def test_generate_axes_returns_structurally_diverse_non_conclusory_axes(self) -> None:
        axis_cards = generate_axes(
            self.question_card,
            knowledge_cards=self.knowledge_cards,
            variable_cards=self.variable_cards,
            controversy_cards=self.controversy_cards,
        )

        self.assertGreaterEqual(len(axis_cards), 8)
        self.assertLessEqual(len(axis_cards), 12)
        self.assertGreaterEqual(len({axis.axis_type for axis in axis_cards}), 8)
        self.assertTrue(all(axis.how_is_it_distinct for axis in axis_cards))
        self.assertEqual(
            len({_normalize_axis_name(axis.name) for axis in axis_cards}),
            len(axis_cards),
        )
        disallowed = {"best", "better", "worse", "beneficial", "harmful", "should", "must"}
        for axis in axis_cards:
            tokens = set(axis.name.split()) | set(axis.focus.lower().split())
            self.assertFalse(tokens & disallowed)

    def test_axis_name_normalization_collapses_shallow_rewrites(self) -> None:
        self.assertEqual(_normalize_axis_name("Mechanism axis"), _normalize_axis_name("mechanisms"))
        self.assertEqual(
            _normalize_axis_name("The stakeholder incentive lens"),
            _normalize_axis_name("stakeholder incentives"),
        )


if __name__ == "__main__":
    unittest.main()
