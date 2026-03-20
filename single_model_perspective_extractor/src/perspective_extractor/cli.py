"""CLI entry point for the perspective extractor scaffold."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from typing import Any, Sequence

from .axes import generate_axes
from .knowledge import generate_controversy_cards, generate_knowledge_cards, generate_variable_cards
from .models import (
    AxisCard,
    ControversyCard,
    KnowledgeCard,
    PipelineInput,
    QuestionCard,
    VariableCard,
)
from .normalize import normalize_question
from .pipeline import PerspectiveExtractionPipeline, expand_axes


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level CLI parser."""

    parser = argparse.ArgumentParser(prog="perspective-extractor")
    subparsers = parser.add_subparsers(dest="command")

    normalize_parser = subparsers.add_parser(
        "normalize",
        help="Normalize a research question into a structured question card.",
    )
    normalize_parser.add_argument("question", help="Question text to normalize.")
    normalize_parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="Output format. JSON remains the stable default output mode.",
    )

    axes_parser = subparsers.add_parser(
        "axes",
        help="Generate question, supporting cards, and axis cards for a research question.",
    )
    axes_parser.add_argument("question", help="Question text to expand into perspective axes.")
    axes_parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="markdown",
        help="Output format. Markdown is the readable default for axis inspection.",
    )
    axes_parser.add_argument(
        "--skip-knowledge",
        action="store_true",
        help="Do not generate or print knowledge cards.",
    )
    axes_parser.add_argument(
        "--skip-variables",
        action="store_true",
        help="Do not generate or print variable cards.",
    )
    axes_parser.add_argument(
        "--skip-controversies",
        action="store_true",
        help="Do not generate or print controversy cards.",
    )

    expand_parser = subparsers.add_parser(
        "expand",
        help="Generate raw PerspectiveNote records by expanding each axis independently.",
    )
    expand_parser.add_argument("question", help="Question text to expand into perspective notes.")
    expand_parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="Output format. JSON remains the stable default for raw PerspectiveNote output.",
    )
    expand_parser.add_argument(
        "--skip-knowledge",
        action="store_true",
        help="Do not generate or use knowledge cards during expansion.",
    )
    expand_parser.add_argument(
        "--skip-variables",
        action="store_true",
        help="Do not generate or use variable cards during expansion.",
    )
    expand_parser.add_argument(
        "--skip-controversies",
        action="store_true",
        help="Do not generate or use controversy cards during expansion.",
    )

    return parser


def _format_question_card_json(question_card: QuestionCard) -> str:
    return json.dumps(asdict(question_card), indent=2, ensure_ascii=False, sort_keys=True)


def _format_question_card_markdown(question_card: QuestionCard) -> str:
    sections = [
        "# Normalized Question",
        f"- **question_id:** `{question_card.question_id}`",
        f"- **raw_question:** {question_card.raw_question}",
        f"- **cleaned_question:** {question_card.cleaned_question}",
        f"- **actor_entity:** {question_card.actor_entity or 'N/A'}",
        f"- **outcome_variable:** {question_card.outcome_variable or 'N/A'}",
        f"- **domain_hint:** {question_card.domain_hint or 'N/A'}",
    ]

    for title, values in (
        ("Assumptions", question_card.assumptions),
        ("Keywords", question_card.keywords),
        ("Missing Pieces", question_card.missing_pieces),
    ):
        sections.append(f"\n## {title}")
        if values:
            sections.extend(f"- {value}" for value in values)
        else:
            sections.append("- None")

    return "\n".join(sections)


def _format_string_list(values: list[str]) -> list[str]:
    if not values:
        return ["- None"]
    return [f"- {value}" for value in values]


def _format_card_collection_markdown(
    title: str,
    cards: list[KnowledgeCard] | list[VariableCard] | list[ControversyCard],
    formatter: Any,
) -> list[str]:
    sections = [f"## {title}"]
    if not cards:
        sections.append("- Disabled or none")
        return sections

    for index, card in enumerate(cards, start=1):
        sections.extend(formatter(index, card))

    return sections


def _format_knowledge_card(index: int, card: KnowledgeCard) -> list[str]:
    sections = [
        f"### KnowledgeCard {index}: {card.title}",
        f"- **knowledge_id:** `{card.knowledge_id}`",
        f"- **content:** {card.content}",
        f"- **source_type:** {card.source_type or 'N/A'}",
        f"- **relevance:** {card.relevance or 'N/A'}",
        f"- **verification_question:** {card.verification_question or 'N/A'}",
        "- **evidence_needed:**",
        *_format_string_list(card.evidence_needed),
    ]
    return sections


def _format_variable_card(index: int, card: VariableCard) -> list[str]:
    sections = [
        f"### VariableCard {index}: {card.name}",
        f"- **variable_id:** `{card.variable_id}`",
        f"- **role:** {card.variable_role}",
        f"- **definition:** {card.definition}",
        f"- **measurement_notes:** {card.measurement_notes or 'N/A'}",
        f"- **testable_implication:** {card.testable_implication or 'N/A'}",
        f"- **verification_question:** {card.verification_question or 'N/A'}",
        "- **possible_values:**",
        *_format_string_list(card.possible_values),
        "- **evidence_needed:**",
        *_format_string_list(card.evidence_needed),
    ]
    return sections


def _format_controversy_card(index: int, card: ControversyCard) -> list[str]:
    sections = [
        f"### ControversyCard {index}: {card.question}",
        f"- **controversy_id:** `{card.controversy_id}`",
        "- **sides:**",
        *_format_string_list(card.sides),
        "- **evidence_contests:**",
        *_format_string_list(card.evidence_contests),
        f"- **verification_question:** {card.verification_question or 'N/A'}",
        "- **competing_perspectives:**",
        *_format_string_list(card.competing_perspectives),
        "- **compatible_perspectives:**",
        *_format_string_list(card.compatible_perspectives),
    ]
    return sections


def _format_axis_card(index: int, card: AxisCard) -> list[str]:
    sections = [
        f"### AxisCard {index}: {card.name}",
        f"- **axis_id:** `{card.axis_id}`",
        f"- **type:** {card.axis_type}",
        f"- **priority:** {card.priority}",
        f"- **focus:** {card.focus}",
        f"- **distinctness:** {card.how_is_it_distinct}",
        f"- **verification_question:** {card.verification_question or 'N/A'}",
        "- **supporting_card_ids:**",
        *_format_string_list(card.supporting_card_ids),
        "- **evidence_needed:**",
        *_format_string_list(card.evidence_needed),
    ]
    return sections


def _format_axes_markdown(
    *,
    question_card: QuestionCard,
    knowledge_cards: list[KnowledgeCard],
    variable_cards: list[VariableCard],
    controversy_cards: list[ControversyCard],
    axis_cards: list[AxisCard],
) -> str:
    sections = [
        "# Perspective Axes",
        "",
        "## QuestionCard",
        f"- **question_id:** `{question_card.question_id}`",
        f"- **raw_question:** {question_card.raw_question}",
        f"- **cleaned_question:** {question_card.cleaned_question}",
        f"- **actor_entity:** {question_card.actor_entity or 'N/A'}",
        f"- **outcome_variable:** {question_card.outcome_variable or 'N/A'}",
        f"- **domain_hint:** {question_card.domain_hint or 'N/A'}",
        "- **assumptions:**",
        *_format_string_list(question_card.assumptions),
        "- **keywords:**",
        *_format_string_list(question_card.keywords),
        "- **missing_pieces:**",
        *_format_string_list(question_card.missing_pieces),
        "",
    ]

    sections.extend(
        _format_card_collection_markdown("Knowledge Cards", knowledge_cards, _format_knowledge_card)
    )
    sections.append("")
    sections.extend(
        _format_card_collection_markdown("Variable Cards", variable_cards, _format_variable_card)
    )
    sections.append("")
    sections.extend(
        _format_card_collection_markdown(
            "Controversy Cards",
            controversy_cards,
            _format_controversy_card,
        )
    )
    sections.append("")
    sections.append("## Axis Cards")
    for index, axis_card in enumerate(axis_cards, start=1):
        sections.extend(_format_axis_card(index, axis_card))

    return "\n".join(sections)


def _format_axes_json(
    *,
    question_card: QuestionCard,
    knowledge_cards: list[KnowledgeCard],
    variable_cards: list[VariableCard],
    controversy_cards: list[ControversyCard],
    axis_cards: list[AxisCard],
) -> str:
    payload = {
        "question_card": asdict(question_card),
        "knowledge_cards": [asdict(card) for card in knowledge_cards],
        "variable_cards": [asdict(card) for card in variable_cards],
        "controversy_cards": [asdict(card) for card in controversy_cards],
        "axis_cards": [asdict(card) for card in axis_cards],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)


def _format_perspective_notes_json(notes: list[Any]) -> str:
    return json.dumps([asdict(note) for note in notes], indent=2, ensure_ascii=False, sort_keys=True)


def _format_perspective_notes_markdown(notes: list[Any]) -> str:
    sections = ["# Perspective Notes"]
    if not notes:
        sections.append("- None")
        return "\n".join(sections)

    for index, note in enumerate(notes, start=1):
        sections.extend(
            [
                "",
                f"## PerspectiveNote {index}",
                f"- **note_id:** `{note.note_id}`",
                f"- **axis_id:** `{note.axis_id}`",
                f"- **core_claim:** {note.core_claim}",
                f"- **reasoning:** {note.reasoning}",
                f"- **counterexample:** {note.counterexample or 'N/A'}",
                f"- **boundary_condition:** {note.boundary_condition or 'N/A'}",
                f"- **testable_implication:** {note.testable_implication or 'N/A'}",
                f"- **verification_question:** {note.verification_question or 'N/A'}",
                "- **supporting_card_ids:**",
                *_format_string_list(note.supporting_card_ids),
                "- **planned_subquestions:**",
                *_format_string_list(note.planned_subquestions),
                "- **subanswer_trace:**",
                *_format_string_list(note.subanswer_trace),
                "- **evidence_needed:**",
                *_format_string_list(note.evidence_needed),
            ]
        )

    return "\n".join(sections)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the perspective extractor CLI."""

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "normalize":
        question_card = normalize_question(args.question)
        if args.format == "markdown":
            print(_format_question_card_markdown(question_card))
        else:
            print(_format_question_card_json(question_card))
        return 0

    if args.command == "axes":
        question_card = normalize_question(args.question)
        knowledge_cards = [] if args.skip_knowledge else generate_knowledge_cards(question_card)
        variable_cards = [] if args.skip_variables else generate_variable_cards(question_card)
        controversy_cards = [] if args.skip_controversies else generate_controversy_cards(question_card)
        axis_cards = generate_axes(
            question_card,
            knowledge_cards=knowledge_cards,
            variable_cards=variable_cards,
            controversy_cards=controversy_cards,
        )
        if args.format == "json":
            print(
                _format_axes_json(
                    question_card=question_card,
                    knowledge_cards=knowledge_cards,
                    variable_cards=variable_cards,
                    controversy_cards=controversy_cards,
                    axis_cards=axis_cards,
                )
            )
        else:
            print(
                _format_axes_markdown(
                    question_card=question_card,
                    knowledge_cards=knowledge_cards,
                    variable_cards=variable_cards,
                    controversy_cards=controversy_cards,
                    axis_cards=axis_cards,
                )
            )
        return 0

    if args.command == "expand":
        question_card = normalize_question(args.question)
        knowledge_cards = [] if args.skip_knowledge else generate_knowledge_cards(question_card)
        variable_cards = [] if args.skip_variables else generate_variable_cards(question_card)
        controversy_cards = [] if args.skip_controversies else generate_controversy_cards(question_card)
        axis_cards = generate_axes(
            question_card,
            knowledge_cards=knowledge_cards,
            variable_cards=variable_cards,
            controversy_cards=controversy_cards,
        )
        perspective_notes = expand_axes(
            axis_cards,
            question_card,
            knowledge_cards=knowledge_cards,
            variable_cards=variable_cards,
            controversy_cards=controversy_cards,
        )
        if args.format == "markdown":
            print(_format_perspective_notes_markdown(perspective_notes))
        else:
            print(_format_perspective_notes_json(perspective_notes))
        return 0

    pipeline = PerspectiveExtractionPipeline()
    demo_input = PipelineInput(
        topic="example topic",
        source_text="Example source text for perspective extraction.",
    )
    print(pipeline.summarize(demo_input))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
