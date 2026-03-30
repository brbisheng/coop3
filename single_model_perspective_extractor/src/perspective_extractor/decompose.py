"""Phase-1 problem decomposition focused on actors, nodes, and constraints."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import asdict
from pathlib import Path

from .models import ActorCard, ConstraintCard, DecomposeResult, NodeCard, ProblemFrame
from .openrouter import call_openrouter

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

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "could", "did", "do", "does", "for", "from", "how", "in",
    "is", "it", "of", "on", "or", "should", "the", "to", "what", "when", "where", "which", "who", "why", "will", "with",
    "would", "than", "vs", "versus", "between", "into", "over", "under", "about", "if", "whether", "we", "they", "this",
}

_TIME_PATTERN = re.compile(r"\b(?:\d{4}|today|yesterday|tomorrow|current|currently|recent|recently|future|near[- ]term|long[- ]term|short[- ]term|next \d+ (?:days|weeks|months|years))\b", re.IGNORECASE)
_PLACE_PATTERN = re.compile(r"\b(?:in|across|within|among|for|between)\s+([A-Z][\w.-]*(?:\s+[A-Z][\w.-]*)*)")
_COMPARATOR_PATTERN = re.compile(r"\b(?:than|versus|vs\.?|compared with|compared to|relative to)\b", re.IGNORECASE)
_TRIM_PREFIX_PATTERN = re.compile(r"^(?:and|or|but|how|what|why|when|where|which|who|if|whether|could|would|should|can|will|does|do|did|is|are|the|a|an|at|to|through|via|over|under|from|of|in|on|force|forces|forcing|reroute|reroutes|rerouting|disruption|disruptions)\s+", re.IGNORECASE)
_TRIM_SUFFIX_PATTERN = re.compile(r"\s+(?:to|through|via|over|under|because|if|when|while|that|which|who|force|forces|forcing|reroute|reroutes|rerouting).*$", re.IGNORECASE)

_ACTOR_KEYWORDS: dict[str, tuple[str, ...]] = {
    "institution": ("ministry", "agency", "authority", "regulator", "court", "customs", "central bank", "congress", "commission", "board"),
    "state": ("government", "state", "province", "country", "nation", "military", "city", "municipality"),
    "firm": ("company", "firm", "operator", "supplier", "carrier", "shipper", "trader", "bank", "platform owner", "manufacturer", "refiner", "distributor"),
    "organization": ("union", "ngo", "hospital", "school", "university", "utility", "port authority", "grid operator"),
    "proxy": ("proxy", "militia", "intermediary", "broker", "contractor"),
    "person": ("consumer", "driver", "patient", "student", "worker", "employee", "voter", "leader"),
}

_NODE_PATTERNS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("facility", "Physical facility that processes, stores, transfers, or concentrates flows", ("port", "terminal", "refinery", "plant", "warehouse", "depot", "factory", "hub", "base", "station", "mine", "substation", "data center", "airport")),
    ("route", "Transit route or corridor through which goods, energy, people, or data must move", ("route", "corridor", "shipping lane", "pipeline", "rail line", "road", "highway", "bridge", "canal", "strait", "crossing", "lane")),
    ("platform", "Platform or coordination layer that matches participants or controls access", ("platform", "marketplace", "exchange", "app", "network", "cloud", "payment rail", "operating system", "portal")),
    ("market", "Market where prices, matching, or substitution pressures are expressed", ("market", "spot market", "futures market", "labor market", "auction", "order book")),
    ("institutional node", "Institutional gatekeeper that authorizes, clears, inspects, or allocates", ("customs", "clearinghouse", "regulator", "court", "ministry", "permit office", "inspection office", "grid operator", "port authority")),
)

_CONSTRAINT_HINTS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("capacity", "congestion", "throughput", "bottleneck", "chokepoint"), "Physical throughput or congestion limits"),
    (("regulation", "regulatory", "permit", "inspection", "compliance", "legal", "law"), "Regulatory and legal process limits"),
    (("budget", "financing", "credit", "capital", "cost"), "Financial limits on response or adaptation"),
    (("labor", "staff", "crew", "workforce", "union", "strike"), "Labor availability or labor conflict"),
    (("weather", "storm", "season", "drought", "heat"), "Environmental or weather exposure"),
    (("sanction", "export control", "embargo", "tariff", "diplomatic"), "Geopolitical restriction on movement or trade"),
    (("data", "visibility", "information", "measurement", "forecast"), "Information or measurement uncertainty"),
    (("safety", "hazard", "security", "risk"), "Safety and security requirements slow action"),
)


def normalize_text(text: str) -> str:
    """Normalize whitespace for downstream processing."""

    return " ".join(text.split())



def decompose_problem(problem_text: str) -> DecomposeResult:
    """Convert a raw problem statement into phase-1 decomposition artifacts."""

    normalized = normalize_text(problem_text)
    if not normalized:
        raise ValueError("problem_text must not be empty")

    cleaned = _strip_filler(normalized)
    core_question = _rewrite_as_core_question(cleaned)
    problem_frame = ProblemFrame(
        core_question=core_question,
        decision_or_analysis_target=_infer_decision_target(cleaned),
        scope_notes=_infer_scope_notes(cleaned),
    )

    actor_cards = _build_actor_cards(cleaned)
    node_cards = _build_node_cards(cleaned)
    constraint_cards = _build_constraint_cards(cleaned, actor_cards, node_cards)

    return DecomposeResult(
        problem_frame=problem_frame,
        actor_cards=actor_cards,
        node_cards=node_cards,
        constraint_cards=constraint_cards,
    )



def decompose_to_json(problem_text: str) -> str:
    """Return a stable JSON rendering of ``decompose_problem`` output."""

    return json.dumps(asdict(decompose_problem(problem_text)), indent=2, ensure_ascii=False, sort_keys=True)



def save_decompose_result(problem_text: str, output_path: str | Path) -> Path:
    """Run decomposition and save the JSON result to disk."""

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(decompose_to_json(problem_text) + "\n", encoding="utf-8")
    return destination



def _strip_filler(text: str) -> str:
    cleaned = text.strip().strip('"\'“”')
    lowered = cleaned.lower()
    for prefix in _FILLER_PREFIXES:
        if lowered.startswith(prefix):
            return cleaned[len(prefix):].lstrip(" ,:-")
    return cleaned



def _rewrite_as_core_question(text: str) -> str:
    base = text.strip().rstrip(".?!")
    lowered = base.lower()
    if lowered.startswith(("what ", "why ", "how ", "when ", "where ", "which ", "who ", "is ", "are ", "do ", "does ", "did ", "can ", "should ", "would ", "could ", "will ")):
        question = base
    elif lowered.startswith(("whether ", "if ")):
        predicate = re.sub(r"^(?:whether|if)\s+", "", base, flags=re.IGNORECASE)
        question = f"What happens if {predicate}?"
    else:
        question = f"What are the main actors, nodes, and constraints in {base}?"

    question = question[:1].upper() + question[1:] if question else question
    return question if question.endswith("?") else f"{question}?"



def _infer_decision_target(text: str) -> str:
    lowered = text.lower()
    if any(token in lowered for token in ("assess", "evaluate", "analyze", "understand", "explain")):
        return "Map the concrete actors, operational nodes, and binding constraints that control the answer."
    if any(token in lowered for token in ("respond", "mitigate", "prevent", "reduce", "improve", "optimize", "plan")):
        return "Identify the operational levers, chokepoints, and limits that would matter for action."
    return "Clarify who matters, which nodes or chokepoints matter, and what constraints could dominate the outcome."



def _infer_scope_notes(text: str) -> list[str]:
    scope_notes: list[str] = []
    if not _TIME_PATTERN.search(text):
        scope_notes.append("Time horizon is not explicit yet.")
    if not _PLACE_PATTERN.search(text):
        scope_notes.append("Geographic or institutional scope is not explicit yet.")
    if _COMPARATOR_PATTERN.search(text):
        scope_notes.append("The problem implies a comparison and needs a clear baseline.")
    if not any(word in text.lower() for word in ("cost", "capacity", "risk", "price", "security", "speed")):
        scope_notes.append("Success criteria or outcome metric should be specified more concretely.")
    return scope_notes



def _build_actor_cards(text: str) -> list[ActorCard]:
    candidates: list[tuple[str, str]] = []
    lower_text = text.lower()

    for actor_type, keywords in _ACTOR_KEYWORDS.items():
        for keyword in keywords:
            for phrase in _extract_keyword_phrases(text, keyword):
                candidates.append((phrase, actor_type))

    for phrase in _extract_list_after_marker(text, ("force", "push", "leave", "require", "allow")):
        if _looks_like_actor(phrase):
            candidates.append((phrase, _infer_actor_type(phrase)))

    if not candidates:
        fallback = _extract_focus_phrase(text)
        if fallback:
            candidates.append((fallback, _infer_actor_type(fallback)))

    cards: list[ActorCard] = []
    seen: set[str] = set()
    for name, actor_type in candidates:
        key = name.casefold()
        if key in seen or _is_noise_phrase(name) or _looks_like_pure_node(name):
            continue
        seen.add(key)
        cards.append(
            ActorCard(
                name=name,
                type=actor_type,
                role=_infer_actor_role(name, text),
                goal_guess=_infer_actor_goal(name, text),
                why_relevant=_infer_actor_relevance(name, text),
            )
        )
        if len(cards) >= 8:
            break

    return cards



def _build_node_cards(text: str) -> list[NodeCard]:
    candidates: list[tuple[str, str, str]] = []
    for node_type, default_function, keywords in _NODE_PATTERNS:
        for keyword in keywords:
            for phrase in _extract_keyword_phrases(text, keyword):
                candidates.append((phrase, node_type, default_function))

    chokepoint_patterns = (
        r"\b([A-Z][\w&./-]*(?:\s+[A-Z][\w&./-]*)*\s+(?:bridge|strait|canal|terminal|pipeline|hub))\b",
        r"\b([a-z][\w&./-]*(?:\s+[a-z][\w&./-]*){0,3}\s+(?:bottleneck|chokepoint|hub|terminal|pipeline|corridor))\b",
    )
    for pattern in chokepoint_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            phrase = _clean_phrase(match.group(1))
            if phrase:
                node_type = _infer_node_type(phrase)
                candidates.append((phrase, node_type, _infer_node_function(phrase, node_type)))

    if not candidates:
        fallback = _extract_focus_phrase(text)
        if fallback:
            node_type = _infer_node_type(fallback)
            if node_type != "other":
                candidates.append((fallback, node_type, _infer_node_function(fallback, node_type)))

    cards: list[NodeCard] = []
    seen: set[str] = set()
    for name, node_type, default_function in candidates:
        key = name.casefold()
        if key in seen or _is_noise_phrase(name) or node_type == "other":
            continue
        seen.add(key)
        function = _infer_node_function(name, node_type) or default_function
        cards.append(
            NodeCard(
                name=name,
                type=node_type,
                function=function,
                why_relevant=_infer_node_relevance(name, node_type, text),
            )
        )
        if len(cards) >= 8:
            break

    return cards



def _build_constraint_cards(text: str, actor_cards: list[ActorCard], node_cards: list[NodeCard]) -> list[ConstraintCard]:
    lower_text = text.lower()
    applies_to = [card.name for card in actor_cards[:2]] + [card.name for card in node_cards[:2]]
    applies_to = _dedupe_preserve_order(applies_to) or ["problem frame"]
    cards: list[ConstraintCard] = []
    seen: set[str] = set()

    for keywords, label in _CONSTRAINT_HINTS:
        if any(keyword in lower_text for keyword in keywords):
            constraint = label
            key = constraint.casefold()
            if key not in seen:
                seen.add(key)
                cards.append(
                    ConstraintCard(
                        constraint=constraint,
                        applies_to=applies_to,
                        why_it_matters=_constraint_why_it_matters(label, actor_cards, node_cards),
                    )
                )

    if not _TIME_PATTERN.search(text):
        cards.append(
            ConstraintCard(
                constraint="Time horizon is underspecified",
                applies_to=applies_to,
                why_it_matters="Short-run versus long-run adaptation can change which actors and nodes become decisive.",
            )
        )
    if not _PLACE_PATTERN.search(text):
        cards.append(
            ConstraintCard(
                constraint="Geographic or institutional scope is underspecified",
                applies_to=applies_to,
                why_it_matters="Without a clear jurisdiction or operating area, it is easy to miss the real gatekeepers and facilities.",
            )
        )
    if _COMPARATOR_PATTERN.search(text):
        cards.append(
            ConstraintCard(
                constraint="Comparator or baseline must be pinned down",
                applies_to=applies_to,
                why_it_matters="Competing routes, platforms, or policies can look stronger or weaker depending on the baseline case.",
            )
        )

    if not cards:
        cards.append(
            ConstraintCard(
                constraint="Outcome metric is still broad",
                applies_to=applies_to,
                why_it_matters="The decomposition is stronger once the analysis target is tied to a measurable failure mode, bottleneck, or operational objective.",
            )
        )

    return cards[:6]



def _constraint_why_it_matters(label: str, actor_cards: list[ActorCard], node_cards: list[NodeCard]) -> str:
    actor_text = actor_cards[0].name if actor_cards else "key actors"
    node_text = node_cards[0].name if node_cards else "key nodes"
    return f"{label} can determine whether {actor_text} can adapt around {node_text} or whether the bottleneck stays binding."




def _looks_like_pure_node(name: str) -> bool:
    lowered = name.lower()
    node_keywords = {keyword for _node_type, _function, keywords in _NODE_PATTERNS for keyword in keywords}
    actor_keywords = {keyword for keywords in _ACTOR_KEYWORDS.values() for keyword in keywords}
    return any(keyword in lowered for keyword in node_keywords) and not any(keyword in lowered for keyword in actor_keywords)

def _infer_actor_type(name: str) -> str:
    lowered = name.lower()
    for actor_type, keywords in _ACTOR_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return actor_type
    if name[:1].isupper() and len(name.split()) <= 3:
        return "organization"
    return "other"



def _infer_actor_role(name: str, text: str) -> str:
    lowered = name.lower()
    if any(token in lowered for token in ("regulator", "authority", "ministry", "court", "customs", "agency")):
        return "Sets or enforces rules that can accelerate, block, or reshape response options"
    if any(token in lowered for token in ("operator", "carrier", "supplier", "shipper", "refiner", "distributor")):
        return "Operates the practical flow of goods, services, traffic, or information"
    if any(token in lowered for token in ("government", "state", "military", "city", "municipality")):
        return "Controls public authority, coercive tools, or policy levers relevant to the problem"
    if any(token in lowered for token in ("consumer", "driver", "patient", "student", "worker", "employee", "voter")):
        return "Absorbs downstream effects and may change behavior in response to pressure"
    focus = _extract_focus_phrase(text) or "the focal issue"
    return f"Has a plausible stake in how {focus} develops"



def _infer_actor_goal(name: str, text: str) -> str:
    lowered = name.lower()
    if any(token in lowered for token in ("regulator", "authority", "customs", "court", "agency")):
        return "Maintain control, compliance, and acceptable risk while avoiding visible failure"
    if any(token in lowered for token in ("operator", "carrier", "supplier", "shipper", "refiner", "distributor", "company", "firm")):
        return "Preserve throughput, margins, and operational continuity"
    if any(token in lowered for token in ("government", "state", "city", "municipality")):
        return "Prevent disruption from becoming a political, economic, or security liability"
    if any(token in lowered for token in ("consumer", "driver", "patient", "student", "worker", "employee", "voter")):
        return "Protect access, affordability, safety, or livelihood"
    focus = _extract_focus_phrase(text) or "the situation"
    return f"Improve its position as {focus} unfolds"



def _infer_actor_relevance(name: str, text: str) -> str:
    if any(token in text.lower() for token in name.lower().split()):
        return "The problem statement directly names or strongly implies this actor as part of the causal picture."
    focus = _extract_focus_phrase(text) or "the focal outcome"
    return f"This actor could redirect, absorb, or amplify pressure around {focus}."



def _infer_node_type(name: str) -> str:
    lowered = name.lower()
    for node_type, _function, keywords in _NODE_PATTERNS:
        if any(keyword in lowered for keyword in keywords):
            return node_type
    if any(keyword in lowered for keyword in ("bottleneck", "chokepoint", "hub")):
        return "facility"
    return "other"



def _infer_node_function(name: str, node_type: str) -> str:
    lowered = name.lower()
    if node_type == "facility":
        if any(token in lowered for token in ("terminal", "port", "airport", "station")):
            return "Transfers flows between transport modes or between arrival and distribution systems"
        if any(token in lowered for token in ("refinery", "plant", "factory", "mine", "data center")):
            return "Transforms inputs into outputs or concentrates production capacity"
        return "Concentrates physical capacity whose disruption can propagate downstream"
    if node_type == "route":
        return "Carries traffic through a corridor where rerouting may be slow, costly, or impossible"
    if node_type == "platform":
        return "Coordinates participants and controls matching, visibility, or access"
    if node_type == "market":
        return "Expresses substitution pressure, scarcity, or pricing under stress"
    if node_type == "institutional node":
        return "Authorizes, clears, inspects, or allocates access at a critical decision point"
    return "A concrete node may matter if it concentrates access, throughput, or coordination"



def _infer_node_relevance(name: str, node_type: str, text: str) -> str:
    if any(token in name.lower() for token in ("bottleneck", "chokepoint", "bridge", "strait", "canal")):
        return "This looks like an explicit chokepoint where small disruptions can create large second-order effects."
    focus = _extract_focus_phrase(text) or "the focal problem"
    return f"This {node_type} is a plausible place where pressure, substitution, or failure could become operationally visible in {focus}."




def _extract_keyword_phrases(text: str, keyword: str) -> list[str]:
    pattern = re.compile(
        rf"\b(?:the\s+)?(?:[A-Za-z0-9&./-]+\s+){{0,3}}{re.escape(keyword)}s?\b",
        re.IGNORECASE,
    )
    phrases = [_clean_phrase(match.group(0)) for match in pattern.finditer(text)]
    return [phrase for phrase in _dedupe_preserve_order(phrases) if phrase]


def _extract_list_after_marker(text: str, markers: tuple[str, ...]) -> list[str]:
    lowered = text.lower()
    for marker in markers:
        marker_text = f" {marker} "
        if marker_text in f" {lowered} ":
            start = lowered.index(marker_text) + len(marker_text) - 1
            segment = text[start:]
            segment = re.split(r"\b(?:to|through|via|over|under|because|if|when)\b", segment, maxsplit=1, flags=re.IGNORECASE)[0]
            parts = re.split(r",|\band\b", segment, flags=re.IGNORECASE)
            phrases = []
            for part in parts:
                phrase = _clean_phrase(part)
                if phrase and _looks_like_content_phrase(phrase):
                    phrases.append(phrase)
            return phrases
    return []

def _extract_focus_phrase(text: str) -> str | None:
    phrases = _candidate_phrases(text)
    return phrases[0] if phrases else None



def _candidate_phrases(text: str) -> list[str]:
    phrases: list[str] = []
    for match in re.finditer(r"\b(?:[A-Z][\w&./-]*|[a-z][\w&./-]*)(?:\s+(?:[A-Z][\w&./-]*|[a-z][\w&./-]*)){0,4}\b", text):
        phrase = _clean_phrase(match.group(0))
        if phrase and _looks_like_content_phrase(phrase):
            phrases.append(phrase)
    return _dedupe_preserve_order(phrases)



def _clean_phrase(text: str) -> str:
    cleaned = normalize_text(re.sub(r"\s+", " ", text.strip(" ,.;:()[]{}")))
    previous = None
    while cleaned and previous != cleaned:
        previous = cleaned
        cleaned = _TRIM_PREFIX_PATTERN.sub("", cleaned).strip()
    cleaned = _TRIM_SUFFIX_PATTERN.sub("", cleaned).strip()
    cleaned = re.sub(r"^(?:the|a|an)\s+", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip(" ,.;:")



def _looks_like_actor(phrase: str) -> bool:
    lowered = phrase.lower()
    return any(keyword in lowered for keywords in _ACTOR_KEYWORDS.values() for keyword in keywords) or len(phrase.split()) <= 3



def _looks_like_content_phrase(phrase: str) -> bool:
    tokens = [token for token in re.findall(r"[A-Za-z][A-Za-z0-9'-]*", phrase.lower()) if token not in _STOPWORDS]
    return bool(tokens) and not _is_noise_phrase(phrase)



def _is_noise_phrase(phrase: str) -> bool:
    lowered = phrase.lower()
    if lowered in _STOPWORDS:
        return True
    if any(token in lowered for token in ("how could", "what happens", "main actors", "force shippers", "reroute through")):
        return True
    if all(token in _STOPWORDS for token in re.findall(r"[A-Za-z][A-Za-z0-9'-]*", lowered)):
        return True
    return len(lowered) < 3



def _dedupe_preserve_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        key = value.casefold()
        if key not in seen:
            seen.add(key)
            ordered.append(value)
    return ordered


DECOMPOSE_SCHEMA = {
    "type": "object",
    "properties": {
        "problem_frame": {
            "type": "object",
            "properties": {
                "core_question": {"type": "string"},
                "decision_or_analysis_target": {"type": "string"},
                "scope_notes": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["core_question", "decision_or_analysis_target", "scope_notes"],
        },
        "actor_cards": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "type": {"type": "string"},
                    "role": {"type": "string"},
                    "goal_guess": {"type": "string"},
                    "why_relevant": {"type": "string"},
                },
                "required": ["name", "type", "role", "goal_guess", "why_relevant"],
            },
        },
        "node_cards": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "type": {"type": "string"},
                    "function": {"type": "string"},
                    "why_relevant": {"type": "string"},
                },
                "required": ["name", "type", "function", "why_relevant"],
            },
        },
        "constraint_cards": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "constraint": {"type": "string"},
                    "applies_to": {"type": "array", "items": {"type": "string"}},
                    "why_it_matters": {"type": "string"},
                },
                "required": ["constraint", "applies_to", "why_it_matters"],
            },
        },
    },
    "required": ["problem_frame", "actor_cards", "node_cards", "constraint_cards"],
}


def build_decompose_prompt(problem_text: str, *, prompt_patch: str | None = None) -> str:
    """Return the live decompose-stage prompt."""

    normalized_problem = normalize_text(problem_text)
    if not normalized_problem:
        raise ValueError("problem_text must not be empty")

    patch_block = f"\nImprovement patch for this round:\n{prompt_patch.strip()}\n" if prompt_patch and prompt_patch.strip() else ""
    return (
        "You are running the phase-1 rigor pipeline decompose stage. "
        "Return JSON only and do not wrap it in markdown.\n\n"
        "Task: extract the concrete problem frame, actors, operational nodes, and binding constraints.\n"
        "Favor specific operational detail over generic commentary.\n\n"
        f"Schema:\n{json.dumps(DECOMPOSE_SCHEMA, indent=2, ensure_ascii=False, sort_keys=True)}\n\n"
        "Rules:\n"
        "- Keep scope_notes concise and concrete.\n"
        "- Hard constraint: prioritize fixing Actor Blindness and Node / Facility Blindness before writing broad context.\n"
        "- Hard constraint: identify concrete actors and operational nodes first; do not start from macro-regional summaries.\n"
        "- Hard constraint: each actor_cards and node_cards entry must include a direct operational relevance link to the decision_or_analysis_target.\n"
        "- Hard constraint: if the prompt text is sparse, still propose the most plausible high-leverage actors and nodes rather than defaulting to generic prose.\n"
        "- actor_cards, node_cards, and constraint_cards may be empty arrays, but only if the text truly gives no support.\n"
        "- Use only the allowed actor types already used in this repository: person, organization, state, firm, proxy, institution, other.\n"
        "- Use only the allowed node types already used in this repository: facility, route, market, institutional node, platform, other.\n\n"
        f"{patch_block}"
        f"Problem text:\n{normalized_problem}\n"
    )


def run_decompose(
    problem_text: str,
    *,
    model: str,
    api_key: str,
    prompt_patch: str | None = None,
) -> DecomposeResult:
    """Run the live decompose stage directly from this module."""

    response_text = call_openrouter(
        api_key=api_key,
        model=model,
        messages=[
            {"role": "system", "content": "Return strict JSON for the requested schema only."},
            {"role": "user", "content": build_decompose_prompt(problem_text, prompt_patch=prompt_patch)},
        ],
        temperature=0.0,
        max_tokens=2400,
    )
    payload = _load_json_object(response_text, stage_name="decompose")
    return DecomposeResult(
        problem_frame=ProblemFrame(**payload["problem_frame"]),
        actor_cards=[ActorCard(**item) for item in payload.get("actor_cards", [])],
        node_cards=[NodeCard(**item) for item in payload.get("node_cards", [])],
        constraint_cards=[ConstraintCard(**item) for item in payload.get("constraint_cards", [])],
    )


def _load_json_object(response_text: str, *, stage_name: str) -> dict[str, object]:
    cleaned = response_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{stage_name} returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{stage_name} must return a JSON object")
    return payload



__all__ = [
    "DECOMPOSE_SCHEMA",
    "build_decompose_prompt",
    "decompose_problem",
    "decompose_to_json",
    "run_decompose",
    "save_decompose_result",
]
