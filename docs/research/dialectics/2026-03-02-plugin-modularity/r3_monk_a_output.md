# The Composition Paradox is a Routing Problem Wearing a Philosophy Costume

## I. What Kind of Knowledge Does Composition Actually Need?

The auditor's paradox rests on a hidden assumption: that closing the tool selection gap requires the composition layer to *understand* inter-plugin relationships. This is wrong. It requires the composition layer to *point at* them.

Consider how a developer actually navigates an unfamiliar ecosystem. They don't read comprehensive documentation about how every library interacts with every other library. They read a function name, a one-line docstring, and maybe a "See also" link. When they call `os.path.join()` in Python, they don't need documentation explaining the deep relationship between `os.path`, `pathlib`, and `shutil`. They need to know `os.path` exists, that it handles filesystem paths, and that `pathlib` is the modern alternative. Three facts. No prose about architectural coupling.

The composition layer needs exactly this: discovery metadata (what exists), routing hints (when to use it), and neighborhood links (what's nearby). These are shallow signals — tags, co-occurrence groups, one-line "use X before Y" hints. The auditor claims this thinness means it "doesn't close the gap." I claim the gap is almost entirely a discovery problem, and discovery is solved by shallow metadata, not deep documentation.

## II. The Opponent's Strongest Case

The best version of the deep-docs argument runs like this: the agent's failure mode isn't "I didn't know interpath.resolve exists." It's "I called interlock.reserve_files without first calling interpath.resolve, because I didn't understand the dependency between them." This looks like a comprehension failure, not a discovery failure. And comprehension failures require deep documentation — you need to explain *why* resolve comes first, what state it produces, what reserve_files expects as input.

This is genuinely the strongest version of the argument. If the majority of selection errors are ordering/dependency errors rather than existence errors, then shallow metadata might be insufficient. The auditor would be right that closing the gap requires encoding enough relationship knowledge to effectively document one integrated system.

I believe this argument is wrong, but not trivially wrong. It deserves a real answer.

## III. Why the Paradox is a False Dilemma

The paradox asserts a binary: either the composition layer is rich enough to close the gap (proving coupling) or thin enough to preserve independence (failing to close it). This is a false dilemma because it ignores the entire middle of the spectrum — and that middle is where all practical systems live.

**Database foreign keys are the perfect counterexample.** A foreign key from `orders.customer_id` to `customers.id` is shallow metadata. It doesn't explain *why* orders reference customers, what business logic connects them, or how to correctly join across five tables for a revenue report. It's a single pointer: "this field references that table." Yet foreign keys, combined with column names and table descriptions, are sufficient for query planners, ORM introspection, and — critically — for LLMs doing text-to-SQL. The research on text-to-SQL consistently shows that schema metadata (table names, column names, foreign keys, and brief descriptions) gets you 80-90% of the way. Deep documentation of table relationships provides marginal improvement.

This is not an analogy. It is the *same problem*. Tool selection is query routing. The agent has a natural language intent and must select from a catalog of tools. The selection mechanism needs the same kind of metadata a query planner needs: names, types, brief descriptions, and join hints (which tools compose). It does not need an essay about the philosophy of composition.

**Recommendation systems confirm this.** Collaborative filtering — the shallowest possible signal, mere co-occurrence — outperforms content-based deep understanding for item selection across virtually every domain studied. Netflix doesn't need to understand the thematic relationship between two films to recommend one after the other. It needs the co-occurrence signal: users who watched A also watched B. Similarly, the composition layer doesn't need to understand the architectural relationship between interlock and interpath. It needs the co-occurrence signal: agents who called interlock.reserve_files in successful sessions also called interpath.resolve first.

**The 74% to 92% gap is predominantly discovery, not comprehension.** When an agent fails with 50+ tools, the primary failure mode is not "I understood all the tools but chose wrong." It is "I didn't surface the right candidate set." Tool Search already addresses this by returning 5 candidates from keyword/semantic matching. The residual gap comes from cases where the right tool has a name or description that doesn't match the query's vocabulary — interpath.resolve doesn't obviously match "figure out which file this refers to." A routing hint — a tag saying `domain:file-resolution`, a curation group linking it with interlock — closes this without any deep documentation. Interchart's regex patterns and forced curation groups are exactly this kind of shallow metadata, and they work.

## IV. Selection Cost is Routing, Not Comprehension

The deeper principle: the auditor conflates two different problems. *Using* tools correctly once selected may require deep understanding. *Selecting* the right tool from a catalog does not. These are fundamentally different cognitive tasks. A librarian who routes you to the right section of the library doesn't need to have read every book. They need a good catalog system — metadata, categories, cross-references.

The agent's tool selection works the same way. Once the agent has selected interpath.resolve, it reads that tool's own documentation to understand how to call it. The composition layer's job is finished at selection time. It never needs to encode the deep knowledge of how interpath's output feeds into interlock's input. That knowledge lives in each tool's own interface documentation — its parameter types, its return values, its error messages. The composition layer just needs to say: "These two tools are in the same neighborhood. If you're doing coordination, you probably need both."

This is why the paradox dissolves. The auditor says: "If you describe how interlock, intermux, and interpath compose into a coordination surface, you've proven they're one system." But the composition layer doesn't describe *how* they compose. It says *that* they compose. "These three tools are related to multi-agent coordination." Full stop. That's a tag, not a treatise. It's a foreign key, not a stored procedure.

## V. The Uncomfortable Version

Push this to its extreme: the auditor's paradox, taken seriously, would prove that *every* ecosystem with related components is secretly one monolith. PyPI packages that work together (requests + beautifulsoup + lxml) would be "one system" because you could write documentation about their composition. Unix pipes would be "one program" because you could document how `grep | sort | uniq` compose. The argument that documenting composition proves coupling would collapse every modular system into a monolith. It doesn't, because there is a categorical difference between "these things work together" and "these things are one thing." Shallow composition metadata encodes the former without implying the latter.

## VI. Skeleton

1. The gap is real (74% → 92%). Both sides agree.
2. The gap is primarily discovery/routing, not comprehension. Evidence: text-to-SQL schema metadata, recommendation system collaborative filtering, Tool Search failure mode analysis.
3. Shallow metadata (tags, curation groups, "related tools" links, one-line workflow hints) is sufficient to close routing gaps. Evidence: foreign keys close join gaps without relational prose; collaborative filtering outperforms content understanding.
4. The paradox is a false dilemma because it treats composition depth as binary (rich or thin) when the effective operating point is shallow-but-structured metadata in the middle.
5. Deep documentation is needed for tool *use*, not tool *selection*. The composition layer operates at selection time. Each tool's own docs handle use time. These are different problems with different information requirements.
6. Therefore: shallow composition closes the accuracy gap without proving coupling. The paradox dissolves.
