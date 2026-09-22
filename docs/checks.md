# Checks

`remove-check PATH --base main` resolves the path physically, requires the exact
worktree root, and verifies registration in `git worktree list`. It distinguishes
the main checkout from linked worktrees by Git/common-directory identity. Symlinks
and spaces in paths are supported, including roots ending in a newline. Status is
parsed with NUL delimiters so a newline in a filename remains one record.

The base must be a named local or remote-tracking branch. The candidate's own
branch cannot be its base. Detached worktrees can pass if their HEAD is retained
by the selected base. The check uses commit ancestry, so a squash merge with
different commit IDs can be refused even if the patch was integrated. Resolve
that case manually; there is no force option in this tool.

Remote-tracking refs are local snapshots. No fetch occurs, so the result does not
say whether commits are pushed or backed up. It proves only that the selected
local ref retains the candidate's HEAD. Deleting that ref later can discard this
protection.

Assume-unchanged and skip-worktree index flags can hide tracked modifications from
`git status`. Both flags block checks, even if the flagged files happen to be clean.
Inspect the files and clear those flags before retrying. Sparse checkouts using
skip-worktree entries are consequently refused rather than treated as fully checked.

Ignored files block by default because Git can remove them along with a worktree.
The explicit `--allow-ignored` option changes only that predicate; tracked edits
and untracked files still block. The JSON result includes ignored entries either
way. Initialized submodules require separate handling even when clean.

`merge-check PATH --branch feature --base main` checks location, branch, pending
operations, cleanliness, and whether the incoming branch is already integrated.
It does not run the merge, pre-compute conflicts, validate project tests, establish
remote freshness, or authorize deletion. A refusal to remove a worktree never
implies that its contents should be discarded.

Ancestry checks ignore replacement objects (`refs/replace/*`) and reject nonempty
legacy `info/grafts` files. A locally rewritten history must not fabricate evidence
that the selected base retains the candidate's actual commit history.

Git's optional index locks, configured hooks, and fsmonitor are disabled during checks.
Caller-provided `GIT_*` environment overrides are cleared to keep the supplied
path authoritative. The tool makes no general sandbox claim about Git or
repositories supplied by an untrusted party. Git may execute trusted configured
clean filters during status inspection; the tool is not a sandbox for those commands.

Inspection consists of multiple Git calls. Concurrent changes can make their
observations inconsistent, even before the process prints its verdict. Stop writers
throughout inspection and the subsequent operation. The tool holds no transaction
lock and cannot prove that a later merge or removal will be safe.

## Split-index boundary

Git's nominally read-only index commands can update a shared index's mtime even
with `GIT_OPTIONAL_LOCKS=0`. The guard therefore checks configuration and directory
entry names before any index-reading command, including `status` or `ls-files`.
It does not use `rev-parse --shared-index-path`, which itself can read the index.

`core.splitIndex=true`, or any `sharedindex.*` entry in the inspected worktree or
common Git administrative directory, makes inspection unsupported (error 2).
Initialized submodules, including nested modules, receive the same check before
parent status can inspect their indexes. Their paths come from each already-checked
parent index. This preflight checks at most 128 repository paths including the
requested worktree; larger initialized-submodule sets return error 2. Revisited
Git directories are not traversed again. Existing split indexes remain unsupported even if configuration says false.
Leftover shared-index files can cause the same conservative refusal after an
index was converted. The tool does not parse Git's binary index, infer whether
artifacts are orphaned, or delete them. Use a separate ordinary-index checkout.
This boundary assumes writers are stopped, like the other preflight observations.
