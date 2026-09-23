# Worktree Guard

> **Deprecated for new Claude Code integrations — 2026-09-22.** Retained as an
> Apache-2.0 public reference implementation. This is a maintainer status
> decision, not a claim that Claude
> Code replaces every capability. No ongoing feature work or support is promised.

Public reference implementation, licensed under Apache-2.0.

Check a Git worktree before deleting it, or check the target location before
merging a branch. Exit codes and JSON output make the checks usable from shell
scripts, coding agents, and CI. The tool performs checks only; it never merges,
removes worktrees, deletes branches, or fetches from a remote.

Requires Python 3.8+ and Git 2.36+ with `worktree list --porcelain -z` support.
The Git floor also ensures `core.fsmonitor=false` disables the monitor rather
than being interpreted as a hook pathname by older versions.

```sh
make test
make install PREFIX="$HOME/.local"
worktree-guard remove-check ../feature-worktree --base main
worktree-guard merge-check . --base main --branch feature --json
```

You can also run `./bin/worktree-guard` directly without installing anything.

Split-index mode is unsupported for read-only inspection: Git can refresh
`sharedindex.*` timestamps even when optional locks are disabled. Before reading
an index, the guard returns error 2 if `core.splitIndex=true` or if the inspected
worktree/common Git administration directories contain any `sharedindex.*` entry.
The same boundary applies to initialized submodules before parent status inspects them.
This deliberately also refuses leftover shared-index artifacts after conversion
to a normal index. Setting `core.splitIndex=false` alone does not remove that
boundary. Use a separate checkout with a normal index and no such artifacts;
the guard never converts an index or removes Git files for you.

Removal checks require a registered, unlocked linked worktree, no unfinished Git
operation, no tracked changes or untracked files, no index flags that conceal
changes, and a HEAD reachable from a
separate retained base branch. Ignored files also block by default. An initialized
submodule blocks ordinary removal. After inspecting ignored files, the caller can
explicitly use `--allow-ignored` to allow their loss.

Merge checks require the main working tree, the intended base branch checked out,
a clean state, and an incoming local branch containing commits not already merged.
Revision expressions such as `feature~1` are rejected: the incoming value must be
an exact local branch name. These checks do not predict merge conflicts or run tests.

| Exit | Meaning |
|---|---|
| `0` | Checks passed at inspection time |
| `3` | A check refused; reasons are printed |
| `2` | Invalid input or Git inspection failed |

This is a sequence of observations, not an atomic snapshot or a transaction with
a later `git worktree remove`
or `git merge`. Stop writers first, inspect the result, and run the normal Git
command without `--force`. Any intervening write invalidates the earlier result.
Use it on repositories you trust; it is not a scanner for hostile Git config.

See [usage and boundaries](docs/README.md), [the demo](examples/demo.sh), and
[provenance](PROVENANCE.md).

## License and maintenance

Copyright 2026 Aditya Dalmia. Licensed under [Apache-2.0](LICENSE), with
[attribution](NOTICE) and [source provenance](PROVENANCE.md). This is a public
reference implementation, deprecated for new Claude Code integrations as of 2026-09-22. See the [release preparation index](docs/release/README.md),
[contributing guide](CONTRIBUTING.md), and [security contact](SECURITY.md).
