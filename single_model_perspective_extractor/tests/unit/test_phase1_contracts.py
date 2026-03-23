import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from perspective_extractor.compete import build_competing_mechanisms
from perspective_extractor.decompose import (
    DECOMPOSE_SCHEMA,
    build_decompose_prompt,
    decompose_problem,
    run_decompose,
    save_decompose_result,
)
from perspective_extractor.final import FINAL_SCHEMA, build_final_prompt, build_final_report, run_final
from perspective_extractor.stress import build_stress_test
from perspective_extractor.trace import TRACE_SCHEMA, build_trace, build_trace_prompt, run_trace


class Phase1ContractUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.problem_text = (
            "How would a shutdown at the main import terminal affect regional fuel supply, "
            "alternate depots, and retail prices over the next 30 days?"
        )
        self.decompose_result = decompose_problem(self.problem_text)
        self.trace_result = build_trace(self.decompose_result)
        self.compete_result = build_competing_mechanisms(
            self.decompose_result,
            self.trace_result,
        )
        self.stress_result = build_stress_test(
            self.decompose_result,
            self.trace_result,
            self.compete_result,
        )

    def test_phase1_schemas_keep_required_stage_fields(self) -> None:
        self.assertEqual(
            DECOMPOSE_SCHEMA["required"],
            ["problem_frame", "actor_cards", "node_cards", "constraint_cards"],
        )
        self.assertEqual(TRACE_SCHEMA["required"], ["trace_target", "consequence_chain"])
        self.assertEqual(
            FINAL_SCHEMA["required"],
            [
                "key_actors_and_nodes",
                "critical_mechanism_chains",
                "competing_explanations_and_divergent_predictions",
                "likely_surprises",
                "main_uncertainties_and_hidden_assumptions",
                "executive_summary",
            ],
        )

    def test_prompt_builders_embed_schema_and_upstream_artifacts(self) -> None:
        decompose_prompt = build_decompose_prompt(self.problem_text)
        trace_prompt = build_trace_prompt(self.decompose_result, trace_target="Fuel disruption")
        final_prompt = build_final_prompt(
            self.decompose_result,
            self.trace_result,
            self.compete_result,
            self.stress_result,
        )

        self.assertIn('"problem_frame"', decompose_prompt)
        self.assertIn(self.problem_text, decompose_prompt)
        self.assertIn('"trace_target"', trace_prompt)
        self.assertIn("Fuel disruption", trace_prompt)
        self.assertIn(self.decompose_result.problem_frame.core_question, trace_prompt)
        self.assertIn('"executive_summary"', final_prompt)
        self.assertIn("Decompose artifact:", final_prompt)
        self.assertIn("Trace artifact:", final_prompt)
        self.assertIn("Stress artifact:", final_prompt)

    def test_artifact_helpers_save_structured_json_to_disk(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "artifacts" / "decompose.json"
            saved_path = save_decompose_result(self.problem_text, output_path)

            self.assertEqual(saved_path, output_path)
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertTrue(payload["problem_frame"]["core_question"])
            self.assertGreaterEqual(len(payload["actor_cards"]), 1)
            self.assertGreaterEqual(len(payload["node_cards"]), 1)
            self.assertGreaterEqual(len(payload["constraint_cards"]), 1)

    def test_fake_model_responses_parse_into_decompose_trace_and_final_outputs(self) -> None:
        decompose_payload = {
            "problem_frame": {
                "core_question": self.decompose_result.problem_frame.core_question,
                "decision_or_analysis_target": self.decompose_result.problem_frame.decision_or_analysis_target,
                "scope_notes": self.decompose_result.problem_frame.scope_notes,
            },
            "actor_cards": [
                {
                    "name": "terminal operator",
                    "type": "firm",
                    "role": "Runs the import terminal.",
                    "goal_guess": "Keep throughput flowing.",
                    "why_relevant": "The outage starts here.",
                }
            ],
            "node_cards": [
                {
                    "name": "main import terminal",
                    "type": "facility",
                    "function": "Receives and stores inbound fuel.",
                    "why_relevant": "It is the focal bottleneck.",
                }
            ],
            "constraint_cards": [
                {
                    "constraint": "Terminal throughput is unavailable.",
                    "applies_to": ["terminal operator", "main import terminal"],
                    "why_it_matters": "It cuts regional supply immediately.",
                }
            ],
        }
        trace_payload = {
            "trace_target": "Regional fuel disruption",
            "consequence_chain": [
                {
                    "order": 1,
                    "event": "The outage removes primary inbound supply.",
                    "mechanism": "Capacity disappears at the terminal.",
                    "affected_entities": ["terminal operator", "main import terminal"],
                },
                {
                    "order": 2,
                    "event": "Alternate depots absorb rerouted flows.",
                    "mechanism": "Substitution spreads congestion into backups.",
                    "affected_entities": ["alternate depots", "truck fleets"],
                },
                {
                    "order": 3,
                    "event": "Retail prices rise after inventories tighten.",
                    "mechanism": "Scarcity passes through to downstream buyers.",
                    "affected_entities": ["retail stations", "consumers"],
                },
            ],
        }
        final_payload = {
            "key_actors_and_nodes": ["Terminal operator controls the focal node."],
            "critical_mechanism_chains": ["1st-order step...", "2nd-order step...", "3rd-order step..."],
            "competing_explanations_and_divergent_predictions": ["Mechanism A...", "Mechanism B..."],
            "likely_surprises": ["A depot becomes the new bottleneck."],
            "main_uncertainties_and_hidden_assumptions": ["The terminal is not the only bottleneck."],
            "executive_summary": "The outage first removes import capacity, then rerouting congests substitutes, then retail prices rise.",
        }

        with patch("perspective_extractor.decompose.call_openrouter", return_value=json.dumps(decompose_payload)):
            decompose_result = run_decompose(self.problem_text, model="openrouter/test", api_key="key")
        with patch("perspective_extractor.trace.call_openrouter", return_value=json.dumps(trace_payload)):
            trace_result = run_trace(decompose_result, model="openrouter/test", api_key="key")
        with patch("perspective_extractor.final.call_openrouter", return_value=json.dumps(final_payload)):
            final_result = run_final(
                decompose_result,
                trace_result,
                self.compete_result,
                self.stress_result,
                model="openrouter/test",
                api_key="key",
            )

        self.assertEqual(decompose_result.actor_cards[0].name, "terminal operator")
        self.assertEqual([step.order for step in trace_result.consequence_chain], [1, 2, 3])
        self.assertTrue(final_result.executive_summary)
        self.assertIn("key_actors_and_nodes", final_payload)

    def test_fixture_path_stays_explicit_separate_from_live_path(self) -> None:
        final_report = build_final_report(
            self.decompose_result,
            self.trace_result,
            self.compete_result,
            self.stress_result,
        )

        self.assertTrue(final_report.executive_summary)
        self.assertEqual(len(final_report.critical_mechanism_chains), 3)


if __name__ == "__main__":
    unittest.main()
