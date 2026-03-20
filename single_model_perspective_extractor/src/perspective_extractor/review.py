"""Review helpers for extracted perspectives."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from .models import PerspectiveNote, PerspectiveRecord, QuestionCard, ReviewDecision

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
_GENERIC_NOTE_TERMS = {
    "affect",
    "cases",
    "context",
    "depends",
    "different",
    "evidence",
    "factor",
    "factors",
    "important",
    "influence",
    "matters",
    "mechanism",
    "outcome",
    "pattern",
    "question",
    "result",
    "setting",
    "should",
    "some",
    "things",
    "variation",
}


@dataclass(slots=True)
class _NoteProfile:
    note: PerspectiveNote
    claim_tokens: set[str]
    counterexample_tokens: set[str]
    implication_tokens: set[str]
    evidence_tokens: set[str]
    evidence_lines: tuple[str, ...]
    support_ids: set[str]
    richness: int


@dataclass(slots=True)
class _PairwiseComparison:
    claim_similarity: float
    counterexample_similarity: float
    implication_similarity: float
    evidence_similarity: float
    evidence_line_overlap: float
    support_overlap: float
    structural_average: float


def _tokenize(text: str | None) -> set[str]:
    if not text:
        return set()
    return {
        token
        for token in _WORD_RE.findall(text.lower())
        if token not in _STOPWORDS and len(token) > 2
    }


def _normalize_line(text: str) -> str:
    return " ".join(sorted(_tokenize(text)))


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _overlap_ratio(left: Iterable[str], right: Iterable[str]) -> float:
    left_set = set(left)
    right_set = set(right)
    if not left_set and not right_set:
        return 1.0
    if not left_set or not right_set:
        return 0.0
    return len(left_set & right_set) / min(len(left_set), len(right_set))


def _note_profile(note: PerspectiveNote) -> _NoteProfile:
    evidence_lines = tuple(_normalize_line(line) for line in note.evidence_needed if _normalize_line(line))
    claim_tokens = _tokenize(note.core_claim)
    counterexample_tokens = _tokenize(note.counterexample)
    implication_tokens = _tokenize(note.testable_implication)
    evidence_tokens: set[str] = set()
    for line in note.evidence_needed:
        evidence_tokens.update(_tokenize(line))

    richness = sum(
        (
            len(claim_tokens),
            len(counterexample_tokens),
            len(implication_tokens),
            len(evidence_tokens),
            len(note.supporting_card_ids),
            len(note.evidence_needed),
        )
    )

    return _NoteProfile(
        note=note,
        claim_tokens=claim_tokens,
        counterexample_tokens=counterexample_tokens,
        implication_tokens=implication_tokens,
        evidence_tokens=evidence_tokens,
        evidence_lines=evidence_lines,
        support_ids=set(note.supporting_card_ids),
        richness=richness,
    )


def _compare_profiles(left: _NoteProfile, right: _NoteProfile) -> _PairwiseComparison:
    claim_similarity = _jaccard(left.claim_tokens, right.claim_tokens)
    counterexample_similarity = _jaccard(left.counterexample_tokens, right.counterexample_tokens)
    implication_similarity = _jaccard(left.implication_tokens, right.implication_tokens)
    evidence_similarity = _jaccard(left.evidence_tokens, right.evidence_tokens)
    evidence_line_overlap = _overlap_ratio(left.evidence_lines, right.evidence_lines)
    support_overlap = _overlap_ratio(left.support_ids, right.support_ids)
    structural_average = (
        claim_similarity * 0.35
        + counterexample_similarity * 0.2
        + implication_similarity * 0.2
        + evidence_similarity * 0.15
        + evidence_line_overlap * 0.1
    )
    return _PairwiseComparison(
        claim_similarity=claim_similarity,
        counterexample_similarity=counterexample_similarity,
        implication_similarity=implication_similarity,
        evidence_similarity=evidence_similarity,
        evidence_line_overlap=evidence_line_overlap,
        support_overlap=support_overlap,
        structural_average=structural_average,
    )


def _question_anchor_tokens(question_card: QuestionCard) -> set[str]:
    anchors = _tokenize(question_card.cleaned_question)
    anchors.update(_tokenize(question_card.actor_entity))
    anchors.update(_tokenize(question_card.outcome_variable))
    anchors.update(_tokenize(question_card.domain_hint))
    return anchors


def _is_vague(question_card: QuestionCard, profile: _NoteProfile) -> bool:
    note = profile.note
    anchors = _question_anchor_tokens(question_card)
    anchor_overlap = len((profile.claim_tokens | profile.implication_tokens) & anchors)
    generic_ratio = 0.0
    if profile.claim_tokens:
        generic_ratio = len(profile.claim_tokens & _GENERIC_NOTE_TERMS) / len(profile.claim_tokens)

    thin_evidence = len(profile.evidence_tokens) < 8 or len(note.evidence_needed) < 2
    weak_counterexample = len(profile.counterexample_tokens) < 5
    weak_implication = len(profile.implication_tokens) < 6
    underspecified_claim = len(profile.claim_tokens) < 7

    return (
        (underspecified_claim and anchor_overlap < 2)
        or (generic_ratio >= 0.35 and anchor_overlap < 3)
        or (thin_evidence and weak_counterexample)
        or (weak_implication and anchor_overlap < 2)
    )


def _choose_better_note(left: _NoteProfile, right: _NoteProfile) -> _NoteProfile:
    left_score = (
        left.richness,
        len(left.support_ids),
        len(left.evidence_lines),
        len(left.claim_tokens | left.counterexample_tokens | left.implication_tokens),
    )
    right_score = (
        right.richness,
        len(right.support_ids),
        len(right.evidence_lines),
        len(right.claim_tokens | right.counterexample_tokens | right.implication_tokens),
    )
    if left_score > right_score:
        return left
    return right


def _field_summary(comparison: _PairwiseComparison) -> str:
    return (
        f"claim={comparison.claim_similarity:.2f}, "
        f"counterexample={comparison.counterexample_similarity:.2f}, "
        f"evidence={comparison.evidence_similarity:.2f}, "
        f"testable_implication={comparison.implication_similarity:.2f}"
    )


def review_notes(question_card: QuestionCard, notes: list[PerspectiveNote]) -> list[ReviewDecision]:
    """Review notes for overlap, novelty, and rewrite needs."""

    profiles = [_note_profile(note) for note in notes]
    canonical_profiles: list[_NoteProfile] = []
    decisions: list[ReviewDecision] = []

    for profile in profiles:
        note = profile.note
        if _is_vague(question_card, profile):
            decisions.append(
                ReviewDecision(
                    target_note_id=note.note_id,
                    action="rewrite",
                    reason=(
                        "Needs rewrite: the claim/evidence package is too generic or weakly anchored to the "
                        f"question. Compare fields -> claim={len(profile.claim_tokens)} tokens, "
                        f"counterexample={len(profile.counterexample_tokens)} tokens, "
                        f"evidence_items={len(note.evidence_needed)}, "
                        f"testable_implication={len(profile.implication_tokens)} tokens."
                    ),
                )
            )
            continue

        best_match: _NoteProfile | None = None
        best_comparison: _PairwiseComparison | None = None
        for candidate in canonical_profiles:
            comparison = _compare_profiles(profile, candidate)
            if best_comparison is None or comparison.structural_average > best_comparison.structural_average:
                best_match = candidate
                best_comparison = comparison

        if best_match is None or best_comparison is None or best_comparison.structural_average < 0.45:
            canonical_profiles.append(profile)
            decisions.append(
                ReviewDecision(
                    target_note_id=note.note_id,
                    action="keep",
                    reason=(
                        "Kept as a distinct perspective: comparisons across claim, counterexample, evidence_needed, "
                        "and testable_implication did not show a high-overlap predecessor."
                    ),
                )
            )
            continue

        stronger = _choose_better_note(profile, best_match)
        weaker = best_match if stronger is profile else profile
        unique_evidence = profile.evidence_tokens - best_match.evidence_tokens
        unique_support = profile.support_ids - best_match.support_ids
        strong_field_matches = sum(
            score >= 0.72
            for score in (
                best_comparison.claim_similarity,
                best_comparison.counterexample_similarity,
                best_comparison.evidence_similarity,
                best_comparison.implication_similarity,
            )
        )
        is_duplicate = (
            best_comparison.claim_similarity >= 0.9
            and best_comparison.counterexample_similarity >= 0.82
            and best_comparison.evidence_similarity >= 0.8
            and best_comparison.implication_similarity >= 0.8
        )
        is_near_duplicate = (
            (strong_field_matches >= 3 and best_comparison.structural_average >= 0.68)
            or (
                strong_field_matches >= 2
                and best_comparison.structural_average >= 0.6
                and best_comparison.claim_similarity >= 0.6
                and best_comparison.evidence_line_overlap >= 0.8
            )
        )

        if is_duplicate:
            if stronger is profile and weaker is best_match:
                replacement_index = canonical_profiles.index(best_match)
                canonical_profiles[replacement_index] = profile
                decisions[replacement_index] = ReviewDecision(
                    target_note_id=best_match.note.note_id,
                    action="drop",
                    reason=(
                        "Dropped as a duplicate after comparing claim, counterexample, evidence_needed, and "
                        f"testable_implication with {note.note_id}; the newer note is richer ({_field_summary(best_comparison)})."
                    ),
                )
                decisions.append(
                    ReviewDecision(
                        target_note_id=note.note_id,
                        action="keep",
                        reason=(
                            "Kept as the canonical version of an otherwise duplicate perspective because it retains the "
                            f"same structure with more detail ({_field_summary(best_comparison)})."
                        ),
                    )
                )
            else:
                decisions.append(
                    ReviewDecision(
                        target_note_id=note.note_id,
                        action="drop",
                        reason=(
                            "Dropped because it duplicates an existing note without a unique contribution after explicit "
                            f"comparison of claim, counterexample, evidence_needed, and testable_implication against "
                            f"{best_match.note.note_id} ({_field_summary(best_comparison)})."
                        ),
                    )
                )
            continue

        if is_near_duplicate:
            if unique_evidence or unique_support:
                decisions.append(
                    ReviewDecision(
                        target_note_id=note.note_id,
                        action="merge",
                        merge_target_note_id=best_match.note.note_id,
                        reason=(
                            "Merge with the closest note because the claim/counterexample/evidence_needed/"
                            "testable_implication structure is near-duplicate, but this note adds a small amount of "
                            f"support or evidence not already present in {best_match.note.note_id} "
                            f"({_field_summary(best_comparison)})."
                        ),
                    )
                )
            else:
                decisions.append(
                    ReviewDecision(
                        target_note_id=note.note_id,
                        action="drop",
                        reason=(
                            "Dropped because it is a near-duplicate with no unique evidence or support after comparing "
                            f"claim, counterexample, evidence_needed, and testable_implication to {best_match.note.note_id} "
                            f"({_field_summary(best_comparison)})."
                        ),
                    )
                )
            continue

        canonical_profiles.append(profile)
        decisions.append(
            ReviewDecision(
                target_note_id=note.note_id,
                action="keep",
                reason=(
                    "Kept: although another note overlaps, at least one of claim, counterexample, evidence_needed, or "
                    f"testable_implication remains meaningfully different from {best_match.note.note_id} "
                    f"({_field_summary(best_comparison)})."
                ),
            )
        )

    return decisions


def review_records(records: list[PerspectiveRecord]) -> list[PerspectiveRecord]:
    """Return records unchanged until review logic is implemented."""

    return records
