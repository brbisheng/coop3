# single_model_perspective_extractor

A scaffolded Python project for extracting and synthesizing perspectives with a
single-model pipeline. The package namespace is `perspective_extractor`.

## Layout

- `src/perspective_extractor/`: package source code
- `pyproject.toml`: project metadata and CLI entry point

## Modules

- `models.py`: shared data models
- `prompts.py`: prompt templates
- `llm.py`: live stage invocation boundary (no fixture fallback)
- `openrouter.py`: real OpenRouter chat-completion integration
- `fixtures.py`: test/demo-only fixture helpers
- `normalize.py`: normalization helpers
- `knowledge.py`: knowledge retrieval stubs
- `axes.py`: perspective-axis generation
- `expand.py`: candidate expansion
- `review.py`: review and filtering
- `synthesize.py`: synthesis stage
- `pipeline.py`: end-to-end orchestration
- `cli.py`: command-line entry point

## CLI

- `perspective-extractor normalize "..."`: emits a stable JSON representation of the normalized question card by default.
- `perspective-extractor normalize "..." --format markdown`: emits a human-readable markdown summary while preserving `--format json` as the stable machine-readable mode.
- `perspective-extractor axes "..."`: emits a readable markdown report containing the `QuestionCard`, optional knowledge / variable / controversy cards, and the generated `AxisCard` list.
- `perspective-extractor axes "..." --format json`: emits the same card collections in JSON, while `--skip-knowledge`, `--skip-variables`, and `--skip-controversies` suppress optional supporting cards.
- `perspective-extractor run "..."`: emits the full `PipelineResult` JSON trace by default, preserving normalized question, support cards, axes, raw notes, review decisions, review partitions, and the synthesized perspective map rather than only the final summary.
- `perspective-extractor run "..." --format markdown`: wraps that same stable JSON export in a markdown code block so a future human-oriented export can evolve without changing JSON as the primary machine-readable contract.

## PerspectiveMap scope after v1

Treat the current `PerspectiveMap` as the default v1 representation, then validate it with real question samples before expanding synthesis complexity. Consider upgrading `synthesize.py` to a stronger tree / branch-comparison mechanism only if repeated reviews show that:

- flat or lightly hierarchical branches cannot capture complex dependency relationships
- one dominant perspective needs systematic branching under the same top-level view
- multi-layer competitive structures are still hard to express even after review cleanup

Until those concrete failures appear, prefer keeping the existing representation simple and evidence-driven.

## Live model requirements

- CLI execution now requires an explicit `--model`.
- OpenRouter credentials must come from `--api-key` or `OPENROUTER_API_KEY`.
- Demo fixtures live in `fixtures.py` and are reserved for tests/manual demos rather than the default CLI path.
