def test_compete_returns_exactly_two_mechanisms_with_distinct_predictions(phase1_scenario) -> None:
    compete_result = phase1_scenario.compete_result

    assert len(compete_result.competing_mechanisms) == 2
    predictions = [mechanism.prediction for mechanism in compete_result.competing_mechanisms]
    observable_signals = [mechanism.observable_signal for mechanism in compete_result.competing_mechanisms]

    assert all(prediction.strip() for prediction in predictions)
    assert predictions[0] != predictions[1]
    assert all(signal.strip() for signal in observable_signals)
    assert compete_result.divergence_note.strip()
