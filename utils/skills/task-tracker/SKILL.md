---
name: task-tracker
description: Create and update tasks/issues on a project's TRACKER.md board. Use when the user or an agent wants to file a task/issue for a project, mark work started/blocked/done, cancel a task, start a board for a project, or otherwise change what is tracked. Each project owns its own TRACKER.md; this skill defines the format and lifecycle so every board stays parseable by the task_tracker TUI.
---

# task-tracker
The objective is to record and update tasks on a project's board (`TRACKER.md`)
in a strict, agent-first format so the `task_tracker` TUI can consolidate every
project's board into one view. Boards are the source of truth; there is no CLI —
you edit `TRACKER.md` directly, and this skill is what keeps every board honest.
Correctness of the format matters more than speed: a malformed block corrupts the
board for the TUI and for other agents.

## On invocation
1. Determine the project you are working in — normally the current working
   directory (or the nearest ancestor that is a project). The board is
   `TRACKER.md` in that project's root.
2. Read the existing `TRACKER.md` if present. If it does not exist and you are
   creating the first task, copy the template from
   `utils/skills/task-tracker/templates/TRACKER.md` and remove the example task.
3. Make the change (create / change state / cancel) following the Format and
   Lifecycle rules below.
4. Re-read your edit and confirm it still parses: every task is a `# ` header
   immediately followed by `ID:` and `State:` lines.
5. Tell the user which board you touched, the task ID, and the new state.

## The board: TRACKER.md
- One `TRACKER.md` per project, living in that project's root directory. It is
  the source of truth for that project's tasks. Do NOT create a central board.
- The `task_tracker` TUI discovers boards by walking the repo for `TRACKER.md`
  files. Only place a board where it genuinely belongs — placement is on you.

## Format (agent-first, line-oriented)
Each task is a block, in this exact field order:

```
# <Title>
ID: <integer>
State: <STATE>
Blocker: <None | comma-separated refs>
Completed: <ISO 8601 UTC>      # only on COMPLETE/ARCHIVED tasks
Description: <detail, may be verbose / multi-line>
```
(A cancelled task uses `Cancelled: <ISO 8601 UTC>` in place of the `Completed:`
line. Non-terminal tasks — TODO / IN PROGRESS / BLOCKED — have neither line.)

- **Record boundary:** a new task begins ONLY where a `# ` header is immediately
  followed by an `ID:` line and a `State:` line. This means a stray line starting
  with `# ` *inside* a Description (a shell/Nix/Python comment, a markdown
  sub-heading) is NOT a new task — it stays part of the Description. Rely on this;
  do not escape `#` in descriptions.
- **Title:** brief summary, on the `# ` header line. Do not repeat the project
  name — the board's location already implies the project.
- **ID:** integer unique within this file, assigned as `max(existing IDs) + 1`.
  Never reuse an ID, even one belonging to a CANCELLED/ARCHIVED task. Gaps are
  fine — the ID is just a stable pointer.
- **Blocker:** a first-class, machine-parsed dependency field — the tool follows
  it to find now-unblockable tasks, so keep the grammar exact. **Always present**,
  on every task in every state. Value is `None`, or a comma-separated list of
  references, e.g. `Blocker: 1, 5`. A reference is either:
  - a **bare integer** = a ticket ID on *this* board (`Blocker: 5`), or
  - a **cross-project ref** `<repo-relative project path>:<ticket-id>` when the
    blocker lives on another project's board (`Blocker: apps/computer_dashboard:5`).
    The colon is what distinguishes a cross-project ref from a bare internal ID.

  A task is `BLOCKED` **iff** it has at least one *unsatisfied* blocker — a
  referenced ticket that is not yet `COMPLETE`/`ARCHIVED` (a `CANCELLED` blocker
  counts as unsatisfied, so it keeps the task blocked); and a task may only be
  `BLOCKED` if its `Blocker:` names a real ticket. A blocker with no
  ticket on any board (waiting on hardware, on a person, on a vendor) does NOT
  make a task BLOCKED — leave it `TODO` (with the caveat in Description) or give
  the blocker its own ticket and point at it. Place `Blocker:` on its own line
  directly after `State:`.
- **Completed: / Cancelled:** ISO 8601 UTC timestamp, e.g. `2026-07-26T14:03:00Z`.
  Set `Completed:` at the moment you move a task to COMPLETE and keep it when the
  sweep later moves it to ARCHIVED. Set `Cancelled:` at the moment you cancel a
  task. Only ever one of the two, only on a terminal task. Place it on its own
  line between `State:` and `Description:`.
- **Description:** as long as needed; runs until the next task header. No length
  or line-break restriction. Keep it the LAST field so this rule holds.
- Leave one blank line between tasks for legibility.

## Lifecycle (states)
Valid states: `TODO` `IN PROGRESS` `BLOCKED` `COMPLETE` `CANCELLED` `ARCHIVED`.

- Every new task starts at **TODO**.
- Move to **IN PROGRESS** when actively working it; **BLOCKED** when it is waiting
  on another ticket — set `State: BLOCKED` and name the blocking ticket(s) in the
  `Blocker:` field (never in prose). Do NOT prune the `Blocker:` list as blockers
  finish — it is a permanent record of the edges. The TUI's launch unblock sweep
  flips a `BLOCKED` task back to `TODO` on its own once every listed blocker is
  `COMPLETE`/`ARCHIVED`, leaving the list intact (so a `TODO` task may legitimately
  still carry a non-empty `Blocker:` list — `State` is what carries workability).
  A blocker that is `CANCELLED` does NOT satisfy the dependency: the task stays
  `BLOCKED` until a human/agent re-scopes it, cancels it, or clears that blocker by
  hand.
- Move to **COMPLETE** when the work satisfies what the task's own Description
  defines as done. There is no enforced state machine — judge transitions against
  the task's description. **Add a `Completed:` timestamp (ISO 8601 UTC) at this
  moment** — the sweep depends on it.
- **CANCELLED** = created then abandoned (never implemented). Set this instead of
  deleting the task, and **add a `Cancelled:` timestamp (ISO 8601 UTC)**. Cancelled
  tasks stay in the file but are hidden from the TUI. This preserves the
  distinction between "built it" and "threw it away."
- **ARCHIVED** is not set by hand during normal work — it is the swept-away state
  for completed tasks (see Sprint sweep). Only COMPLETE tasks become ARCHIVED.

## Sprint sweep
- A sprint is a repo-wide 2-week cycle; the boundary is 00:00 UTC on every second
  Monday (anchored to the first UTC Monday ever, stepping 2 weeks at a time).
- The sweep is lazy and stateless: on launch, the TUI moves a `COMPLETE` task to
  `ARCHIVED` iff its `Completed:` timestamp falls in a sprint that has already
  ended. A task completed in the current sprint stays visible. No global "last
  swept" state is stored — the per-task timestamp is the only input.
- As an agent, do not pre-emptively ARCHIVE tasks and do not remove the
  `Completed:` timestamp. Mark work `COMPLETE` with its timestamp and let the
  sweep move it.

## Unblock sweep
- On the same launch pass, the TUI runs an unblock sweep. For each `BLOCKED` task
  it resolves every reference in `Blocker:` (internal ID on this board, or a
  cross-project `path:id` on another board) and flips the task `BLOCKED → TODO`
  iff every referenced blocker is `COMPLETE`/`ARCHIVED`. A `CANCELLED` blocker
  does not count as satisfied, so the task stays `BLOCKED`.
- The sweep only ever changes `State`; it never edits the `Blocker:` list. Keep
  the list accurate at creation and leave it — it is the permanent edge record and
  the tool depends on it to compute workability.

## Do / Don't
- DO edit `TRACKER.md` directly; DO keep the exact field order and record
  boundary.
- DO give every task a `Blocker:` line (`None` when nothing blocks it); DO encode
  dependencies there, never as `Blocked by:` prose in the Description.
- DO set `CANCELLED` rather than deleting an abandoned task.
- DO stamp `Completed:` / `Cancelled:` (ISO 8601 UTC) the moment a task turns
  terminal.
- DON'T reuse IDs. DON'T repeat the project name in titles. DON'T hand-set
  `ARCHIVED` or remove a `Completed:` timestamp. DON'T create a central/shared
  board.
