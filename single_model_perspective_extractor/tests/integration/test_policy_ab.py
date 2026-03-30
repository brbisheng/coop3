from __future__ import annotations

import json
from dataclasses import asdict

from perspective_extractor.compete import run_compete
from perspective_extractor.decompose import run_decompose
from perspective_extractor.evaluate import evaluate_phase1_artifacts
from perspective_extractor.final import run_final
from perspective_extractor.policy import save_policy_benchmark_result
from perspective_extractor.stress import run_stress
from perspective_extractor.trace import run_trace


def _mock_openrouter_response(*, messages: list[dict[str, str]]) -> str:
    user_prompt = next(message["content"] for message in messages if message["role"] == "user")
    is_policy_b = "Policy lens:" in user_prompt

    if "decompose stage" in user_prompt:
        if is_policy_b:
            return json.dumps({
                "problem_frame": {
                    "core_question": "How do terminal disruptions reshape regional fuel logistics?",
                    "decision_or_analysis_target": "Identify dominant actors and bottlenecks.",
                    "scope_notes": ["30-day horizon", "Regional scope"],
                },
                "actor_cards": [
                    {"name": "Customs authority", "type": "institution", "role": "clearance", "goal_guess": "keep compliance", "why_relevant": "controls release flow"},
                    {"name": "Fuel distributors", "type": "firm", "role": "rerouting", "goal_guess": "maintain supply", "why_relevant": "set downstream allocation"},
                ],
                "node_cards": [
                    {"name": "Main import terminal", "type": "facility", "function": "import and storage", "why_relevant": "first chokepoint"},
                    {"name": "Inland pipeline junction", "type": "route", "function": "redistribution", "why_relevant": "substitute path constraint"},
                ],
                "constraint_cards": [
                    {"constraint": "inspection throughput", "applies_to": ["Customs authority", "Main import terminal"], "why_it_matters": "caps release speed"},
                ],
            })
        return json.dumps({
            "problem_frame": {
                "core_question": "How do terminal disruptions reshape logistics?",
                "decision_or_analysis_target": "Find key constraints.",
                "scope_notes": [],
            },
            "actor_cards": [
                {"name": "Distributors", "type": "firm", "role": "supply", "goal_guess": "deliver fuel", "why_relevant": "move product"},
            ],
            "node_cards": [
                {"name": "Main terminal", "type": "facility", "function": "imports", "why_relevant": "major node"},
            ],
            "constraint_cards": [],
        })

    if "trace stage" in user_prompt:
        return json.dumps({
            "trace_target": "Regional fuel flow",
            "consequence_chain": [
                {"order": 1, "event": "Terminal throughput drops", "mechanism": "direct capacity loss", "affected_entities": ["Main terminal"]},
                {"order": 2, "event": "Rerouting into inland paths", "mechanism": "substitution congestion", "affected_entities": ["Inland pipeline junction"]},
                {"order": 3, "event": "Retail supply volatility", "mechanism": "delayed inventory feedback", "affected_entities": ["Fuel distributors"]},
            ],
        })

    if "compete stage" in user_prompt:
        return json.dumps({
            "competing_mechanisms": [
                {"label": "A", "core_mechanism": "facility bottleneck dominates", "what_it_explains": "first-order scarcity", "prediction": "recovery after facility clears", "observable_signal": "queues drop first"},
                {"label": "B", "core_mechanism": "coordination frictions dominate", "what_it_explains": "persistent propagation", "prediction": "lagged normalization", "observable_signal": "downstream lag remains"},
            ],
            "divergence_note": "A predicts immediate relief, B predicts delayed relief.",
        })

    if "stress stage" in user_prompt:
        if is_policy_b:
            return json.dumps({
                "falsification_ledger": [
                    {"claim_under_stress": "A", "hidden_assumption": "Terminal is only bottleneck", "how_it_could_fail": "inspection remains binding", "what_evidence_would_break_it": "delays persist after terminal recovery"},
                    {"claim_under_stress": "B", "hidden_assumption": "coordination dominates", "how_it_could_fail": "rapid normalization", "what_evidence_would_break_it": "downstream lag clears rapidly"},
                ],
                "surprise_ledger": [
                    {"surprise": "Secondary depot fails", "why_shallow_analysis_misses_it": "attention bias", "what_actor_or_node_it_depends_on": ["Fuel distributors"]},
                ],
            })
        return json.dumps({
            "falsification_ledger": [
                {"claim_under_stress": "A", "hidden_assumption": "single bottleneck", "how_it_could_fail": "other node binds", "what_evidence_would_break_it": "persistent delays"},
            ],
            "surprise_ledger": [
                {"surprise": "Fallback depot queues rise", "why_shallow_analysis_misses_it": "focus remains on headline node", "what_actor_or_node_it_depends_on": ["Distributors"]},
            ],
        })

    if "final stage" in user_prompt:
        return json.dumps({
            "key_actors_and_nodes": ["Main terminal", "Fuel distributors"],
            "critical_mechanism_chains": ["Capacity shock -> reroute -> lagged recovery"],
            "competing_explanations_and_divergent_predictions": ["A fast recovery", "B delayed recovery"],
            "likely_surprises": ["Secondary depot failure"],
            "main_uncertainties_and_hidden_assumptions": ["Inspection throughput remains binding"],
            "executive_summary": "Fuel distributors and terminal clearance timing drive divergence.",
        })

    raise AssertionError("Unexpected stage prompt")


def test_policy_ab_comparison_tracks_win_rate_and_persists_benchmark(monkeypatch, tmp_path) -> None:
    for module_path in (
        "perspective_extractor.decompose.call_openrouter",
        "perspective_extractor.trace.call_openrouter",
        "perspective_extractor.compete.call_openrouter",
        "perspective_extractor.stress.call_openrouter",
        "perspective_extractor.final.call_openrouter",
    ):
        monkeypatch.setattr(module_path, lambda **kwargs: _mock_openrouter_response(messages=kwargs["messages"]))

    question = "How would a major terminal shutdown affect regional fuel supply over 30 days?"
    comparisons: list[dict[str, object]] = []
    for policy_id in ("policy_a", "policy_b"):
        decompose_result = run_decompose(question, model="mock/model", api_key="mock", policy_version=policy_id)
        trace_result = run_trace(decompose_result, model="mock/model", api_key="mock", policy_version=policy_id)
        compete_result = run_compete(decompose_result, trace_result, model="mock/model", api_key="mock", policy_version=policy_id)
        stress_result = run_stress(decompose_result, trace_result, compete_result, model="mock/model", api_key="mock", policy_version=policy_id)
        final_report = run_final(decompose_result, trace_result, compete_result, stress_result, model="mock/model", api_key="mock", policy_version=policy_id)
        evaluation = evaluate_phase1_artifacts(
            decompose_artifact=asdict(decompose_result),
            trace_artifact=asdict(trace_result),
            compete_artifact=asdict(compete_result),
            stress_artifact=asdict(stress_result),
            final_artifact=asdict(final_report),
        )
        comparisons.append({
            "policy_id": policy_id,
            "active_failure_flags": evaluation.active_failure_flags,
            "failure_count": len(evaluation.active_failure_flags),
            "metrics": asdict(evaluation.metrics),
        })

    winner = min(comparisons, key=lambda item: int(item["failure_count"]))
    benchmark_payload = {
        "question": question,
        "comparisons": comparisons,
        "winner_policy": winner["policy_id"],
        "win_rate": {
            "policy_a": 1.0 if winner["policy_id"] == "policy_a" else 0.0,
            "policy_b": 1.0 if winner["policy_id"] == "policy_b" else 0.0,
        },
    }
    output_path = save_policy_benchmark_result(
        benchmark_payload,
        output_root=tmp_path / "policy_benchmarks",
        run_id="ab-test",
    )

    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert output_path.exists()
    assert saved["winner_policy"] == "policy_b"
    assert saved["win_rate"]["policy_b"] == 1.0
    assert saved["comparisons"][1]["failure_count"] < saved["comparisons"][0]["failure_count"]
