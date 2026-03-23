import json
import unittest

from perspective_extractor.axes_stage import build_axes_stage_prompt, run_axes_stage
from perspective_extractor.expand_stage import build_expand_stage_prompt, run_expand_stage
from perspective_extractor.fixtures import (
    build_axes_stage_fixture,
    build_expand_stage_fixture,
    build_normalize_stage_fixture,
)
from perspective_extractor.llm import ModelInvocationError
from perspective_extractor.normalize_stage import build_normalize_stage_prompt, run_normalize_stage
from perspective_extractor.models import AxisCard, KnowledgeCard, QuestionCard, VariableCard


class StageModuleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.question_card = QuestionCard(
            raw_question="How does remote work affect employee productivity?",
            cleaned_question="How does remote work affect employee productivity?",
            actor_entity="remote work",
            outcome_variable="employee productivity",
            domain_hint="business",
            assumptions=["Remote work may influence productivity."],
            missing_pieces=["Time frame is not specified."],
        )
        self.axis_card = AxisCard(
            name="causal pathways",
            axis_type="mechanism",
            focus="Trace the channels through which remote work could shape employee productivity.",
            how_is_it_distinct="Focuses on process rather than only measurement or scope.",
            axis_id="axis_demo",
        )
        self.knowledge_card = KnowledgeCard(
            title="Mechanism map",
            content="Map the direct and indirect channels.",
        )
        self.variable_card = VariableCard(
            name="remote work intensity",
            variable_role="actor",
            definition="How much remote work is used.",
        )

    def test_run_normalize_stage_requires_an_explicit_live_model(self) -> None:
        with self.assertRaises(ModelInvocationError):
            run_normalize_stage("How does remote work affect employee productivity?")

    def test_normalize_stage_fixture_is_available_only_via_fixture_helpers(self) -> None:
        result = json.loads(
            build_normalize_stage_fixture("How does remote work affect employee productivity?")
        )

        self.assertEqual(result["raw_question"], "How does remote work affect employee productivity?")
        self.assertEqual(result["actor_entity"], "demo actor")
        self.assertIn("missing_pieces", result)

    def test_build_normalize_stage_prompt_keeps_requirements_visible(self) -> None:
        stage_prompt = build_normalize_stage_prompt("How does remote work affect employee productivity?")

        self.assertIn("Return JSON with exactly these keys", stage_prompt.prompt)
        self.assertIn("missing_pieces", stage_prompt.prompt)
        self.assertEqual(stage_prompt.stage_name, "normalize")

    def test_run_axes_stage_passes_the_explicit_stage_prompt_to_a_live_callback(self) -> None:
        captured = {}

        def fake_model(stage_prompt):
            captured["prompt"] = stage_prompt.prompt
            captured["stage_name"] = stage_prompt.stage_name
            return '{"axes": []}'

        result = run_axes_stage(
            self.question_card,
            knowledge_cards=[self.knowledge_card],
            variable_cards=[self.variable_card],
            call_model=fake_model,
        )

        self.assertEqual(result, '{"axes": []}')
        self.assertEqual(captured["stage_name"], "axes")
        self.assertIn("support summary", captured["prompt"])
        self.assertIn("Generate perspective axes", captured["prompt"])

    def test_axes_stage_demo_fixture_is_runnable_json(self) -> None:
        stage_prompt = build_axes_stage_prompt(
            self.question_card,
            knowledge_cards=[self.knowledge_card],
            variable_cards=[self.variable_card],
        )

        result = json.loads(
            build_axes_stage_fixture(
                self.question_card,
                knowledge_cards=[self.knowledge_card],
                variable_cards=[self.variable_card],
            )
        )

        self.assertEqual(stage_prompt.stage_name, "axes")
        self.assertEqual(len(result["axes"]), 8)
        self.assertTrue(all("how_is_it_distinct" in axis for axis in result["axes"]))

    def test_expand_stage_prompt_and_demo_fixture_stay_axis_local(self) -> None:
        stage_prompt = build_expand_stage_prompt(
            self.question_card,
            self.axis_card,
            context_cards=[self.knowledge_card, self.variable_card],
        )
        result = json.loads(
            build_expand_stage_fixture(
                self.question_card,
                self.axis_card,
                context_cards=[self.knowledge_card, self.variable_card],
            )
        )

        self.assertIn("Write one note for this axis only", stage_prompt.prompt)
        self.assertIn(self.axis_card.axis_id, stage_prompt.prompt)
        self.assertEqual(result["axis_id"], "axis_demo")
        self.assertEqual(
            result["supporting_card_ids"],
            [self.knowledge_card.knowledge_id, self.variable_card.variable_id],
        )


if __name__ == "__main__":
    unittest.main()
