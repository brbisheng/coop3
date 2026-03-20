import unittest
from unittest.mock import patch

from perspective_extractor.models import (
    AxisCard,
    ControversyCard,
    KnowledgeCard,
    PerspectiveNote,
    PipelineResult,
    QuestionCard,
    VariableCard,
)
from perspective_extractor.pipeline import expand_axis, generate_axes, run_pipeline


class PipelineFlowTests(unittest.TestCase):
    def test_run_pipeline_calls_normalize_and_knowledge_before_axis_generation(self) -> None:
        call_order: list[str] = []
        question_card = QuestionCard(
            raw_question="How does remote work affect employee productivity?",
            cleaned_question="How does remote work affect employee productivity?",
            actor_entity="remote work",
            outcome_variable="employee productivity",
            domain_hint="business",
        )
        knowledge_cards = [
            KnowledgeCard(title="Question framing", content="frame"),
        ]
        variable_cards = [
            VariableCard(name="remote work", variable_role="actor", definition="actor"),
        ]
        controversy_cards = [
            ControversyCard(question="Is it causal?", sides=["yes", "no"]),
        ]
        axis_cards = [
            AxisCard(
                name="baseline framing",
                axis_type="framing",
                focus="focus",
                how_is_it_distinct="distinct",
                supporting_card_ids=[knowledge_cards[0].knowledge_id],
            )
        ]
        perspective_notes = [
            PerspectiveNote(axis_id=axis_cards[0].axis_id, core_claim="claim", reasoning="reasoning")
        ]

        def normalize_stub(question: str) -> QuestionCard:
            call_order.append("normalize")
            return question_card

        def knowledge_stub(card: QuestionCard) -> list[KnowledgeCard]:
            self.assertIs(card, question_card)
            call_order.append("knowledge")
            return knowledge_cards

        def variable_stub(card: QuestionCard) -> list[VariableCard]:
            self.assertIs(card, question_card)
            call_order.append("variable")
            return variable_cards

        def controversy_stub(card: QuestionCard) -> list[ControversyCard]:
            self.assertIs(card, question_card)
            call_order.append("controversy")
            return controversy_cards

        def axes_stub(card: QuestionCard, **kwargs) -> list[AxisCard]:
            self.assertEqual(call_order, ["normalize", "knowledge", "variable", "controversy"])
            self.assertIs(kwargs["knowledge_cards"], knowledge_cards)
            self.assertIs(kwargs["variable_cards"], variable_cards)
            self.assertIs(kwargs["controversy_cards"], controversy_cards)
            call_order.append("axes")
            return axis_cards

        def expand_stub(axis_card: AxisCard, card: QuestionCard, **kwargs) -> list[PerspectiveNote]:
            self.assertEqual(call_order[-1], "axes")
            self.assertIs(axis_card, axis_cards[0])
            self.assertIs(card, question_card)
            self.assertIs(kwargs["knowledge_cards"], knowledge_cards)
            self.assertIs(kwargs["variable_cards"], variable_cards)
            self.assertIs(kwargs["controversy_cards"], controversy_cards)
            call_order.append("expand")
            return perspective_notes

        with (
            patch("perspective_extractor.pipeline.normalize_question", side_effect=normalize_stub),
            patch("perspective_extractor.pipeline.generate_knowledge_cards", side_effect=knowledge_stub),
            patch("perspective_extractor.pipeline.generate_variable_cards", side_effect=variable_stub),
            patch("perspective_extractor.pipeline.generate_controversy_cards", side_effect=controversy_stub),
            patch("perspective_extractor.pipeline.generate_axes", side_effect=axes_stub),
            patch("perspective_extractor.pipeline.expand_axis", side_effect=expand_stub),
        ):
            result = run_pipeline(question_card.raw_question)

        self.assertIsInstance(result, PipelineResult)
        self.assertEqual(call_order, ["normalize", "knowledge", "variable", "controversy", "axes", "expand"])

    def test_generate_axes_and_expand_axis_keep_supporting_card_trace(self) -> None:
        question_card = QuestionCard(
            raw_question="How does remote work affect employee productivity?",
            cleaned_question="How does remote work affect employee productivity?",
            actor_entity="remote work",
            outcome_variable="employee productivity",
            domain_hint="business",
        )
        knowledge_cards = [
            KnowledgeCard(title="Question framing", content="framing support"),
            KnowledgeCard(title="Mechanism map", content="mechanism support"),
        ]
        variable_cards = [
            VariableCard(name="remote work", variable_role="actor", definition="actor definition"),
            VariableCard(name="employee productivity", variable_role="outcome", definition="outcome definition"),
            VariableCard(name="scope constraint", variable_role="constraint", definition="constraint definition"),
        ]
        controversy_cards = [
            ControversyCard(question="Is it causal?", sides=["yes", "no"]),
        ]

        axis_cards = generate_axes(
            question_card,
            knowledge_cards=knowledge_cards,
            variable_cards=variable_cards,
            controversy_cards=controversy_cards,
        )

        self.assertGreaterEqual(len(axis_cards), 4)
        self.assertTrue(all(axis.supporting_card_ids for axis in axis_cards))

        notes = expand_axis(
            axis_cards[0],
            question_card,
            knowledge_cards=knowledge_cards,
            variable_cards=variable_cards,
            controversy_cards=controversy_cards,
        )

        self.assertEqual(len(notes), 1)
        self.assertTrue(all(note.supporting_card_ids == axis_cards[0].supporting_card_ids for note in notes))
        self.assertTrue(all(any("Support card" in item for item in note.evidence_needed) for note in notes))


if __name__ == "__main__":
    unittest.main()
