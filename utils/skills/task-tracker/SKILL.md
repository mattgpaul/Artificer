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
- Move to **IN PROGRESS** when actively working it; **BLOCKED** when it cannot
  proceed (put the reason / blocker in the Description).
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

## Do / Don't
- DO edit `TRACKER.md` directly; DO keep the exact field order and record
  boundary.
- DO set `CANCELLED` rather than deleting an abandoned task.
- DO stamp `Completed:` / `Cancelled:` (ISO 8601 UTC) the moment a task turns
  terminal.
- DON'T reuse IDs. DON'T repeat the project name in titles. DON'T hand-set
  `ARCHIVED` or remove a `Completed:` timestamp. DON'T create a central/shared
  board.
