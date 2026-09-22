# Worktree Guard

Private release candidate. Public redistribution licensing is not selected yet.

Check a Git worktree before deleting it, or check the target location before
merging a branch. Exit codes and JSON output make the checks usable from shell
scripts, coding agents, and CI. The tool performs checks only; it never merges,
removes worktrees, deletes branches, or fetches from a remote.

Requires Python 3.8+ and Git with `worktree list --porcelain -z` support.

```sh
make test
make install PREFIX="$HOME/.local"
worktree-guard remove-check ../feature-worktree --base main
worktree-guard merge-check . --base main --branch feature --json
```

You can also run `./bin/worktree-guard` directly without installing anything.

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
