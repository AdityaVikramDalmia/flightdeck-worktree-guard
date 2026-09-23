# Worktree Guard

Worktree Guard checks a Git worktree before you delete it, or the target location
before you merge a branch, with exit codes and JSON output for shell scripts,
coding agents, and CI.

> **Status:** public Apache-2.0 reference implementation, deprecated for new Claude Code
> integrations as of 2026-09-22. Not a claim that Claude Code replaces every capability; no
> ongoing feature work or support is promised.

## What it does

- `remove-check PATH --base main` refuses when removing a linked worktree could
  lose uncommitted, untracked, ignored, hidden, or unmerged work.
- `merge-check PATH --base main --branch feature` checks that a merge would run
  from the main working tree, on the intended base branch, with a clean state and
  an incoming local branch that still has unmerged commits.

The tool performs checks only; it never merges, removes worktrees, deletes
branches, or fetches from a remote.

## Why it exists

Removing the wrong linked worktree can discard untracked or unmerged work. Merging
from the wrong checkout or branch can apply a valid command to the wrong target.
Ordinary status output can also omit files hidden by index flags, and Git can
remove ignored files along with a worktree. Worktree Guard turns those
preconditions into explicit checks with stable refusal reasons.

## Install

Requires Python 3.8+ and Git 2.36+ with `worktree list --porcelain -z` support.
The Git floor also ensures `core.fsmonitor=false` disables the monitor rather
than being interpreted as a hook pathname by older versions.

Install the `worktree-guard` command with pipx (the pipx route needs Python 3.9+):

```sh
pipx install git+https://github.com/AdityaVikramDalmia/flightdeck-worktree-guard
```

Or clone the repository and install the script with `make`:

```sh
git clone https://github.com/AdityaVikramDalmia/flightdeck-worktree-guard.git
cd flightdeck-worktree-guard
make install PREFIX="$HOME/.local"
```

You can also run `./bin/worktree-guard` directly without installing anything.

## Quick use

```sh
worktree-guard remove-check ../feature-worktree --base main
worktree-guard merge-check . --base main --branch feature --json
```

[The demo](examples/demo.sh) creates a disposable repository with a linked
worktree, checks it, then shows an untracked file blocking removal.

| Exit | Meaning |
|---|---|
| `0` | Checks passed at inspection time |
| `3` | A check refused; reasons are printed |
| `2` | Invalid input or Git inspection failed |

## Checks

Removal checks require a registered, unlocked linked worktree, no unfinished Git
operation, no tracked changes or untracked files, no index flags that conceal
changes, and a HEAD reachable from a separate retained base branch. Ignored files
also block by default. An initialized submodule blocks ordinary removal. After
inspecting ignored files, the caller can explicitly use `--allow-ignored` to allow
their loss.

Merge checks require the main working tree, the intended base branch checked out,
a clean state, and an incoming local branch containing commits not already merged.
Revision expressions such as `feature~1` are rejected: the incoming value must be
an exact local branch name.

See [usage and boundaries](docs/README.md) for what each predicate proves and the
JSON fields.

## Limits

- This is a sequence of observations, not an atomic snapshot or a transaction with
  a later `git worktree remove` or `git merge`. Stop writers first, inspect the
  result, and run the normal Git command without `--force`. Any intervening write
  invalidates the earlier result.
- These checks do not predict merge conflicts or run tests.
- Use it on repositories you trust; it is not a scanner for hostile Git config.
- Split-index mode is unsupported for read-only inspection: Git can refresh
  `sharedindex.*` timestamps even when optional locks are disabled. Before reading
  an index, the guard returns error 2 if `core.splitIndex=true` or if the inspected
  worktree/common Git administration directories contain any `sharedindex.*` entry.
  The same boundary applies to initialized submodules before parent status inspects
  them. This deliberately also refuses leftover shared-index artifacts after
  conversion to a normal index. Setting `core.splitIndex=false` alone does not
  remove that boundary. Use a separate checkout with a normal index and no such
  artifacts; the guard never converts an index or removes Git files for you.

## Test

Run the regression suite with `make test`. Tests and [the demo](examples/demo.sh)
create temporary local repositories without network access or an AI account.

## License and maintenance

Copyright 2026 Aditya Dalmia. Licensed under [Apache-2.0](LICENSE), with
[attribution](NOTICE) and [source provenance](PROVENANCE.md). This is a public
reference implementation, deprecated for new Claude Code integrations as of 2026-09-22. See the [release preparation index](docs/release/README.md),
[contributing guide](CONTRIBUTING.md), and [security contact](SECURITY.md).
