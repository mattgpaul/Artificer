<!--
ADR.md — Architecture Decision Record.
A log of the *major* decisions only (hard to reverse, surprising without
context, or a real trade-off). Use sparingly. Newest entry first.
Each entry: what was decided, and the description/reasoning behind it.
-->

# Architecture Decision Record

## 002 — Tool auto-resolves task dependencies via an unblock sweep
- **Date:** 2026-07-27
- **Status:** accepted
- **Decision:** Task dependencies are a first-class, machine-parsed `Blocker:`
  field on every task (`None`, or a comma-separated list of internal IDs and/or
  cross-project `<repo-relative path>:<id>` refs). On launch — on the same pass as
  the COMPLETE→ARCHIVED archive sweep — the tool runs an *unblock sweep*: for each
  `BLOCKED` task it resolves the referenced tickets and flips it `BLOCKED → TODO`
  iff every blocker is `COMPLETE`/`ARCHIVED`. The tool only ever changes `State`;
  it never edits the `Blocker:` list (preserve, never prune). A `CANCELLED` blocker
  counts as *unsatisfied*, holding the task in `BLOCKED`.
- **Why:** The `to-tasks` skill decomposes specs into dependency-linked tasks, so
  most boards are dominated by dependency-gated BLOCKED items (the
  `computer_dashboard` board was 17 of 18). Making dependencies a parseable field
  lets the tool notice when a task becomes workable, instead of a human hand-walking
  the graph on every completion. Alternatives passed over: (1) leaving `Blocked by:`
  as free-text prose — not machine-actionable; (2) *pruning* satisfied blockers from
  the list — rejected because it erases the dependency history and, worse, lets a
  *cancelled* dependency vanish silently; (3) treating CANCELLED as satisfied —
  rejected because "abandoned" is not "built," and auto-advancing a task past a
  scrapped prerequisite hides a real gap. Preserve + CANCELLED-blocks fails toward
  visible-and-stuck, which is the safe direction.
- **Consequences:** Reverses the earlier "TUI is a pure viewer" stance — the tool
  now has a second write path (BLOCKED→TODO) beyond the archive sweep, so a
  read-mostly viewer mutates task state, which is surprising without this record.
  The `Blocker:` list is permanent history, so a `TODO` task may legitimately carry
  a non-empty list — `State`, not the list, carries workability. The parser must
  resolve cross-project references (walk to another board), coupling the sweep to
  repo-wide discovery. The tool never judges completion — it only *releases* blocks
  once prerequisites are provably done; all other transitions remain agent-judged,
  so "no enforced state machine" still holds for everything except this one
  mechanical release.

## 001 — TUI built in Rust with ratatui
- **Date:** 2026-07-26
- **Status:** accepted
- **Decision:** Build the `task_tracker` TUI as a Rust crate using the `ratatui`
  library, wired up as a per-project Nix dev shell (`flake.nix` + `.envrc`) per
  repo convention.
- **Why:** Preference — it is the stack Matthew wants to build with — reinforced
  by fit with the repo (existing Rust apps: `telemetry_rust`, `algo_trader_rust`)
  and the Nix-first workflow. The realistic alternative was Python + Textual,
  which would have been faster to prototype and easier for quick edits, but adds
  a runtime and cuts against the desire to work in Rust here.
- **Consequences:** Stronger performance and a single static binary; parsing of
  `TRACKER.md` and the lazy sweep are written in Rust. Cost: more upfront effort
  than a Python TUI, and the choice is hard to reverse once the crate exists.
  Note the tool is now read-only plus the launch sweep; if interactive editing is
  added later, the write path lands in this same Rust codebase. *(Superseded in
  part by ADR-002: the tool gained a second launch-time write path — the unblock
  sweep — so it is no longer read-only-plus-archive-sweep.)*
