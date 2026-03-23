import json
import unittest
from unittest.mock import patch

from perspective_extractor.compete import build_compete_prompt, run_compete
from perspective_extractor.decompose import build_decompose_prompt, run_decompose
from perspective_extractor.final import build_final_prompt, run_final
from perspective_extractor.pipeline import run_phase1_pipeline
from perspective_extractor.stress import build_stress_prompt, run_stress
from perspective_extractor.trace import build_trace_prompt, run_trace


class Phase1LiveModuleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.problem_text = (
            "How would a shutdown at the main import terminal affect regional fuel supply, "
            "alternate depots, and retail prices over the next 30 days?"
        )

    def test_decompose_module_owns_prompt_and_live_runner(self) -> None:
        prompt = build_decompose_prompt(self.problem_text)
        self.assertIn("Schema:", prompt)
        self.assertIn("actor_cards", prompt)

        response_payload = {
            "problem_frame": {
                "core_question": "How would a shutdown at the main import terminal affect regional fuel supply, alternate depots, and retail prices over the next 30 days?",
                "decision_or_analysis_target": "Map the actors, nodes, and constraints that control near-term fuel disruption.",
                "scope_notes": ["30-day horizon is explicit."],
            },
            "actor_cards": [
                {
                    "name": "terminal operator",
                    "type": "firm",
                    "role": "Runs the import terminal.",
                    "goal_guess": "Keep supply flowing.",
                    "why_relevant": "Its outage triggers the shock.",
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
                    "why_it_matters": "It cuts immediate supply into the region.",
                }
            ],
        }
        with patch("perspective_extractor.decompose.call_openrouter", return_value=json.dumps(response_payload)):
            result = run_decompose(self.problem_text, model="openrouter/test", api_key="key")

        self.assertEqual(result.problem_frame.scope_notes, ["30-day horizon is explicit."])
        self.assertEqual(result.actor_cards[0].name, "terminal operator")

    def test_downstream_live_modules_parse_json_into_phase1_models(self) -> None:
        decompose_result = run_phase1_pipeline(self.problem_text).decompose_result
        trace_payload = {
            "trace_target": "Regional fuel supply disruption",
            "consequence_chain": [
                {
                    "order": 1,
                    "event": "The terminal outage blocks primary inbound supply.",
                    "mechanism": "Immediate capacity loss hits the import node.",
                    "affected_entities": ["main import terminal", "terminal operator"],
                },
                {
                    "order": 2,
                    "event": "Alternate depots absorb rerouted flows.",
                    "mechanism": "Rerouting spreads congestion into substitute storage and trucking.",
                    "affected_entities": ["alternate depots", "truck fleets"],
                },
                {
                    "order": 3,
                    "event": "Retail prices rise after inventories tighten.",
                    "mechanism": "Downstream scarcity passes through to retail markets.",
                    "affected_entities": ["retail stations", "consumers"],
                },
            ],
        }
        compete_payload = {
            "competing_mechanisms": [
                {
                    "label": "A",
                    "core_mechanism": "Physical capacity loss dominates.",
                    "what_it_explains": "Why shortages follow the outage.",
                    "prediction": "Prices normalize quickly after the terminal reopens.",
                    "observable_signal": "Depot congestion clears with terminal recovery.",
                },
                {
                    "label": "B",
                    "core_mechanism": "Behavioral hoarding and coordination failures dominate.",
                    "what_it_explains": "Why disruption persists after reopening.",
                    "prediction": "Shortages continue even after throughput returns.",
                    "observable_signal": "Retail allocations stay distorted after node recovery.",
                },
            ],
            "divergence_note": "A predicts quick normalization; B predicts persistence.",
        }
        stress_payload = {
            "falsification_ledger": [
                {
                    "claim_under_stress": "Prices normalize quickly after the terminal reopens.",
                    "hidden_assumption": "The terminal is the only real bottleneck.",
                    "how_it_could_fail": "Truck or depot limits remain binding.",
                    "what_evidence_would_break_it": "Persistent depot queues after reopening.",
                }
            ],
            "surprise_ledger": [
                {
                    "surprise": "A depot becomes the new bottleneck.",
                    "why_shallow_analysis_misses_it": "Attention stays on the headline outage.",
                    "what_actor_or_node_it_depends_on": ["alternate depots", "truck fleets"],
                }
            ],
        }
        final_payload = {
            "key_actors_and_nodes": ["Terminal operator controls the focal node."],
            "critical_mechanism_chains": ["1st-order step...", "2nd-order step...", "3rd-order step..."],
            "competing_explanations_and_divergent_predictions": ["Mechanism A...", "Mechanism B..."],
            "likely_surprises": ["A depot becomes the new bottleneck."],
            "main_uncertainties_and_hidden_assumptions": ["The terminal is the only real bottleneck."],
            "executive_summary": "The outage first removes import capacity, then rerouting congests substitutes, then retail prices rise.",
        }

        self.assertIn("consequence_chain", build_trace_prompt(decompose_result))
        self.assertIn("divergent predictions", build_compete_prompt(decompose_result, run_phase1_pipeline(self.problem_text).trace_result))
        self.assertIn("falsification", build_stress_prompt(decompose_result, run_phase1_pipeline(self.problem_text).trace_result, run_phase1_pipeline(self.problem_text).compete_result))
        self.assertIn("dense final report", build_final_prompt(decompose_result, run_phase1_pipeline(self.problem_text).trace_result, run_phase1_pipeline(self.problem_text).compete_result, run_phase1_pipeline(self.problem_text).stress_result))

        with patch("perspective_extractor.trace.call_openrouter", return_value=json.dumps(trace_payload)):
            trace_result = run_trace(decompose_result, model="openrouter/test", api_key="key")
        with patch("perspective_extractor.compete.call_openrouter", return_value=json.dumps(compete_payload)):
            compete_result = run_compete(decompose_result, trace_result, model="openrouter/test", api_key="key")
        with patch("perspective_extractor.stress.call_openrouter", return_value=json.dumps(stress_payload)):
            stress_result = run_stress(decompose_result, trace_result, compete_result, model="openrouter/test", api_key="key")
        with patch("perspective_extractor.final.call_openrouter", return_value=json.dumps(final_payload)):
            final_result = run_final(decompose_result, trace_result, compete_result, stress_result, model="openrouter/test", api_key="key")

        self.assertEqual([step.order for step in trace_result.consequence_chain], [1, 2, 3])
        self.assertEqual(len(compete_result.competing_mechanisms), 2)
        self.assertEqual(stress_result.surprise_ledger[0].surprise, "A depot becomes the new bottleneck.")
        self.assertTrue(final_result.executive_summary)

    def test_run_phase1_pipeline_uses_live_modules_when_credentials_are_supplied(self) -> None:
        with (
            patch("perspective_extractor.pipeline.run_decompose") as run_decompose_mock,
            patch("perspective_extractor.pipeline.run_trace") as run_trace_mock,
            patch("perspective_extractor.pipeline.run_compete") as run_compete_mock,
            patch("perspective_extractor.pipeline.run_stress") as run_stress_mock,
            patch("perspective_extractor.pipeline.run_final") as run_final_mock,
        ):
            offline = run_phase1_pipeline(self.problem_text)
            run_decompose_mock.return_value = offline.decompose_result
            run_trace_mock.return_value = offline.trace_result
            run_compete_mock.return_value = offline.compete_result
            run_stress_mock.return_value = offline.stress_result
            run_final_mock.return_value = offline.final_report

            live = run_phase1_pipeline(
                self.problem_text,
                model="openrouter/test",
                api_key="key",
            )

        self.assertEqual(live.final_report.executive_summary, offline.final_report.executive_summary)
        run_decompose_mock.assert_called_once()
        run_trace_mock.assert_called_once()
        run_compete_mock.assert_called_once()
        run_stress_mock.assert_called_once()
        run_final_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
