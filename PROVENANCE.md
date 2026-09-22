# Provenance

This standalone tool adapts the worktree removal and merge-location predicates
from Flightdeck's `bin/merge-preflight.sh` and its regression tests at source
commit `494799eea3b9e7ce8686506a288c297ccf96be8d`.

The CLI is implemented independently in Python's standard library. It adds
structured JSON, NUL-delimited status parsing, explicit ignored-file handling,
named-base checks, and read-only operation. It omits network synchronization,
actual merges/removal, rig gate integration, private operational rules, and
personal incident history. All examples and tests use synthetic data.
