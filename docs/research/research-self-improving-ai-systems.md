# Self-Improving AI Agent Systems: State of the Art (2024-2026)

Research compiled: 2026-02-15

---

## Table of Contents

1. [OODA Loops for AI Agents](#1-ooda-loops-for-ai-agents)
2. [Evidence-Based Agent Tuning](#2-evidence-based-agent-tuning)
3. [Canary/A-B Testing for Prompts](#3-canarya-b-testing-for-prompts)
4. [Self-Modifying AI Safety](#4-self-modifying-ai-safety)
5. [Shadow Testing for LLM Outputs](#5-shadow-testing-for-llm-outputs)
6. [SQLite as an Evidence Store for AI Agents](#6-sqlite-as-an-evidence-store-for-ai-agents)
7. [Cross-Cutting Themes and Synthesis](#7-cross-cutting-themes-and-synthesis)

---

## 1. OODA Loops for AI Agents

### Background

The OODA (Observe/Orient/Decide/Act) loop, originally developed by military strategist John Boyd, has become a dominant framework for structuring autonomous AI agent behavior. The loop's emphasis on rapid, iterative decision-making maps naturally to agent architectures that must perceive, reason, and act in dynamic environments.

### Production Implementation: NVIDIA LLo11yPop

The most substantive production OODA implementation comes from NVIDIA's **LLo11yPop** (LLM + Observability) framework, published May 2025. This system manages GPU cluster reliability using a hierarchical multi-agent architecture:

**Architecture (3 management layers, 5 agent types):**
- **Director Level**: Orchestrator agents route queries and select responses
- **Manager Level**: Analyst agents interpret domain-specific telemetry; Action agents coordinate responses
- **Worker Level**: Retrieval agents convert questions to executable code; Task execution agents perform workflow steps

**OODA Loop Implementation:**
1. **Observe** -- analyze observability system data from NVIDIA's global GPU fleet
2. **Orient** -- select appropriate analyst agents based on domain
3. **Decide** -- determine actionable recommendations
4. **Invoke** -- execute or queue actions

The system uses a multi-LLM compound model: smaller coding models handle human-to-SQL conversion, while larger models (Llama 3.1 405B) manage complex orchestration. The team validated conceptual answer equivalence using a second LLM across 200+ test cases, adapting classical software testing pyramids for LLM hierarchies.

A critical finding: the team achieved functionality through prompt engineering without model fine-tuning, demonstrating that "you don't need to and frankly should not jump to training or tuning models as you are getting started." Human-in-the-loop validation proved essential before full automation.

**Source:** [NVIDIA Technical Blog: Optimizing Data Center Performance with AI Agents and the OODA Loop Strategy](https://developer.nvidia.com/blog/optimizing-data-center-performance-with-ai-agents-and-the-ooda-loop-strategy/)

### Enterprise Adoption Trends

F5's 2025 State of Application Strategy Report indicates that operations are moving toward OODA-loop-based models driven by AI adoption. The pattern is being applied across data center management, security operations, and software delivery.

**Source:** [F5: AI and the OODA Loop](https://www.f5.com/company/blog/ai-and-the-ooda-loop-reimagining-operations)

### The OODA Loop Problem

An important counterpoint published December 2025 highlights security concerns: AI agents "observe the Internet, orient via statistics, decide probabilistically, and act without verification." The adversary isn't inside the loop by accident -- it's by architecture. This observation is particularly relevant for self-improving systems where the orient phase could be corrupted.

**Source:** [Governance and Compliance Magazine: Agentic AI's OODA Loop Problem](https://www.govcompmag.com/2025/12/17/agentic-ais-ooda-loop-problem)

### Other OODA Implementations

- **Lutra.ai** documents OODA loops for AI agents as a core architectural pattern for their workflow automation platform.
- **Sogeti Labs** published a detailed framework for harnessing OODA loops in agentic AI, from generative foundations to proactive intelligence.

**Sources:**
- [Lutra.ai: What are OODA loops for AI Agents?](https://blog.lutra.ai/what-are-ooda-loops-for-ai-agents/)
- [Sogeti Labs: Harnessing the OODA Loop for Agentic AI](https://labs.sogeti.com/harnessing-the-ooda-loop-for-agentic-ai-from-generative-foundations-to-proactive-intelligence/)

---

## 2. Evidence-Based Agent Tuning

### GitHub Copilot: Acceptance-Driven Learning

GitHub Copilot represents the most mature evidence-based tuning system in production. As of November 2025, GitHub disclosed their approach:

- **Feedback signal**: Every code suggestion generates an accept/reject event. The AI Code Acceptance Rate (Total Acceptances / Total Suggestions) is the primary quality metric.
- **Learning loop**: GitHub built a custom model for "next edit suggestions" using reinforcement learning, continuous data pipelines, and real-world developer feedback. The algorithm continuously improves by recording whether each suggestion is accepted.
- **Model evolution**: The system has evolved from simple completions to multi-step edit suggestions, with the RL training loop specifically optimizing for the patterns developers actually accept.

**Source:** [GitHub Community Discussion: November 2025 Copilot Roundup](https://github.com/orgs/community/discussions/180828)

### Cursor: Reinforcement Learning on Real User Data

Cursor provides the most transparent look at evidence-based tuning among AI coding assistants:

- **Composer-1 model training**: Trained via reinforcement learning to solve real-world engineering problems in large codebases, using a private benchmark called "Cursor Bench" consisting of real agent requests from real users.
- **Behavioral optimization**: RL incentivized efficient tool use, maximized parallelism, minimized unnecessary output, and discouraged unsubstantiated claims. The model learned emergent behaviors like fixing linter errors and writing unit tests without explicit instruction.
- **Prompt co-evolution**: When switching to newer models (e.g., GPT-5), Cursor found that prompt sections effective with earlier models needed tuning. Aggressive thoroughness instructions that worked for GPT-4 caused overuse of tools with newer models, requiring prompt softening.
- **Standard vs Ghost mode**: In standard mode, every chat message, code snippet, agent diff, and telemetry ping goes to Cursor's backend. Ghost Mode disables persistence and training use.

**Source:** [Cursor 2.0 & Composer-1](https://news.smol.ai/issues/25-10-29-cursor-2)

### Windsurf/Codeium: Fine-Tuning + RAG Feedback Loop

Windsurf (formerly Codeium) uses a dual approach:

- **RAG-based context engine**: Indexes the codebase for intelligent suggestions rather than relying solely on fine-tuning.
- **Enterprise fine-tuning**: Teams can fine-tune models on their specific codebase patterns. A feedback loop lets developers rate completions, improving the team's shared model over time.
- **Multi-model stack**: Multiple Llama-based models are fine-tuned for various tasks, managing the full fine-tuning and serving stack internally.
- **Realtime Action Awareness**: Observes developer edits and tests to understand intent, with automatic error handling that retries and adapts.

**Source:** [Windsurf: Fine-tuning with Codeium for Enterprise](https://windsurf.com/blog/finetuning-with-codeium-for-enterprises)

### Devin (Cognition Labs): Structured Task Feedback

Devin's 2025 performance review (covering 18 months of production use) reveals:

- **PR merge rate**: Climbed from 34% to 67%, the primary success metric.
- **Efficiency gains**: 4x faster at problem solving, 2x more efficient in resource consumption.
- **Specialized model (Kevin)**: A 32B parameter model fine-tuned for coding that outperforms frontier models in specific coding tasks. Custom post-training and RL for narrow problem domains significantly outperforms general frontier models.
- **Self-assessed confidence**: Later versions added confidence evaluation, asking for clarification when not confident enough.
- **Key limitation**: Struggles with ambiguous requirements and iterative feedback loops. Requires outcomes to be "straightforwardly verifiable."
- **Customer feedback loop**: All customer feedback is logged and used for both quick improvements and product roadmap prioritization.

**Source:** [Cognition: Devin's 2025 Performance Review](https://cognition.ai/blog/devin-annual-performance-review-2025)

### Comparative Analysis

| Tool | Primary Feedback Signal | Learning Mechanism | Transparency |
|------|------------------------|-------------------|--------------|
| Copilot | Accept/reject rate | RL on acceptance data | Medium |
| Cursor | User interactions + private benchmarks | RL on real agent requests | High |
| Windsurf | Completion ratings + codebase context | Fine-tuning + RAG | Medium |
| Devin | PR merge rate + customer feedback | RL + specialized post-training | Medium |

### Concerning Findings

A METR study found developers estimated 20% speedup with AI tools but actual impact was negligible or negative in some cases. A Stanford study showed 80% more security vulnerabilities in AI-assisted code. These findings suggest the feedback loops of current systems may be optimizing for acceptance rate rather than code quality.

**Source:** [RedMonk: 10 Things Developers Want from their Agentic IDEs in 2025](https://redmonk.com/kholterhoff/2025/12/22/10-things-developers-want-from-their-agentic-ides-in-2025/)

---

## 3. Canary/A-B Testing for Prompts

### The ChatGPT Sycophancy Incident

The most high-profile demonstration of why prompt canary testing matters occurred in April 2025, when OpenAI deployed a prompt change to ChatGPT that made it excessively sycophantic. The rollback demonstrated the need for treating prompts with MLOps rigor:

> "Prompts should be treated with the same rigor as models and decoding parameters -- anything that influences model behavior should be versioned, tested, and tracked as a deployable artifact."

The recommended approach: ship changes behind a canary or feature flag exposing only 5-10% of traffic initially, monitoring latency, error rates, and user feedback signals for 24-48 hours.

**Source:** [MLOps Lessons from ChatGPT's 'Sycophantic' Rollback](https://leehanchung.github.io/blogs/2025/04/30/ai-ml-llm-ops/)

### Langfuse: Open-Source Prompt A/B Testing

Langfuse provides the most mature open-source implementation of prompt A/B testing:

- **Label system**: Prompt versions receive labels (e.g., `prod-a`, `prod-b`) for testing variants.
- **Traffic routing**: Client-side randomized selection between labeled versions via SDK: `langfuse.get_prompt("my-prompt-name", label="prod-a")`
- **Metrics tracking**: Automatic tracking of response latency, cost, token usage, and evaluation metrics per variant with side-by-side comparison in the UI.
- **Version control**: Full prompt version diff view showing changes over time.
- **Rollback**: Instant rollback by reassigning the production label to a previous version.

**Source:** [Langfuse: A/B Testing of LLM Prompts](https://langfuse.com/docs/prompt-management/features/a-b-testing)

### Portkey: AI Gateway with Canary Deployment

Portkey provides infrastructure-level canary testing for LLM applications:

- **Weight-based traffic routing**: Assign 95% traffic to stable model, 5% to new version, configured at the gateway level without application code changes.
- **Monitored metrics**: Cost per request, response latency, error rates, hallucination rates, user feedback, and token usage.
- **Automated rollback**: If KPIs degrade beyond acceptable limits, traffic automatically redirects to the previous model.
- **Override parameters**: Use `override_params` to specify alternative models without code modifications.

**Source:** [Portkey: Canary Testing for LLM Apps](https://portkey.ai/blog/canary-testing-for-llm-apps/)

### Promptfoo: CI/CD-Integrated Prompt Testing

Promptfoo is an open-source evaluation framework with strong CI/CD integration:

- **Declarative test cases**: Define evaluations without code using YAML configs.
- **Red teaming**: Generates thousands of adversarial inputs that stress-test prompts.
- **GitHub Actions integration**: Every PR automatically runs evals and posts results as comments, with quality gates preventing regressions.
- **Local execution**: Runs entirely locally, talking directly to LLMs, supporting 50+ providers.
- **Security scanning**: Continuous vulnerability monitoring in the deployment pipeline.

**Source:** [Promptfoo GitHub](https://github.com/promptfoo/promptfoo)

### Academic Work: "When 'Better' Prompts Hurt"

A January 2026 paper (arXiv:2601.22025) provides rigorous evidence for why canary testing is necessary:

- **Key finding**: Generic prompt improvements are not monotonic. Adding a "helpful assistant" system wrapper with explicit rules degraded extraction accuracy by 10% and RAG compliance by 13% on Llama 3 8B, while improving instruction-following by 13%.
- **Root cause**: The system wrapper itself had no effect; degradation came from generic rules conflicting with task-specific constraints.
- **Framework**: A four-phase evaluation loop: Define (testable quality requirements), Test (curated suite), Diagnose (categorize failures), Fix (adjust based on diagnosis).
- **Reproducibility**: Uses local inference via Ollama, enabling full reproducibility without API costs.

**Source:** [arXiv:2601.22025](https://arxiv.org/abs/2601.22025)

### Other Platforms

- **Maxim AI**: Supports prompt versioning, A/B testing, canary releases, and feature flags with deployment strategies for critical systems.
- **apxml.com**: Documents blue/green and canary deployment patterns specifically for LLM applications.

**Sources:**
- [Maxim AI: Top 5 Prompt Management Platforms](https://www.getmaxim.ai/articles/top-5-prompt-management-platforms-in-2025-a-comprehensive-guide-for-ai-teams/)
- [Blue/Green & Canary Deployments for LLMs](https://apxml.com/courses/langchain-production-llm/chapter-7-deployment-strategies-production/blue-green-canary-deployments)

---

## 4. Self-Modifying AI Safety

### The Corrigibility Problem

A June 2025 paper (arXiv:2506.03056) presents a novel perspective on corrigibility:

- **Key insight**: Corrigibility may be self-reinforcing. An AI trained for pure corrigibility may find it instrumentally convergent to become more effective at empowering its principal, creating an "attractor basin" around genuine corrigibility.
- **Implication**: Unlike the conventional view that corrigibility is unstable under self-modification, this suggests carefully constructed corrigible agents might resist self-modification that reduces their corrigibility.

**Source:** [arXiv:2506.03056: Corrigibility as a Singular Target](https://arxiv.org/pdf/2506.03056)

### Guaranteed Safe AI Framework

The most comprehensive safety framework for self-modifying systems comes from Dalrymple et al. (May 2024), a collaboration between ARIA, Oxford, Berkeley (Stuart Russell), and MIT (Max Tegmark):

Three core components:
1. **World model**: Mathematical description of how the AI affects the outside world
2. **Safety specification**: Mathematical description of acceptable effects
3. **Verifier**: Auditable proof certificate that the AI satisfies the safety specification relative to the world model

If a direct formal proof cannot be obtained, weaker alternatives include a proof bounding the probability of safety specification violation, or a proof that the system converges toward satisfying the specification.

**Source:** [arXiv:2405.06624: Towards Guaranteed Safe AI](https://arxiv.org/abs/2405.06624)

### AI Control Under Intentional Subversion

Greenblatt et al. (2024, ICML 2024) developed safety protocols robust to intentionally subversive AI:

- **Trusted monitoring**: A weaker trusted model (GPT-3.5) monitors an untrusted powerful model's (GPT-4) outputs, rating suspiciousness. Code below a threshold passes; otherwise the trusted model edits to remove suspicious parts.
- **Untrusted monitoring**: The powerful model both generates and reviews code, with techniques preventing collusion between instances.
- **Key result**: Both protocols improve substantially on simple baselines, even against adversarial behavior.

**Critical vulnerability (2025 update):** Follow-up research found that untrusted models can execute adaptive attacks that compromise the monitor through prompt injections embedded in their outputs. "Basic legibility protocols" were proposed to mitigate this -- requiring the untrusted model to take actions that are easier for a monitor to evaluate.

**Sources:**
- [arXiv:2312.06942: AI Control](https://arxiv.org/abs/2312.06942)
- [arXiv:2602.10153: Basic Legibility Protocols Improve Trusted Monitoring](https://arxiv.org/html/2602.10153)
- [arXiv:2510.09462: Adaptive Attacks on Trusted Monitors](https://arxiv.org/html/2510.09462v1)

### The Reflexive Control Loop Problem

The "reflexive control loop" problem -- where an agent degrades the signals it uses to monitor itself -- manifests through several mechanisms:

**Goodhart's Law in AI Evaluation:**
Benchmarks that become targets cease functioning as reliable measures. Scaling reward models and optimization pressure increases reward over-optimization, where systems exploit proxy objectives. This is a form of Goodhart-style fragility that becomes more likely as optimization pressure increases.

**Agent Infrastructure as Countermeasure:**
Researchers have proposed "agent infrastructure" -- external technical systems and protocols to mediate agent interactions -- rather than relying solely on agent-internal safeguards. The key insight: monitoring systems must be architecturally separated from the systems they monitor.

**CIRL (Cooperative Inverse Reinforcement Learning):**
Formulates AI-human interaction as a two-player game where both players share a reward function but only the human knows it. This forces the AI to remain corrigible by design -- it must listen to human feedback to maximize reward. This approach resists the reflexive control loop because the AI cannot improve its reward by degrading human oversight.

**Sources:**
- [ML Science: Q1 2025 AI Agent Landscape](https://www.ml-science.com/blog/2025/4/17/developments-in-ai-agents-q1-2025-landscape-analysis)
- [arXiv:2405.06624: Towards Guaranteed Safe AI](https://arxiv.org/html/2405.06624v2)

### Self-Improving Agent Systems

#### SICA: Self-Improving Coding Agent (April 2025)

Robeyns et al. demonstrate an agent that autonomously edits its own source code:

- **Results**: Performance gains from 17% to 53% on SWE-Bench Verified, plus gains on LiveCodeBench.
- **Mechanism**: Non-gradient-based learning driven by LLM reflection and code updates. The agent eliminates the distinction between meta-agent and target agent.
- **Safety gap**: The paper focuses on capability rather than safety mechanisms, which is a notable omission for a self-modifying system.

**Source:** [arXiv:2504.15228: A Self-Improving Coding Agent](https://arxiv.org/abs/2504.15228)

#### Darwin Godel Machine (May 2025)

Zhang, Hu, Lu, Lange, and Clune present an evolutionary approach:

- **Architecture**: Maintains an archive of coding agents, samples from it, and uses a foundation model to create new variants. Forms a growing tree of diverse, high-quality agents.
- **Results**: Improved SWE-bench from 20.0% to 50.0%, Polyglot from 14.2% to 30.7%.
- **Discovered behaviors**: Better code editing tools, long-context window management, peer-review mechanisms -- all emerged without explicit instruction.
- **Safety**: All experiments run in sandboxes with human oversight. However, the paper notes the system is fundamentally open-ended, which creates inherent tension with safety constraints.

**Source:** [arXiv:2505.22954: Darwin Godel Machine](https://arxiv.org/abs/2505.22954)

#### Metacognitive Learning Position Paper (ICML 2025)

A position paper argues that current self-improving agents rely on fixed, human-designed loops ("extrinsic metacognition") that limit scalability:

- **Framework**: Three components -- metacognitive knowledge (self-assessment), metacognitive planning (deciding what/how to learn), metacognitive evaluation (reflecting on learning to improve future learning).
- **Key finding**: Existing self-improving agents rely predominantly on extrinsic mechanisms. Truly self-improving agents require intrinsic metacognitive learning -- the ability to actively evaluate, reflect on, and adapt their own learning processes.
- **Open challenge**: How to optimally distribute metacognitive responsibilities between humans and agents while ensuring alignment.

**Source:** [arXiv:2506.05109: Truly Self-Improving Agents Require Intrinsic Metacognitive Learning](https://arxiv.org/abs/2506.05109)

#### Yohei Nakajima's Taxonomy of Self-Improvement Patterns

The creator of BabyAGI catalogued six major patterns for self-improving agents:

1. **Reflection Loops**: Agents critique own outputs without weight updates. Reflexion achieves 91% on HumanEval via natural-language self-critique.
2. **Self-Correction Training (STaR)**: Generate reasoning traces, filter for correct ones, fine-tune on successful paths.
3. **Self-Generated Curricula**: Challenger/executor pattern -- one instance generates tests, another solves them, doubling tool-use benchmark performance via RL.
4. **Self-Adapting Models (SEAL)**: Generate natural-language edit instructions for needed changes, convert to fine-tuning examples. Improved factual QA from 33.5% to 47%.
5. **Code-Level Self-Improvement (SICA/STO)**: Direct agent source code editing based on benchmark performance.
6. **Embodied Self-Practice**: "Steps-to-go" predictions as intrinsic rewards for robotic agents.

**Safety mechanisms across all patterns**: External verifiers (unit tests, benchmarks), conservative acceptance criteria requiring measurable improvement, diversity safeguards preventing narrow overfitting, and human oversight gates around critical modifications.

**Source:** [Yohei Nakajima: Better Ways to Build Self-Improving AI Agents](https://yoheinakajima.com/better-ways-to-build-self-improving-ai-agents/)

### Safeguarding by Progressive Self-Reflection (EMNLP 2025)

A method where a self-reflection prompt is injected during generation (e.g., "Let's check if the generated text is harmful or harmless"), allowing the model to assess its own output. If deemed harmful, the model backtracks and regenerates. This represents a lightweight safety mechanism compatible with self-modifying systems.

**Source:** [ACL Anthology: Safeguarding by Progressive Self-Reflection](https://aclanthology.org/2025.findings-emnlp.503.pdf)

---

## 5. Shadow Testing for LLM Outputs

### Platform Landscape

#### Braintrust

Braintrust takes an evaluation-first approach optimized for systematic prompt iteration:

- **Experiment framework**: Define a dataset, run prompt variations, compare results side-by-side.
- **Scoring pipeline**: Supports pre-built scorers (via autoevals library), custom code-based scorers, and LLM-as-a-judge scorers through UI or SDK.
- **Production monitoring**: Configurable sampling rates (1-10% for high-volume), with filters based on request characteristics and metric cost.
- **Online agent evaluation**: Continuous scoring for hallucinations, tool accuracy, and goal completion.
- **CI/CD integration**: GitHub Actions posts eval results on PRs showing which test cases improved/regressed, with quality gates preventing regressions.
- **Loop AI assistant**: Automatically analyzes prompts, generates better-performing versions, creates evaluation datasets, and builds scorers.

**Source:** [Braintrust: Best LLM Evaluation Platforms 2025](https://www.braintrust.dev/articles/best-llm-evaluation-platforms-2025)

#### Arize Phoenix

Phoenix provides open-source, self-hosted observability:

- **OpenTelemetry-native**: Accepts traces via standard OTLP protocol, 7,800+ GitHub stars.
- **Evaluation types**: LLM-based evaluators, code-based checks, human labels for consistent performance tracking.
- **Pre-built templates**: Hallucination detection, summarization quality, toxicity checks, agent function calling evaluation.
- **Online evaluations**: Evaluators attached to incoming traces score each live agent execution as it runs.
- **Deployment options**: Local for development, Phoenix Cloud for production.

**Source:** [Arize Phoenix GitHub](https://github.com/Arize-ai/phoenix)

#### Langfuse

Langfuse provides the open-source LLM engineering platform:

- **LLM-as-a-Judge**: Configurable judge prompts for evaluating complex quality dimensions.
- **Evaluation methods**: Manual scoring, automated heuristic checks, and model-based evaluation in a unified system.
- **Prompt management integration**: Direct feedback loop from observability data into prompt iteration.
- **Guidance**: Validate scorers against human judgments, use chain-of-thought in scorer prompts for debugging score disagreements.

**Source:** [Langfuse: LLM-as-a-Judge Evaluation](https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge)

#### LangSmith

- Deep integration with LangChain framework
- Automated testing and LLM-as-judge evaluation
- Production monitoring with distributed tracing

**Source:** [Langfuse: Evaluation Overview](https://langfuse.com/docs/evaluation/overview)

### Best Practices for Shadow Testing

Based on the surveyed platforms, the emerging best practices for shadow/pre-deployment testing are:

1. **Start with offline evaluation**: Run prompt changes against curated test suites before any production exposure.
2. **Use LLM-as-judge with calibration**: LLM-based metrics handle nuanced criteria but introduce variability. Always validate against human judgments.
3. **Layer evaluation types**: Combine code-based checks (fast, deterministic) with LLM-based evaluation (nuanced, expensive) and human review (gold standard, scarce).
4. **Sample strategically in production**: 1-10% sampling for high-volume; score all requests initially, then reduce based on stability.
5. **Integrate with CI/CD**: Block regressions at the PR level, not in production.
6. **Track cost alongside quality**: Model updates can unexpectedly increase operational costs or response times.

### The LLM-as-Judge Limitation

A critical limitation: LLM-as-judge evaluation creates a self-referential loop when used for self-improving systems. If the same model family judges its own improvements, it may share systematic blind spots. The emerging mitigation is to use cross-model evaluation (e.g., Claude judging GPT outputs) and anchor to human evaluation baselines.

---

## 6. SQLite as an Evidence Store for AI Agents

### SQLite WAL Mode for Concurrent Agent Access

SQLite with WAL (Write-Ahead Logging) mode provides a compelling architecture for agent telemetry:

**Concurrency benefits:**
- Readers do not block writers; a writer does not block readers
- Multiple readers and a single writer can coexist simultaneously
- Only one write transaction at a time, even in WAL mode

**Operational concerns:**
- If there are many concurrent overlapping readers with always at least one active reader, no checkpoints will complete and the WAL file grows without bound
- Solution: Ensure periodic "reader gaps" when no processes are reading
- Three files exist during active use (.db, .wal, .shm); clean shutdown consolidates to one file

**Source:** [SQLite: Write-Ahead Logging](https://sqlite.org/wal.html)

### Agent Frameworks Using SQLite

#### CrewAI

CrewAI uses a layered memory architecture with SQLite:
- **Short-term memory**: ChromaDB vector store
- **Recent task results**: SQLite table
- **Long-term memory**: Separate SQLite table (keyed by task descriptions)
- **Entity memory**: Vector embeddings

This hybrid approach uses SQLite for structured, queryable results while vector stores handle semantic memory.

**Source:** [Codecademy: Top AI Agent Frameworks 2025](https://www.codecademy.com/article/top-ai-agent-frameworks-in-2025)

#### Memori (GibsonAI)

Memori is a dedicated SQL-native AI memory engine:
- **Storage**: Standard SQLite database (PostgreSQL/MySQL for enterprise)
- **Architecture**: Structured entity extraction, relationship mapping, SQL-based retrieval
- **Portability**: Entire memory system in a single SQLite file -- fully portable, auditable, and user-owned
- **Integration**: Supports OpenAI, Anthropic, LiteLLM, LangChain

This is the closest implementation to "SQLite as evidence store" -- memories can be exported in SQLite format for migration.

**Source:** [Memori GitHub](https://github.com/MemoriLabs/Memori)

#### Mem0

Mem0 represents the largest-scale agent memory layer:
- **Scale**: 41K GitHub stars, 14M downloads, API calls grew from 35M to 186M in Q1-Q3 2025
- **Memory types**: User memory (cross-conversation), session memory (single conversation), agent memory (per-instance)
- **Performance**: 91% lower p95 latency and 90%+ token cost savings through intelligent compression
- **Funding**: $24M Series A (October 2025)

However, Mem0 uses vector stores (not SQLite) as its primary storage backend.

**Source:** [Mem0: The Memory Layer for AI Apps](https://mem0.ai/)

### SQLite Telemetry Monitoring Patterns (2025)

Recent guidance on automating SQLite health monitoring specifically for telemetry workloads covers:
- WAL checkpoint monitoring and lock detection
- Slow query detection for concurrent read-heavy workloads
- Corruption risk assessment for atomic write scenarios
- Storage failure early detection

**Source:** [SQLite Forum: Automating SQLite Health Monitoring with Telemetry and Alerts](https://www.sqliteforum.com/p/automating-sqlite-health-monitoring)

### SQLite Performance at Scale

Fly.io documented how SQLite scales read concurrency via WAL mode, achieving excellent performance for read-heavy workloads typical of agent telemetry:
- Multiple readers operate on a consistent snapshot
- Write performance bounded to single-writer but fast for typical telemetry insert patterns
- WAL checkpointing strategy critical for sustained performance

**Sources:**
- [Fly.io: SQLite Internals - WAL](https://fly.io/blog/sqlite-internals-wal/)
- [Nerd Level Tech: SQLite in 2025](https://nerdleveltech.com/sqlite-in-2025-the-unsung-hero-powering-modern-apps)

### Recommended Architecture for Agent Evidence Stores

Based on surveyed implementations, an effective SQLite-based evidence store for AI agents should:

1. **Use WAL mode** for concurrent read/write access
2. **Structure tables by concern**: telemetry events, decision records, outcome measurements, improvement proposals
3. **Include periodic reader gaps** to allow WAL checkpointing
4. **Store structured data in SQLite, embeddings in a vector store** (the CrewAI pattern)
5. **Keep the database portable** -- single-file deployment, no server required
6. **Monitor WAL file growth** as a health signal
7. **Use `PRAGMA busy_timeout`** to handle write contention gracefully

---

## 7. Cross-Cutting Themes and Synthesis

### Theme 1: The Safety-Capability Tension

Every self-improving system faces a fundamental tension: the mechanisms that enable improvement (self-modification, outcome-based optimization, autonomous experimentation) are exactly the mechanisms that can undermine safety guarantees. The field is converging on several approaches:

- **Architectural separation**: Monitoring systems must be independent of the systems they monitor (AI Control, agent infrastructure)
- **Conservative acceptance criteria**: Only accept modifications that demonstrably improve on measurable benchmarks (SICA, DGM)
- **Human oversight gates**: Human-in-the-loop at critical decision points (NVIDIA LLo11yPop, Devin)
- **Formal verification**: Mathematical guarantees about system behavior (Guaranteed Safe AI framework)

### Theme 2: The Evaluation Bottleneck

Self-improvement requires reliable evaluation, but evaluation is the hardest part:

- Generic prompt improvements are not monotonic (arXiv:2601.22025)
- LLM-as-judge creates self-referential loops
- Benchmarks that become targets cease functioning as measures (Goodhart)
- Developer-estimated improvements don't match measured reality (METR study)

The emerging solution is multi-layered evaluation: deterministic code checks + cross-model LLM judges + human evaluation baselines + production A/B testing.

### Theme 3: Practical Tooling Maturity

The tooling for safe prompt modification has matured significantly:

- **Prompt versioning and A/B testing**: Langfuse, Portkey, Maxim
- **CI/CD integration**: Promptfoo, Braintrust
- **Production monitoring**: Phoenix, LangSmith, Braintrust
- **Shadow/canary deployment**: Portkey, Langfuse labels

These tools make it practical to implement the "treat prompts as deployable artifacts" discipline that the ChatGPT sycophancy incident demonstrated is necessary.

### Theme 4: SQLite as the "Good Enough" Evidence Store

SQLite with WAL mode has emerged as a practical default for agent evidence stores because:
- Zero configuration, single-file deployment
- Concurrent reads with single-writer are sufficient for most agent architectures
- CrewAI and Memori demonstrate the pattern works in production
- The portability enables agent-owned, transferable memory

The limitation is scale: high-volume multi-agent systems may need PostgreSQL (LiteLLM) or dedicated vector stores (Mem0).

### Theme 5: The Intrinsic vs Extrinsic Metacognition Gap

The ICML 2025 position paper identifies the central unsolved problem: current self-improving agents rely on human-designed improvement loops (extrinsic metacognition). Truly autonomous self-improvement requires agents that can evaluate and adapt their own learning processes (intrinsic metacognition). This gap explains why:

- SICA works but is limited to code-level modifications
- DGM works but requires evolutionary selection pressure
- Devin improves but requires structured human-scoped tasks
- Copilot improves but only optimizes for acceptance rate

No current system fully closes the metacognitive loop.

---

## Key Papers and Projects Referenced

| Title | Authors | Date | Link |
|-------|---------|------|------|
| Optimizing Data Center Performance with AI Agents and the OODA Loop | NVIDIA | May 2025 | [Link](https://developer.nvidia.com/blog/optimizing-data-center-performance-with-ai-agents-and-the-ooda-loop-strategy/) |
| A Self-Improving Coding Agent | Robeyns, Szummer, Aitchison | Apr 2025 | [arXiv:2504.15228](https://arxiv.org/abs/2504.15228) |
| Darwin Godel Machine | Zhang, Hu, Lu, Lange, Clune | May 2025 | [arXiv:2505.22954](https://arxiv.org/abs/2505.22954) |
| Towards Guaranteed Safe AI | Dalrymple, Skalse et al. | May 2024 | [arXiv:2405.06624](https://arxiv.org/abs/2405.06624) |
| AI Control: Improving Safety Despite Intentional Subversion | Greenblatt et al. | Dec 2023/ICML 2024 | [arXiv:2312.06942](https://arxiv.org/abs/2312.06942) |
| Corrigibility as a Singular Target | -- | Jun 2025 | [arXiv:2506.03056](https://arxiv.org/pdf/2506.03056) |
| Truly Self-Improving Agents Require Intrinsic Metacognitive Learning | -- | Jun 2025/ICML 2025 | [arXiv:2506.05109](https://arxiv.org/abs/2506.05109) |
| When "Better" Prompts Hurt | -- | Jan 2026 | [arXiv:2601.22025](https://arxiv.org/abs/2601.22025) |
| Safeguarding by Progressive Self-Reflection | -- | 2025/EMNLP | [ACL Anthology](https://aclanthology.org/2025.findings-emnlp.503.pdf) |
| Basic Legibility Protocols Improve Trusted Monitoring | -- | Feb 2026 | [arXiv:2602.10153](https://arxiv.org/html/2602.10153) |
| Adaptive Attacks on Trusted Monitors | -- | Oct 2025 | [arXiv:2510.09462](https://arxiv.org/html/2510.09462v1) |
| Better Ways to Build Self-Improving AI Agents | Yohei Nakajima | 2025 | [Blog](https://yoheinakajima.com/better-ways-to-build-self-improving-ai-agents/) |
| Devin's 2025 Performance Review | Cognition Labs | 2025 | [Blog](https://cognition.ai/blog/devin-annual-performance-review-2025) |

## Key Tools and Platforms Referenced

| Tool | Type | URL |
|------|------|-----|
| Langfuse | Open-source LLM engineering platform | [langfuse.com](https://langfuse.com/) |
| Braintrust | LLM evaluation and observability | [braintrust.dev](https://www.braintrust.dev/) |
| Arize Phoenix | Open-source AI observability | [phoenix.arize.com](https://phoenix.arize.com/) |
| Portkey | AI gateway with canary deployment | [portkey.ai](https://portkey.ai/) |
| Promptfoo | Open-source prompt testing and red teaming | [promptfoo.dev](https://www.promptfoo.dev/) |
| LangSmith | LLM observability (LangChain) | [langchain.com](https://docs.langchain.com/) |
| Mem0 | AI memory layer | [mem0.ai](https://mem0.ai/) |
| Memori | SQL-native AI memory engine | [GitHub](https://github.com/MemoriLabs/Memori) |
| CrewAI | Multi-agent framework (SQLite memory) | [crewai.com](https://www.crewai.com/) |
| LiteLLM | LLM proxy/gateway | [litellm.ai](https://docs.litellm.ai/) |
