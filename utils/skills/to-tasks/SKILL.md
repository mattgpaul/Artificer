---
name: to-tasks
description: "Explicit command only (/to-tasks). Do not auto-invoke. Reads a settled SPEC.md and decomposes it into TRACKER.md tasks via the task-tracker format. No re-design."
---

# to-tasks
The objective is to turn a settled `SPEC.md` into a set of `TRACKER.md` tasks —
narrow, ordered, individually verifiable slices of the work the spec describes.
Do NOT re-design here: `/architect` walked the design tree and `/to-spec` already
synthesized every decision into the spec. Your job is *decomposition*, not
design. You take what the spec settled and cut it into tasks. If a decision the
tasks need is missing, that is a gap to surface — not a blank for you to fill on
the user's behalf. New design belongs back in `/architect`; new spec text back in
`/to-spec`.

## Where this sits in the pipeline
`/architect` → `DESIGN.md` → `/to-spec` → `SPEC.md` → **`/to-tasks` →
`TRACKER.md` tasks**.

`to-tasks` is the decomposition hop. It does not invent the board format — the
`task-tracker` skill (`utils/skills/task-tracker/SKILL.md`) stays the authority on
`TRACKER.md` mechanics: fields, record boundary, IDs, states, timestamps, the
sprint sweep. `to-tasks` decides *what the tasks are and how they depend on each
other*, then writes them in that format. When in doubt about board mechanics,
defer to `task-tracker`.

## On invocation
1. Find `SPEC.md` — in the current directory, or a directory the user names. If
   none exists, stop and point the user at `/to-spec`: there is nothing to
   decompose, and tasks must not be invented from scratch here.
2. Read `SPEC.md` in full, plus any ADRs in the project's `adr/` folder. Briefly
   explore the relevant code area so task titles and descriptions speak in the
   spec's Glossary vocabulary and respect the current state of the code — reuse
   existing modules and patterns rather than proposing new ones where suitable
   ones already exist. Look for prefactoring that would make later slices easier:
   *make the change easy, then make the easy change.*
3. Draft the task breakdown per the **Decomposition doctrine** below, and work out
   each task's blocking edges (**Expressing dependencies** below).
4. **Checkpoint with the user.** Present the proposed breakdown as a numbered
   list — for each task: its title, what it delivers end-to-end, and what it is
   blocked by. Ask whether the granularity is right (too coarse / too fine),
   whether the blocking edges are correct, and whether any task should be merged
   or split. Iterate until the user approves. This is the one interaction point —
   everything else is decomposition. Do NOT file anything before approval.
5. File the approved tasks to the project's `TRACKER.md`, following the
   `task-tracker` format and the BLOCKED-edge rule below.
6. Tell the user which board you touched and the task IDs you assigned.

## Decomposition doctrine
Break the work into **tracer-bullet** tasks. A tracer bullet is a round that
glows so you can see where it lands and adjust — a tracer-bullet task builds a
thin but *complete* path all the way through the system, doing only a sliver of
functionality, but a working, observable one.

<vertical-slice-rules>
- Each task is a **vertical slice**: it cuts a narrow but COMPLETE path through
  every layer it touches (e.g. schema → logic → API → UI), NOT a **horizontal
  slice** of one whole layer across all features. A vertical slice is demoable or
  verifiable on its own (one narrow feature working end-to-end); a horizontal
  slice (a whole layer built across every feature) is real work but cannot be run
  or checked alone. Prefer vertical.
- A completed task is demoable or verifiable by itself.
- Each task is sized to fit in a single fresh context window.
- Any prefactoring is its own task, sequenced first.
</vertical-slice-rules>

**Wide refactors are the exception to vertical slicing.** A **wide refactor** is
one mechanical change — rename a shared field, retype a symbol — whose **blast
radius** fans across the whole codebase, so a single edit breaks hundreds of call
sites at once and no vertical slice can land with tests green. Don't force it into
a tracer bullet; sequence it as **expand → migrate → contract**:
- **Expand** — add the new form beside the old so nothing breaks (its own task).
- **Migrate** — move the call sites over in batches sized by blast radius (per
  package, per directory), each batch its own task blocked by the expand, kept
  green because the old form still exists.
- **Contract** — delete the old form once no caller remains, in a task blocked by
  every migrate batch.

Watch for wide-refactor candidates in the spec — a repo-wide rename, a shared
type change, a cross-tree rewiring — and sequence those expand→migrate→contract
rather than forcing them into a single slice.

## Expressing dependencies (the BLOCKED rule)
`TRACKER.md` has no dependency field — only states and a free-form Description.
Encode blocking edges through the **BLOCKED state**:
- File tasks **blockers-first** so IDs increase in dependency order.
- A task whose blockers are all absent (nothing gates it) is filed **`TODO`** —
  it is on the frontier and can start immediately.
- A task that depends on others is filed **`BLOCKED`**, with a
  `Blocked by: <blocker titles / IDs>` line at the top of its Description naming
  exactly the tasks that gate it.
- IDs are assigned by `task-tracker` as `max(existing) + 1`, so a blocker filed
  earlier in the same run already has its ID. Reference blockers by ID once known;
  if you must forward-reference within a batch, name the blocker by title and
  reconcile to its ID once assigned. Never guess an ID.

Do NOT invent new states or fields to model dependencies — BLOCKED plus the
`Blocked by:` note is the whole mechanism. When a blocker later reaches COMPLETE,
moving the dependent from BLOCKED to TODO is a normal, judged `task-tracker`
transition — not something `to-tasks` does at filing time.

## Do / Don't
- DO decompose only from `SPEC.md`, its ADRs, and the current code — nothing else.
- DO speak in the spec's Glossary vocabulary throughout task titles and bodies.
- DO keep each task a demoable vertical slice sized to one context window.
- DO file blockers-first: frontier tasks `TODO`, dependent tasks `BLOCKED` with a
  `Blocked by:` note.
- DO delegate all board mechanics (fields, record boundary, IDs, timestamps) to
  the `task-tracker` format, and re-read your edit so every task still parses.
- DON'T re-design or re-open settled decisions — that is `/architect`'s job.
- DON'T invent decisions the spec never settled; surface the gap to the user
  instead of guessing.
- DON'T inline specific file paths or code snippets — they go stale fast.
  Exception: a prototype snippet that encodes a decision more precisely than prose
  can (a schema, a state machine, a type shape) may be inlined in a task, trimmed
  to the decision-rich part and noted as coming from a prototype.
- DON'T file anything before the user approves the breakdown at the checkpoint.
