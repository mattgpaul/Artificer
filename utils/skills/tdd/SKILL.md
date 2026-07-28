---
name: tdd
description: "Explicit command only (/tdd). Do not auto-invoke. Picks a TODO task off a project's TRACKER.md, moves it to IN PROGRESS, and writes only the failing (red) tests plus the minimal stubs a compiled runtime needs to build — never the business logic. The RED phase of the TDD cycle."
---

# tdd
The objective is to run the **RED phase** of test-driven development for one task:
pick a task that is ready to work, move it to IN PROGRESS, and write the *failing
tests* that pin down what "done" means — plus only the scaffolding a compiled
runtime needs to build. You do NOT implement the business logic here. RED is a
contract, not a solution: the tests fail because the behavior does not exist yet,
and the next (separate) GREEN step makes them pass. Getting the tests right
matters more than getting them fast — an over-constricting or flaky test outlives
this session and punishes every future change to the code.

## Where this sits in the pipeline
`/architect` → `DESIGN.md` → `/to-spec` → `SPEC.md` → `/to-tasks` → `TRACKER.md`
tasks → **`/tdd` → red tests + compile scaffold**.

`/tdd` is the first hop *into code*. Everything before it decided *what* to build
and *how* the work is sliced; `/tdd` takes one settled slice and writes the tests
that will judge it. It does not invent the board format (that is `task-tracker`),
it does not choose the test seams from scratch (`SPEC.md`'s Testing Decisions
already settled them), and it does not write the implementation (that is GREEN, a
separate step). Keep those boundaries clean.

## On invocation
1. **Find the board.** Determine the project — the current directory, the nearest
   ancestor that owns a `TRACKER.md`, or a directory the user names. Read that
   `TRACKER.md`.
2. **Pick one ready task.** Eligible tasks are exactly those in **TODO** — the
   frontier of workable tickets (`BLOCKED`, `IN PROGRESS`, and terminal states
   are not eligible). If the user named an ID, use it (confirm it is TODO; if it
   is BLOCKED or already IN PROGRESS, stop and say so). If several TODO tasks
   exist and none was named, list them (ID + title) and ask which to start. If
   none are TODO, say the frontier is empty and stop. Take **one** task per
   invocation.
3. **Read the contract before writing a line of test.** Read the task's
   Description in full, then the project's `SPEC.md` — especially **Testing
   Decisions** (the settled seams, what makes a good test here) — and any ADRs in
   the project's `adr/`. Explore the code area the task touches so the tests speak
   the spec's Glossary and target the seam the spec already chose. Do NOT pick a
   new seam if the spec settled one.
4. **Confirm the runtime builds first.** A project is only workable if its dev
   shell + buildable scaffold exist (`flake.nix` + `.envrc`; the crate compiles).
   If they are missing, that is a prefactor task for `/devenv`, not something to
   fake — surface it and stop rather than scaffolding into a project that cannot
   build.
5. **Move the task TODO → IN PROGRESS.** Do this through the `task-tracker` format
   (delegate all board mechanics — field order, record boundary, re-parse check —
   to that skill). Re-read the edit to confirm the board still parses.
6. **Write the RED tests + minimal compile scaffold** per the doctrine below,
   placed at the runtime's native seam (see *Where tests live*).
7. **Verify red — for the right reason.** Run the runtime's test command and
   confirm: the code *compiles/links*, the new tests *run*, and they *fail because
   the behavior is unimplemented* (an assertion failure or a
   `todo!()`/`unimplemented!()` panic) — not because of a typo, a missing import,
   or a compile error, and not passing by accident. Iterate until red is honest. A
   red you have not run is not a red.
8. **Report and stop.** Tell the user which board and task you moved (ID → IN
   PROGRESS), where the tests live (in-file unit tests / the crate's `tests/`),
   and the proof they are red. State plainly that GREEN — the implementation — is
   the next, separate step; `/tdd` deliberately leaves the task IN PROGRESS with
   failing tests as the contract for whoever implements it.

## What you write (and what you don't)
- **Tests, and only enough scaffold to build.** Write the failing tests. Then add
  the *minimum* surface the tests reference — module paths, function/method
  signatures, type and trait declarations — with bodies that are `todo!()` /
  `unimplemented!()` (Rust) or the runtime's equivalent unimplemented marker. Just
  enough that the test target compiles and links and the tests fail at runtime.
- **No business logic. Ever.** If a stub body is tempting to fill in with real
  behavior, that is GREEN — stop. The line is: the code compiles, the tests fail.
  A stub that makes a test *pass* means you implemented something; back it out.
- **Only surface the tests exercise.** Do not scaffold speculative types, fields,
  or functions the tests do not touch. The tests define the surface; the scaffold
  serves the tests, nothing more.
- **Public where the seam is public.** Whatever an integration test reaches must be
  `pub` (exported). Whatever only an in-file unit test reaches can stay private.

## Where tests live (Rust; and the general rule)
Tests live **with the thing they test**, at the runtime's native test seam (see
`AGENTS.md`). For Rust specifically:
- **Unit tests → in-file.** Behavior of a private/internal unit is tested in the
  same file, in a `#[cfg(test)] mod tests { use super::*; … }` block. This is the
  settled repo precedent (`apps/telemetry_tdd_qwen`, `libs/microlib`).
- **Integration tests → the crate's own `tests/` directory** (sibling to `src/`),
  each file compiled as its own crate against the library's **public API**. This
  is where you test the crate's observable behavior — the highest, most honest
  seam. No `Cargo.toml` wiring is needed; `cargo test` discovers `tests/*.rs`
  automatically.
- **The repo-level `tests/` tree is NOT for a single project's tests.** It is
  reserved for cross-`apps/` end-to-end tests that span more than one project. Do
  not put a crate's integration tests there.
- **Other runtimes:** same principle — tests sit with the code at the language's
  native seam (e.g. a Python package's own `tests/`), never in the repo-level
  `tests/` unless they are genuinely cross-project e2e.

Prefer the integration seam (public API) for behavior the task promises; reach for
an in-file unit test only when the behavior genuinely lives below the public
surface and cannot be observed from outside.

## Reliable, not constricting — the test doctrine
The stress here is tests that are **reliable without being over-constricting**.
Over-testing is a real failure: it locks the code's *shape* in place, breaks on
every refactor, and trains people to distrust the suite. Aim for the fewest tests
that fully pin the behavior the task promises — and no more.

**Test behavior, not structure.**
- Test observable behavior at the **highest reasonable seam** — the public API,
  how the thing is actually used — not internal wiring. A test that only breaks
  when behavior changes is good; one that breaks when you rename a private helper
  or reorder a struct is over-constricting. (This is the same seam doctrine
  `SPEC.md` settled — honor it.)
- Pin the **contract from the task's Description and the spec**, not the current
  implementation's incidental choices.

**Cover the promise — exactly.**
- The task's Description is the definition of done. Cover the behavior it promises:
  the happy path, the boundaries, and the failure modes the spec calls out. Pick
  **representative + edge cases**, not the cartesian product of every input. A few
  pointed cases (e.g. "completed in the current sprint stays; completed in an
  ended sprint archives") beat an exhaustive sweep.
- One behavior per test; name each test for the behavior it pins, so a failure
  reads as a sentence about what broke. Use table/fixture-driven cases to vary
  inputs without duplicating the test body.

**Don't test what you don't own.**
- Don't test the compiler, the type system, the stdlib, or a framework's
  guarantees.
- Don't test trivial delegation — getters/setters, pass-throughs, `Default`
  derivations.
- Don't assert on things the spec never made a contract: exact error-message
  strings, log text, incidental collection ordering, private field layout. Assert
  the property that matters (it errored, the set contains X), not the incidental
  spelling of it.

**Reliable = deterministic.**
- No dependence on wall-clock time, the network, ambient filesystem state,
  randomness, sleeps, or hash-map iteration order. Inject those as fixtures/inputs
  so the test is the same every run. A flaky test is worse than no test — it
  erodes trust in all the others. (Temp-dir fixture trees, a fixed time anchor, a
  seeded RNG — those are the moves.)
- A test must fail for exactly one reason. If it can fail for three, you cannot
  read the failure.

When unsure whether a case earns a test, ask: *"if this test breaks, will it be
because real behavior the task promised changed — or because someone refactored?"*
Only the first kind earns its place.

## Example: an honest red (Rust, illustrative)
A prototype of the *shape* to aim at — the stub panics, the test asserts behavior,
not structure. Not a file to copy verbatim.

```rust
// src/sprint.rs — unit seam: behavior below the public surface
pub fn sprint_index(completed: DateTime<Utc>) -> u64 {
    todo!("map a UTC timestamp to a sprint index off the fixed Monday anchor")
}

#[cfg(test)]
mod tests {
    use super::*;
    // pins the boundary RULE, not the arithmetic used to get there
    #[test]
    fn the_anchor_monday_is_sprint_zero() {
        let t = "2020-01-06T00:00:00Z".parse().unwrap(); // the anchor Monday
        assert_eq!(sprint_index(t), 0);
    }
}
```

```rust
// tests/load.rs — integration seam: the crate's public behavior
use task_tracker::load; // the pub entry point the test pins

#[test]
fn a_task_completed_in_an_ended_sprint_is_archived() {
    let repo = fixture_tree(/* a TRACKER.md whose COMPLETE task is stale */);
    let model = load(repo.path()); // todo!() inside load → panics → RED
    assert!(model.project("app").archived().any(|t| t.id == 1));
}
```

Both fail today: the unit test panics on `todo!()`, the integration test panics
when `load` hits its own `todo!()`. Neither passes by accident, and neither
asserts on the *arithmetic* or the *struct layout* — only on the behavior the task
promised. That is the target.

## Do / Don't
- DO work one TODO task per run; move it to IN PROGRESS via `task-tracker` before
  writing tests, and re-read so the board still parses.
- DO read the task Description, `SPEC.md` Testing Decisions, and ADRs first, and
  test at the seam the spec already settled.
- DO write failing tests plus only the stubs needed to compile; verify red by
  running the tests and confirming they fail for the right reason.
- DO place tests with the thing: Rust unit tests in-file, integration tests in the
  crate's own `tests/`; keep the repo-level `tests/` for cross-`apps/` e2e only.
- DO stop at RED — leave the task IN PROGRESS with failing tests and hand GREEN to
  the next step.
- DON'T implement business logic, or let any stub make a test pass. If a test goes
  green, you wrote too much — back it out.
- DON'T over-test: no tests of the compiler/stdlib/framework, trivial accessors,
  private structure, exact message strings, or incidental ordering.
- DON'T write flaky tests: no real clock, network, filesystem globals, randomness,
  or timing — inject them.
- DON'T invent a new seam the spec didn't choose, or scaffold surface the tests
  don't exercise.
- DON'T pick up a BLOCKED or already-IN PROGRESS task, and DON'T re-open
  design/spec/decomposition — those are `/architect`, `/to-spec`, `/to-tasks`.
