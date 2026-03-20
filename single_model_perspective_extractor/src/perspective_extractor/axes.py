"""Perspective axis generation."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from .models import AxisCard, ControversyCard, KnowledgeCard, QuestionCard, VariableCard

_AXIS_GENERATION_PROMPT = """Generate perspective axes for the research question below.

Question:
- {cleaned_question}

Known context:
- actor: {actor}
- outcome: {outcome}
- domain: {domain}
- assumptions: {assumptions}
- missing pieces: {missing_pieces}
- support summary: {support_summary}

Output requirements:
- Produce 8 to 12 axes.
- Cover multiple structure types rather than only mechanism. Include a mix such as framing, mechanism, measurement, comparison, scope, temporal, decision, distributional, evidence-quality, or stakeholder/conflict lenses when relevant.
- For every axis include: name, axis_type, focus, and how_is_it_distinct.
- Every axis must explain why it is distinct from the others.
- Remove shallow rewrites or duplicate axes.
- Do not generate direct conclusions, verdicts, recommendations, or claims that one side is true.
- Axis names should be short noun phrases that label an observation window, not an answer.
"""

_CONCLUSION_CUES = {
    "best",
    "better",
    "worse",
    "worst",
    "good",
    "bad",
    "beneficial",
    "harmful",
    "effective",
    "ineffective",
    "should",
    "must",
    "prove",
    "proves",
    "proved",
    "disprove",
    "disproves",
    "wrong",
    "right",
}

_FILLER_TOKENS = {
    "a",
    "an",
    "and",
    "axis",
    "frame",
    "framing",
    "lens",
    "of",
    "perspective",
    "the",
    "view",
    "window",
}


@dataclass(frozen=True, slots=True)
class _AxisTemplate:
    name: str
    axis_type: str
    focus_template: str
    distinct_template: str
    support_roles: tuple[str, ...] = ()
    knowledge_slice: tuple[int, int] = (0, 0)
    controversy_slice: tuple[int, int] = (0, 0)


_AXIS_TEMPLATES: tuple[_AxisTemplate, ...] = (
    _AxisTemplate(
        name="construct definition",
        axis_type="framing",
        focus_template="Clarify how {actor} and {outcome} are defined, bounded, and separated from nearby concepts before comparing perspectives.",
        distinct_template="Separates construct definition and category boundaries from causal, evaluative, or implementation claims.",
        support_roles=("actor", "outcome", "constraint"),
        knowledge_slice=(0, 2),
    ),
    _AxisTemplate(
        name="causal pathways",
        axis_type="mechanism",
        focus_template="Map the direct and indirect channels through which {actor} could shape {outcome}, including mediators and moderators.",
        distinct_template="Focuses on process and transmission channels rather than only whether an association appears.",
        support_roles=("actor", "state", "outcome"),
        knowledge_slice=(1, 3),
        controversy_slice=(1, 2),
    ),
    _AxisTemplate(
        name="measurement strategy",
        axis_type="measurement",
        focus_template="Compare how {actor} and {outcome} are operationalized, measured, and observed across possible studies or cases.",
        distinct_template="Centers measurement choices and indicator validity rather than substantive explanations of the relationship.",
        support_roles=("actor", "outcome"),
        knowledge_slice=(0, 1),
        controversy_slice=(2, 3),
    ),
    _AxisTemplate(
        name="counterfactual comparison",
        axis_type="comparison",
        focus_template="Ask which comparator or counterfactual is appropriate when judging how {actor} relates to {outcome}.",
        distinct_template="Frames the question around which comparator is appropriate, not around a single favored explanation.",
        support_roles=("decision", "constraint", "outcome"),
        knowledge_slice=(0, 1),
        controversy_slice=(0, 1),
    ),
    _AxisTemplate(
        name="decision and implementation",
        axis_type="decision",
        focus_template="Examine choices about whether, when, and how to deploy or respond to {actor} in the {domain} domain.",
        distinct_template="Looks at controllable levers and implementation tradeoffs instead of abstract claims about the relationship alone.",
        support_roles=("decision", "constraint", "outcome"),
        knowledge_slice=(0, 2),
    ),
    _AxisTemplate(
        name="scope conditions",
        axis_type="scope",
        focus_template="Test when claims about {actor} and {outcome} travel across populations, settings, and time horizons.",
        distinct_template="Highlights external-validity boundaries and heterogeneity instead of treating one setting as universal.",
        support_roles=("state", "constraint", "outcome"),
        knowledge_slice=(2, 4),
        controversy_slice=(2, 3),
    ),
    _AxisTemplate(
        name="temporal dynamics",
        axis_type="temporal",
        focus_template="Distinguish short-run, long-run, delayed, and feedback effects linking {actor} to {outcome}.",
        distinct_template="Organizes disagreement around timing and sequence, not only average direction or magnitude.",
        support_roles=("state", "decision", "outcome"),
        knowledge_slice=(1, 3),
    ),
    _AxisTemplate(
        name="distributional effects",
        axis_type="distributional",
        focus_template="Compare who benefits, who bears costs, and which subgroups experience different effects on {outcome}.",
        distinct_template="Moves from average effects to subgroup patterns and uneven consequences across affected populations.",
        support_roles=("state", "constraint", "outcome"),
        knowledge_slice=(1, 2),
        controversy_slice=(2, 3),
    ),
    _AxisTemplate(
        name="evidence quality",
        axis_type="evidence",
        focus_template="Evaluate which study designs, data sources, or identification strategies are needed before interpreting claims about {actor} and {outcome}.",
        distinct_template="Treats the strength of inference as the main differentiator, separate from any one substantive theory.",
        support_roles=("constraint", "outcome"),
        knowledge_slice=(0, 2),
        controversy_slice=(0, 1),
    ),
    _AxisTemplate(
        name="stakeholder incentives",
        axis_type="stakeholder",
        focus_template="Examine how institutions, groups, or stakeholders may interpret, amplify, resist, or reshape the effects of {actor} on {outcome}.",
        distinct_template="Centers strategic interaction and incentive conflicts rather than only impersonal causal structure.",
        support_roles=("actor", "decision", "constraint"),
        knowledge_slice=(0, 1),
        controversy_slice=(1, 3),
    ),
)


def derive_axes(topic: str) -> list[str]:
    """Return initial perspective axes for a topic."""

    return [topic]


def generate_axes(
    question_card: QuestionCard,
    knowledge_cards: list[KnowledgeCard] | None = None,
    variable_cards: list[VariableCard] | None = None,
    controversy_cards: list[ControversyCard] | None = None,
) -> list[AxisCard]:
    """Generate 8-12 structurally distinct axis cards for a question.

    The implementation is intentionally deterministic for the single-model
    scaffold, but it still codifies the prompt and post-processing rules that a
    future LLM-backed version should follow.
    """

    knowledge_cards = knowledge_cards or []
    variable_cards = variable_cards or []
    controversy_cards = controversy_cards or []

    actor = question_card.actor_entity or "the focal actor"
    outcome = question_card.outcome_variable or "the focal outcome"
    domain = question_card.domain_hint or "general"
    prompt = _build_axes_prompt(
        question_card,
        knowledge_cards=knowledge_cards,
        variable_cards=variable_cards,
        controversy_cards=controversy_cards,
    )

    role_groups = _group_variable_cards(variable_cards)
    raw_axes: list[AxisCard] = []
    for priority, template in enumerate(_AXIS_TEMPLATES, start=1):
        supporting_cards = _pick_supporting_cards(
            template,
            knowledge_cards=knowledge_cards,
            role_groups=role_groups,
            controversy_cards=controversy_cards,
        )
        summary = _summarize_supporting_cards(supporting_cards)
        distinctness = template.distinct_template
        if summary:
            distinctness = f"{distinctness} Support trace: {'; '.join(summary)}."

        raw_axes.append(
            AxisCard(
                name=template.name,
                axis_type=template.axis_type,
                focus=template.focus_template.format(actor=actor, outcome=outcome, domain=domain),
                how_is_it_distinct=distinctness,
                priority=priority,
                evidence_needed=[
                    f"Evidence needed for the {template.name} axis on question {question_card.question_id}.",
                    f"Prompt rule trace: {prompt.splitlines()[0]}",
                ],
                verification_question=f"Does the {template.name} axis add a distinct lens on {question_card.cleaned_question}?",
                supporting_card_ids=_unique_card_ids(supporting_cards),
            )
        )

    return _postprocess_axes(raw_axes)


def _build_axes_prompt(
    question_card: QuestionCard,
    *,
    knowledge_cards: list[KnowledgeCard],
    variable_cards: list[VariableCard],
    controversy_cards: list[ControversyCard],
) -> str:
    return _AXIS_GENERATION_PROMPT.format(
        cleaned_question=question_card.cleaned_question,
        actor=question_card.actor_entity or "the focal actor",
        outcome=question_card.outcome_variable or "the focal outcome",
        domain=question_card.domain_hint or "general",
        assumptions=", ".join(question_card.assumptions[:3]) or "none noted",
        missing_pieces=", ".join(question_card.missing_pieces[:4]) or "none noted",
        support_summary="; ".join(
            _summarize_supporting_cards([*knowledge_cards[:2], *variable_cards[:3], *controversy_cards[:2]])
        ) or "no auxiliary cards supplied",
    )


def _group_variable_cards(variable_cards: list[VariableCard]) -> dict[str, list[VariableCard]]:
    groups: dict[str, list[VariableCard]] = {}
    for card in variable_cards:
        groups.setdefault(card.variable_role, []).append(card)
    return groups


def _pick_supporting_cards(
    template: _AxisTemplate,
    *,
    knowledge_cards: list[KnowledgeCard],
    role_groups: dict[str, list[VariableCard]],
    controversy_cards: list[ControversyCard],
) -> list[KnowledgeCard | VariableCard | ControversyCard]:
    selected: list[KnowledgeCard | VariableCard | ControversyCard] = []
    knowledge_start, knowledge_end = template.knowledge_slice
    controversy_start, controversy_end = template.controversy_slice
    selected.extend(knowledge_cards[knowledge_start:knowledge_end])
    for role in template.support_roles:
        selected.extend(role_groups.get(role, [])[:1])
    selected.extend(controversy_cards[controversy_start:controversy_end])
    return _dedupe_cards(selected)


def _postprocess_axes(raw_axes: list[AxisCard]) -> list[AxisCard]:
    seen_names: set[str] = set()
    axes: list[AxisCard] = []
    type_counts: Counter[str] = Counter()

    for axis in raw_axes:
        normalized_name = _normalize_axis_name(axis.name)
        if not normalized_name or normalized_name in seen_names:
            continue
        if _is_conclusion_like(axis):
            continue
        axis.name = _display_axis_name(axis.name)
        axis.how_is_it_distinct = axis.how_is_it_distinct.strip()
        seen_names.add(normalized_name)
        type_counts[axis.axis_type] += 1
        axes.append(axis)

    if len(type_counts) < 4:
        raise ValueError("generate_axes must retain multiple structural axis types")
    if not 8 <= len(axes) <= 12:
        raise ValueError("generate_axes must return between 8 and 12 axes after deduplication")
    if any(not axis.how_is_it_distinct for axis in axes):
        raise ValueError("each axis must retain how_is_it_distinct after post-processing")
    return axes


def _display_axis_name(name: str) -> str:
    cleaned = re.sub(r"\s+", " ", name).strip(" -_")
    return cleaned.lower()


def _normalize_axis_name(name: str) -> str:
    tokens = re.findall(r"[a-z0-9]+", name.lower().replace("&", " and "))
    normalized_tokens = []
    for token in tokens:
        if token in _FILLER_TOKENS:
            continue
        normalized_tokens.append(_singularize_token(token))
    if not normalized_tokens:
        return ""
    return " ".join(sorted(dict.fromkeys(normalized_tokens)))


def _singularize_token(token: str) -> str:
    if token.endswith("ies") and len(token) > 4:
        return f"{token[:-3]}y"
    if token.endswith("s") and len(token) > 3 and not token.endswith("ss"):
        return token[:-1]
    return token


def _is_conclusion_like(axis: AxisCard) -> bool:
    text = " ".join((axis.name, axis.focus, axis.how_is_it_distinct)).lower()
    tokens = set(re.findall(r"[a-z]+", text))
    return bool(tokens & _CONCLUSION_CUES)


def _card_id(card: KnowledgeCard | VariableCard | ControversyCard) -> str:
    if isinstance(card, KnowledgeCard):
        return card.knowledge_id
    if isinstance(card, VariableCard):
        return card.variable_id
    return card.controversy_id


def _card_label(card: KnowledgeCard | VariableCard | ControversyCard) -> str:
    if isinstance(card, KnowledgeCard):
        return card.title
    if isinstance(card, VariableCard):
        return f"{card.variable_role}:{card.name}"
    return card.question


def _unique_card_ids(cards: list[KnowledgeCard | VariableCard | ControversyCard]) -> list[str]:
    return [_card_id(card) for card in _dedupe_cards(cards)]


def _dedupe_cards(cards: list[KnowledgeCard | VariableCard | ControversyCard]) -> list[KnowledgeCard | VariableCard | ControversyCard]:
    seen: set[str] = set()
    ordered: list[KnowledgeCard | VariableCard | ControversyCard] = []
    for card in cards:
        card_id = _card_id(card)
        if card_id not in seen:
            seen.add(card_id)
            ordered.append(card)
    return ordered


def _summarize_supporting_cards(cards: list[KnowledgeCard | VariableCard | ControversyCard]) -> list[str]:
    grouped: dict[str, list[str]] = {"knowledge": [], "variable": [], "controversy": []}
    for card in cards:
        if isinstance(card, KnowledgeCard):
            grouped["knowledge"].append(_card_label(card))
        elif isinstance(card, VariableCard):
            grouped["variable"].append(_card_label(card))
        else:
            grouped["controversy"].append(_card_label(card))

    summary: list[str] = []
    for label in ("knowledge", "variable", "controversy"):
        if grouped[label]:
            summary.append(f"{label} support: {', '.join(grouped[label][:2])}")
    return summary
