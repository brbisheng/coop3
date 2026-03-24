import unittest
from unittest.mock import patch

from perspective_extractor.baseline import build_baseline_prompt, run_baseline_analysis


class BaselineModuleTests(unittest.TestCase):
    def test_prompt_requires_non_empty_question(self) -> None:
        with self.assertRaises(ValueError):
            build_baseline_prompt("   ")

    def test_prompt_includes_question_and_baseline_instruction(self) -> None:
        prompt = build_baseline_prompt("How does rerouting affect inland bottlenecks?")
        self.assertIn("baseline path", prompt)
        self.assertIn("Question:", prompt)
        self.assertIn("rerouting", prompt)

    def test_live_runner_calls_openrouter_and_returns_trimmed_markdown(self) -> None:
        with patch("perspective_extractor.baseline.call_openrouter", return_value="  # Analysis\ntext\n  ") as mocked_call:
            result = run_baseline_analysis(
                "How does rerouting affect inland bottlenecks?",
                model="openrouter/test",
                api_key="key",
            )

        self.assertEqual(result, "# Analysis\ntext")
        mocked_call.assert_called_once()
        _, kwargs = mocked_call.call_args
        self.assertEqual(kwargs["model"], "openrouter/test")
        self.assertEqual(kwargs["api_key"], "key")
        self.assertEqual(kwargs["temperature"], 0.0)


if __name__ == "__main__":
    unittest.main()
