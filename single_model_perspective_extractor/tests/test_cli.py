import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from perspective_extractor import cli


class DecomposeCliTests(unittest.TestCase):
    def test_decompose_defaults_to_json_output(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = cli.main(
                [
                    "decompose",
                    "How would a shutdown at the main import terminal affect regional fuel supply?",
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
            input_path.write_text(
                "How would a shutdown at the main import terminal affect regional fuel supply?",
                encoding="utf-8",
            )
            buffer = io.StringIO()

            with redirect_stdout(buffer):
                exit_code = cli.main(
                    [
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


class TraceCliTests(unittest.TestCase):
    def test_trace_defaults_to_json_with_explicit_chain(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = cli.main(
                [
                    "trace",
                    "How would a shutdown at the main import terminal affect regional fuel supply?",
                ]
            )

        payload = json.loads(buffer.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertIn("trace_target", payload)
        self.assertEqual([step["order"] for step in payload["consequence_chain"]], [1, 2, 3])
        self.assertTrue(all(step["mechanism"] for step in payload["consequence_chain"]))


class CompeteCliTests(unittest.TestCase):
    def test_compete_defaults_to_json_with_two_divergent_mechanisms(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = cli.main(
                [
                    "compete",
                    "How would a shutdown at the main import terminal affect regional fuel supply?",
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


class StressCliTests(unittest.TestCase):
    def test_stress_defaults_to_json_with_ledgers(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = cli.main(
                [
                    "stress",
                    "How would a shutdown at the main import terminal affect regional fuel supply?",
                ]
            )

        payload = json.loads(buffer.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertGreaterEqual(len(payload["falsification_ledger"]), 1)
        self.assertGreaterEqual(len(payload["surprise_ledger"]), 1)
        self.assertTrue(payload["falsification_ledger"][0]["hidden_assumption"])
        self.assertTrue(payload["surprise_ledger"][0]["surprise"])


class FinalCliTests(unittest.TestCase):
    def test_final_defaults_to_json_with_dense_report_sections(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = cli.main(
                [
                    "final",
                    "How would a shutdown at the main import terminal affect regional fuel supply?",
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


if __name__ == "__main__":
    unittest.main()
