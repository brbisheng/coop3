# CODEX.md — Mono-Agent Rigor Engine (Phase 1)

## Mission

Build a **single-agent capability engine** whose only goal is to **make one LLM stronger** on complex problems.

“Stronger” does **not** mean:
- longer answers
- more personas
- more perspectives in name only
- more architecture
- prettier software

“Stronger” means the agent is better at:
- finding the truly relevant actors, nodes, institutions, facilities, constraints, and third-party pressure points
- generating non-obvious mechanisms and substitute pathways
- tracing second-order and third-order effects
- exposing hidden assumptions
- generating competing explanations with divergent predictions
- surfacing plausible surprises a shallow analyst would miss
- resisting shallow macro-template answers
- producing denser, more decision-useful output

---

## Phase 1 philosophy

Do **not** build a broad framework first.

Do **not** spend unnecessary time expanding non-core components in the first MVP version.

The first MVP must be:
- narrow
- sharp
- testable
- runnable from simple commands
- easy to inspect by hand
- easy to compare before vs after

The system should improve one agent by forcing it through a small number of **high-value structural gates**, not by simulating many agents or many roles.

Core pipeline:

`DECOMPOSE -> TRACE -> COMPETE -> STRESS -> DENSE_DRAFT`

This sequence is the phase-1 backbone.

---

## Non-negotiable build rules for Codex

1. **Do not spend unnecessary time expanding non-core components in the first MVP version.**  
   Build only the smallest set of functions that directly improve the agent’s reasoning ability.

2. **Provide a testable demo example program at each key milestone.**  
   Every major function must come with a minimal runnable example that proves it works.

3. **Each core function must be independently runnable from a simple command.**  
   No core capability should depend on a large unfinished framework before it can be tested.

4. **Do not build decorative architecture before the core reasoning gain is verified.**  
   No dashboards, service layers, broad plugin systems, UI polish, or orchestration bloat in phase 1.

5. **Every new component must justify itself by visibly improving output quality.**  
   If a component does not clearly improve depth, structure, relevance, or surprise generation, postpone it.

6. **Prefer a small number of hard-working modules over many weak modules.**  
   The first MVP should be narrow, sharp, and testable.

7. **Each milestone must end with a concrete before-vs-after demonstration.**  
   Show output without the function, then with the function.

8. **Use structured outputs from the beginning.**  
   Outputs must be easy to inspect, compare, save, and diff.

9. **Do not hide incomplete logic behind placeholder abstractions.**  
   If a feature is not implemented, leave it out.

10. **Optimize for measurable reasoning improvement, not software completeness.**

11. **Keep the first MVP easy to inspect, debug, and modify.**

12. **Add tests and demo cases at the same time as each core function, not afterward.**

---

## What this engine is trying to fix

The engine exists to reduce these common single-agent failure modes:

- **Actor Blindness**  
  The model misses relevant people, organizations, or institutions.

- **Node / Facility Blindness**  
  The model misses facilities, infrastructures, chokepoints, or concrete operational nodes.

- **Mechanism Collapse**  
  The model gives first-order cliché explanations instead of tracing real causal chains.

- **Substitute-Path Blindness**  
  The model fails to ask what happens when the obvious route is blocked and actors adapt.

- **Hidden-Assumption Blindness**  
  The model does not expose the assumptions propping up its own strongest answer.

- **Weak Surprise Generation**  
  The model does not surface plausible-but-underestimated developments.

- **Macro-Template Drift**  
  The model falls into generic summaries instead of grounded structural analysis.

- **Output Bloat**  
  The model spends too many tokens on filler instead of structure.

---

## Phase 1 hard cuts

Do **not** build these in phase 1:

- multi-agent debate
- persona theater / roleplay systems
- soul systems
- dashboards
- large API/service layers
- domain-wide ontologies
- mind-map memory systems
- broad plugin registries
- generic “many perspectives” prompts
- flat axis decomposition as the main engine
- elaborate UI
- hidden chain-of-thought auditing
- latent probability / token-rank introspection
- corpus-scale co-occurrence engines
- any feature whose main benefit is “sounds sophisticated”

These are either phase 2+ or not worth building at all unless a later benchmark proves clear gain.

---

## Core phase-1 architecture

The engine is a **single-agent rigor pipeline** with exactly five functions:

1. `decompose`
2. `trace`
3. `compete`
4. `stress`
5. `final`

Nothing else is phase-1 essential.

---

## Core function 1 — `decompose`

### Purpose
Force the agent out of macro-summary mode and into concrete entity / node identification.

### Input
A user problem statement as plain text.

### Output
A structured object with:
- `problem_frame`
- `actor_cards`
- `node_cards`
- `constraint_cards`

### Required output schema

```json
{
  "problem_frame": {
    "core_question": "...",
    "decision_or_analysis_target": "...",
    "scope_notes": ["..."]
  },
  "actor_cards": [
    {
      "name": "...",
      "type": "person|organization|state|firm|proxy|institution|other",
      "role": "...",
      "goal_guess": "...",
      "why_relevant": "..."
    }
  ],
  "node_cards": [
    {
      "name": "...",
      "type": "facility|route|market|institutional node|platform|other",
      "function": "...",
      "why_relevant": "..."
    }
  ],
  "constraint_cards": [
    {
      "constraint": "...",
      "applies_to": ["..."],
      "why_it_matters": "..."
    }
  ]
}
```

### Ability improved
- actor / node coverage
- relevance grounding
- resistance to macro-template drift

### Failure prevented
- actor blindness
- node blindness
- generic macro-summary answers

### Why phase-1 indispensable
No deep analysis is possible if the table is missing the real pieces.

### Minimal demo requirement
Codex must provide a runnable demo such as:

```bash
python demos/demo_decompose.py
```

The demo must:
- run on one hard-coded sample problem
- print structured `actor_cards`, `node_cards`, and `constraint_cards`
- save output to `examples/out/decompose_example.json`

### Test requirement
Must include tests that check:
- keys exist
- arrays are non-empty on sample problem
- at least one actor and one node are produced
- no freeform prose-only response is allowed

---

## Core function 2 — `trace`

### Purpose
Force the agent to generate causal chains instead of shallow bullet points.

### Input
One selected actor move, node change, or state change plus the current structured context.

### Output
A structured consequence chain with depth 1 to 3.

### Required output schema

```json
{
  "trace_target": "...",
  "consequence_chain": [
    {
      "order": 1,
      "event": "...",
      "mechanism": "...",
      "affected_entities": ["..."]
    },
    {
      "order": 2,
      "event": "...",
      "mechanism": "...",
      "affected_entities": ["..."]
    },
    {
      "order": 3,
      "event": "...",
      "mechanism": "...",
      "affected_entities": ["..."]
    }
  ]
}
```

### Ability improved
- mechanism depth
- second-order / third-order effect discovery
- substitute-path visibility

### Failure prevented
- mechanism collapse
- shallow first-order cliché analysis

### Why phase-1 indispensable
This is the heart of “deeper than a template answer.”

### Minimal demo requirement
Codex must provide:

```bash
python demos/demo_trace.py
```

The demo must:
- load a sample `decompose` output
- pick one actor move or node change
- print a 3-step consequence chain
- save output to `examples/out/trace_example.json`

### Test requirement
Must include tests that check:
- trace depth reaches at least 3 in sample demo
- each step has `event`, `mechanism`, and `affected_entities`
- order numbers are valid and increasing

---

## Core function 3 — `compete`

### Purpose
Prevent premature convergence by forcing competing causal explanations and divergent predictions.

### Input
Current analysis state, including `decompose` output and at least one trace.

### Output
Two competing mechanism cards with divergent predictions.

### Required output schema

```json
{
  "competing_mechanisms": [
    {
      "label": "A",
      "core_mechanism": "...",
      "what_it_explains": "...",
      "prediction": "...",
      "observable_signal": "..."
    },
    {
      "label": "B",
      "core_mechanism": "...",
      "what_it_explains": "...",
      "prediction": "...",
      "observable_signal": "..."
    }
  ],
  "divergence_note": "..."
}
```

### Ability improved
- competing explanation generation
- divergent prediction quality
- uncertainty mapping

### Failure prevented
- premature consensus
- pseudo-diversity where outputs differ only in wording

### Why phase-1 indispensable
If two paths do not produce meaningfully different predictions, the engine is not really exploring.

### Minimal demo requirement
Codex must provide:

```bash
python demos/demo_compete.py
```

The demo must:
- load sample prior artifacts
- generate two competing mechanism cards
- save output to `examples/out/compete_example.json`

### Test requirement
Must include tests that check:
- exactly two competing mechanisms exist
- both include predictions
- predictions are not string-identical
- both include observable signals

---

## Core function 4 — `stress`

### Purpose
Attack the current strongest analysis to expose hidden assumptions, failure points, and likely surprises.

### Input
Current strongest draft conclusion plus all previous artifacts.

### Output
A falsification ledger and a surprise ledger.

### Required output schema

```json
{
  "falsification_ledger": [
    {
      "claim_under_stress": "...",
      "hidden_assumption": "...",
      "how_it_could_fail": "...",
      "what_evidence_would_break_it": "..."
    }
  ],
  "surprise_ledger": [
    {
      "surprise": "...",
      "why_shallow_analysis_misses_it": "...",
      "what_actor_or_node_it_depends_on": ["..."]
    }
  ]
}
```

### Ability improved
- hidden-assumption exposure
- surprise generation
- robustness against the model’s own default answer path

### Failure prevented
- confirmation bias
- weak surprise generation
- false confidence

### Why phase-1 indispensable
Without stress-testing, the system just polishes its own first answer.

### Minimal demo requirement
Codex must provide:

```bash
python demos/demo_stress.py
```

The demo must:
- load sample artifacts
- create a falsification ledger
- create a surprise ledger
- save output to `examples/out/stress_example.json`

### Test requirement
Must include tests that check:
- at least one falsification entry exists
- at least one surprise entry exists
- each falsification entry includes a hidden assumption
- each surprise entry links back to actors or nodes

---

## Core function 5 — `final`

### Purpose
Produce a dense final answer using the structured artifacts, not generic filler prose.

### Input
All intermediate objects:
- problem frame
- actor cards
- node cards
- constraint cards
- consequence chains
- competing mechanism cards
- falsification ledger
- surprise ledger

### Output
A final dense report.

### Required output sections
The final answer must include:
1. `Key Actors and Nodes`
2. `Critical Mechanism Chains`
3. `Competing Explanations and Divergent Predictions`
4. `Likely Surprises`
5. `Main Uncertainties / Hidden Assumptions`

### Ability improved
- structural density
- usefulness per token
- resistance to output bloat

### Failure prevented
- generic long-form summary
- filler-heavy answers
- loss of structure at the last mile

### Why phase-1 indispensable
A strong intermediate pipeline still fails if the final output collapses back into generic summary language.

### Minimal demo requirement
Codex must provide:

```bash
python demos/demo_final.py
```

The demo must:
- load sample prior artifacts
- generate a final dense report
- print to console
- save to `examples/out/final_example.md`

### Test requirement
Must include tests that check:
- all required sections appear
- the report is built from artifacts, not empty placeholders
- no section is missing
- output stays within a reasonable length bound for the sample case

---

## Recommended execution order

Phase 1 must be built in this exact order:

1. `decompose`
2. `trace`
3. `compete`
4. `stress`
5. `final`

Reason:
- no analysis without entities
- no depth without causal chains
- no rigor without competing mechanisms
- no robustness without stress
- no usable delivery without dense synthesis

---

## Suggested code layout for phase 1

Keep it small.

```text
project_root/
  CODEX.md
  README.md
  requirements.txt
  src/
    engine.py
    schemas.py
    prompts.py
    functions/
      decompose.py
      trace.py
      compete.py
      stress.py
      final.py
  demos/
    demo_decompose.py
    demo_trace.py
    demo_compete.py
    demo_stress.py
    demo_final.py
  tests/
    test_decompose.py
    test_trace.py
    test_compete.py
    test_stress.py
    test_final.py
  examples/
    sample_problem.txt
    out/
```

Do not add extra layers unless a core function truly needs them.

---

## Command-line requirement

Each function must be callable directly.

Minimum acceptable command shape:

```bash
python -m src.functions.decompose --input examples/sample_problem.txt
python -m src.functions.trace --input examples/out/decompose_example.json --target "..."
python -m src.functions.compete --input examples/out/trace_example.json
python -m src.functions.stress --input examples/out/compete_example.json
python -m src.functions.final --input-dir examples/out/
```

Codex may wrap these later, but phase 1 must first prove each function works independently.

---

## Demo policy

At each milestone, provide:

1. one runnable demo script
2. one saved output artifact
3. one before-vs-after note

The before-vs-after note can be short. Example:

- Before `trace`: answer is a flat summary.
- After `trace`: answer includes a 3-step causal chain with named mechanisms.

Do not skip this requirement.

---

## Evaluation for phase 1

These metrics do not need to be perfect at MVP stage, but the code should be written so they can be computed later.

### 1. Actor / Node Coverage Score (ANCS)
Count how many relevant actors or nodes appear that were not explicitly mentioned in the prompt.

### 2. Mechanism Novelty Rate (MNR)
Estimate the fraction of mechanism statements that are non-cliché and not just first-order boilerplate.

### 3. Structural Density Ratio (SDR)
Estimate the share of output devoted to structured artifacts rather than filler prose.

### 4. Surprise Usefulness Rate (SUR)
Judge whether the generated surprises are plausible and decision-relevant rather than random.

### 5. Divergent Prediction Quality (DPQ)
Check whether competing explanations actually lead to meaningfully different predictions.

### 6. Resistance to Shallow Macro-Summaries (RSMS)
Check whether the output avoids generic overview prose and enters node/mechanism structure quickly.

Phase 1 does not need perfect automatic scoring, but it must preserve enough structure so these can be evaluated.

---

## Implementation notes for Codex

### Keep
- strict schemas
- direct commands
- runnable demos
- saved example outputs
- small codebase
- explicit tests
- structured intermediate artifacts

### Cut
- elaborate memory
- roleplay
- agent societies
- plugin ecosystems
- generic “perspective expansion”
- broad academic framework terms unless they change code behavior

### Prefer
- plain Python
- explicit JSON artifacts
- simple file-based demos
- visible incremental progress
- hand-checkable outputs

---

## Milestone checklist

### Milestone 1
Implement `decompose`
- runnable demo
- saved json
- tests pass

### Milestone 2
Implement `trace`
- runnable demo
- saved json
- tests pass

### Milestone 3
Implement `compete`
- runnable demo
- saved json
- tests pass

### Milestone 4
Implement `stress`
- runnable demo
- saved json
- tests pass

### Milestone 5
Implement `final`
- runnable demo
- saved markdown
- tests pass

No milestone is complete unless its demo and tests exist.

---

## Codex handoff note

Build the smallest possible **single-agent rigor engine**.

Do not branch into non-core features.

The only phase-1 job is to make one agent better by forcing it through:
- entity decomposition
- causal tracing
- competing explanation generation
- stress testing
- dense structured final drafting

Every function must be independently runnable.
Every milestone must include a demo.
Every output must be structured and saved.
Do not build architecture that does not directly improve reasoning ability.
