def test_trace_chain_has_increasing_order_and_reaches_third_order_depth(phase1_scenario) -> None:
    trace_result = phase1_scenario.trace_result

    assert trace_result.trace_target == phase1_scenario.trace_target
    assert len(trace_result.consequence_chain) >= 3

    orders = [step.order for step in trace_result.consequence_chain]
    assert orders == sorted(orders)
    assert orders == list(range(1, len(trace_result.consequence_chain) + 1))

    for step in trace_result.consequence_chain:
        assert step.event.strip()
        assert step.mechanism.strip()
        assert step.affected_entities
