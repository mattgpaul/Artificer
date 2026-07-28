<!--
DESIGN.md — running design document for this project.
Filled out during an /architect session. Human- and agent-readable.
Keep entries short: what was decided, and a line on why.
-->

# task_tracker — Design

## Overview
A local-only task/issue tracker for the Artificer monorepo. Each project owns a
`TRACKER.md` board in its own directory; agents are the primary writers. The
`task_tracker` tool consolidates every project's `TRACKER.md` into one TUI so the
architect can see all open work at a glance. Agent functionality is the priority;
the TUI is secondary.

## Glossary
| Term | Meaning |
|------|---------|
| TRACKER.md | Per-project board file living in that project's directory; the source of truth for that project's tasks/issues. |
| Consolidated view | The TUI's aggregated display of tasks gathered from all projects' TRACKER.md files. |
| Task | A single tracked item within a project. Fields: Title, ID, State, (Completed/Cancelled timestamp when terminal), Description. |
| State | One of TODO, IN PROGRESS, BLOCKED, COMPLETE, ARCHIVED, CANCELLED. |
| Sprint | A repo-wide 2-week period; boundary is 00:00 on every second Monday. At each boundary, COMPLETE tasks are swept to ARCHIVED across all projects. |

## Decisions
- **Name is `task_tracker`; lives at `apps/task_tracker/`** — deployable tool, follows repo `apps/` convention.
- **Distributed source of truth: one `TRACKER.md` per project directory** — each project manages its own board; the tool consolidates rather than owning a central store.
- **~~Writes go through a CLI~~ (SUPERSEDED)** — originally a CLI was to enforce the format. Dropped: a CLI adds build/ship/maintain friction for no real gain in a personal lab. Replaced by a **template + a skill** (below).
- **Format contract lives in a template + a skill, not a binary** — a canonical `TRACKER.md` template plus a `task-tracker` skill under `utils/skills/` encode the format, states, and lifecycle. Matthew and agents follow the skill to write boards by hand. Enforcement is social/skill-based, consistent with the discovery decision. The TUI still relies on the same parse contract.
- **Task fields: Title, ID, State, (Completed/Cancelled timestamp), Description** — project is implied by which TRACKER.md the task lives in, so it is not repeated on the task. ID is a per-project integer incrementing from 1. Title is a brief summary; Description carries as much detail as needed. The terminal timestamp is present only once a task is COMPLETE/ARCHIVED (`Completed:`) or CANCELLED (`Cancelled:`).
- **States: TODO → (IN PROGRESS, BLOCKED, COMPLETE, CANCELLED, ARCHIVED)** — every task starts in TODO. Transitions are decided by the agent (or architect) working it, judged against what the task's own Description defines as "complete." No enforced state machine.
- **No priority field** — priority is judged in-the-moment by Matthew and the agents, not stored. Rationale: fixed priority levels are meaningless when everything is effectively high priority.
- **IDs are just unique pointers; gaps are fine** — an ID's only job is to reference one ticket unambiguously. Next ID = `max(existing) + 1`; no persisted counter. The only hard rule is no *reuse* of a live number. Archived tasks stay in TRACKER.md (hidden from TUI), so max+1 holds today. (If CANCELLED pruning is ever added, revisit to ensure numbers still aren't reused.)
- **Terminal states distinguish outcome** — `ARCHIVED` holds only tasks that were `COMPLETE` (swept in at each 2-week sprint boundary); `CANCELLED` is its own category for tasks created then abandoned. Both are hidden from the TUI. This lets Matthew and agents tell "built and implemented" from "created then thrown away."
- **CANCELLED lives forever for now, but pruning is left open** — we may later prune CANCELLED entries from TRACKER.md to keep it lean.
- **Tasks carry a terminal timestamp** — a task gets a `Completed:` timestamp when it reaches COMPLETE (retained through ARCHIVED) or a `Cancelled:` timestamp when cancelled. ISO 8601 UTC (e.g. `2026-07-26T14:03:00Z`). Sits between `State:` and `Description:` so the record boundary and last-field-Description rule are unchanged. Only ever one of the two is present.
- **Unblock sweep — the tool auto-releases satisfied dependencies (the `Blocker:` field earns its keep).** Bolted onto the same launch pass as the archive sweep. For each `BLOCKED` task, the tool resolves every reference in its `Blocker:` list (internal ID → this board; cross-project `path:id` → walk to that board) and reads each referenced ticket's state. It flips the task `BLOCKED → TODO` **iff every** referenced blocker is `COMPLETE` **or** `ARCHIVED` (a completed blocker already swept to ARCHIVED still counts as done — order-independent).
  - **Preserve, never prune.** The tool NEVER mutates the `Blocker:` list — it is the permanent record of the dependency edges. It only flips `State`. Consequence: a `TODO` task may carry a non-empty `Blocker:` list (the edges are history, not live status); `State` alone carries workability. This was chosen over pruning specifically so a *cancelled* dependency can't vanish silently.
  - **CANCELLED = unsatisfied.** A blocker in `CANCELLED` does NOT satisfy the dependency — "abandoned" is not "built." The dependent stays `BLOCKED`, now *visibly* stuck on a cancelled ticket (the preserved reference shows why), which is the signal for Matthew or an agent to intervene: re-scope the dependent, cancel it too, or clear the blocker by hand. The tool does not auto-resolve this — it deliberately fails toward visible-and-stuck.
  - **This is the only tool-enforced state transition.** It does not contradict "no enforced state machine": the tool never auto-completes or auto-blocks and never judges completion — it only *releases* a block once the named prerequisites are provably done. Every other transition stays agent/architect-judged. See ADR-002.
- **No dependency visualization in the TUI — column placement is the whole signal.** The BLOCKED vs TODO column is enough: the unblock sweep moves a task to TODO exactly when it is workable, so "which column it's in" already answers "can I work it." The TUI does not render `Blocker:` edges or a stuck-on-CANCELLED badge for now. Revisit only if the column proves insufficient in practice.
- **Sweep is lazy, on launch, and stateless** — no persisted marker. Sprint boundaries are computed deterministically (anchor: the first UTC Monday ever; 2-week steps; boundary at 00:00 UTC). On launch, for each COMPLETE task the tool parses `Completed:` and archives it iff that timestamp falls in a sprint that has already ended. Because the decision is per-task from its own timestamp, no global state is needed and freshly-completed tasks in the current sprint stay visible.

- **TRACKER.md format is agent-first and line-oriented** — human reading is the TUI's job. Each task is a block led by a markdown header, cheap for agents to scan:
  ```
  # <Title>
  ID: <num>
  State: <state>
  Description: <description, may be verbose / multi-line>
  ```
  The `# ` header is the record separator, so Description has no length/line-break restriction — it runs until the next task header. Tasks separated by a blank line for legibility.
- **Record-boundary parse contract** — a new task begins only where a `# ` header is *immediately followed by an `ID:` line and a `State:` line*. A stray `# ...` inside a verbose Description is therefore not mistaken for a new task (important in this shell/Nix/Python-heavy repo). Keeps descriptions unrestricted.
- **Ship a template TRACKER.md, living with the skill** — canonical example at `utils/skills/task-tracker/templates/TRACKER.md` (not with the app — it is skill material, agents reference it to create boards).
- **`task-tracker` skill created at `utils/skills/task-tracker/SKILL.md`** — encodes the format, record-boundary parse contract, state lifecycle, discovery/placement rules, and sprint-sweep behavior for agents.
- **TUI is a near-pure viewer with exactly two permitted writes, both launch-time sweeps** — it otherwise only reads and displays boards. The two writes are (1) the archive sweep (COMPLETE → ARCHIVED) and (2) the unblock sweep (BLOCKED → TODO when dependencies are satisfied; see below). Both are *mechanical* — they resolve deterministic rules, never judge whether work is "done." Interactive task editing (moving tasks around by hand) remains a deliberate future consideration, not built now.
- **TUI owns the lazy sweep** — with no CLI, the TUI is the only program that launches, so it performs the on-launch catch-up sweep.
- **TUI layout: left project list + right Jira-style board** — left panel lists every project that currently has a `TRACKER.md`; the rest of the screen (to the right edge) is a Jira-style board of state columns for the selected project.
- **Board renders 4 columns: TODO, IN PROGRESS, BLOCKED, COMPLETE** — the visible (non-hidden) states. ARCHIVED and CANCELLED are never shown. COMPLETE stays visible until the sweep moves it to ARCHIVED.
- **Cards show Title, ID, and truncated Description** — Description is clipped to the bounds of the card box (no overflow).
- **Navigation: hjkl (vim-native)** — highlighting a project on the left switches the right board to that project's tracker. h/l move across columns, j/k move through tickets within the focused column, and a column scrolls when it holds more tickets than fit on screen.
- **Stack: Rust + ratatui** — chosen by preference (what Matthew wants to build with); consistent with existing Rust apps in the repo. Wired as a per-project Nix dev shell (`flake.nix` + `.envrc`) per repo convention. See ADR-001.

- **Discovery by repo walk** — the tool walks the repo and collects every `TRACKER.md`; a "project" is simply any directory containing one, and its identity is its path relative to the repo root. No registration (keeps it agent-first). The walk skips VCS/build noise (`.git`, `.jj`, `node_modules`, Nix results). Enforcement against misplaced boards is social (Matthew + agents), not built in.

- **BLOCKED has exactly one meaning: "gated by a named dependency ticket."** The old "externally stuck vs. waiting on a sibling task" split is dissolved — both are just dependencies, distinguished only by *which board the blocker lives on*. A BLOCKED task renders as a normal ticket (Title, ID, Description) and always carries a dependency pointer (the `Blocker:` field — grammar below). The pointer is *internal* by default (a sibling task's ID on the same board); when the blocker lives in another project, it references *that project's TRACKER* (project path + ticket). Resolves the overloading raised by `to-tasks`.
- **BLOCKED requires a real ticket to point at — no ticket, no BLOCKED.** A blocker with no ticket on any board (waiting on hardware to arrive, on Matthew to make a call, on an upstream vendor) does *not* make a task BLOCKED — it stays TODO, with the caveat in its Description if it matters. Either the blocker gets a ticket (on the relevant project's board) and the task points at it, or the task is simply TODO. This keeps the BLOCKED column honest: every card in it references a concrete, go-look-at-it thing.
- **Dependencies are a first-class parseable `Blocker:` field, not free-text prose.** Replaces the `to-tasks` skill's `Blocked by:` line buried in Description. Because the field is machine-parsed, the tool can follow it to find now-unblockable tasks. Grammar:
  - **Always present.** Every task carries a `Blocker:` line; a task with no dependency reads `Blocker: None`. Uniform fields keep the board agent-first and trivially parseable.
  - **Placement:** in field order immediately after `State:` (before the `Completed:/Cancelled:` slot and `Description:`). A `Blocker:` and a terminal timestamp can both appear on the same task (e.g. a COMPLETE task keeps `Blocker: None`), so the order is header → ID → State → Blocker → [Completed:/Cancelled:] → Description.
  - **Value:** `None`, or a comma-separated list of references — `Blocker: 1, 5`.
  - **Internal reference:** a bare integer = a ticket ID on *this* board (`Blocker: 5`).
  - **Cross-project reference:** `<repo-relative project path>:<ticket-id>` (`Blocker: apps/computer_dashboard:5`). The colon distinguishes a cross-project ref from a bare internal ID; the path is the project's identity from repo root (same identity discovery uses), naming both which board and which ticket so the tool can walk to it and read its state.

## Open Questions
_(none open)_

## Deferred to Implementation
- **Nix dev shell — approach is settled, files are a build task.** No design decision remains: AGENTS.md already mandates the convention (a per-project `flake.nix` + `.envrc` that direnv auto-loads), and the repo has a Rust precedent to copy in `apps/telemetry_tdd_qwen` (flake-utils + `rustc/cargo/clippy/rustfmt`, `.envrc` = `use flake`). Actually creating those files is implementation, not architecture — it belongs to the first build task, not this doc.
- **Testing convention — now settled repo-wide (see AGENTS.md).** When first drafted this was open (`tests/` was empty and the repo young); the convention has since been decided: tests live *with* the crate — Rust integration tests in the crate's own `tests/`, unit tests in-file — while the repo-level `tests/` tree is reserved for cross-`apps/` end-to-end tests. task_tracker's fixture-driven integration tests (against the `load(repo_root)` seam) therefore live in its crate `tests/`. (Earlier draft guessed a central `tests/system/task_tracker/`; withdrawn.)
