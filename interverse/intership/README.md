# intership

Culture ship names as Claude Code spinner verbs. Because why would you settle for "Thinking..." when you could have *Experiencing A Significant Gravitas Shortfall*?

237 curated names: 56 canonical Banks originals from the Culture novels, plus 181 generated Banksian originals refined through six rounds of editorial culling.

## Install

From the interagency marketplace:

```bash
/plugin marketplace add mistakeknot/interagency-marketplace
/plugin install intership
```

Ship names load automatically on session start. Restart Claude Code after first install to see them.

## What you get

Canonical Banks names are marked with \*asterisks\* so you can tell them apart:

> *Sleeper Service*... *Falling Outside The Normal Moral Constraints*... Mildly Thermonuclear... I Was Told There Would Be Cake... On Reflection You Should Run... Pursuant To No Particular Authority...

The names span eight rhetorical registers: terse loaded phrases (*Sunk Cost*, *Fait Accompli*), conversational asides (Does Anyone Remember Why), dry understatement (Not Without A Certain Doomed Charm), bewildered observers (I Wasn't Briefed On The Volcano), polite menace (This Concludes The Polite Version), dark whimsy (Sympathetic Detonation), bureaucratic absurdity (Provisionally Classified As Intentional), and single evocative words (Temerity).

## Customize

```
/intership:setup
```

Toggle between canonical-only, generated-only, or both. Filter by source novel, add your own ships, or switch from replace to append mode (keeping Claude's defaults alongside the Culture names).

## Edit directly

Ship names live in `data/ships.txt`, one per line. Lines starting with `#` are comments. Names wrapped in `*asterisks*` are canonical Banks originals. Changes apply next session.

Configuration lives in `data/config.json`:

```json
{
  "includeCanonical": true,
  "includeGenerated": true
}
```

## Generate more

`data/generator-prompt.md` contains the v6 generator prompt, iteratively refined over six rounds and ~380 candidates. Feed it to any LLM to generate names that match the curated quality bar. The prompt documents rhetorical patterns, anti-patterns (with the "why"), and nine quality tests.

## Source novels

The canonical names come from: Consider Phlebas, The Player of Games, Use of Weapons, Excession, Look to Windward, Matter, Surface Detail, and The Hydrogen Sonata.
