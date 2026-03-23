import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from perspective_extractor import cli
from perspective_extractor.compete import build_competing_mechanisms
from perspective_extractor.decompose import decompose_problem
from perspective_extractor.final import build_final_report
from perspective_extractor.stress import build_stress_test
from perspective_extractor.trace import build_trace


class _PatchedCliTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.problem_text = (
            "How would a shutdown at the main import terminal affect regional fuel supply?"
        )
        self.decompose_result = decompose_problem(self.problem_text)
        self.trace_result = build_trace(self.decompose_result)
        self.compete_result = build_competing_mechanisms(self.decompose_result, self.trace_result)
        self.stress_result = build_stress_test(
            self.decompose_result,
            self.trace_result,
            self.compete_result,
        )
        self.final_report = build_final_report(
            self.decompose_result,
            self.trace_result,
            self.compete_result,
            self.stress_result,
        )

        self.patchers = [
            patch.object(cli, "run_decompose", side_effect=lambda problem_text, **_: decompose_problem(problem_text)),
            patch.object(
                cli,
                "run_trace",
                side_effect=lambda decompose_result, **kwargs: build_trace(
                    decompose_result,
                    trace_target=kwargs.get("trace_target"),
                ),
            ),
            patch.object(
                cli,
                "run_compete",
                side_effect=lambda decompose_result, trace_result, **_: build_competing_mechanisms(
                    decompose_result,
                    trace_result,
                ),
            ),
            patch.object(
                cli,
                "run_stress",
                side_effect=lambda decompose_result, trace_result, compete_result, **_: build_stress_test(
                    decompose_result,
                    trace_result,
                    compete_result,
                ),
            ),
            patch.object(
                cli,
                "run_final",
                side_effect=lambda decompose_result, trace_result, compete_result, stress_result, **_: build_final_report(
                    decompose_result,
                    trace_result,
                    compete_result,
                    stress_result,
                ),
            ),
        ]
        for patcher in self.patchers:
            patcher.start()
        self.addCleanup(lambda: [patcher.stop() for patcher in reversed(self.patchers)])


class DecomposeCliTests(_PatchedCliTestCase):
    def test_decompose_defaults_to_json_output(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = cli.main(
                [
                    "--model",
                    "openrouter/test-model",
                    "--api-key",
                    "test-key",
                    "decompose",
                    self.problem_text,
                ]
            )

        payload = json.loads(buffer.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertIn("problem_frame", payload)
        self.assertIn("actor_cards", payload)
        self.assertIn("node_cards", payload)
        self.assertIn("constraint_cards", payload)
        self.assertTrue(payload["problem_frame"]["core_question"])

    def test_decompose_can_read_input_file_and_save_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "problem.txt"
            output_path = Path(tmp_dir) / "artifacts" / "decompose.json"
            input_path.write_text(self.problem_text, encoding="utf-8")
            buffer = io.StringIO()

            with redirect_stdout(buffer):
                exit_code = cli.main(
                    [
                        "--model",
                        "openrouter/test-model",
                        "--api-key",
                        "test-key",
                        "decompose",
                        "--input-file",
                        str(input_path),
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            printed_payload = json.loads(buffer.getvalue())
            saved_payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(saved_payload, printed_payload)


class TraceCliTests(_PatchedCliTestCase):
    def test_trace_defaults_to_json_with_explicit_chain(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = cli.main(
                [
                    "--model",
                    "openrouter/test-model",
                    "--api-key",
                    "test-key",
                    "trace",
                    self.problem_text,
                ]
            )

        payload = json.loads(buffer.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertIn("trace_target", payload)
        self.assertEqual([step["order"] for step in payload["consequence_chain"]], [1, 2, 3])
        self.assertTrue(all(step["mechanism"] for step in payload["consequence_chain"]))


class CompeteCliTests(_PatchedCliTestCase):
    def test_compete_defaults_to_json_with_two_divergent_mechanisms(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = cli.main(
                [
                    "--model",
                    "openrouter/test-model",
                    "--api-key",
                    "test-key",
                    "compete",
                    self.problem_text,
                ]
            )

        payload = json.loads(buffer.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(len(payload["competing_mechanisms"]), 2)
        self.assertIn("divergence_note", payload)
        self.assertNotEqual(
            payload["competing_mechanisms"][0]["prediction"],
            payload["competing_mechanisms"][1]["prediction"],
        )


class StressCliTests(_PatchedCliTestCase):
    def test_stress_defaults_to_json_with_ledgers(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = cli.main(
                [
                    "--model",
                    "openrouter/test-model",
                    "--api-key",
                    "test-key",
                    "stress",
                    self.problem_text,
                ]
            )

        payload = json.loads(buffer.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertGreaterEqual(len(payload["falsification_ledger"]), 1)
        self.assertGreaterEqual(len(payload["surprise_ledger"]), 1)
        self.assertTrue(payload["falsification_ledger"][0]["hidden_assumption"])
        self.assertTrue(payload["surprise_ledger"][0]["surprise"])


class FinalCliTests(_PatchedCliTestCase):
    def test_final_defaults_to_json_with_dense_report_sections(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = cli.main(
                [
                    "--model",
                    "openrouter/test-model",
                    "--api-key",
                    "test-key",
                    "final",
                    self.problem_text,
                ]
            )

        payload = json.loads(buffer.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertIn("key_actors_and_nodes", payload)
        self.assertIn("critical_mechanism_chains", payload)
        self.assertIn("competing_explanations_and_divergent_predictions", payload)
        self.assertIn("likely_surprises", payload)
        self.assertIn("main_uncertainties_and_hidden_assumptions", payload)
        self.assertIn("executive_summary", payload)
        self.assertEqual(len(payload["critical_mechanism_chains"]), 3)


class CliModelConfigTests(_PatchedCliTestCase):
    def test_cli_requires_model(self) -> None:
        stderr = io.StringIO()

        with redirect_stdout(io.StringIO()), redirect_stderr(stderr):
            exit_code = cli.main(["decompose", "How does remote work affect productivity?"])

        self.assertEqual(exit_code, 2)
        self.assertIn("Provide --model", stderr.getvalue())

    def test_cli_accepts_api_key_from_environment(self) -> None:
        buffer = io.StringIO()
        previous_api_key = os.environ.get("OPENROUTER_API_KEY")
        os.environ["OPENROUTER_API_KEY"] = "env-test-key"
        try:
            with redirect_stdout(buffer):
                exit_code = cli.main(
                    [
                        "--model",
                        "openrouter/test-model",
                        "decompose",
                        self.problem_text,
                    ]
                )
        finally:
            if previous_api_key is None:
                os.environ.pop("OPENROUTER_API_KEY", None)
            else:
                os.environ["OPENROUTER_API_KEY"] = previous_api_key

        self.assertEqual(exit_code, 0)
        payload = json.loads(buffer.getvalue())
        self.assertIn("problem_frame", payload)


if __name__ == "__main__":
    unittest.main()
