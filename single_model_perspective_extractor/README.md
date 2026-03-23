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

The CLI now treats a live OpenRouter-backed run as the default mode for the
phase-1 engine. Each stage is invoked explicitly:

- `perspective-extractor decompose --model <openrouter_model> --question "..."`
- `perspective-extractor trace --model <openrouter_model> --question "..."`
- `perspective-extractor compete --model <openrouter_model> --question "..."`
- `perspective-extractor stress --model <openrouter_model> --question "..."`
- `perspective-extractor final --model <openrouter_model> --question "..."`

Additional CLI rules:

- `--model` is required for live execution.
- OpenRouter credentials must come from `--api-key` or `OPENROUTER_API_KEY`.
- `--question` or `--input-file` is required for every command.
- `--output` writes the rendered artifact to disk.
- `--format json` remains the default, while `--format markdown` writes a
  markdown artifact that embeds the structured JSON payload.
- `--use-fixture` is an explicit deterministic test/demo path and is not the
  default behavior.

## PerspectiveMap scope after v1

Treat the current `PerspectiveMap` as the default v1 representation, then validate it with real question samples before expanding synthesis complexity. Consider upgrading `synthesize.py` to a stronger tree / branch-comparison mechanism only if repeated reviews show that:

- flat or lightly hierarchical branches cannot capture complex dependency relationships
- one dominant perspective needs systematic branching under the same top-level view
- multi-layer competitive structures are still hard to express even after review cleanup

Until those concrete failures appear, prefer keeping the existing representation simple and evidence-driven.

## Live model requirements

- CLI execution now requires an explicit `--model` unless `--use-fixture` is selected.
- OpenRouter credentials must come from `--api-key` or `OPENROUTER_API_KEY` for live runs.
- Demo fixtures live in `fixtures.py` and are reserved for tests/manual demos rather than the default CLI path.
