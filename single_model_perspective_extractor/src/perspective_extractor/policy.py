"""Policy registry for stage-level live prompt variants."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True, slots=True)
class StagePolicy:
    """Prompt fragments and generation params for one stage."""

    prompt_prefix: str = ""
    prompt_rules_extra: tuple[str, ...] = ()
    system_prompt: str = "Return strict JSON for the requested schema only."
    temperature: float = 0.0
    max_tokens: int = 2200


@dataclass(frozen=True, slots=True)
class PolicyVersion:
    """Named policy bundle with stage overrides and applicability metadata."""

    policy_id: str
    label: str
    applicable_scenarios: tuple[str, ...]
    stages: dict[str, StagePolicy] = field(default_factory=dict)

    def stage(self, stage_name: str, *, default_max_tokens: int) -> StagePolicy:
        """Resolve stage config with fallback defaults."""

        stage_policy = self.stages.get(stage_name)
        if stage_policy is None:
            return StagePolicy(max_tokens=default_max_tokens)
        if stage_policy.max_tokens <= 0:
            return StagePolicy(
                prompt_prefix=stage_policy.prompt_prefix,
                prompt_rules_extra=stage_policy.prompt_rules_extra,
                system_prompt=stage_policy.system_prompt,
                temperature=stage_policy.temperature,
                max_tokens=default_max_tokens,
            )
        return stage_policy


POLICY_REGISTRY: dict[str, PolicyVersion] = {
    "policy_a": PolicyVersion(
        policy_id="policy_a",
        label="Baseline operational rigor",
        applicable_scenarios=(
            "General phase-1 extraction",
            "Balanced detail and speed",
        ),
        stages={},
    ),
    "policy_b": PolicyVersion(
        policy_id="policy_b",
        label="Counterfactual-heavy rigor",
        applicable_scenarios=(
            "High-uncertainty policy questions",
            "Stress-testing and contradiction-rich analysis",
        ),
        stages={
            "decompose": StagePolicy(
                prompt_prefix=(
                    "Policy lens: aggressively surface hidden institutional actors and substitute operational nodes.\n"
                ),
                prompt_rules_extra=(
                    "- Policy B constraint: include at least one actor and one node that are not explicitly named but are strongly implied by operating mechanics.",
                ),
                max_tokens=2500,
            ),
            "trace": StagePolicy(
                prompt_prefix="Policy lens: prioritize adaptation loops and delayed second-order effects.\n",
                prompt_rules_extra=(
                    "- Policy B constraint: explicitly include at least one delayed feedback mechanism by order 3.",
                ),
                max_tokens=2400,
            ),
            "compete": StagePolicy(
                prompt_prefix="Policy lens: maximize falsifiable divergence between mechanism cards.\n",
                prompt_rules_extra=(
                    "- Policy B constraint: divergence_note must identify a measurable time-lag difference.",
                ),
                max_tokens=2400,
            ),
            "stress": StagePolicy(
                prompt_prefix="Policy lens: favor brittle assumptions and institutional failure triggers.\n",
                prompt_rules_extra=(
                    "- Policy B constraint: each falsification entry must include one concrete actor-specific trigger.",
                ),
                max_tokens=2600,
            ),
            "final": StagePolicy(
                prompt_prefix="Policy lens: preserve disagreement and explicit rollback criteria.\n",
                prompt_rules_extra=(
                    "- Policy B constraint: executive_summary must name one explicit rollback trigger for the current leading view.",
                ),
                max_tokens=2800,
            ),
        },
    ),
}

DEFAULT_POLICY_VERSION = "policy_a"


def resolve_policy_version(policy_version: str | PolicyVersion | None) -> PolicyVersion:
    """Resolve a policy identifier or object to a concrete policy version."""

    if isinstance(policy_version, PolicyVersion):
        return policy_version
    policy_id = (policy_version or DEFAULT_POLICY_VERSION).strip()
    if policy_id not in POLICY_REGISTRY:
        supported = ", ".join(sorted(POLICY_REGISTRY))
        raise ValueError(f"Unknown policy_version '{policy_id}'. Supported policy versions: {supported}")
    return POLICY_REGISTRY[policy_id]


def save_policy_benchmark_result(
    result: dict[str, object],
    *,
    output_root: str | Path = "examples/out/policy_benchmarks",
    run_id: str | None = None,
) -> Path:
    """Persist one policy comparison result for manual review and rollback trails."""

    resolved_run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = Path(output_root) / f"{resolved_run_id}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return destination


def policy_to_dict(policy: PolicyVersion) -> dict[str, object]:
    """Expose policy metadata in a JSON-serializable shape."""

    return asdict(policy)


__all__ = [
    "DEFAULT_POLICY_VERSION",
    "POLICY_REGISTRY",
    "PolicyVersion",
    "StagePolicy",
    "policy_to_dict",
    "resolve_policy_version",
    "save_policy_benchmark_result",
]
