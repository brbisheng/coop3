# single_model_perspective_extractor

A scaffolded Python project for extracting and synthesizing perspectives with a
single-model pipeline. The package namespace is `perspective_extractor`.

## Layout

- `src/perspective_extractor/`: package source code
- `pyproject.toml`: project metadata and CLI entry point

## Modules

- `models.py`: shared data models
- `prompts.py`: prompt templates
- `llm.py`: LLM client abstraction
- `normalize.py`: normalization helpers
- `knowledge.py`: knowledge retrieval stubs
- `axes.py`: perspective-axis generation
- `expand.py`: candidate expansion
- `review.py`: review and filtering
- `synthesize.py`: synthesis stage
- `pipeline.py`: end-to-end orchestration
- `cli.py`: command-line entry point
