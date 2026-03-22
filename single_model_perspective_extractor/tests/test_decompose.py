import json
import unittest
from dataclasses import asdict
from pathlib import Path

from perspective_extractor.decompose import decompose_problem, decompose_to_json, save_decompose_result


class DecomposeTests(unittest.TestCase):
    def test_decompose_problem_returns_required_phase1_keys_with_non_empty_cards(self) -> None:
        result = decompose_problem(
            "How could a disruption at the main fuel import terminal force shippers, customs, and regional distributors "
            "to reroute through alternate ports and inland pipeline chokepoints over the next 30 days?"
        )

        payload = asdict(result)
        self.assertEqual(set(payload), {"problem_frame", "actor_cards", "node_cards", "constraint_cards"})
        self.assertTrue(payload["actor_cards"])
        self.assertTrue(payload["node_cards"])
        self.assertTrue(payload["constraint_cards"])
        self.assertIn("core_question", payload["problem_frame"])

    def test_decompose_problem_detects_explicit_nodes_routes_platforms_and_chokepoints(self) -> None:
        result = decompose_problem(
            "If regulators force a payments platform to stop serving an exchange, which banks, clearinghouses, "
            "bridges, and shipping routes become the next chokepoints for cross-border settlement?"
        )

        node_names = {card.name.lower() for card in result.node_cards}
        node_types = {card.type for card in result.node_cards}

        self.assertTrue(any("platform" in name for name in node_names))
        self.assertTrue(any("route" in name or "bridge" in name or "chokepoint" in name for name in node_names))
        self.assertIn("platform", node_types)
        self.assertTrue({"route", "institutional node"} & node_types)

    def test_decompose_json_and_save_helpers_emit_structured_output(self) -> None:
        payload = json.loads(
            decompose_to_json("How does a refinery outage change which distributors, pipelines, and ports matter most?")
        )
        self.assertIn("actor_cards", payload)
        self.assertIn("node_cards", payload)
        self.assertNotIsInstance(payload, str)

        output_path = Path("/tmp/decompose_test_output.json")
        save_decompose_result(
            "How does a refinery outage change which distributors, pipelines, and ports matter most?",
            output_path,
        )
        self.assertTrue(output_path.exists())
        saved_payload = json.loads(output_path.read_text())
        self.assertEqual(set(saved_payload), {"problem_frame", "actor_cards", "node_cards", "constraint_cards"})


if __name__ == "__main__":
    unittest.main()
