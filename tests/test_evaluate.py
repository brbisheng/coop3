from __future__ import annotations

import json
from dataclasses import asdict

from perspective_extractor.evaluate import (
    REQUIRED_FINAL_REPORT_FIELDS,
    evaluate_from_json_paths,
    evaluate_phase1_artifacts,
)
from perspective_extractor.pipeline import run_phase1_pipeline


def test_evaluate_phase1_artifacts_returns_expected_minimal_metrics(phase1_scenario) -> None:
    result = evaluate_phase1_artifacts(
        decompose_artifact=asdict(phase1_scenario.decompose_result),
        trace_artifact=asdict(phase1_scenario.trace_result),
        compete_artifact=asdict(phase1_scenario.compete_result),
        stress_artifact=asdict(phase1_scenario.stress_result),
        final_artifact=asdict(phase1_scenario.final_report),
    )

    assert result.metrics.actor_count == len(phase1_scenario.decompose_result.actor_cards)
    assert result.metrics.node_count == len(phase1_scenario.decompose_result.node_cards)
    assert result.metrics.trace_depth == len(phase1_scenario.trace_result.consequence_chain)

    assert result.metrics.competing_mechanism_count == 2
    assert result.metrics.has_exactly_two_competing_mechanisms is True
    assert result.metrics.predictions_differ is True

    assert result.metrics.hidden_assumption_count == len(phase1_scenario.stress_result.falsification_ledger)
    assert result.metrics.surprise_count == len(phase1_scenario.stress_result.surprise_ledger)
    assert set(result.metrics.final_report_section_presence) == set(REQUIRED_FINAL_REPORT_FIELDS)
    assert all(result.metrics.final_report_section_presence.values())

    assert set(result.future_scores) == {"ANCS", "MNR", "SDR", "SUR", "DPQ", "RSMS"}
    assert all(value is None for value in result.future_scores.values())
    assert result.failure_flags["predictions_differ_false"] is False
    assert result.failure_flags["surprise_count_zero"] is False
    assert result.active_failure_flags == []


def test_evaluate_from_json_paths_loads_five_artifacts(tmp_path, phase1_scenario) -> None:
    decompose = tmp_path / "decompose.json"
    trace = tmp_path / "trace.json"
    compete = tmp_path / "compete.json"
    stress = tmp_path / "stress.json"
    final = tmp_path / "final.json"

    decompose.write_text(json.dumps(asdict(phase1_scenario.decompose_result)), encoding="utf-8")
    trace.write_text(json.dumps(asdict(phase1_scenario.trace_result)), encoding="utf-8")
    compete.write_text(json.dumps(asdict(phase1_scenario.compete_result)), encoding="utf-8")
    stress.write_text(json.dumps(asdict(phase1_scenario.stress_result)), encoding="utf-8")
    final.write_text(json.dumps(asdict(phase1_scenario.final_report)), encoding="utf-8")

    result = evaluate_from_json_paths(
        decompose_path=decompose,
        trace_path=trace,
        compete_path=compete,
        stress_path=stress,
        final_path=final,
    )

    assert result.metrics.actor_count > 0
    assert result.metrics.trace_depth > 0
    assert result.metrics.has_exactly_two_competing_mechanisms is True


def test_run_phase1_pipeline_improve_rounds_writes_round_artifacts(tmp_path) -> None:
    artifacts = run_phase1_pipeline(
        "How would a shutdown at the main import terminal affect regional fuel supply and retail prices?",
        improve_rounds=2,
        run_id="test-run",
        live_run_output_root=tmp_path,
    )

    base = tmp_path / "test-run"
    assert (base / "round_1" / "01_decompose.json").exists()
    assert (base / "round_1" / "06_evaluate.json").exists()
    assert (base / "round_2" / "05_final.json").exists()
    assert len(artifacts.round_evaluations) == 2
    assert artifacts.run_id == "test-run"
