# single_model_perspective_extractor

`single_model_perspective_extractor` now centers the **phase1 rigor engine** as the
main product path. New users should think about the repo as one primary flow:

```
decompose -> trace -> compete -> stress -> final
```

The package namespace remains `perspective_extractor`.

## Primary path: phase1 rigor engine

The main implementation lives in `src/perspective_extractor/` and is organized
around the phase-1 stages:

- `decompose.py`: turn a question into actors, nodes, and constraints
- `trace.py`: build an explicit consequence chain
- `compete.py`: generate competing mechanisms and divergent predictions
- `stress.py`: test those mechanisms against falsification and surprise ledgers
- `final.py`: assemble the final report
- `cli.py`: expose the phase-1 commands for direct use
- `pipeline.py`: keep the phase-1 orchestration path as the primary pipeline

## CLI

The CLI only exposes the phase-1 main path by default:

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
- `--use-fixture` is an explicit deterministic test/demo path and is not the
  default behavior.

## Legacy path: perspective extraction

The older `axes / expand / review / synthesize` flow is **not** the primary
product path anymore. It is retained only as a compatibility layer under:

- `src/perspective_extractor/legacy/axes.py`
- `src/perspective_extractor/legacy/expand.py`
- `src/perspective_extractor/legacy/review.py`
- `src/perspective_extractor/legacy/synthesize.py`

That legacy flow still supports compatibility-oriented code in `pipeline.py`,
but new feature work and user-facing guidance should start from the phase-1
rigor engine instead of multi-perspective extraction.

## Live model requirements

- CLI execution requires an explicit `--model` unless `--use-fixture` is selected.
- OpenRouter credentials must come from `--api-key` or `OPENROUTER_API_KEY` for live runs.
- Demo fixtures live in `fixtures.py` and are reserved for tests/manual demos rather than the default CLI path.

## Test layout

- `tests/unit/` covers deterministic schema checks, prompt assembly, artifact persistence, and fake-model parsing without hitting OpenRouter.
- `tests/integration/` contains real OpenRouter smoke tests for `decompose`, `trace`, and `final`. Those tests only run when `OPENROUTER_API_KEY` is set, and they verify that live CLI runs fail without model/key but succeed with non-empty required output when credentials are present.
