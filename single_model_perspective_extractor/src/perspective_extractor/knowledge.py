"""Knowledge-card generation helpers for the perspective extractor.

The v1 implementation intentionally avoids external retrieval. It expands a
``QuestionCard`` into several structured card types using only the normalized
question fields that already exist in memory.
"""

from __future__ import annotations

from .models import ControversyCard, KnowledgeCard, QuestionCard, VariableCard

_ALLOWED_VARIABLE_ROLES = ("actor", "state", "decision", "constraint", "outcome")


def collect_background(topic: str) -> list[str]:
    """Return placeholder background items for a topic."""

    return [f"background:{topic}"]



def generate_knowledge_cards(question_card: QuestionCard) -> list[KnowledgeCard]:
    """Generate background-fact and mechanism cards from a normalized question.

    The cards focus on reusable context: background facts, common mechanisms,
    and concept frames that can later inform axis generation without answering
    the question outright.
    """

    actor = question_card.actor_entity or "the focal actor"
    outcome = question_card.outcome_variable or "the focal outcome"
    domain = question_card.domain_hint or "the topic domain"
    missing_scope = ", ".join(question_card.missing_pieces[:3]) or "population, setting, and timeframe"

    cards = [
        KnowledgeCard(
            title="Question framing",
            content=(
                f"This question studies how {actor} relates to {outcome}. "
                f"The working domain is {domain}, so useful background should separate descriptive facts, "
                "causal mechanisms, and evaluative claims."
            ),
            source_type="single-model",
            relevance="Establishes the baseline frame before generating perspectives.",
            evidence_needed=[
                f"A clear operational definition of {actor}.",
                f"A clear operational definition of {outcome}.",
            ],
            verification_question=f"Is the question really about how {actor} relates to {outcome}?",
        ),
        KnowledgeCard(
            title="Background facts to establish",
            content=(
                f"A strong analysis should first map the baseline prevalence, distribution, or institutional context of {actor} "
                f"and {outcome}. Before debating mechanisms, it helps to know who is affected, in what setting, and whether the pattern varies across contexts."
            ),
            source_type="single-model",
            relevance="Highlights core background facts that support later comparisons.",
            evidence_needed=[
                f"Baseline levels or prevalence of {outcome}.",
                f"Context about where and among whom {actor} appears.",
                "Any obvious historical trend or institutional backdrop.",
            ],
            verification_question="What baseline facts are needed before interpreting any relationship?",
        ),
        KnowledgeCard(
            title="Mechanism map",
            content=(
                f"A useful mechanism frame asks through which channels {actor} could change {outcome}, whether effects are direct or indirect, "
                "and which mediators or moderators might strengthen, weaken, or reverse the effect."
            ),
            source_type="single-model",
            relevance="Encourages mechanism-first reasoning instead of jumping directly to conclusions.",
            evidence_needed=[
                "Potential mediating steps between cause and outcome.",
                "Potential moderators such as subgroup, setting, or timing.",
            ],
            verification_question=f"Which plausible channels connect {actor} to {outcome}?",
        ),
        KnowledgeCard(
            title="Conceptual boundaries",
            content=(
                f"The question may mix multiple concepts unless the analyst distinguishes construct definition, measurement, scope conditions, and comparator choices. "
                f"In this case, unresolved scope items include {missing_scope}."
            ),
            source_type="single-model",
            relevance="Prevents concept drift when expanding perspectives.",
            evidence_needed=[
                "Definitions for key constructs and their measurement boundaries.",
                "Explicit scope conditions for population, geography, and time horizon.",
            ],
            verification_question="Which conceptual boundaries must be fixed so later perspectives stay comparable?",
        ),
    ]

    if question_card.assumptions:
        cards.append(
            KnowledgeCard(
                title="Embedded assumptions",
                content=(
                    "The wording already carries assumptions that shape interpretation: "
                    + "; ".join(question_card.assumptions)
                ),
                source_type="single-model",
                relevance="Makes implicit assumptions explicit before perspective generation.",
                evidence_needed=["Whether each embedded assumption is justified in the target context."],
                verification_question="Which assumptions come from the wording rather than from evidence?",
            )
        )

    return cards



def generate_variable_cards(question_card: QuestionCard) -> list[VariableCard]:
    """Generate structured variable cards for the normalized question.

    The v1 schema emphasizes actor / state / decision / constraint / outcome.
    Cards are generated from the normalized question alone and do not attempt
    to retrieve or validate outside information.
    """

    actor = question_card.actor_entity or "focal actor"
    outcome = question_card.outcome_variable or "focal outcome"
    domain = question_card.domain_hint or "general"
    missing_scope = ", ".join(question_card.missing_pieces[:2]) or "scope conditions"

    cards = [
        VariableCard(
            name=actor,
            variable_role="actor",
            definition=f"Primary entity, intervention, exposure, or driver whose role in shaping {outcome} is being examined.",
            possible_values=[
                "absence vs presence",
                "low / medium / high intensity",
                "different forms or implementations",
            ],
            measurement_notes="Operationalize the actor as a concrete exposure, intervention, policy, or characteristic rather than a vague label.",
            evidence_needed=[f"A measurable definition of {actor}.", "Evidence that variation in the actor can be observed across cases."],
            testable_implication=f"If {actor} matters, changes in it should correspond to changes in {outcome} under at least some conditions.",
            verification_question=f"How should {actor} be measured so different studies refer to the same construct?",
        ),
        VariableCard(
            name="contextual state",
            variable_role="state",
            definition=(
                f"The background condition or starting context in which the relationship between {actor} and {outcome} unfolds in the {domain} domain."
            ),
            possible_values=[
                "baseline high vs low",
                "stable vs changing environment",
                "different institutional or social settings",
            ],
            measurement_notes="State variables capture initial conditions, subgroup context, or macro environment rather than the focal intervention itself.",
            evidence_needed=["Baseline conditions before the focal actor changes.", "Contextual indicators that differ across settings."],
            testable_implication=f"The apparent effect of {actor} on {outcome} may differ across baseline states.",
            verification_question="Which starting conditions are likely to condition the observed relationship?",
        ),
        VariableCard(
            name="decision lever",
            variable_role="decision",
            definition=(
                f"A controllable choice about whether, when, or how to deploy {actor}, including intensity, timing, targeting, or design."
            ),
            possible_values=[
                "adopt / delay / avoid",
                "broad vs targeted implementation",
                "short-term vs sustained use",
            ],
            measurement_notes="Decision variables matter most when the question can inform policy, management, or strategic action.",
            evidence_needed=["A clearly identifiable choice point.", "Information about implementation timing and intensity."],
            testable_implication=f"Different deployment choices for {actor} should produce different patterns in {outcome}.",
            verification_question=f"What concrete decisions change exposure to {actor}?",
        ),
        VariableCard(
            name="scope constraint",
            variable_role="constraint",
            definition=(
                f"A boundary condition that limits interpretation, including missing scope details such as {missing_scope}, data quality limits, or institutional frictions."
            ),
            possible_values=[
                "resource-limited vs resource-rich setting",
                "short vs long timeframe",
                "narrow vs broad target population",
            ],
            measurement_notes="Constraints should capture what prevents a simple one-size-fits-all inference.",
            evidence_needed=["Explicit scope boundaries.", "Information about feasibility, data quality, or implementation limits."],
            testable_implication=f"When constraints tighten, the observed relationship between {actor} and {outcome} may weaken or look different.",
            verification_question="Which constraints most limit external validity or implementation?",
        ),
        VariableCard(
            name=outcome,
            variable_role="outcome",
            definition=f"The dependent variable or target phenomenon whose level, direction, or distribution may change in response to {actor}.",
            possible_values=[
                "increase / decrease / no change",
                "short-term vs long-term effect",
                "average effect vs uneven subgroup effect",
            ],
            measurement_notes="Specify whether the outcome is measured as incidence, level, rate, perception, behavior, or performance.",
            evidence_needed=[f"A reliable measure of {outcome}.", "Evidence about timing and heterogeneity of the outcome."],
            testable_implication=f"Competing explanations can be compared by the pattern they predict for {outcome}.",
            verification_question=f"What is the best observable measure of {outcome}?",
        ),
    ]

    _validate_variable_roles(cards)
    return cards



def generate_controversy_cards(question_card: QuestionCard) -> list[ControversyCard]:
    """Generate controversy cards centered on competing explanations.

    The cards articulate disagreements worth testing: whether a relationship is
    real, which mechanism dominates, and how much results depend on context or
    measurement choices.
    """

    actor = question_card.actor_entity or "the focal actor"
    outcome = question_card.outcome_variable or "the focal outcome"
    domain = question_card.domain_hint or "the target domain"

    cards = [
        ControversyCard(
            question=f"Does {actor} meaningfully affect {outcome}, or is the apparent relationship mostly spurious?",
            sides=[
                f"{actor} has a substantive causal effect on {outcome}.",
                f"The observed relationship is mostly confounding, selection, or reverse causality rather than a causal effect of {actor}.",
            ],
            evidence_contests=[
                "Causal identification versus correlational evidence.",
                "Alternative explanations such as selection effects or omitted variables.",
            ],
            verification_question="What evidence would distinguish a genuine causal relationship from a spurious association?",
            competing_perspectives=[
                "causal explanation",
                "selection/confounding explanation",
            ],
            compatible_perspectives=["mixed or context-dependent effects"],
        ),
        ControversyCard(
            question=f"If {actor} affects {outcome}, which mechanism matters most?",
            sides=[
                f"The main pathway is direct and intrinsic to {actor}.",
                "The main pathway is indirect, operating through mediators, institutions, or social responses.",
            ],
            evidence_contests=[
                "Whether direct channels outperform mediated explanations.",
                "Which intermediate variables best account for observed changes.",
            ],
            verification_question=f"Which mechanism-specific predictions differ when explaining how {actor} shapes {outcome}?",
            competing_perspectives=[
                "direct-mechanism explanation",
                "indirect-mechanism explanation",
            ],
            compatible_perspectives=["multiple mechanisms can coexist"],
        ),
        ControversyCard(
            question=f"Are findings about {actor} and {outcome} general across contexts in {domain}, or highly contingent on scope conditions?",
            sides=[
                "The pattern is broadly generalizable across populations, places, and time periods.",
                "The pattern depends heavily on subgroup, geography, timeframe, institutions, or measurement choices.",
            ],
            evidence_contests=[
                "External validity across settings.",
                "Sensitivity to measurement and scope choices.",
            ],
            verification_question="Which contextual changes would most likely reverse or shrink the observed pattern?",
            competing_perspectives=[
                "generalizability-first explanation",
                "context-dependence explanation",
            ],
            compatible_perspectives=["stable average effects with heterogeneous subgroup impacts"],
        ),
    ]

    if question_card.assumptions:
        cards.append(
            ControversyCard(
                question="Which assumptions embedded in the question are substantive versus merely convenient framing choices?",
                sides=[
                    "The embedded assumptions are reasonable simplifications for the inquiry.",
                    "The embedded assumptions bias the framing and may exclude important alternatives.",
                ],
                evidence_contests=["Whether the initial framing narrows the explanatory space too early."],
                verification_question="What alternative framing would change the interpretation of the same evidence?",
                competing_perspectives=["assumption-preserving frame", "assumption-challenging frame"],
                compatible_perspectives=["some assumptions are useful while others should be relaxed"],
            )
        )

    return cards



def _validate_variable_roles(cards: list[VariableCard]) -> None:
    for card in cards:
        if card.variable_role not in _ALLOWED_VARIABLE_ROLES:
            raise ValueError(f"Unsupported variable_role: {card.variable_role}")
