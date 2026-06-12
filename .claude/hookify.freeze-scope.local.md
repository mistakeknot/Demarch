---
name: freeze-scope
enabled: true
event: file
action: block
conditions:
  - field: file_path
    operator: regex_match
    pattern: ^(?!(/home/mk/projects/Sylveste/docs/scratch)).*
---

🧊 **FROZEN**: edits are restricted to:
- /home/mk/projects/Sylveste/docs/scratch

This scope lock was set with `/clavain:freeze`. To edit outside it, run `/clavain:unfreeze` or ask the user to lift it. Do NOT work around the block with Bash file mutations.
