# Nix dev shell + Rust crate scaffold
ID: 1
State: COMPLETE
Blocker: None
Completed: 2026-07-27T20:52:00Z
Description: Prefactor. Stand up the project's dev environment and buildable
crate before any tool code lands. Add `flake.nix` + `.envrc` (`use flake`)
copying the `apps/telemetry_tdd_qwen` precedent — flake-utils + `rustc`, `cargo`,
`clippy`, `rustfmt` — and a `cargo` crate that compiles a stub binary. Done when
`nix develop` (via direnv) provides the toolchain and `cargo build` succeeds.

# TRACKER.md parser to Task records
ID: 2
State: IN PROGRESS
Blocker: 1
Description: Pure parse of a single board's text into ordered Task records,
honoring the record boundary and full field grammar. A new record begins ONLY
where a `# ` header is immediately followed by an `ID:` line and a `State:` line;
a stray `# ` inside a Description is therefore not a new record. Parse the fields
in exact order — Title, ID (integer), State, Blocker, the terminal
`Completed:`/`Cancelled:` slot (at most one, only on a terminal task), and an
unrestricted multi-line Description that runs until the next valid header. Parse
the `Blocker:` grammar: `None`, a bare integer (internal ref on this board), a
`<repo-relative path>:<id>` cross-project ref (the colon is the discriminator),
and comma-separated lists of these. Verifiable on parse output against known
board text, including the stray-`#`-in-Description case.

# Discovery and consolidated view model
ID: 3
State: BLOCKED
Blocker: 2
Description: The settled entry point. Implement `load(repo_root)`: walk the repo
from the root collecting every `TRACKER.md`, skipping `.git`, `.jj`,
`node_modules`, and Nix build results. Identify each project by its path relative
to the repo root (the same identity used to resolve cross-project blocker refs).
Parse each board (ID 2) and build the in-memory consolidated model: projects,
each holding its tasks bucketed by State. This is the highest test seam — drive
it against temp-directory fixture trees and assert the resulting model (projects,
per-column cards). Covers discovery skipping VCS/build noise and project identity
by repo-relative path.

# Archive sweep
ID: 4
State: BLOCKED
Blocker: 3
Description: Write #1, on the load pass, lazy and stateless. Compute sprint
boundaries deterministically: anchor at the first UTC Monday ever, step 2 weeks,
boundary at 00:00 UTC. For each COMPLETE task, parse `Completed:` and rewrite its
State to ARCHIVED on disk iff that timestamp falls in a sprint that has already
ended; retain the `Completed:` timestamp through ARCHIVED. No persisted marker —
the per-task timestamp is the only input. Verifiable at the seam by re-reading
the rewritten files: completed-in-current-sprint stays COMPLETE, completed-in-an-
ended-sprint becomes ARCHIVED.

# Unblock sweep
ID: 5
State: BLOCKED
Blocker: 4
Description: Write #2, bolted onto the same launch pass, after the archive sweep
so a just-archived blocker can release its dependents. For each BLOCKED task,
resolve every reference in its `Blocker:` list — internal ID against this board,
cross-project `path:id` by walking to that board — and read each referenced
ticket's State. Flip the task BLOCKED to TODO iff EVERY referenced blocker is
COMPLETE or ARCHIVED (order-independent; an already-ARCHIVED blocker still
counts). A CANCELLED blocker does NOT satisfy the dependency — the task stays
BLOCKED and visibly stuck. NEVER mutate the `Blocker:` list — only `State` —
so a released TODO task keeps its edges. Verifiable at the seam: all-done
releases, any-incomplete holds, CANCELLED-stays-stuck, order-independence with an
already-ARCHIVED blocker, and edges preserved on release (including cross-project
`path:id` resolution).

# TUI consolidated view and hjkl navigation
ID: 6
State: BLOCKED
Blocker: 3
Description: Wire `main()` from the load entry point to a ratatui UI, rendering
whatever the loaded model holds (so it picks up the sweeps automatically once
they land). Left panel lists every discovered project; the rest of the screen is
a Jira-style board for the selected project with exactly four columns — TODO, IN
PROGRESS, BLOCKED, COMPLETE (never ARCHIVED or CANCELLED). Cards show Title, ID,
and a Description truncated to the card box. Navigation is hjkl: project highlight
on the left switches the board; h/l move across columns; j/k move through tickets
within the focused column; a column scrolls when it overflows. No dependency-edge
visualization — column placement is the whole signal. Verified by hand (the
ratatui render layer is deliberately not a test seam).

# task-tracker skill and template lockstep
ID: 7
State: BLOCKED
Blocker: 2
Description: Keep the `task-tracker` skill and its canonical `TRACKER.md`
template (under `utils/skills/`) in lockstep with the implemented parse contract:
field order header, ID, State, Blocker, [Completed:/Cancelled:], Description.
Confirm the template parses cleanly under the ID 2 parser, and fix the drift in
the template's second example — it instructs "reset `Blocker: None`" when a task
returns to TODO, which contradicts ADR-002's rule that the `Blocker:` list is
never mutated (edges are permanent history; `State` alone carries workability).
