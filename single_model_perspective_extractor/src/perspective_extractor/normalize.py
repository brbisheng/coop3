"""Normalization helpers for extracted perspective content."""

from __future__ import annotations

import re
from collections.abc import Iterable

from .models import QuestionCard

_FILLER_PREFIXES = (
    "i want to know",
    "i'd like to know",
    "i would like to know",
    "i am trying to understand",
    "i'm trying to understand",
    "i am curious about",
    "i'm curious about",
    "can you tell me",
    "could you tell me",
    "can you explain",
    "could you explain",
    "please explain",
    "please tell me",
)

_RELATION_VERBS = (
    "affect",
    "affects",
    "impact",
    "impacts",
    "influence",
    "influences",
    "predict",
    "predicts",
    "explain",
    "explains",
    "drive",
    "drives",
    "cause",
    "causes",
    "improve",
    "improves",
    "reduce",
    "reduces",
    "increase",
    "increases",
    "decrease",
    "decreases",
    "shape",
    "shapes",
    "determine",
    "determines",
)

_DOMAIN_KEYWORDS = {
    "economics": {"inflation", "gdp", "unemployment", "wages", "income", "trade", "prices", "housing", "tax", "market"},
    "public health": {"health", "disease", "mortality", "hospital", "patient", "vaccine", "obesity", "infection", "mental health", "anxiety", "depression", "teen"},
    "education": {"student", "students", "school", "schools", "teacher", "teachers", "learning", "education", "classroom", "achievement"},
    "technology": {"ai", "software", "algorithm", "algorithms", "internet", "platform", "data", "automation", "cybersecurity", "robot"},
    "politics": {"government", "policy", "policies", "voter", "voters", "election", "congress", "regulation", "regulations", "state"},
    "climate": {"climate", "emissions", "carbon", "temperature", "warming", "renewable", "energy", "weather", "pollution"},
    "business": {"company", "companies", "firm", "firms", "customer", "customers", "profit", "revenue", "productivity", "strategy"},
}

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "could", "did", "do", "does", "for", "from", "how", "in",
    "is", "it", "of", "on", "or", "should", "the", "to", "what", "when", "where", "which", "who", "why", "will", "with",
    "would", "than", "vs", "versus", "between", "into", "over", "under", "about",
}

_POPULATION_HINTS = {
    "people", "person", "adults", "children", "teens", "teenagers", "teen", "students", "workers", "employees", "patients", "voters", "consumers", "households", "firms", "companies",
}

_PLACE_PATTERN = re.compile(r"\b(?:in|across|within|among|for)\s+([A-Z][\w-]*(?:\s+[A-Z][\w-]*)*)")
_TIME_PATTERN = re.compile(r"\b(?:\d{4}|today|yesterday|tomorrow|current|currently|recent|recently|future|long[- ]term|short[- ]term)\b", re.IGNORECASE)
_COMPARATOR_PATTERN = re.compile(r"\b(?:than|versus|vs\.?|compared with|compared to|relative to)\b", re.IGNORECASE)


def normalize_text(text: str) -> str:
    """Normalize whitespace for downstream processing."""

    return " ".join(text.split())


def normalize_question(question: str) -> QuestionCard:
    """Convert a raw question into a structured QuestionCard."""

    raw_question = normalize_text(question)
    if not raw_question:
        raise ValueError("question must not be empty")

    cleaned_source = _strip_filler(raw_question)
    cleaned_question = _rewrite_as_research_question(cleaned_source)
    actor_entity, outcome_variable = _extract_actor_and_outcome(cleaned_question)
    assumptions = _extract_assumptions(cleaned_question, actor_entity, outcome_variable)
    domain_hint = _infer_domain_hint(cleaned_question)
    keywords = _extract_keywords(cleaned_question, actor_entity, outcome_variable)
    missing_pieces = _extract_missing_pieces(cleaned_question, actor_entity, outcome_variable)

    return QuestionCard(
        raw_question=raw_question,
        cleaned_question=cleaned_question,
        actor_entity=actor_entity,
        outcome_variable=outcome_variable,
        domain_hint=domain_hint,
        assumptions=assumptions,
        keywords=keywords,
        missing_pieces=missing_pieces,
    )


def _strip_filler(text: str) -> str:
    cleaned = text.strip().strip('"\'“”')
    lowered = cleaned.lower()
    for prefix in _FILLER_PREFIXES:
        if lowered.startswith(prefix):
            cleaned = cleaned[len(prefix):].lstrip(" ,:-")
            break
    return cleaned


def _rewrite_as_research_question(text: str) -> str:
    base = text.strip().rstrip(".?!")
    lowered = base.lower()

    if lowered.startswith(("what ", "why ", "how ", "when ", "where ", "which ", "who ", "is ", "are ", "do ", "does ", "did ", "can ", "should ", "would ", "could ", "will ")):
        question = base
    elif lowered.startswith(("whether ", "if ")):
        predicate = re.sub(r"^(?:whether|if)\s+", "", base, flags=re.IGNORECASE)
        question = f"To what extent does {predicate}?"
    else:
        question = f"What does available evidence suggest about {base}?"

    question = question[:1].upper() + question[1:] if question else question
    question = re.sub(
        r"\bdoes\s+(.+?)\s+(affects|impacts|influences|predicts|explains|drives|causes|improves|reduces|increases|decreases|shapes|determines)\b",
        lambda match: f"does {match.group(1)} {_singularize_relation_verb(match.group(2))}",
        question,
        flags=re.IGNORECASE,
    )
    if not question.endswith("?"):
        question = f"{question}?"
    return question


def _singularize_relation_verb(verb: str) -> str:
    irregular = {
        "does": "do",
        "has": "have",
    }
    lowered = verb.lower()
    if lowered in irregular:
        return irregular[lowered]
    if lowered.endswith("ies"):
        return f"{lowered[:-3]}y"
    if lowered.endswith("s"):
        return lowered[:-1]
    return lowered


def _extract_actor_and_outcome(question: str) -> tuple[str | None, str | None]:
    core = question.strip().rstrip("?")
    core = re.sub(r"^To what extent does\s+", "", core, flags=re.IGNORECASE)
    core = re.sub(r"^(?:What|Why|How|When|Where|Which|Who)\s+(?:does|do|did|is|are|can|could|should|would|will)?\s*", "", core, flags=re.IGNORECASE)

    relation_pattern = re.compile(
        rf"(?P<actor>.+?)\s+(?P<verb>{'|'.join(_RELATION_VERBS)})\s+(?P<outcome>.+)",
        re.IGNORECASE,
    )
    match = relation_pattern.search(core)
    if match:
        actor = _clean_phrase(match.group("actor"))
        outcome = _clean_phrase(match.group("outcome"))
        return actor or None, outcome or None

    if core.lower().startswith("the relationship between ") and " and " in core.lower():
        pair_text = core[len("the relationship between "):]
        left, right = pair_text.split(" and ", 1)
        return _clean_phrase(left) or None, _clean_phrase(right) or None

    place_match = _PLACE_PATTERN.search(question)
    if place_match:
        entity = _clean_phrase(place_match.group(1))
        return entity or None, _clean_phrase(core) or None

    noun_chunks = _candidate_phrases(core)
    actor = noun_chunks[0] if noun_chunks else None
    outcome = noun_chunks[1] if len(noun_chunks) > 1 else None
    return actor, outcome


def _extract_assumptions(question: str, actor_entity: str | None, outcome_variable: str | None) -> list[str]:
    assumptions: list[str] = []
    lowered = question.lower()

    if actor_entity and outcome_variable and any(verb in lowered for verb in _RELATION_VERBS):
        assumptions.append(f"{actor_entity} may influence {outcome_variable}.")
    if _COMPARATOR_PATTERN.search(question):
        assumptions.append("The compared options are meaningfully comparable.")
    if "should " in lowered:
        assumptions.append("The question assumes a decision objective or evaluation criterion can be specified.")
    if any(token in lowered for token in ("will ", "would ", "future", "forecast", "predict")):
        assumptions.append("Current evidence can support a forward-looking inference.")
    if any(token in lowered for token in ("best", "optimal", "most effective")):
        assumptions.append("A ranked or optimal answer is possible under stated criteria.")

    return _dedupe_preserve_order(assumptions)


def _infer_domain_hint(question: str) -> str | None:
    lowered = question.lower()
    best_domain: str | None = None
    best_score = 0
    for domain, keywords in _DOMAIN_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in lowered)
        if score > best_score:
            best_score = score
            best_domain = domain
    return best_domain


def _extract_keywords(question: str, actor_entity: str | None, outcome_variable: str | None) -> list[str]:
    keywords: list[str] = []
    for phrase in (actor_entity, outcome_variable):
        if phrase:
            keywords.append(phrase)

    tokens = re.findall(r"[A-Za-z][A-Za-z0-9'-]*", question.lower())
    for token in tokens:
        if token not in _STOPWORDS and len(token) > 2:
            keywords.append(token)

    return _dedupe_preserve_order(keywords)[:8]


def _extract_missing_pieces(
    question: str,
    actor_entity: str | None,
    outcome_variable: str | None,
) -> list[str]:
    missing: list[str] = []
    lowered = question.lower()

    if not any(hint in lowered for hint in _POPULATION_HINTS):
        missing.append("Target population or unit of analysis is not specified.")
    if not _TIME_PATTERN.search(question):
        missing.append("Time frame or study period is not specified.")
    if not _PLACE_PATTERN.search(question):
        missing.append("Geographic or institutional scope is not specified.")
    if _COMPARATOR_PATTERN.search(question) is None and any(token in lowered for token in ("better", "worse", "more", "less", "higher", "lower")):
        missing.append("Comparator or baseline is not clearly specified.")
    if outcome_variable is None:
        missing.append("Primary outcome variable is not clearly defined.")
    if actor_entity is None:
        missing.append("Primary actor, entity, or intervention is not clearly defined.")

    return _dedupe_preserve_order(missing)


def _candidate_phrases(text: str) -> list[str]:
    parts = re.split(r"\b(?:of|for|in|on|among|between|and|with|to)\b", text, flags=re.IGNORECASE)
    candidates = [_clean_phrase(part) for part in parts]
    return [candidate for candidate in candidates if candidate]


def _clean_phrase(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip(" ,:-")
    cleaned = re.sub(r"^(?:the|a|an)\s+", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def _dedupe_preserve_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            deduped.append(value)
    return deduped
