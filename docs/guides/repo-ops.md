# Repo operations

Operational patterns for working with the Demarch monorepo's nested-git architecture.

## Nested git repos

Each subproject (`os/clavain/`, `core/intercore/`, `interverse/interflux/`, etc.) has its own `.git` directory and its own GitHub repo under `mistakeknot/`. The root `Demarch/` also has a `.git` for the monorepo skeleton (scripts, docs, beads, CLAUDE.md).

The root `.gitignore` excludes all subproject directories:

```
apps/
os/
core/
interverse/
sdk/*
```

This means subproject files are NOT pushed to the Demarch GitHub repo. Only the skeleton is.

## Links in root-tracked files must be absolute GitHub URLs

Because subproject directories are gitignored, relative links like `[Clavain](os/clavain/)` will 404 on GitHub. Any markdown file tracked by the root Demarch repo (README.md, docs/*.md) must use absolute GitHub URLs for subproject references:

```markdown
# Wrong (404 on GitHub)
[Clavain](os/clavain/)
[Intercore](core/intercore/)

# Right
[Clavain](https://github.com/mistakeknot/Clavain)
[Intercore](https://github.com/mistakeknot/intercore)
```

Links to files within the Demarch skeleton are fine as relative paths (e.g., `docs/guide-power-user.md`), since those files are tracked.

## Finding GitHub repo URLs

```bash
# Get the GitHub URL for any subproject
git -C core/intercore remote get-url origin
```

Common repos:

| Local path | GitHub repo |
|-----------|------------|
| `os/clavain/` | `mistakeknot/Clavain` |
| `core/intercore/` | `mistakeknot/intercore` |
| `core/intermute/` | `mistakeknot/intermute` |
| `core/marketplace/` | `mistakeknot/interagency-marketplace` |
| `apps/autarch/` | `mistakeknot/Autarch` |
| `sdk/interbase/` | `mistakeknot/interbase` |
| `interverse/<name>/` | `mistakeknot/<name>` |

## Which repo am I in?

```bash
git rev-parse --show-toplevel
```

This is critical before any git operation. If you're at `interverse/interflux/` and run `git push`, it pushes the interflux repo, not Demarch.

## Committing to multiple repos

When changes span the Demarch skeleton and a subproject, you need separate commits:

```bash
# Commit subproject changes first
git -C os/clavain add .claude-plugin/plugin.json
git -C os/clavain commit -m "fix: update plugin manifest"
git -C os/clavain push

# Then commit skeleton changes
git -C /home/mk/projects/Demarch add README.md
git -C /home/mk/projects/Demarch commit -m "docs: update README links"
git -C /home/mk/projects/Demarch push
```

## Common mistakes

1. **Relative links in root README**: will 404 on GitHub because subprojects are gitignored.
2. **`git add .` from root**: stages nothing for subprojects (gitignored). Use `git -C <subproject> add` instead.
3. **Assuming one push covers everything**: each repo needs its own push.
4. **Editing files in `~/.claude/plugins/cache/`**: always edit the source repo, push, and reinstall. Cache is ephemeral.
