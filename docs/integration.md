# Integration

Use the structured result when another program consumes the verdict:

```sh
worktree-guard remove-check ../feature-worktree --base main --json
```

The object contains `status`, `operation`, `path`, `head`, `branch`, `base_ref`,
`base_commit`, `changes`, `unchecked_index_entries`, and `reasons`. Removal results also include `merged` and
`initialized_submodules`. Errors have `status: "error"` and an `error` message.
Each refusal includes a stable reason `code` and a human-readable `message`.
`unchecked_index_entries` lists filenames with assume-unchanged or skip-worktree
flags; its refusal code is `unchecked_index_entries`. Pending sequencer state also
counts as `operation_in_progress`.

An integration should inspect the exit code, not whether output is empty. A tool
failure is exit 2 and must not be treated as permission to proceed. Tests and the
demo create temporary local repositories without network access or an AI account.

```sh
# First stop every writer of this worktree. The check does not lock out writers.
candidate=../feature-worktree
if worktree-guard remove-check "$candidate" --base main; then
    git worktree remove "$candidate"
fi
```

Run the Git removal from another worktree in the same repository. Git performs its
own final checks. Avoid `--force`: it would erase protections that this workflow
depends on. If files change between inspection and removal, rerun the check.
