<!--
TRACKER.md — this project's task/issue board. Source of truth for THIS project.
Copy this template into a project directory to start its board.

FORMAT (agent-first, line-oriented — see the `task-tracker` skill for full rules):
  - Each task is a block led by a `# <Title>` header.
  - A new task begins ONLY where a `# ` header is immediately followed by an
    `ID:` line and a `State:` line. A stray `# ...` inside a Description is
    therefore NOT a new task.
  - Fields, in order: header (Title), ID, State, Blocker, [Completed:/Cancelled:], Description.
  - ID: integer unique within THIS file, never reused. Next ID = max(existing)+1.
    Gaps are fine.
  - State: one of TODO | IN PROGRESS | BLOCKED | COMPLETE | CANCELLED | ARCHIVED.
    New tasks start at TODO.
  - Blocker: ALWAYS present. `None`, or a comma-separated list of dependency refs.
    A ref is a bare integer (a ticket on THIS board, e.g. `5`) or a cross-project
    ref `<repo-relative project path>:<ticket-id>` (e.g. `apps/computer_dashboard:5`).
    A task is BLOCKED iff it has a live blocker; encode dependencies here, never as
    prose in the Description.
  - Completed: / Cancelled: ISO 8601 UTC timestamp (e.g. 2026-07-26T14:03:00Z).
    Add `Completed:` when a task reaches COMPLETE (keep it through ARCHIVED); add
    `Cancelled:` when a task is CANCELLED. Only one is ever present, and only on a
    terminal task. Omit for TODO / IN PROGRESS / BLOCKED.
  - Description: may be as long / multi-line as needed. Runs until the next task
    header, so it stays the LAST field.
  - Leave a blank line between tasks for legibility.
  - CANCELLED and ARCHIVED tasks stay in this file but are hidden from the TUI.
Delete this comment block once real tasks exist, or keep it as a reminder.
-->

# Example: replace me with a real task title
ID: 1
State: TODO
Blocker: None
Description: One block per task. Keep the header short; put the detail here. This
line can wrap across as many lines as you need — the block runs until the next
`# ` header that is followed by ID/State lines.

# Example of a task waiting on another ticket
ID: 2
State: BLOCKED
Blocker: 1
Description: This task is gated by ticket 1 on this board. When 1 reaches
COMPLETE, move this back to TODO and reset `Blocker: None`. A cross-project
dependency would read e.g. `Blocker: apps/computer_dashboard:5`.

# Example of a finished task (note the Completed timestamp)
ID: 3
State: COMPLETE
Blocker: None
Completed: 2026-07-26T14:03:00Z
Description: A terminal task carries its timestamp between State and Description.
The launch sweep uses this to decide when to move it to ARCHIVED.
