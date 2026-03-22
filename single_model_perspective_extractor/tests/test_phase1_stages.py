import unittest

from perspective_extractor.compete import build_competing_mechanisms
from perspective_extractor.decompose import decompose_problem
from perspective_extractor.final import build_final_report
from perspective_extractor.pipeline import run_phase1_pipeline
from perspective_extractor.stress import build_stress_test
from perspective_extractor.trace import build_trace


class Phase1StageModuleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.problem_text = (
            "How would a shutdown at the main import terminal affect regional fuel supply, "
            "alternate depots, and retail prices over the next 30 days?"
        )
        self.decompose_result = decompose_problem(self.problem_text)

    def test_trace_stage_builds_explicit_three_order_chain(self) -> None:
        trace_result = build_trace(self.decompose_result)

        self.assertEqual([step.order for step in trace_result.consequence_chain], [1, 2, 3])
        self.assertTrue(all(step.mechanism for step in trace_result.consequence_chain))
        self.assertTrue(all(step.affected_entities for step in trace_result.consequence_chain))
        self.assertIn("mechanism", trace_result.consequence_chain[0].mechanism.lower())

    def test_compete_stage_returns_exactly_two_divergent_cards(self) -> None:
        trace_result = build_trace(self.decompose_result)
        compete_result = build_competing_mechanisms(self.decompose_result, trace_result)

        self.assertEqual(len(compete_result.competing_mechanisms), 2)
        self.assertNotEqual(
            compete_result.competing_mechanisms[0].prediction,
            compete_result.competing_mechanisms[1].prediction,
        )
        self.assertTrue(all(card.observable_signal for card in compete_result.competing_mechanisms))

    def test_stress_stage_emits_falsification_and_surprise_ledgers(self) -> None:
        trace_result = build_trace(self.decompose_result)
        compete_result = build_competing_mechanisms(self.decompose_result, trace_result)
        stress_result = build_stress_test(self.decompose_result, trace_result, compete_result)

        self.assertGreaterEqual(len(stress_result.falsification_ledger), 1)
        self.assertGreaterEqual(len(stress_result.surprise_ledger), 1)
        self.assertTrue(all(entry.hidden_assumption for entry in stress_result.falsification_ledger))
        self.assertTrue(all(entry.surprise for entry in stress_result.surprise_ledger))

    def test_final_stage_assembles_dense_report_from_prior_artifacts(self) -> None:
        trace_result = build_trace(self.decompose_result)
        compete_result = build_competing_mechanisms(self.decompose_result, trace_result)
        stress_result = build_stress_test(self.decompose_result, trace_result, compete_result)
        final_report = build_final_report(
            self.decompose_result,
            trace_result,
            compete_result,
            stress_result,
        )

        self.assertTrue(final_report.key_actors_and_nodes)
        self.assertEqual(len(final_report.critical_mechanism_chains), 3)
        self.assertGreaterEqual(
            len(final_report.competing_explanations_and_divergent_predictions),
            3,
        )
        self.assertIsNotNone(final_report.executive_summary)
        self.assertIn(trace_result.trace_target.lower(), final_report.executive_summary.lower())

    def test_phase1_pipeline_composes_new_reasoning_stage_modules(self) -> None:
        artifacts = run_phase1_pipeline(self.problem_text)

        self.assertEqual(len(artifacts.trace_result.consequence_chain), 3)
        self.assertEqual(len(artifacts.compete_result.competing_mechanisms), 2)
        self.assertGreaterEqual(len(artifacts.stress_result.falsification_ledger), 1)
        self.assertTrue(artifacts.final_report.likely_surprises)


if __name__ == "__main__":
    unittest.main()
