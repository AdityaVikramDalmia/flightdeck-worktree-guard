# Worktree Guard

Use [.agents/skills/worktree-guard-maintainer/SKILL.md](.agents/skills/worktree-guard-maintainer/SKILL.md)
for work in this repository. Contracts and installation start at [README.md](README.md).

- Keep inspection read-only, exact branch matching, hidden-index-change checks, and conservative split-index/submodule refusal. Passing predicates do not authorize a later mutation or predict conflicts.
- Release record: [docs/release/README.md](docs/release/README.md).
- Run `make test` and relevant documented demos before committing changes.
- Keep tests synthetic and isolated; preserve unrelated user edits.
- Keep source-history dates truthful and retain license/notice attribution.
- The repository is public. Do not change visibility or modify the original
  Flightdeck runtime while maintaining this component.

These are deprecated reference artifacts for new Claude Code integrations as of
2026-09-22. Preserve that status in README, examples, skills, and release material;
do not imply native feature equivalence without evidence.
