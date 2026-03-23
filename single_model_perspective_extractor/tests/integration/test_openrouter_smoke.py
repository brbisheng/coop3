import io
import json
import os
import unittest
from contextlib import redirect_stderr, redirect_stdout

from perspective_extractor import cli


_OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()
_OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4.1-mini").strip()
_PROBLEM_TEXT = (
    "How would a shutdown at the main import terminal affect regional fuel supply, "
    "alternate depots, and retail prices over the next 30 days?"
)


def _run_cli(argv: list[str]) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        exit_code = cli.main(argv)
    return exit_code, stdout.getvalue(), stderr.getvalue()


@unittest.skipUnless(_OPENROUTER_API_KEY, "OPENROUTER_API_KEY is required for live OpenRouter smoke tests")
class OpenRouterSmokeIntegrationTests(unittest.TestCase):
    def test_cli_requires_model_for_live_execution(self) -> None:
        exit_code, _stdout, stderr = _run_cli([
            "decompose",
            "--api-key",
            _OPENROUTER_API_KEY,
            "--question",
            _PROBLEM_TEXT,
        ])

        self.assertEqual(exit_code, 2)
        self.assertIn("Provide --model", stderr)

    def test_cli_requires_api_key_for_live_execution(self) -> None:
        previous_api_key = os.environ.get("OPENROUTER_API_KEY")
        os.environ.pop("OPENROUTER_API_KEY", None)
        try:
            exit_code, _stdout, stderr = _run_cli([
                "decompose",
                "--model",
                _OPENROUTER_MODEL,
                "--question",
                _PROBLEM_TEXT,
            ])
        finally:
            if previous_api_key is not None:
                os.environ["OPENROUTER_API_KEY"] = previous_api_key

        self.assertEqual(exit_code, 2)
        self.assertIn("OPENROUTER_API_KEY", stderr)

    def test_decompose_live_run_returns_non_empty_required_fields(self) -> None:
        exit_code, stdout, stderr = _run_cli([
            "decompose",
            "--model",
            _OPENROUTER_MODEL,
            "--api-key",
            _OPENROUTER_API_KEY,
            "--question",
            _PROBLEM_TEXT,
        ])

        self.assertEqual(exit_code, 0, stderr)
        payload = json.loads(stdout)
        self.assertTrue(payload["problem_frame"]["core_question"])
        self.assertGreaterEqual(len(payload["actor_cards"]), 1)
        self.assertGreaterEqual(len(payload["node_cards"]), 1)
        self.assertGreaterEqual(len(payload["constraint_cards"]), 1)

    def test_trace_live_run_returns_non_empty_required_fields(self) -> None:
        exit_code, stdout, stderr = _run_cli([
            "trace",
            "--model",
            _OPENROUTER_MODEL,
            "--api-key",
            _OPENROUTER_API_KEY,
            "--question",
            _PROBLEM_TEXT,
        ])

        self.assertEqual(exit_code, 0, stderr)
        payload = json.loads(stdout)
        self.assertTrue(payload["trace_target"])
        self.assertEqual([step["order"] for step in payload["consequence_chain"]], [1, 2, 3])
        self.assertTrue(all(step["event"] for step in payload["consequence_chain"]))
        self.assertTrue(all(step["mechanism"] for step in payload["consequence_chain"]))

    def test_final_live_run_returns_core_report_sections(self) -> None:
        exit_code, stdout, stderr = _run_cli([
            "final",
            "--model",
            _OPENROUTER_MODEL,
            "--api-key",
            _OPENROUTER_API_KEY,
            "--question",
            _PROBLEM_TEXT,
        ])

        self.assertEqual(exit_code, 0, stderr)
        payload = json.loads(stdout)
        required_sections = [
            "key_actors_and_nodes",
            "critical_mechanism_chains",
            "competing_explanations_and_divergent_predictions",
            "likely_surprises",
            "main_uncertainties_and_hidden_assumptions",
            "executive_summary",
        ]
        for section in required_sections:
            self.assertIn(section, payload)
        self.assertTrue(payload["executive_summary"])
        self.assertGreaterEqual(len(payload["key_actors_and_nodes"]), 1)
        self.assertGreaterEqual(len(payload["critical_mechanism_chains"]), 3)
        self.assertGreaterEqual(
            len(payload["competing_explanations_and_divergent_predictions"]),
            2,
        )
        self.assertGreaterEqual(len(payload["likely_surprises"]), 1)
        self.assertGreaterEqual(
            len(payload["main_uncertainties_and_hidden_assumptions"]),
            1,
        )


if __name__ == "__main__":
    unittest.main()
