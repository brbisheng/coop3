# Single-Model Perspective Extraction Engine — Codex Execution Spec (v1)

## 0. Goal

Build a **single-model** system that can take one research question and produce **genuinely different perspectives**, without relying on multi-agent debate, fake personas, or shallow randomness tricks.

This v1 must focus only on the smallest set of components that are very likely to be useful in practice.

The system should not try to simulate many agents. It should force one model to look at the same question through multiple **structurally different windows**.

---

## 1. Hard constraints

1. Use **one model only**.
2. Do **not** make multi-agent debate the core engine.
3. Do **not** rely on temperature tuning as the main source of diversity.
4. Core goal: for one research question, produce multiple perspectives that are:
   - distinct,
   - non-redundant,
   - evidence-aware,
   - useful for later research design.
5. Build the system in small stages.
6. After each core stage is finished, the program must already be callable with **one simple command**.
7. Do not start with dashboards, APIs, web UI, analytics, soul systems, or large plugin ecosystems.

---

## 2. Remove these ideas from v1

These may sound sophisticated, but for this v1 they are either unnecessary, unstable, or likely to waste implementation time.

### Remove from v1 entirely
- Multi-agent debate engine
- Persona theater / role-play experts
- Soul injection / temperament systems
- HumanBase weighting systems
- Multilingual diversification
- Tree-of-Thought search trees
- TransferSeat / analogy seat
- ManuscriptCard / writing bridge
- Adaptive seat policy
- FastAPI / server layer
- Dashboard / telemetry / evaluation platform
- Large module registry for many disciplines

### Reason
These ideas may become useful later, but they are not the shortest path to the core requirement:

> with one model, force real perspective diversity.

For v1, most of them add complexity before proving the core mechanism.

---

## 3. Keep only the core innovations that are very likely to help

These are the only innovations that should define v1.

### Innovation 1: Perspective Axes before Answers
Do **not** ask the model directly for “many perspectives”.

First ask it to generate a set of **perspective axes**.
A perspective axis is a distinct observation window, not a final opinion.

Examples of axis types:
- mechanism
- incentives
- constraints
- behavior
- measurement
- evidence gaps
- counterexamples
- boundary conditions
- alternative explanations
- normative tradeoffs

Why this matters:
If the model jumps directly to answers, it tends to collapse into a few familiar explanations. Axis generation forces structural separation first.

### Innovation 2: Isolated Passes
Each axis must be expanded **independently**.

When expanding one axis, the model must **not** see the full answers from the other axes.
It may see only:
- the original question,
- the current axis definition,
- optional minimal background cards.

Why this matters:
This is the simplest practical way to reduce answer collapse from a single model.

### Innovation 3: Overlap / Novelty Judge
After all axis expansions are done, run a separate judging pass to detect:
- duplicates,
- near-duplicates,
- shallow reformulations,
- actually novel perspectives.

The system must explicitly label each perspective as one of:
- keep
- merge
- rewrite
- drop

Why this matters:
Without this step, “10 perspectives” often means “4 ideas repeated 10 times”.

### Innovation 4: Evidence Slots
Every perspective note must include:
- what it claims,
- why it might matter,
- what evidence would be needed to support or challenge it.

Why this matters:
A perspective is much more useful if it naturally points toward research design instead of remaining abstract talk.

### Innovation 5: One Final Perspective Map
The final output should not be a flattened summary paragraph.
It should be a structured map showing:
- which perspectives are compatible,
- which compete,
- which need evidence to decide,
- which are boundary-condition cases.

Why this matters:
Research usefulness comes from preserving structure, not from collapsing everything into one final answer.

---

## 4. Minimum system architecture

The system should contain only five core objects.

### 4.1 QuestionCard
Represents the original research question.

Fields:
- `question_id`
- `raw_question`
- `cleaned_question`
- `domain_hint`
- `assumptions`
- `keywords`

### 4.2 AxisCard
Represents one perspective axis.

Fields:
- `axis_id`
- `name`
- `axis_type`
- `focus`
- `how_is_it_distinct`
- `priority`

### 4.3 PerspectiveNote
Represents one independently generated perspective under one axis.

Fields:
- `note_id`
- `axis_id`
- `core_claim`
- `reasoning`
- `counterexample`
- `boundary_condition`
- `evidence_needed`
- `testable_implication`

### 4.4 ReviewDecision
Represents overlap/novelty judgment.

Fields:
- `decision_id`
- `target_note_id`
- `action`  # keep | merge | rewrite | drop
- `reason`
- `merge_target_note_id`

### 4.5 PerspectiveMap
Final structured result.

Fields:
- `map_id`
- `question_id`
- `kept_notes`
- `merged_groups`
- `competing_perspectives`
- `compatible_perspectives`
- `evidence_contests`
- `final_summary`

---

## 5. Core pipeline

Build only this pipeline in v1.

### Step 1. Normalize the question
Input one raw question.
Output one `QuestionCard`.

Purpose:
Remove ambiguity, pull out topic, likely outcome, actors, and basic assumptions.

### Step 2. Generate perspective axes
Input `QuestionCard`.
Output 8–12 `AxisCard`s.

Rules:
- axes must be structurally different
- no duplicate wording
- no final answers yet
- must cover multiple categories, not only mechanism

### Step 3. Expand each axis independently
Input:
- `QuestionCard`
- one `AxisCard`

Output:
- one `PerspectiveNote`

Rules:
- each axis expansion is isolated
- no peeking at other full notes
- each note must contain claim, reasoning, counterexample, evidence needed, testable implication

### Step 4. Judge overlap and novelty
Input all `PerspectiveNote`s.
Output `ReviewDecision`s.

Rules:
- explicitly detect duplicates
- merge near-duplicates
- rewrite vague notes if salvageable
- drop notes with no unique contribution

### Step 5. Build final perspective map
Input kept notes + review decisions.
Output one `PerspectiveMap`.

Rules:
- do not flatten everything into one conclusion
- preserve competition and tension among perspectives
- show where evidence is needed to discriminate

---

## 6. Prompts: required behavior

Codex should implement prompts as plain template files or clearly separated Python strings.
They should not be buried inside random functions.

### 6.1 Question normalization prompt must do
- restate the question clearly
- identify likely outcome variable
- identify actors / entities
- identify obvious assumptions
- identify domain hints
- avoid answering the question deeply at this stage

### 6.2 Axis generation prompt must do
- generate 8–12 axes
- each axis must explain why it is distinct from other axes
- prohibit shallow paraphrases
- prohibit jumping to conclusion language
- prioritize structural diversity over stylistic diversity

### 6.3 Axis expansion prompt must do
For one axis only, produce:
- core claim
- why this axis matters
- strongest support logic
- strongest counterexample
- boundary condition
- evidence needed
- one testable implication

### 6.4 Review prompt must do
- compare notes for redundancy
- identify notes that are truly different
- detect fake novelty
- choose keep / merge / rewrite / drop

### 6.5 Map synthesis prompt must do
- preserve differences
- list competing notes
- list compatible notes
- list evidence contests
- produce a short synthesis without erasing structure

---

## 7. File structure

Use a very small, clean project structure.

```text
single_model_perspective_extractor/
  README.md
  pyproject.toml
  src/
    perspective_extractor/
      __init__.py
      models.py
      prompts.py
      llm.py
      normalize.py
      axes.py
      expand.py
      review.py
      synthesize.py
      pipeline.py
      cli.py
  tests/
    test_normalize.py
    test_axes.py
    test_expand.py
    test_review.py
    test_pipeline.py
```

---

## 8. Packaging rule after each core milestone

This is mandatory.
After each milestone, the program must already be runnable with one short command.

### Milestone A: question normalization only
Deliverable:
- `normalize_question()`
- CLI command works

Command example:

```bash
perspective-extract normalize "Why do some borrowers avoid a lower-interest formal loan product?"
```

### Milestone B: axis generation added
Deliverable:
- `generate_axes()`
- CLI command works

Command example:

```bash
perspective-extract axes "Why do some borrowers avoid a lower-interest formal loan product?"
```

### Milestone C: isolated axis expansion added
Deliverable:
- `expand_axes()`
- CLI command works

Command example:

```bash
perspective-extract expand "Why do some borrowers avoid a lower-interest formal loan product?"
```

### Milestone D: overlap/novelty review added
Deliverable:
- `review_notes()`
- CLI command works

Command example:

```bash
perspective-extract review "Why do some borrowers avoid a lower-interest formal loan product?"
```

### Milestone E: full pipeline added
Deliverable:
- `run_pipeline()`
- CLI command works

Command example:

```bash
perspective-extract run "Why do some borrowers avoid a lower-interest formal loan product?"
```

This final command should output a complete `PerspectiveMap` as JSON or markdown.

---

## 9. Minimal program interface

Codex should implement both:

### Python interface
```python
from perspective_extractor.pipeline import run_pipeline

result = run_pipeline(
    question="Why do some borrowers avoid a lower-interest formal loan product?"
)
```

### CLI interface
```bash
perspective-extract run "Why do some borrowers avoid a lower-interest formal loan product?"
```

Do not build server infrastructure in v1.
CLI + Python import are enough.

---

## 10. Output format requirements

The final output must be machine-readable.
Prefer JSON, optionally also support markdown export.

The final JSON must contain at least:
- normalized question
- generated axes
- raw perspective notes
- review decisions
- final kept notes
- perspective map

---

## 11. Testing priorities

Tests should focus on structure and invariants, not on fragile exact text matching.

### Must test
1. `normalize_question()` returns required fields
2. `generate_axes()` returns 8–12 axes
3. axes are not empty duplicates by normalized names
4. `expand_axes()` returns required fields for each note
5. `review_notes()` only emits allowed actions
6. `run_pipeline()` returns valid `PerspectiveMap`

### Optional but useful
- deterministic mock LLM tests
- schema validation tests
- simple redundancy scoring tests

---

## 12. Explicit non-goals for v1

Do not implement these now:
- multi-model orchestration
- debate loop
- expert module marketplace
- soul / personality system
- dashboards
- web app
- API server
- long-term memory system
- retrieval system
- database persistence beyond simple local output files

If needed later, they can be added after the core mechanism is proven.

---

## 13. Definition of success for v1

v1 is successful if, for one question, the system can reliably produce:
1. a clean normalized question,
2. a set of structurally different perspective axes,
3. independently expanded notes for each axis,
4. an overlap/novelty filtering pass,
5. a final map that preserves differences instead of flattening them.

The core win is this:

> one model, many genuinely different windows.

Not fake debate. Not decorative complexity.

---

## 14. Instruction to Codex

Implement this spec in the smallest working way.

Priority order:
1. correctness of core pipeline,
2. clean prompt separation,
3. clean Python package structure,
4. simple CLI packaging,
5. readable JSON output.

Do not over-engineer.
Do not add systems not required by this spec.
Finish one milestone completely before starting the next one.
