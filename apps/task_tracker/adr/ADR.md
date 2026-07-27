<!--
ADR.md — Architecture Decision Record.
A log of the *major* decisions only (hard to reverse, surprising without
context, or a real trade-off). Use sparingly. Newest entry first.
Each entry: what was decided, and the description/reasoning behind it.
-->

# Architecture Decision Record

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
  added later, the write path lands in this same Rust codebase.
