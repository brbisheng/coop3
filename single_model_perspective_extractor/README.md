# single_model_perspective_extractor

`single_model_perspective_extractor` now treats the **phase-1 rigor engine** as the
single primary product path.

## Phase-1 main path (core)

Core execution flow:

```text
decompose -> trace -> compete -> stress -> final
```

Only these five stages are the default user journey.

## Repository structure (core vs legacy)

```text
single_model_perspective_extractor/
├─ src/perspective_extractor/
│  ├─ decompose.py            # phase-1 core
│  ├─ trace.py                # phase-1 core
│  ├─ compete.py              # phase-1 core
│  ├─ stress.py               # phase-1 core
│  ├─ final.py                # phase-1 core
│  ├─ cli.py                  # phase-1 focused CLI
│  ├─ pipeline.py             # phase-1 orchestration entry
│  └─ legacy/                 # non-core compatibility path
│     ├─ axes.py
│     ├─ expand.py
│     ├─ review.py
│     └─ synthesize.py
├─ demos/
│  └─ demo_decompose.py       # live phase-1 demo only
└─ tests/
   ├─ unit/                   # default phase-1 test focus
   └─ integration/            # live OpenRouter smoke checks
```

## CLI (default focus = phase-1 rigor engine)

`perspective-extractor --help` and subcommand help are intentionally centered on
phase-1 only:

- `perspective-extractor decompose --model <openrouter_model> --question "..."`
- `perspective-extractor trace --model <openrouter_model> --question "..."`
- `perspective-extractor compete --model <openrouter_model> --question "..."`
- `perspective-extractor stress --model <openrouter_model> --question "..."`
- `perspective-extractor final --model <openrouter_model> --question "..."`

Operational rules:

- `--model` is required for live execution.
- OpenRouter credentials must come from `--api-key` or `OPENROUTER_API_KEY`.
- `--question` or `--input-file` is required for every command.
- `--output` writes the rendered artifact to disk.
- `--format json` remains the default, while `--format markdown` writes a
  markdown artifact that embeds the structured JSON payload.
- `--use-fixture` is explicit deterministic test/demo mode and is not the
  default behavior.

## Demo policy

Demos should present the **phase-1 live path** first. The packaged demo script
uses live OpenRouter execution for the phase-1 `decompose` stage and requires:

- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL`

## Legacy modules (non-core)

The older perspective-extraction path is retained only for compatibility under:

- `src/perspective_extractor/legacy/axes.py`
- `src/perspective_extractor/legacy/expand.py`
- `src/perspective_extractor/legacy/review.py`
- `src/perspective_extractor/legacy/synthesize.py`

Treat that folder as **legacy / non-core**. New guidance and new feature work
should start from the phase-1 rigor engine.

## Tests (default emphasis)

Default `pytest` discovery is scoped to `tests/unit/` and
`tests/integration/`, which keeps phase-1 contracts and live phase-1 smoke
checks as the default quality signal.

Legacy compatibility tests remain in the repository but are not the default
entry point for first-pass test runs.
