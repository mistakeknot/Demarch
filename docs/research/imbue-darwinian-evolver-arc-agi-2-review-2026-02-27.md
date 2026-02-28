# Imbue: Darwinian Evolver & ARC-AGI-2 Code Evolution Review

> **Date:** 2026-02-27
> **Sources:**
> - [Beating ARC-AGI-2 with Code Evolution](https://imbue.com/research/2026-02-27-arc-agi-2-evolution/)
> - [LLM-based Evolution as a Universal Optimizer](https://imbue.com/research/2026-02-27-darwinian-evolver/)
> - [GitHub: imbue-ai/darwinian_evolver](https://github.com/imbue-ai/darwinian_evolver) (cloned to `docs/research/darwinian_evolver/`)
> - [HN Discussion](https://news.ycombinator.com/item?id=47185163)
> - Inspired by [Darwin Goedel Machines](https://arxiv.org/abs/2505.22954)

## TL;DR

Imbue open-sources a **problem-agnostic evolutionary optimization framework** that maintains a population of LLM-generated code/prompt "organisms," iteratively selecting, mutating, and evaluating them. Applied to ARC-AGI-2, it **triples open-weight model performance** (Kimi K2.5: 12.1% → 34.0%) and pushes Gemini 3.1 Pro to **95.1%** (from 88.1% baseline), at $2.67–$8.71 per task. The framework is general enough to optimize arbitrary code, prompts, or agents.

---

## 1. What Is the Darwinian Evolver?

A lightweight Python framework implementing evolutionary optimization over code and prompts. Unlike gradient-based optimization, it operates on **non-differentiable solution spaces** — any problem where you can score an output and describe failures.

### Core Abstraction: Three Components

| Component | Role | Example |
|-----------|------|---------|
| **Organism** | The thing being evolved | Python function, prompt template, git commit |
| **Evaluator** | Scores organisms, identifies failure cases | Run code on test inputs, check correctness |
| **Mutator** | LLM-powered; takes organism + failures → improved variant | "This code failed on input X because Y; here's a fix" |

### Evolution Loop (per iteration)

```
Population.sample_parents(weighted by fitness × novelty)
  → for each parent:
      sample failure cases from evaluation
      Mutator.mutate(parent, failures, learning_log) → children
      (optional) Evaluator.verify_mutation(child) → filter trivial changes
      Evaluator.evaluate(child) → score + new failure cases
      Population.add(child, result)
```

### Key Design Choice: Resilience Over Precision

The framework explicitly tolerates **noisy evaluators and unreliable mutators**. If the mutator only produces improvements 20% of the time, the population-level dynamics still drive progress. This is the critical insight — you don't need a perfect optimizer, you need a good enough one running at population scale.

---

## 2. ARC-AGI-2 Application: Code Evolution

### How It Works for ARC

Each **organism** is a Python function (`transform(input_grid) → output_grid`) that attempts to solve an ARC task. The evolutionary process:

1. **Initial organism**: LLM generates a first-attempt `transform` function from the task examples
2. **Evaluation**: Run the function on training examples, compute soft correctness score (partial credit for approximately-correct grids), plus:
   - **Transfer score** (7% weight): LLM assesses whether the solution generalizes to challenge inputs
   - **Simplicity score** (3% weight): LLM counts branches, literals, hardcoded colors — simpler code preferred
   - **Correctness** (90% weight): Soft match against training outputs, with baseline rescaling
3. **Mutation**: LLM sees the failing examples and current code, proposes diagnosis + fix
4. **Crossover** (25% of mutations): Sample 3 parents, ask LLM to combine their transformation rules
5. **Verification filter**: Reject mutations that produce identical outputs to parent on all inputs (prevents trivial edits from polluting the population)

### Scoring Formula

```
score = 0.9 × correctness + 0.07 × transfer + 0.03 × simplicity
```

The correctness score is **rescaled** relative to a baseline similarity between inputs and outputs — this ensures the sigmoid-weighted parent selection uses the full score range effectively.

### Multi-Provider LLM Support

The code supports mixing providers during evolution:

| Provider | Model | Cost/1M tokens (out) | Use Case |
|----------|-------|---------------------|----------|
| Google | Gemini 3.1 Pro | $12.00 | High-thinking mutations |
| Google | Gemini 3 Flash | $3.00 | Low-thinking evaluations |
| Anthropic | Claude Opus 4.6 | $25.00 | Alternative high-thinking |
| OpenAI | GPT-5.2 | $14.00 | Alternative high-thinking |
| OpenRouter | Kimi K2.5 | $3.00 | Budget-friendly |

Random mixing strategies (`random_google_openai`, `random_google_anthropic`, etc.) provide diversity in mutation strategies — different models have different reasoning strengths.

### Results

| Base Model | Baseline Score | Evolved Score | Improvement | Cost/Task |
|------------|---------------|---------------|-------------|-----------|
| Kimi K2.5 (open-weight) | 12.1% | 34.0% | **2.8×** | $2.67 |
| Gemini 3 Flash | — | — | **1.8×** | — |
| Gemini 3.1 Pro | 88.1% | 95.1% | **+7pp** | $8.71 |

The open-weight result (34% with Kimi K2.5) sets a **new ARC-AGI-2 record for open-weight models**.

---

## 3. Framework Architecture (from code review)

### Population Management

**WeightedSamplingPopulation** — the default strategy, based on the Darwin Goedel Machines paper:

```
sampling_weight(organism) = sigmoid(score; sharpness, midpoint) × novelty_bonus

novelty_bonus = 1 / (1 + λ × num_children)
```

- `sharpness` (default 10): How sharply to prefer high-scoring organisms
- `midpoint` (default `p75`): Dynamically tracks the 75th percentile — auto-tunes as population improves
- `novelty_weight λ` (default 1.0): Encourages exploration of under-sampled organisms

This balances **exploitation** (evolve the best) with **exploration** (try the less-tested).

### Learning Log System

A mechanism for sharing insights across the population:

1. Each mutation records: `attempted_change` (what was tried) + `observed_outcome` (score delta)
2. Future mutations receive relevant log entries based on strategy:
   - `ancestors`: Full lineage history
   - `neighborhood-N`: All organisms within N mutation steps (siblings, cousins, etc.)

This lets mutators learn from failed experiments without re-attempting them.

### Post-Mutation Verification

Optional filter that checks whether a mutation actually changes behavior:

- For ARC: "Does the mutated code produce different output on at least one input?"
- For multiplication verifier: "Does it fix at least one of the target failure cases?"

Prevents trivial edits (whitespace, comments, reorderings) from consuming expensive full evaluation slots.

### Batch Mutations

Pass 2-5 failure cases to a single mutator call instead of one. Tradeoffs:
- **Pro**: Mutator can identify cross-failure patterns
- **Con**: Reduces diversity, LLMs sometimes degrade with too much context

### Example Problems Included

1. **Parrot** — Minimal: evolve a prompt to echo phrases (tutorial-level)
2. **Circle Packing** — Code evolution: maximize circle radii within unit square
3. **Multiplication Verifier** — Prompt evolution with batch mutations + verification
4. **ARC-AGI** — Full multi-provider code evolution (the research result)

---

## 4. Relevance to Demarch

### Direct Applicability

| Concept | Demarch Parallel | Notes |
|---------|-----------------|-------|
| Population of organisms | Pool of agent strategies | Evolving agent prompts/tools over time |
| Fitness-weighted selection | Agent performance scoring | Intercore could score agent effectiveness |
| Learning log | Solution compounding | Cross-session learning from past attempts |
| Crossover mutations | Multi-agent synthesis | Combining strategies from different agents |
| Post-mutation verification | Smoke tests before deploy | Filter bad changes before full evaluation |
| Provider mixing | Model routing | Clavain already does heterogeneous model routing |

### Key Insights for Autonomous Agents

1. **Resilience > precision**: A mutator that succeeds 20% of the time is fine if you run enough iterations. This maps directly to agent autonomy — let agents try many approaches, keep what works.

2. **Soft scoring enables gradual improvement**: Partial credit (soft_score) is crucial for ARC. Hard pass/fail would make the fitness landscape too sparse for evolution to navigate. Same principle applies to agent evaluation — grade on a spectrum, not binary.

3. **Simplicity pressure prevents overfitting**: The 3% simplicity weight in ARC scoring penalizes organisms that hardcode colors and branches. For agents, this maps to preferring general strategies over task-specific hacks.

4. **Transfer scoring as generalization check**: Using an LLM to assess whether a solution would generalize to unseen inputs is a lightweight alternative to held-out test sets. Could apply to agent strategy evaluation.

5. **The verification filter is cheap but powerful**: Checking "did anything actually change?" before running expensive evaluation saves significant compute. Trivial for agents to implement.

### Potential Integration Points

- **Intercore scheduler**: Could use evolutionary dynamics for task allocation strategies
- **Clavain model routing**: Evolve routing rules based on task outcomes
- **Interflux review agents**: Evolve reviewer prompts/focus areas based on finding quality
- **Autarch agent strategies**: Population of agent configurations, evolved by performance

---

## 5. Technical Notes

### Dependencies
- Python with UV package manager
- `anthropic >= 0.78.0`, `google-genai >= 1.56.0`, `openai >= 2.16.0`
- `pydantic`, `jinja2`, `numpy`, `func_timeout`, `fsspec` (S3)
- Runs ARC code in subprocess with 8GB memory limit and 30s timeout

### Interesting Implementation Details

- **Thread-safe cost tracking**: Global mutex-protected cost accumulator across all LLM calls
- **Subprocess isolation**: ARC code execution uses `ProcessPoolExecutor` + `resource.setrlimit` for memory caps
- **Retry with exponential backoff**: All LLM calls use `tenacity` with 4-10 retries
- **Anthropic Opus 4.6 insight**: From their system card — "Opus 4.6 saturates available thinking tokens at all effort levels on ARC-AGI, leading to very similar scores. At low effort, the model saves tokens by stopping early for easier problems." So they always use `effort="low"` for Anthropic.
- **Score = 0.9 × correctness + 0.07 × transfer + 0.03 × simplicity**: The weighting was empirically tuned; transfer score uses multiplicative combination of three LLM-judged factors

### Visualization

Includes `lineage_visualizer.html` — load JSONL results to interactively explore the evolutionary tree, inspect organisms at each generation, and track score progression.

---

## 6. Assessment

### Strengths
- **Genuinely general**: The same framework handles prompt optimization, code evolution, and (potentially) agent self-improvement
- **Clean abstraction**: 3-component interface (Organism, Evaluator, Mutator) is minimal and well-designed
- **Production quality**: Cost tracking, retry logic, subprocess isolation, checkpoint/resume
- **Novel ARC approach**: Divergence-first (vs. Poetiq's convergence/consensus) is philosophically interesting

### Weaknesses / Open Questions
- **Cost scaling**: $8.71/task × hundreds of ARC tasks = significant spend for full benchmark
- **No self-improvement demonstrated**: Despite DGM inspiration, the released code uses static (external LLM) mutators, not self-improving organisms
- **Evaluation is the bottleneck**: Each organism evaluation requires multiple LLM calls (correctness, transfer, simplicity) — expensive
- **Limited crossover**: 25% crossover rate with 3 parents is simple; more sophisticated recombination could help
- **No formal convergence guarantees**: Evolutionary methods can plateau; no mechanism for detecting/escaping stagnation beyond novelty bonus

### Bottom Line

This is a **well-engineered, production-ready evolutionary optimization framework** with strong ARC-AGI-2 results. The key contribution isn't the algorithm (which is fairly standard evolutionary computation with LLM mutators) but the **demonstration that simple evolutionary dynamics + LLM reasoning = powerful optimization on hard reasoning tasks**. The open-sourcing is genuine — the code is clean, documented, and immediately usable.

For Demarch, the most transferable ideas are: (1) population-level resilience over individual precision, (2) soft scoring for gradual improvement, (3) learning logs for cross-organism knowledge sharing, and (4) the verification filter pattern.
