# The Sovereignty Thesis: Why Every Plugin Boundary Is Load-Bearing

## I. What a Plugin Actually Is

A plugin is not a convenient organizational unit. A plugin is a **sovereignty boundary** — an independently deployable, independently evolvable, independently *killable* unit of capability. It has its own release cadence. Its own documentation. Its own failure domain. Its own reason for existing that does not require justification from any neighboring unit.

Sovereignty is binary. A module that cannot be versioned independently is not a plugin — it is a namespace. A module that cannot fail independently is not isolated — it is coupled with extra steps. A module that cannot be deleted without auditing its siblings has already lost the property that made it worth creating.

The Demarch monorepo has 49 sovereign plugins. That number is not a problem to be solved. It is a **structural achievement** to be protected.

## II. The Opponent's Best Shot

The consolidation argument is not stupid. It deserves to be stated at full strength before it is dismantled.

The argument goes: 49 sovereign units impose coordination overhead that exceeds the value of independence for most of those units. Cross-plugin changes touch 3-4 plugins per feature. Discovery is hard. Publish and version overhead is constant. Context loading costs tokens. Segment consolidated 140 microservices into a monolith and saw deployment velocity triple. Uber went from 2,200 services to 70 macro-services. Amazon reportedly saved 90% on a video pipeline by merging lambdas. The evidence is real: sometimes consolidation works, and the people who did it are not fools.

The consolidation advocate looks at a routing plugin that just dispatches calls between two other plugins and asks: "Why does *this* need its own manifest, its own AGENTS.md, its own version number?" It is a fair question. They look at the token cost of loading 49 plugin contexts and ask: "Is the boundary tax worth it when most of these plugins will never be deployed independently?" Also fair.

Now let me explain why they are wrong anyway.

## III. The Diagnosis

Every consolidation success story shares the same structure: an organization that lacked the **infrastructure to make fine-grained boundaries cheap** decided to make boundaries coarse instead. This is not engineering wisdom. It is capitulation.

Segment did not prove that 140 services were too many. Segment proved that Segment could not build the routing, discovery, and deployment infrastructure to sustain 140 services. Uber did not prove that 2,200 services were architecturally wrong. Uber proved that their service mesh, their deployment pipeline, and their organizational coordination could not keep pace with the granularity they had chosen. The consolidation worked *for them* because rebuilding infrastructure was harder than surrendering boundaries.

But the Demarch ecosystem is not Segment. It is not Uber. It is a plugin ecosystem — and plugin ecosystems have a completely different cost structure because **the infrastructure for sustaining fine-grained boundaries already exists and keeps getting better**.

Look at the evidence:

**VSCode** sustains 60,000+ extensions. Not because 60,000 boundaries are "free," but because the Extension Host architecture — process isolation, Activation Events, lazy loading — makes the marginal cost of the 60,001st extension approximately zero. The cost of N plugins is the cost of *activated* plugins, not all plugins. Azure Account cut activation time 50% through bundling its *internal* code, not by merging with another extension.

**Terraform** has 3,000+ providers, each a separate OS process communicating over gRPC. When HashiCorp bundled providers into Core, any provider change required a Core release. The Terraform team's own words: it "wasn't sustainable." They unbundled. Now the AWS provider ships weekly, independently of Core, independently of the GCP provider, independently of every other provider. The boundary *is the feature*.

**Neovim's lazy.nvim** loads 50+ plugins with sub-100ms startup through demand-driven loading. Nobody looks at a lazy.nvim configuration and says "you should merge your colorscheme with your LSP client to reduce plugin count." The idea is laughable because the loading infrastructure made it laughable.

**Anthropic's own Tool Search** cut token overhead 85% — from 77K to 8.7K tokens for 50+ tools — while *simultaneously* improving accuracy from 49% to 74%. This is the proof of concept sitting inside the very system running this conversation. The loading problem was solved without consolidation. The boundaries remained. Performance improved.

The pattern is always the same: **invest in infrastructure, not in boundary erasure**.

## IV. Why Boundary Erosion Is Irreversible in Practice

Here is the fact that consolidation advocates never want to discuss: **splitting is 10x harder than merging**.

When you merge two plugins, you get immediate relief. One fewer manifest. One fewer version to track. Fewer cross-boundary calls. The benefits are instant and visible.

When you later discover that the merged unit needs to be split — because one half needs a different release cadence, or a different failure domain, or a different maintainer — you face an archaeology project. Which types belong to which half? Which shared utilities were truly shared versus accidentally coupled? Where did the boundary *used to be* before six months of co-evolution blurred it?

Go modules within a single repository demonstrate this perfectly. The Go team designed modules as independence boundaries. But when multiple modules share a repository, developers inevitably take shortcuts — internal packages leak across module boundaries, replace directives paper over version mismatches, and within a year the modules are coupled in ways that make independent versioning a fiction. The boundary exists in `go.mod` but not in reality.

Rust workspaces show the same pattern. Crates within a workspace can technically be versioned independently. In practice, `cargo publish` order dependencies, shared `Cargo.lock` files, and path dependencies create a coupling gradient that makes independent release a heroic act rather than a routine one.

Physical boundaries are Sam Newman's "ratchet" — they resist erosion mechanically. You cannot accidentally import across a process boundary. You cannot accidentally share state across a plugin manifest boundary. Logical boundaries require continuous policing, and continuous policing always loses to deadline pressure.

The 49 plugins in Demarch are 49 ratchets. Each one mechanically resists the coupling that would otherwise accumulate silently.

## V. The Long Tail Is Where the Value Lives

Plugin ecosystems do not derive their value from the top 10 plugins that everyone uses. They derive their value from the long tail — the 39th plugin that serves three users who would otherwise have no solution at all.

A consolidated system optimizes for the common case. It merges the routing plugin into the transport plugin because "they always change together." It merges the niche formatter into the core because "it's too small to justify its own package." Each merge is locally rational.

But the long tail cannot survive consolidation. The niche formatter, once merged into core, is now subject to core's release cadence. Core's review standards. Core's priorities. The maintainer of the niche formatter — who might be a single person with a specific use case — now needs permission from core maintainers to ship a fix. The sovereignty that let them move fast, experiment freely, and serve their three users without coordination overhead is gone.

Interverse has 49 plugins because 49 capabilities deserve independent evolution. Some of those capabilities are "small." Some are "glue." None of them are *less sovereign* for being small. A five-line plugin with its own manifest is making a precise, testable claim: "this capability can be understood, deployed, versioned, and deleted independently." That claim has value even if the capability is trivial — *especially* if the capability is trivial, because trivial things should be trivial to manage, and sovereignty makes them so.

## VI. The Uncomfortable Truth

Here is the strongest version of what I believe:

**The pain of managing 49 plugins is not a sign that you have too many plugins. It is a sign that your plugin infrastructure is not yet good enough.** Every ounce of energy spent consolidating plugins is energy stolen from building the infrastructure that would make 490 plugins effortless.

Discovery is hard? Build better discovery. Context loading costs tokens? Build lazy loading — Anthropic already proved it works. Cross-plugin changes are painful? Build better cross-cutting tooling — atomic multi-plugin commits, dependency-aware CI, coordinated releases. Publish overhead is constant? Automate it until it is zero.

The consolidation path is seductive because it provides immediate relief. But it is a **debt payment disguised as a refactor**. You are not simplifying your architecture. You are reducing the surface area of your ambition to match the current capacity of your tooling. And next year, when the tooling catches up — as it always does, as VSCode proved, as Terraform proved, as lazy.nvim proved, as Tool Search proved — you will be stuck with coarse boundaries and no way back.

## VII. The Inferential Chain

1. A plugin boundary is a sovereignty boundary: independent versioning, deployment, failure, and deletion.
2. Sovereignty is a mechanical property enforced by physical separation, not a policy enforced by discipline.
3. Physical boundaries resist erosion; logical boundaries erode under pressure. This is empirically demonstrated across ecosystems.
4. Consolidation is easy and irreversible. Splitting is hard and always incomplete. Therefore, consolidation is a one-way door that should be opened only under extreme duress.
5. The pain attributed to "too many boundaries" is actually caused by insufficient boundary infrastructure (loading, discovery, routing, activation).
6. Investing in infrastructure preserves optionality. Investing in consolidation destroys it.
7. The correct response to boundary pain is always: **make boundaries cheaper**, never **make boundaries fewer**.

The 49 plugins are not the disease. They are the immune system. The disease is any force — convenience, token cost, coordination fatigue — that tempts you to dissolve them.
