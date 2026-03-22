def test_stress_ledgers_include_hidden_assumptions_and_actor_or_node_links(phase1_scenario) -> None:
    stress_result = phase1_scenario.stress_result

    assert stress_result.falsification_ledger
    assert stress_result.surprise_ledger

    for entry in stress_result.falsification_ledger:
        assert entry.claim_under_stress.strip()
        assert entry.hidden_assumption.strip()
        assert entry.how_it_could_fail.strip()
        assert entry.what_evidence_would_break_it.strip()

    for entry in stress_result.surprise_ledger:
        assert entry.surprise.strip()
        assert entry.why_shallow_analysis_misses_it.strip()
        assert entry.what_actor_or_node_it_depends_on
