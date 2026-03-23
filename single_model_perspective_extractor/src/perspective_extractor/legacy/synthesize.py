"""Legacy synthesis stage retained for compatibility only."""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable

from ..models import (
    AxisHierarchy,
    PerspectiveBranch,
    PerspectiveMap,
    PerspectiveNote,
    PerspectiveRecord,
    QuestionCard,
    ReviewDecision,
)

_WORD_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "because",
    "but",
    "by",
    "for",
    "from",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "so",
    "that",
    "the",
    "their",
    "then",
    "there",
    "this",
    "to",
    "when",
    "where",
    "which",
    "with",
}
_OPPOSING_TERM_SETS = (
    {"increase", "improve", "gain", "higher", "rise", "stronger"},
    {"decrease", "decline", "drop", "fall", "lower", "weaker", "reduce"},
)


def synthesize_summary(records: list[PerspectiveRecord]) -> str:
    """Create a newline-delimited summary for the current records."""

    return "\n".join(f"- {record.axis}: {record.summary}" for record in records)


def synthesize_map(
    question_card: QuestionCard,
    kept_notes: list[PerspectiveNote],
    review_decisions: list[ReviewDecision],
) -> PerspectiveMap:
    """Build a structured perspective map without flattening note-level differences."""

    note_lookup = {note.note_id: note for note in kept_notes}
    merged_groups = _merged_groups(review_decisions, note_lookup)
    competing_pairs = _collect_relationships(kept_notes, relation_type="competing")
    compatible_pairs = _collect_relationships(kept_notes, relation_type="compatible")
    evidence_contests = _collect_evidence_contests(kept_notes, competing_pairs, compatible_pairs)
    boundary_cases = _collect_boundary_cases(kept_notes)
    axis_hierarchies, perspective_branches = _build_hierarchy(
        kept_notes,
        evidence_contests,
    )
    final_summary = _build_final_summary(
        question_card,
        kept_notes,
        merged_groups,
        axis_hierarchies,
        perspective_branches,
        competing_pairs,
        compatible_pairs,
        evidence_contests,
        boundary_cases,
    )

    return PerspectiveMap(
        question_id=question_card.question_id,
        kept_notes=kept_notes,
        merged_groups=merged_groups,
        axis_hierarchies=axis_hierarchies,
        perspective_branches=perspective_branches,
        competing_perspectives=competing_pairs,
        compatible_perspectives=compatible_pairs,
        evidence_contests=evidence_contests,
        boundary_cases=boundary_cases,
        final_summary=final_summary,
    )


def _tokenize(text: str | None) -> set[str]:
    if not text:
        return set()
    return {
        token
        for token in _WORD_RE.findall(text.lower())
        if token not in _STOPWORDS and len(token) > 2
    }


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _normalize_pair(left: str, right: str) -> tuple[str, str]:
    return tuple(sorted((left, right)))


def _unique_in_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        cleaned = " ".join(value.split())
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            ordered.append(cleaned)
    return ordered


def _merged_groups(
    review_decisions: list[ReviewDecision],
    note_lookup: dict[str, PerspectiveNote],
) -> list[list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for decision in review_decisions:
        if decision.action != "merge" or not decision.merge_target_note_id:
            continue
        if decision.merge_target_note_id not in note_lookup:
            continue

        target_group = groups[decision.merge_target_note_id]
        if decision.merge_target_note_id not in target_group:
            target_group.append(decision.merge_target_note_id)
        if decision.target_note_id not in target_group:
            target_group.append(decision.target_note_id)

    return list(groups.values())


def _collect_relationships(
    kept_notes: list[PerspectiveNote],
    *,
    relation_type: str,
) -> list[tuple[str, str]]:
    relationships: list[tuple[str, str]] = []
    seen_pairs: set[tuple[str, str]] = set()

    for index, left in enumerate(kept_notes):
        left_claim_tokens = _tokenize(left.core_claim)
        left_evidence_tokens = _tokenize(" ".join(left.evidence_needed))
        left_boundary_tokens = _tokenize(left.boundary_condition)

        for right in kept_notes[index + 1:]:
            right_claim_tokens = _tokenize(right.core_claim)
            right_evidence_tokens = _tokenize(" ".join(right.evidence_needed))
            right_boundary_tokens = _tokenize(right.boundary_condition)

            claim_overlap = _jaccard(left_claim_tokens, right_claim_tokens)
            evidence_overlap = _jaccard(left_evidence_tokens, right_evidence_tokens)
            boundary_overlap = _jaccard(left_boundary_tokens, right_boundary_tokens)
            pair = _normalize_pair(left.note_id, right.note_id)

            if relation_type == "competing":
                if (
                    _has_directional_tension(left_claim_tokens, right_claim_tokens)
                    or (claim_overlap >= 0.12 and evidence_overlap >= 0.16 and left.axis_id != right.axis_id)
                ):
                    if pair not in seen_pairs:
                        relationships.append(pair)
                        seen_pairs.add(pair)
            else:
                if (
                    left.axis_id != right.axis_id
                    and (
                        evidence_overlap >= 0.1
                        or boundary_overlap >= 0.12
                        or _share_supporting_cards(left, right)
                    )
                    and not _has_directional_tension(left_claim_tokens, right_claim_tokens)
                ):
                    if pair not in seen_pairs:
                        relationships.append(pair)
                        seen_pairs.add(pair)

    return relationships


def _has_directional_tension(left_tokens: set[str], right_tokens: set[str]) -> bool:
    left_has_up = bool(left_tokens & _OPPOSING_TERM_SETS[0])
    left_has_down = bool(left_tokens & _OPPOSING_TERM_SETS[1])
    right_has_up = bool(right_tokens & _OPPOSING_TERM_SETS[0])
    right_has_down = bool(right_tokens & _OPPOSING_TERM_SETS[1])
    return (left_has_up and right_has_down) or (left_has_down and right_has_up)


def _share_supporting_cards(left: PerspectiveNote, right: PerspectiveNote) -> bool:
    return bool(set(left.supporting_card_ids) & set(right.supporting_card_ids))


def _collect_evidence_contests(
    kept_notes: list[PerspectiveNote],
    competing_pairs: list[tuple[str, str]],
    compatible_pairs: list[tuple[str, str]],
) -> list[str]:
    note_lookup = {note.note_id: note for note in kept_notes}
    contests: list[str] = []

    for left_id, right_id in competing_pairs:
        left = note_lookup[left_id]
        right = note_lookup[right_id]
        contests.append(
            (
                f"{left_id} vs {right_id}: distinguish '{_short_phrase(left.testable_implication, left.core_claim)}' "
                f"from '{_short_phrase(right.testable_implication, right.core_claim)}'."
            )
        )

    for left_id, right_id in compatible_pairs:
        left = note_lookup[left_id]
        right = note_lookup[right_id]
        shared_evidence = _shared_evidence_topics(left, right)
        if shared_evidence:
            contests.append(
                f"{left_id} + {right_id}: shared evidence needs include {shared_evidence}."
            )

    for note in kept_notes:
        if note.verification_question:
            contests.append(f"{note.note_id}: {note.verification_question}")

    return _unique_in_order(contests)


def _collect_boundary_cases(kept_notes: list[PerspectiveNote]) -> list[str]:
    cases = [
        f"{note.note_id}: {note.boundary_condition}"
        for note in kept_notes
        if note.boundary_condition
    ]
    return _unique_in_order(cases)


def _build_hierarchy(
    kept_notes: list[PerspectiveNote],
    evidence_contests: list[str],
) -> tuple[list[AxisHierarchy], list[PerspectiveBranch]]:
    notes_by_axis: dict[str, list[PerspectiveNote]] = defaultdict(list)
    note_disputes: dict[str, list[str]] = defaultdict(list)

    for note in kept_notes:
        notes_by_axis[note.axis_id].append(note)

    for contest in evidence_contests:
        for note in kept_notes:
            if note.note_id in contest:
                note_disputes[note.note_id].append(contest)

    axis_hierarchies: list[AxisHierarchy] = []
    perspective_branches: list[PerspectiveBranch] = []

    for axis_id, axis_notes in notes_by_axis.items():
        ordered_notes = list(axis_notes)
        main_note = ordered_notes[0]
        child_note_ids = [note.note_id for note in ordered_notes[1:]]
        axis_hierarchies.append(
            AxisHierarchy(
                axis_id=axis_id,
                main_note_id=main_note.note_id,
                sub_perspective_ids=child_note_ids,
            )
        )

        for index, note in enumerate(ordered_notes):
            perspective_branches.append(
                PerspectiveBranch(
                    note_id=note.note_id,
                    axis_id=axis_id,
                    claim=note.core_claim,
                    child_note_ids=child_note_ids if index == 0 else [],
                    boundary_conditions=[note.boundary_condition] if note.boundary_condition else [],
                    counterexamples=[note.counterexample] if note.counterexample else [],
                    evidence_disputes=note_disputes.get(note.note_id, []),
                )
            )

    return axis_hierarchies, perspective_branches


def _build_final_summary(
    question_card: QuestionCard,
    kept_notes: list[PerspectiveNote],
    merged_groups: list[list[str]],
    axis_hierarchies: list[AxisHierarchy],
    perspective_branches: list[PerspectiveBranch],
    competing_pairs: list[tuple[str, str]],
    compatible_pairs: list[tuple[str, str]],
    evidence_contests: list[str],
    boundary_cases: list[str],
) -> str:
    lines = [
        f"Question focus: {question_card.cleaned_question}",
        "",
        "Kept note structure:",
    ]
    for note in kept_notes:
        lines.append(
            (
                f"- {note.note_id} [{note.axis_id}]: {_short_phrase(note.core_claim)} | "
                f"evidence hook: {_short_phrase(note.testable_implication, note.reasoning)}"
            )
        )

    lines.extend(["", "Axis hierarchy:"])
    lines.extend(_render_hierarchy(axis_hierarchies, perspective_branches))
    lines.extend(["", "Merged overlap groups:"])
    lines.extend(_render_lines((_format_group(group) for group in merged_groups)))
    lines.extend(["", "Competing perspectives:"])
    lines.extend(_render_lines((_format_pair(pair) for pair in competing_pairs)))
    lines.extend(["", "Compatible perspectives:"])
    lines.extend(_render_lines((_format_pair(pair) for pair in compatible_pairs)))
    lines.extend(["", "Evidence contests:"])
    lines.extend(_render_lines((f"- {item}" for item in evidence_contests)))
    lines.extend(["", "Boundary cases:"])
    lines.extend(_render_lines((f"- {item}" for item in boundary_cases)))
    return "\n".join(lines)


def _shared_evidence_topics(left: PerspectiveNote, right: PerspectiveNote) -> str | None:
    overlap = _tokenize(" ".join(left.evidence_needed)) & _tokenize(" ".join(right.evidence_needed))
    filtered = sorted(token for token in overlap if len(token) > 4)
    if not filtered:
        return None
    return ", ".join(filtered[:4])


def _short_phrase(primary: str | None, fallback: str | None = None, *, limit: int = 18) -> str:
    text = primary or fallback or "N/A"
    words = " ".join(text.split()).split()
    if len(words) <= limit:
        return " ".join(words)
    return " ".join(words[:limit]).rstrip(",;") + " ..."


def _format_group(group: list[str]) -> str:
    return "- " + " + ".join(group)


def _format_pair(pair: tuple[str, str]) -> str:
    return f"- {pair[0]} <-> {pair[1]}"


def _render_lines(values: Iterable[str]) -> list[str]:
    rendered = list(values)
    return rendered if rendered else ["- None"]


def _render_hierarchy(
    axis_hierarchies: list[AxisHierarchy],
    perspective_branches: list[PerspectiveBranch],
) -> list[str]:
    if not axis_hierarchies:
        return ["- None"]

    branch_lookup = {branch.note_id: branch for branch in perspective_branches}
    lines: list[str] = []
    for hierarchy in axis_hierarchies:
        lines.append(f"- {hierarchy.axis_id}: main {hierarchy.main_note_id}")
        main_branch = branch_lookup.get(hierarchy.main_note_id)
        if main_branch:
            lines.extend(_render_branch(main_branch, branch_lookup, indent="  "))
    return lines


def _render_branch(
    branch: PerspectiveBranch,
    branch_lookup: dict[str, PerspectiveBranch],
    *,
    indent: str,
) -> list[str]:
    lines = [f"{indent}- {branch.note_id}: {_short_phrase(branch.claim)}"]
    lines.extend(
        f"{indent}  - boundary: {item}"
        for item in branch.boundary_conditions
    )
    lines.extend(
        f"{indent}  - counterexample: {item}"
        for item in branch.counterexamples
    )
    lines.extend(
        f"{indent}  - evidence dispute: {item}"
        for item in branch.evidence_disputes
    )
    for child_note_id in branch.child_note_ids:
        child_branch = branch_lookup.get(child_note_id)
        if child_branch:
            lines.extend(_render_branch(child_branch, branch_lookup, indent=indent + "  "))
    return lines
