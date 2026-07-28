---
name: code-review
description: "Two-axis review of the diff since a fixed point (commit, branch, tag, or merge-base) — Standards (does the code follow this repo's documented conventions and avoid code smells?) and Spec (does it implement what the project's SPEC.md / TRACKER.md task asked for?). Runs both axes as parallel sub-agents and reports them side by side. Use to review a branch, work-in-progress changes, or 'review since X' — including the review step of /implement."
---

# code-review
Review the diff between `HEAD` and a fixed point along two independent axes:

- **Standards** — does the code follow this repo's documented conventions
  (`AGENTS.md`, the project's `adr/`, its `SPEC.md` Testing Decisions) and avoid
  the code smells below?
- **Spec** — does the code faithfully implement what the originating `SPEC.md` and
  `TRACKER.md` task(s) asked for?

Both axes run as **parallel sub-agents** so they don't pollute each other's
context; this skill then aggregates their findings side by side. This is the
review hop `/implement` calls before it commits.

## Process

### 1. Pin the fixed point
Whatever the user named is the fixed point — a commit SHA, branch, tag, `main`,
`HEAD~5`, etc. If they named none, default to the merge-base with `main`; if that's
ambiguous, ask.

Capture the diff command once: `git diff <fixed-point>...HEAD` (three-dot, against
the merge-base), and the commit list via `git log <fixed-point>..HEAD --oneline`.
Before spawning anything, confirm the ref resolves (`git rev-parse <fixed-point>`)
and the diff is non-empty — a bad ref or empty diff fails *here*, not inside two
sub-agents. (This repo carries both git and jj; use git for the diff — it's the
common denominator.)

### 2. Identify the spec source
Find what the change was supposed to do, in this order:
1. The project's **`SPEC.md`** (the nearest ancestor that owns one), plus the
   **`TRACKER.md`** task(s) the commits reference (a task title or ID).
2. A path the user passed as an argument.
3. If nothing is found, ask the user. If there is no spec, the Spec sub-agent skips
   and reports "no spec available".

### 3. Identify the standards sources
Read this repo's documented conventions: **`AGENTS.md`** (the repo-wide roadmap and
rules — Nix-first, per-project dev shells, tests-with-the-thing, ADRs-with-the-thing),
the touched project's **`adr/`** (the *why* behind its design), and its **`SPEC.md`
Testing Decisions** (the settled seams). A documented convention here is a real
standard the diff can violate.

On top of the repo's own docs, the Standards axis always carries the **smell
baseline** below — Fowler's code smells (_Refactoring_, ch.3), which apply even
where the repo documents nothing. Two rules bind it:

- **The repo overrides.** A documented repo convention always wins; where it
  endorses something the baseline would flag, suppress the smell.
- **Always a judgement call.** Each smell is a labelled heuristic ("possible
  Feature Envy"), never a hard violation — and skip anything tooling (`clippy`,
  `rustfmt`) already enforces.

Each smell reads *what it is* → *how to fix*; match it against the diff:

- **Mysterious Name** — a function, variable, or type whose name doesn't reveal what it does or holds. → rename it; if no honest name comes, the design's murky.
- **Duplicated Code** — the same logic shape appears in more than one hunk or file in the change. → extract the shared shape, call it from both.
- **Feature Envy** — a method that reaches into another object's data more than its own. → move the method onto the data it envies.
- **Data Clumps** — the same few fields or params keep travelling together (a type wanting to be born). → bundle them into one type, pass that.
- **Primitive Obsession** — a primitive or string standing in for a domain concept that deserves its own type. → give the concept its own small type.
- **Repeated Switches** — the same `match`/`if`-cascade on the same type recurs across the change. → replace with polymorphism, or one map both sites share.
- **Shotgun Surgery** — one logical change forces scattered edits across many files in the diff. → gather what changes together into one module.
- **Divergent Change** — one file or module is edited for several unrelated reasons. → split so each module changes for one reason.
- **Speculative Generality** — abstraction, parameters, or hooks added for needs the spec doesn't have. → delete it; inline back until a real need shows.
- **Message Chains** — long `a.b().c().d()` navigation the caller shouldn't depend on. → hide the walk behind one method on the first object.
- **Middle Man** — a type or function that mostly just delegates onward. → cut it, call the real target direct.
- **Refused Bequest** — an implementer that ignores or overrides most of what it inherits (in Rust: a trait impl that panics on / no-ops most of the trait). → drop the inheritance, use composition.

### 4. Spawn both sub-agents in parallel
Send one message with two `Agent` calls, `general-purpose` for both.

**Standards sub-agent** — include the diff command and commit list; the list of
standards-source files from step 3 **plus the smell baseline pasted in full** (the
sub-agent has no other access to it); and the brief: *"Report — per file/hunk where
relevant — (a) every place the diff violates a documented convention: cite it
(`AGENTS.md` rule, ADR, or SPEC Testing Decision); and (b) any baseline smell you
spot: name it and quote the hunk. Distinguish hard violations from judgement calls
— documented-convention breaches can be hard, baseline smells are always judgement
calls, and a documented repo convention overrides the baseline. Skip anything
`clippy`/`rustfmt` enforces. Under 400 words."*

**Spec sub-agent** — include the diff command and commit list, and the `SPEC.md` +
`TRACKER.md` task(s) from step 2; and the brief: *"Report: (a) requirements the
spec/task asked for that are missing or partial; (b) behaviour in the diff that
wasn't asked for (scope creep); (c) requirements that look implemented but wrong.
Quote the spec line or task for each finding. Note especially any test that was
weakened/deleted to pass, or business logic added beyond the task. Under 400
words."* If there's no spec, skip this sub-agent and note it.

### 5. Aggregate
Present the two reports under `## Standards` and `## Spec` headings, verbatim or
lightly cleaned. Do **not** merge or rerank across axes — they're deliberately
separate (see below). End with a one-line summary: total findings per axis and the
worst issue *within each axis*. Don't crown a single winner across axes — that's
the reranking the separation exists to prevent.

## Why two axes
A change can pass one axis and fail the other:
- Follows every convention but implements the wrong thing → **Standards pass, Spec fail.**
- Does exactly what the task asked but breaks the repo's conventions → **Spec pass, Standards fail.**

Reporting them separately stops one axis from masking the other.
