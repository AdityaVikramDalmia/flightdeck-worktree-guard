#!/usr/bin/env bash
# Deprecated reference example for new Claude Code integrations (2026-09-22).
set -eu
tool="$(cd "$(dirname "$0")/../bin" && pwd)/worktree-guard"
demo_dir="$(mktemp -d "${TMPDIR:-/tmp}/worktree-guard-demo.XXXXXX")"
trap 'rm -rf "$demo_dir"' EXIT
git init -q -b main "$demo_dir/repo"
git -C "$demo_dir/repo" config user.name Example
git -C "$demo_dir/repo" config user.email example@example.test
git -C "$demo_dir/repo" config commit.gpgsign false
git -C "$demo_dir/repo" -c core.hooksPath=/dev/null commit -qm initial --allow-empty
git -C "$demo_dir/repo" worktree add -qb feature "$demo_dir/feature"
"$tool" remove-check "$demo_dir/feature" --base main --json
printf 'uncommitted report\n' > "$demo_dir/feature/report.txt"
if "$tool" remove-check "$demo_dir/feature" --base main --json; then
    echo 'Expected untracked report to block removal' >&2
    exit 1
else
    result=$?
    [ "$result" -eq 3 ]
fi
