"""Prompt patch generation for iterative phase-1 improvement rounds."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True, slots=True)
class PromptPatchBundle:
    """Per-stage prompt patch text derived from evaluation failure flags."""

    decompose_patch: str = ""
    trace_patch: str = ""
    compete_patch: str = ""
    stress_patch: str = ""
    final_patch: str = ""

    def as_dict(self) -> dict[str, str]:
        """Return a JSON-serializable dictionary for logging artifacts."""

        return {
            "decompose_patch": self.decompose_patch,
            "trace_patch": self.trace_patch,
            "compete_patch": self.compete_patch,
            "stress_patch": self.stress_patch,
            "final_patch": self.final_patch,
        }


def build_prompt_patch_from_failure_flags(failure_flags: Mapping[str, bool]) -> PromptPatchBundle:
    """Map failure flags to targeted prompt patch instructions for the next round."""

    decompose_notes: list[str] = []
    trace_notes: list[str] = []
    compete_notes: list[str] = []
    stress_notes: list[str] = []
    final_notes: list[str] = []

    if failure_flags.get("actor_count_too_low"):
        decompose_notes.append(
            "强化 actor 抽取：至少提取 3 个具名 actor，优先包含操作者、监管/制度方、受影响方，并说明各自 operational relevance。"
        )
        trace_notes.append("在每个因果阶次明确写出 actor 变化路径，避免只写抽象系统变化。")

    if failure_flags.get("node_count_too_low"):
        decompose_notes.append(
            "强化 node/facility 抽取：至少提取 3 个具名 operational nodes（设施、路径、平台或制度节点），并与 decision target 建立直接连接。"
        )
        trace_notes.append("一阶到三阶链路必须显式经过具体节点，不可仅写宏观市场叙述。")

    if failure_flags.get("predictions_differ_false") or failure_flags.get("mechanism_count_not_two"):
        compete_notes.append(
            "强化机制分歧约束：必须输出 A/B 两条因果上可区分机制，并给出同一时间窗下方向或时序明显不同的 prediction。"
        )
        compete_notes.append("divergence_note 必须点名至少一个可观测信号并说明 A/B 预期差异。")
        final_notes.append("在最终报告中保留机制冲突，不得把 A/B 差异平滑成单一路径。")

    if failure_flags.get("surprise_count_zero"):
        stress_notes.append(
            "强化 surprise ledger：至少列出 2 条非显然 surprise，要求包含触发条件、依赖节点/actor、以及可观察后果。"
        )
        final_notes.append("likely_surprises 段落必须包含具体 actor/node 与触发条件。")

    return PromptPatchBundle(
        decompose_patch="\n".join(decompose_notes),
        trace_patch="\n".join(trace_notes),
        compete_patch="\n".join(compete_notes),
        stress_patch="\n".join(stress_notes),
        final_patch="\n".join(final_notes),
    )


__all__ = ["PromptPatchBundle", "build_prompt_patch_from_failure_flags"]
