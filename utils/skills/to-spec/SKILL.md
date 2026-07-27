---
name: to-spec
description: "Explicit command only (/to-spec). Do not auto-invoke. Reads the DESIGN.md from an /architect session and synthesizes a SPEC.md specification — the input for creating TRACKER.md issues. No re-interview."
---

# to-spec
The objective is to turn a settled `DESIGN.md` into a `SPEC.md` — a specification
document precise enough that its parts can be decomposed into `TRACKER.md` issues.
Do NOT re-interview the user: the `/architect` session already walked the design
tree and vetted every answer. Your job here is *synthesis*, not design. You take
what is already decided and shape it into a spec. If a decision is missing, that
is a gap to surface — not a blank for you to fill in on the user's behalf. New
design belongs back in `/architect`, not here.

## Where this sits in the pipeline
`/architect` → `DESIGN.md` → **`/to-spec` → `SPEC.md`** → `/task-tracker` →
`TRACKER.md` issues.

`to-spec` stops at `SPEC.md`. It does not file tasks. Turning the spec into
tracker issues is a separate, deliberate `/task-tracker` step — keep that
boundary clean.

## On invocation
1. Find `DESIGN.md` — in the current directory, or a directory the user names. If
   none exists, stop and point the user at `/architect`: there is nothing to
   synthesize from, and a spec must not be invented from scratch here.
2. Read `DESIGN.md` in full, plus any ADRs in the project's `adr/` folder. Explore
   the relevant code area so the spec is grounded in the current state of the
   codebase, not just the design's aspirations. Reuse existing modules and
   patterns rather than proposing new ones where suitable ones already exist.
3. Handle **Open Questions**. Walk the design's Open Questions:
   - If one is settled-enough in the surrounding Decisions to fold in, fold it in.
   - If one genuinely blocks a spec section, surface it to the user — do not
     silently guess an answer.
   - If one remains open and does not block the core, record it explicitly as
     deferred under **Out of Scope** or **Further Notes**. A spec should never
     rest on a hidden unknown.
4. Sketch the testing **seams** (see below) and **checkpoint** with the user.
   Present the seams you intend to test at and the scope boundary you are drawing,
   and confirm both match their expectations before finalizing. This is the one
   interaction point — everything else is synthesis.
5. Write `SPEC.md` from `templates/SPEC.md`, alongside `DESIGN.md`. Carry the
   Glossary over verbatim and use its vocabulary throughout the spec. Reference
   relevant ADRs by number rather than restating them.
6. Tell the user where `SPEC.md` was written, and that the next step is
   `/task-tracker` to file issues from it.

## Seams
A seam is the place you write the test against — the boundary at which you observe
the feature's behavior. The seam choices shape the whole Testing Decisions
section, so get them right at the checkpoint:
- **Prefer existing seams** to new ones. A test that plugs into a boundary the
  codebase already exposes is cheaper and more honest than one that forces a new
  hole.
- **Use the highest seam possible** — test observable external behavior, close to
  how the feature is actually used, not internal wiring.
- **If a new seam is needed, propose it at the highest point** you reasonably can.
- **Fewer seams across the codebase is better.** The ideal number is one.

## SPEC.md layout
Fill out every section of `templates/SPEC.md`:
- **Problem Statement** — the problem from the user's perspective (from the design's Overview / intent).
- **Solution** — the solution from the user's perspective (from the design's Decisions).
- **Glossary** — carried verbatim from `DESIGN.md` so the spec and the issues it spawns share one vocabulary.
- **User Stories** — a long, numbered list in the form `As an <actor>, I want a <feature>, so that <benefit>`, covering every aspect of the feature.
- **Implementation Decisions** — modules built/modified and their interfaces, architectural decisions, schema changes, API contracts, specific interactions. Cite relevant ADRs by number.
- **Testing Decisions** — what makes a good test, the seams you settled on, which modules are tested, where those tests live under the centralized `tests/` tree (per the repo's current convention in `AGENTS.md`), and prior art.
- **Out of Scope** — what is explicitly excluded, including deferred Open Questions.
- **Further Notes** — anything else worth recording.

## Do / Don't
- DO synthesize only from `DESIGN.md`, its ADRs, and the codebase — nothing else.
- DO carry the Glossary verbatim and speak in its terms throughout.
- DO cite relevant ADRs by number instead of restating their reasoning.
- DO make the Testing Decisions section point tests at the right place: tests are
  centralized under the repo's `tests/` tree, mirroring the source path rather
  than sitting beside the code. Follow the repo's current testing convention
  (see `AGENTS.md`) for the exact layout instead of assuming one.
- DO stop at `SPEC.md`.
- DON'T re-interview the user or re-open settled design — that is `/architect`'s job.
- DON'T invent decisions the design never settled; surface the gap instead.
- DON'T include specific file paths or code snippets — they go stale fast.
  Exception: a prototype snippet that encodes a decision more precisely than prose
  can (a schema, a state machine, a type shape) may be inlined in the relevant
  decision, trimmed to the decision-rich part and noted as coming from a prototype.
- DON'T file `TRACKER.md` tasks here — leave that to `/task-tracker`.
