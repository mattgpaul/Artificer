---
name: implement
description: "Explicit command only (/implement). Do not auto-invoke. Implements the work described by a SPEC.md or a set of TRACKER.md tasks — the GREEN phase. Drives failing tests to passing at pre-agreed seams via /tdd, verifies as it goes, then reviews and commits."
---

# implement
The objective is to **make the work real**: take a spec or a set of tasks and
build the behavior until it works and is proven. This is the GREEN phase — where
`/tdd` left off with failing (red) tests as the contract, `/implement` writes the
business logic that turns them green, and no further.

## Where this sits in the pipeline
`/to-tasks` → `TRACKER.md` → `/tdd` (red tests) → **`/implement` (green + review +
commit)**.

`/tdd` decided *what "done" means* by pinning it in failing tests; `/implement`
satisfies that contract. Don't re-open the seams `/tdd` and `SPEC.md` settled —
implement against them.

## On invocation
1. **Read the work.** The `SPEC.md` and the `TRACKER.md` task(s) the user names
   (or the IN PROGRESS tasks with red tests waiting). Read the failing tests —
   they are the definition of done.
2. **Implement to green — at pre-agreed seams.** Fill in the stubs `/tdd` left
   with real behavior. Where a task still needs its red tests written first, use
   `/tdd` at the seam the SPEC already chose rather than inventing a new one.
   Write only what the tests and spec require; no speculative surface.
3. **Verify continuously.** Run typechecking/lint often (Rust: `cargo check`,
   `cargo clippy`) and the relevant *single* test file as you go. Run the **full**
   suite once at the end and confirm it's green. Fix, don't suppress.
4. **Update the board.** Move each finished task to COMPLETE via `task-tracker`
   (delegate the format); leave anything unfinished IN PROGRESS with an honest note.
5. **Review.** Run `/code-review` on the diff and address what it surfaces.
6. **Commit** the work to the current branch (branch first if you're on `main`,
   per repo norms). Report what landed, the test proof, and anything left open.

## Do / Don't
- DO implement against the red tests and the settled seams; use `/tdd` for any
  still-untested slice before writing its logic.
- DO run typecheck/lint and single test files continuously, the full suite once at
  the end, and `/code-review` before committing.
- DO move completed tasks to COMPLETE via `task-tracker` and commit to the current
  branch.
- DON'T re-open design/spec/seam decisions — those are `/architect`, `/to-spec`,
  `/to-tasks`, `/tdd`.
- DON'T weaken or delete a test to get green, add surface the spec didn't ask for,
  or commit with a red suite.
