# task_tracker — Specification

## Problem Statement
Matthew runs many projects in the Artificer monorepo, and agents are the primary
people filing and updating work. Tasks for each project need to live *with* that
project (source of truth stays local and agent-writable), but there is no single
place to see all open work across every project at a glance. Without that, the
architect can't answer "what is in flight, everywhere?" without opening each
project by hand, and cross-project dependencies between tasks are invisible.

## Solution
Each project owns a `TRACKER.md` board in its own directory, written by hand by
Matthew and agents in a strict, line-oriented, agent-first format defined by the
`task-tracker` skill and its template (no CLI, no central store). The
`task_tracker` tool is a Rust + ratatui TUI that, on launch, walks the repo,
discovers every `TRACKER.md`, and presents a **consolidated view**: a left panel
listing every project that has a board, and a Jira-style board of state columns
(TODO, IN PROGRESS, BLOCKED, COMPLETE) for the selected project, navigated with
vim keys. It is a near-pure viewer whose only writes are two deterministic,
mechanical launch-time sweeps: an **archive sweep** (COMPLETE → ARCHIVED at sprint
boundaries) and an **unblock sweep** (BLOCKED → TODO once a task's named blocker
tickets are all done). The architect gets one screen for all open work; agents get
a format simple enough to write by hand and a tool that keeps dependency status
honest without judging whether work is finished.

## Glossary
| Term | Meaning |
|------|---------|
| TRACKER.md | Per-project board file living in that project's directory; the source of truth for that project's tasks/issues. |
| Consolidated view | The TUI's aggregated display of tasks gathered from all projects' TRACKER.md files. |
| Task | A single tracked item within a project. Fields: Title, ID, State, Blocker, (Completed/Cancelled timestamp when terminal), Description. |
| State | One of TODO, IN PROGRESS, BLOCKED, COMPLETE, ARCHIVED, CANCELLED. |
| Sprint | A repo-wide 2-week period; boundary is 00:00 on every second Monday. At each boundary, COMPLETE tasks are swept to ARCHIVED across all projects. |

## User Stories
1. As an agent, I want to file a task on a project's `TRACKER.md` by writing a
   plain line-oriented block, so that I can record work without building or
   invoking any CLI.
2. As an agent, I want the task format to be strict and uniform (fixed field
   order), so that every board stays trivially parseable by the tool and by other
   agents.
3. As an agent, I want each new task to start in TODO with an ID of
   `max(existing) + 1`, so that IDs are unique, stable pointers and I never have
   to consult a central counter.
4. As an agent, I want to write a verbose, multi-line Description (including lines
   that start with `#`), so that I can capture full detail without escaping
   anything or breaking the parser.
5. As an agent, I want to move a task to IN PROGRESS or BLOCKED as work state
   changes, so that the board reflects reality.
6. As an agent, I want to mark a task COMPLETE with a `Completed:` ISO 8601 UTC
   timestamp, so that the archive sweep can later retire it deterministically.
7. As an agent, I want to CANCEL an abandoned task with a `Cancelled:` timestamp
   rather than deleting it, so that "created then thrown away" stays
   distinguishable from "built and implemented."
8. As an agent, I want to express a dependency with a first-class `Blocker:`
   field (a bare ID for a sibling task, or `path:id` for a task on another
   project's board), so that dependencies are machine-parseable rather than buried
   in prose.
9. As an agent, I want every task to always carry a `Blocker:` line (`Blocker:
   None` when there is no dependency), so that fields are uniform and the board is
   agent-first to parse.
10. As an agent, I want a task to be BLOCKED only when it points at a real
    dependency ticket, so that the BLOCKED column always references a concrete,
    go-look-at-it thing (waiting on hardware/vendor/a decision with no ticket
    stays TODO).
11. As Matthew (the architect), I want to launch one tool and see every project
    that currently has a `TRACKER.md` listed in a left panel, so that I know the
    full set of active boards without hunting through directories.
12. As Matthew, I want the tool to discover boards by walking the repo (any
    directory containing a `TRACKER.md` is a project, identified by its path
    relative to the repo root), so that no registration step is required.
13. As Matthew, I want the walk to skip VCS/build noise (`.git`, `.jj`,
    `node_modules`, Nix results), so that discovery is fast and only surfaces real
    boards.
14. As Matthew, I want to select a project on the left and see a Jira-style board
    of its tasks on the right, so that I can focus on one project's work at a
    time.
15. As Matthew, I want the board to render exactly four columns — TODO, IN
    PROGRESS, BLOCKED, COMPLETE — so that I see only actionable/visible work and
    never ARCHIVED or CANCELLED clutter.
16. As Matthew, I want each card to show Title, ID, and a Description truncated to
    the card's bounds, so that columns stay scannable and nothing overflows.
17. As Matthew, I want to navigate entirely with vim keys — h/l across columns,
    j/k through tickets, project highlight on the left switching the board — so
    that the tool feels native to how I already work.
18. As Matthew, I want a column to scroll when it holds more tickets than fit on
    screen, so that no work is hidden by a full column.
19. As Matthew, I want the tool, on launch, to move each COMPLETE task whose
    `Completed:` timestamp falls in an already-ended sprint to ARCHIVED, so that
    finished work retires automatically at sprint boundaries while
    freshly-completed work stays visible in the current sprint.
20. As Matthew, I want the archive sweep to be lazy and stateless (sprint
    boundaries computed deterministically, no persisted "last swept" marker), so
    that the tool needs no state file and always self-corrects.
21. As an agent, I want a BLOCKED task to be auto-released to TODO on launch once
    **every** ticket in its `Blocker:` list is COMPLETE or ARCHIVED, so that a
    now-workable task surfaces in the TODO column without manual intervention.
22. As an agent, I want the unblock sweep to resolve both internal (`5`) and
    cross-project (`apps/foo:5`) blocker references by walking to the referenced
    board and reading that ticket's state, so that dependencies across projects
    are honored, not just within one board.
23. As an agent, I want the tool to NEVER mutate the `Blocker:` list (only flip
    `State`), so that the dependency edges remain a permanent record even after a
    task moves to TODO.
24. As Matthew, I want a task whose blocker is CANCELLED to stay BLOCKED (a
    cancelled blocker does not satisfy the dependency), so that the task is
    visibly stuck on an abandoned ticket and I know to intervene.
25. As Matthew, I want the two sweeps to be the tool's only writes and to be
    purely mechanical (never judging whether work is "done"), so that the tool
    stays a trustworthy viewer and all real state transitions remain
    agent/architect-judged.
26. As an agent, I want a canonical `TRACKER.md` template and the `task-tracker`
    skill to define the format, states, lifecycle, and sweeps, so that I can
    create and maintain boards correctly by following one source.

## Implementation Decisions
- **Stack & packaging.** The tool is a single Rust crate using `ratatui` for the
  TUI, wired as a per-project Nix dev shell (`flake.nix` + `.envrc`) per repo
  convention. See ADR-001. Creating the Nix dev-shell files is a build task (the
  design defers it to implementation), copying the existing Rust precedent in the
  repo (`apps/telemetry_tdd_qwen`: flake-utils + `rustc/cargo/clippy/rustfmt`,
  `.envrc` = `use flake`).
- **`TRACKER.md` format & parse contract (the shared contract the tool reads).**
  Each task is a line-oriented block in this exact field order — a prototype
  snippet is inlined here because the field grammar *is* the contract:
  ```
  # <Title>
  ID: <integer>
  State: <TODO|IN PROGRESS|BLOCKED|COMPLETE|CANCELLED|ARCHIVED>
  Blocker: <None | comma-separated refs>
  Completed: <ISO 8601 UTC>      # xor Cancelled:, only on a terminal task
  Description: <verbose, multi-line, runs until the next task header>
  ```
  - **Record boundary:** a new task begins ONLY where a `# ` header is immediately
    followed by an `ID:` line and a `State:` line. A stray `# ...` inside a
    Description is therefore not a new record. This is what lets Description be
    unrestricted (the last field, running until the next valid header).
  - **ID:** integer unique within a board, `max(existing) + 1`, never reused; gaps
    are fine.
  - **Blocker:** always present. `None`, or a comma-separated list of references. A
    bare integer is an internal reference (a ticket ID on the same board); a
    `<repo-relative project path>:<ticket-id>` value (the colon is the
    discriminator) is a cross-project reference naming both the board and the
    ticket. Placed immediately after `State:`, before the terminal-timestamp slot.
  - **Completed: / Cancelled:** ISO 8601 UTC (e.g. `2026-07-26T14:03:00Z`), exactly
    one, only on a terminal task, between `Blocker:` and `Description:`.
- **Discovery.** On launch, walk the repo from the root and collect every
  `TRACKER.md`. A project is any directory containing one; its identity is its path
  relative to the repo root (the same identity used to resolve cross-project
  `Blocker:` references). The walk skips `.git`, `.jj`, `node_modules`, and Nix
  build results. No registration.
- **Consolidated view model.** Discovery + parse produce an in-memory model:
  projects (each identified by repo-relative path) each holding their parsed
  tasks, bucketed by State. This model is what the TUI renders and what tests
  assert against (see Testing Decisions).
- **Archive sweep (write #1).** Lazy, on-launch, stateless. Sprint boundaries are
  computed deterministically (anchor: the first UTC Monday ever; 2-week steps;
  boundary at 00:00 UTC). For each COMPLETE task, parse `Completed:` and rewrite
  its State to ARCHIVED iff that timestamp falls in a sprint that has already
  ended. The `Completed:` timestamp is retained through ARCHIVED. No persisted
  marker; the per-task timestamp is the only input.
- **Unblock sweep (write #2).** Bolted onto the same launch pass. For each BLOCKED
  task, resolve every reference in its `Blocker:` list (internal ID → this board;
  cross-project `path:id` → walk to that board) and read each referenced ticket's
  state. Flip the task BLOCKED → TODO iff **every** referenced blocker is COMPLETE
  or ARCHIVED (order-independent — an already-archived blocker still counts). A
  CANCELLED blocker does NOT satisfy the dependency: the task stays BLOCKED and
  visibly stuck. The tool NEVER mutates the `Blocker:` list — only `State`.
  Consequence: a TODO task may carry a non-empty `Blocker:` list (edges are
  history; State alone carries workability). This is the tool's only enforced
  state transition and it never judges completion — it only *releases* a block once
  named prerequisites are provably done. See ADR-002.
- **TUI.** Left panel lists every discovered project; the rest of the screen is a
  Jira-style board for the selected project with four columns — TODO, IN PROGRESS,
  BLOCKED, COMPLETE (ARCHIVED and CANCELLED are never shown). Cards show Title, ID,
  and Description truncated to the card box. Navigation is hjkl: project highlight
  on the left switches the board; h/l move across columns; j/k move through tickets
  within the focused column; a column scrolls when it overflows. No dependency-edge
  visualization — column placement is the whole signal (the unblock sweep moves a
  task to TODO exactly when it is workable).
- **Skill & template (the write path, out of this crate).** The format, parse
  contract, state lifecycle, discovery/placement rules, and both sweeps are encoded
  for agents in the `task-tracker` skill and its canonical `TRACKER.md` template
  under `utils/skills/`. The tool relies on the same contract but does not own the
  write path (agents write boards by hand).

## Testing Decisions
- **What makes a good test here:** exercise the tool's observable external
  behavior — given real `TRACKER.md` files on disk, does the consolidated view
  model come out right, and do the two sweeps rewrite the files correctly? Do not
  assert on parser internals or ratatui render output.
- **Seam (settled at checkpoint — one high seam):** drive discovery + parse + both
  sweeps together through a single "load the repo root" entry point against
  **temp-directory fixture trees** of `TRACKER.md` files. Assert two things:
  (a) the resulting in-memory consolidated view model (projects, per-column
  cards), and (b) both sweeps' on-disk effects by re-reading the rewritten files
  (archive: COMPLETE → ARCHIVED for an ended sprint; unblock: BLOCKED → TODO when
  all blockers COMPLETE/ARCHIVED, including cross-project `path:id` resolution and
  the CANCELLED-blocker-stays-BLOCKED case). Fixtures are the only setup; the
  filesystem is the seam. This is the highest, fewest-seam choice — the ratatui
  render layer is deliberately not a seam.
- **Cases to cover at that seam:** record-boundary parsing (a `#` line inside a
  Description is not a new task); `Blocker:` grammar (None, internal ID,
  cross-project `path:id`, multiple refs); archive-sweep boundary math (completed
  in current sprint stays visible, completed in an ended sprint archives);
  unblock-sweep resolution (all-done releases, any-incomplete holds, CANCELLED
  blocker holds and stays visibly stuck, order-independence with an
  already-ARCHIVED blocker); discovery skipping VCS/build noise and identifying
  projects by repo-relative path; `Blocker:` list never mutated (a released task
  keeps its edges).
- **Where tests live:** with the crate, per the now-settled repo convention (see
  AGENTS.md). The fixture-driven integration tests — driven against the single
  `load(repo_root)` seam through temp-dir fixture trees — live in the crate's own
  `tests/` directory (compiled against its public API); any unit test sits in-file
  (`#[cfg(test)] mod tests`). The repo-level `tests/` tree is reserved for
  cross-`apps/` end-to-end tests and is not used here. The failing (red) tests are
  written first via `/tdd`.
- **Prior art:** none yet — this is the repo's first fixture-driven integration
  suite. `apps/telemetry_tdd_qwen` is the Rust dev-shell precedent to copy for
  toolchain wiring, not for test layout.

## Out of Scope
- **Interactive task editing in the TUI** — moving/creating/editing tasks by hand
  in the tool. The TUI is a near-pure viewer; the only writes are the two
  mechanical launch-time sweeps. Deliberate future consideration.
- **Dependency-edge visualization in the TUI** — no rendering of `Blocker:` edges,
  no stuck-on-CANCELLED badge. Column placement is the whole signal; revisit only
  if the column proves insufficient in practice.
- **Priority** — no priority field; priority is judged in-the-moment.
- **Pruning CANCELLED (or `Blocker:`) entries** — CANCELLED tasks live in the file
  forever for now; the `Blocker:` list is never pruned. Pruning is left open.
- **A CLI / central store** — explicitly dropped; boards are distributed and
  written by hand via the skill.
- **Persisting the Nix dev-shell files as a design artifact** — creating
  `flake.nix` + `.envrc` is a build task, not part of this spec's decisions.

## Further Notes
- The `task-tracker` skill and template already exist under `utils/skills/` and
  encode the write-side contract; when `Blocker:` field ordering or the unblock
  sweep is implemented in the tool, keep the skill/template in lockstep with the
  parse contract above (field order is now header → ID → State → Blocker →
  [Completed:/Cancelled:] → Description).
- ADR-001 (Rust + ratatui) and ADR-002 (tool auto-resolves dependencies via the
  unblock sweep) are the load-bearing decisions behind, respectively, the stack
  and the one enforced state transition; consult them before reworking either.
