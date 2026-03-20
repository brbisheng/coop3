"""CLI entry point for the perspective extractor scaffold."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from typing import Sequence

from .models import PipelineInput, QuestionCard
from .normalize import normalize_question
from .pipeline import PerspectiveExtractionPipeline


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

    pipeline = PerspectiveExtractionPipeline()
    demo_input = PipelineInput(
        topic="example topic",
        source_text="Example source text for perspective extraction.",
    )
    print(pipeline.summarize(demo_input))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
