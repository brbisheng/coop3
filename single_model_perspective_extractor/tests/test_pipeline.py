import unittest
from unittest.mock import patch

from perspective_extractor.models import (
    AxisCard,
    ControversyCard,
    KnowledgeCard,
    PerspectiveNote,
    ReviewDecision,
    PipelineResult,
    QuestionCard,
    VariableCard,
)
from perspective_extractor.pipeline import (
    PipelinePromptConfig,
    expand_axes,
    expand_axis,
    generate_axes,
    run_pipeline,
)


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

    def test_expand_axes_runs_each_axis_with_only_its_support_cards_and_stable_note_ids(self) -> None:
        question_card = QuestionCard(
            raw_question="How does remote work affect employee productivity?",
            cleaned_question="How does remote work affect employee productivity?",
            actor_entity="remote work",
            outcome_variable="employee productivity",
            domain_hint="business",
        )
        knowledge_cards = [
            KnowledgeCard(title="Question framing", content="frame"),
            KnowledgeCard(title="Mechanism map", content="channels"),
        ]
        variable_cards = [
            VariableCard(name="remote work", variable_role="actor", definition="actor"),
            VariableCard(name="employee productivity", variable_role="outcome", definition="outcome"),
        ]
        controversy_cards = [
            ControversyCard(question="Is it causal?", sides=["yes", "no"]),
        ]
        axis_cards = [
            AxisCard(
                name="framing lens",
                axis_type="framing",
                focus="focus one",
                how_is_it_distinct="distinct one",
                axis_id="axis_custom_one",
                supporting_card_ids=[knowledge_cards[0].knowledge_id, variable_cards[0].variable_id],
            ),
            AxisCard(
                name="causal lens",
                axis_type="mechanism",
                focus="focus two",
                how_is_it_distinct="distinct two",
                axis_id="axis_custom_two",
                supporting_card_ids=[knowledge_cards[1].knowledge_id, controversy_cards[0].controversy_id],
            ),
        ]

        captured_contexts: list[list[str]] = []

        def expand_note_stub(question: QuestionCard, axis: AxisCard, *, context_cards: list[object]) -> PerspectiveNote:
            captured_contexts.append(
                [
                    getattr(card, "knowledge_id", None)
                    or getattr(card, "variable_id", None)
                    or getattr(card, "controversy_id", None)
                    for card in context_cards
                ]
            )
            return PerspectiveNote(
                axis_id=axis.axis_id,
                core_claim=f"claim for {axis.name}",
                reasoning="reasoning",
                note_id="note_random",
                supporting_card_ids=[
                    getattr(card, "knowledge_id", None)
                    or getattr(card, "variable_id", None)
                    or getattr(card, "controversy_id", None)
                    for card in context_cards
                ],
            )

        with patch("perspective_extractor.pipeline.expand_axis_note", side_effect=expand_note_stub):
            notes = expand_axes(
                axis_cards,
                question_card,
                knowledge_cards=knowledge_cards,
                variable_cards=variable_cards,
                controversy_cards=controversy_cards,
            )

        self.assertEqual(
            captured_contexts,
            [
                [knowledge_cards[0].knowledge_id, variable_cards[0].variable_id],
                [knowledge_cards[1].knowledge_id, controversy_cards[0].controversy_id],
            ],
        )
        self.assertEqual([note.note_id for note in notes], ["note_custom_one", "note_custom_two"])
        self.assertEqual([note.axis_id for note in notes], ["axis_custom_one", "axis_custom_two"])

    def test_run_pipeline_returns_review_partitions_for_debugging(self) -> None:
        question_card = QuestionCard(
            raw_question="How does remote work affect employee productivity?",
            cleaned_question="How does remote work affect employee productivity?",
            actor_entity="remote work",
            outcome_variable="employee productivity",
            domain_hint="business",
        )
        axis_cards = [
            AxisCard(
                name="framing lens",
                axis_type="framing",
                focus="focus one",
                how_is_it_distinct="distinct one",
                axis_id="axis_keep",
            ),
            AxisCard(
                name="measurement lens",
                axis_type="measurement",
                focus="focus two",
                how_is_it_distinct="distinct two",
                axis_id="axis_merge",
            ),
            AxisCard(
                name="scope lens",
                axis_type="scope",
                focus="focus three",
                how_is_it_distinct="distinct three",
                axis_id="axis_rewrite",
            ),
            AxisCard(
                name="boundary lens",
                axis_type="boundary",
                focus="focus four",
                how_is_it_distinct="distinct four",
                axis_id="axis_drop",
            ),
        ]
        notes = [
            PerspectiveNote(axis_id="axis_keep", note_id="note_keep", core_claim="claim keep", reasoning="reasoning"),
            PerspectiveNote(axis_id="axis_merge", note_id="note_merge", core_claim="claim merge", reasoning="reasoning"),
            PerspectiveNote(axis_id="axis_rewrite", note_id="note_rewrite", core_claim="claim rewrite", reasoning="reasoning"),
            PerspectiveNote(axis_id="axis_drop", note_id="note_drop", core_claim="claim drop", reasoning="reasoning"),
        ]
        review_decisions = [
            ReviewDecision(target_note_id="note_keep", action="keep", reason="distinct"),
            ReviewDecision(
                target_note_id="note_merge",
                action="merge",
                reason="near duplicate",
                merge_target_note_id="note_keep",
            ),
            ReviewDecision(target_note_id="note_rewrite", action="rewrite", reason="needs specificity"),
            ReviewDecision(target_note_id="note_drop", action="drop", reason="no unique contribution"),
        ]

        with (
            patch("perspective_extractor.pipeline.normalize_question", return_value=question_card),
            patch("perspective_extractor.pipeline.generate_knowledge_cards", return_value=[]),
            patch("perspective_extractor.pipeline.generate_variable_cards", return_value=[]),
            patch("perspective_extractor.pipeline.generate_controversy_cards", return_value=[]),
            patch("perspective_extractor.pipeline.generate_axes", return_value=axis_cards),
            patch("perspective_extractor.pipeline.expand_axes", return_value=notes),
            patch("perspective_extractor.pipeline.review_notes", return_value=review_decisions),
        ):
            result = run_pipeline(question_card.raw_question)

        self.assertEqual([note.note_id for note in result.kept_notes], ["note_keep"])
        self.assertEqual([note.note_id for note in result.merged_notes], ["note_merge"])
        self.assertEqual([note.note_id for note in result.rewrite_notes], ["note_rewrite"])
        self.assertEqual([note.note_id for note in result.dropped_notes], ["note_drop"])
        self.assertEqual([note.note_id for note in result.perspective_map.kept_notes], ["note_keep"])


class PipelinePromptConfigTests(unittest.TestCase):
    def test_pipeline_prompt_config_accepts_reserved_variants(self) -> None:
        config = PipelinePromptConfig(prompt_variant="language_lens")

        self.assertEqual(config.resolved_prompt_variant, "language_lens")

    def test_run_pipeline_validates_reserved_variant_aliases(self) -> None:
        with self.assertRaisesRegex(ValueError, "prompt_variant and lens must match"):
            run_pipeline("How does remote work affect productivity?", prompt_variant="language_lens", lens="cultural_lens")

    def test_run_pipeline_accepts_future_lens_placeholders_without_behavior_change(self) -> None:
        with (
            patch("perspective_extractor.pipeline.normalize_question") as normalize_mock,
            patch("perspective_extractor.pipeline.generate_knowledge_cards", return_value=[]),
            patch("perspective_extractor.pipeline.generate_variable_cards", return_value=[]),
            patch("perspective_extractor.pipeline.generate_controversy_cards", return_value=[]),
            patch("perspective_extractor.pipeline.generate_axes", return_value=[]),
            patch("perspective_extractor.pipeline.review_notes", return_value=[]),
            patch("perspective_extractor.pipeline.build_perspective_map", return_value=None),
        ):
            normalize_mock.return_value = QuestionCard(
                raw_question="How does remote work affect productivity?",
                cleaned_question="How does remote work affect productivity?",
                actor_entity="remote work",
                outcome_variable="productivity",
                domain_hint="business",
            )

            result = run_pipeline(
                "How does remote work affect productivity?",
                lens="institutional_lens",
            )

        normalize_mock.assert_called_once_with("How does remote work affect productivity?")
        self.assertIsInstance(result, PipelineResult)


if __name__ == "__main__":
    unittest.main()
