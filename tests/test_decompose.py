from dataclasses import asdict


def test_decompose_sample_output_has_problem_frame_actor_node_and_structured_shape(phase1_scenario) -> None:
    artifact = asdict(phase1_scenario.decompose_result)

    assert set(artifact) == {
        "problem_frame",
        "actor_cards",
        "node_cards",
        "constraint_cards",
    }
    assert artifact["problem_frame"]["core_question"].strip()
    assert artifact["actor_cards"]
    assert artifact["node_cards"]
    assert any(card["name"].strip() for card in artifact["actor_cards"])
    assert any(card["name"].strip() for card in artifact["node_cards"])
    assert artifact["constraint_cards"]
    assert not isinstance(artifact, str)
