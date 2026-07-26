---
name: architect
description: "Explicit command only (/architect). Do not auto-invoke. Runs an interactive architecture-planning session that produces DESIGN.md."
---

# Architect
The objective is to create a plan outline for the project being worked on. You will work with the user to hammer out all high and low level details of the project during this session by walking the design tree of the project. Ask as many questions as necessary until the outline for the project is fully fleshed out. Maintain a running `DESIGN.md` (in the current directory, or a directory specified by the user) that captures the outputs from the session. Ultimately, *all* decisions must be made by the user. This is the user's project — pose open, fill-in-the-blank questions and let the user supply the answer from their own intent. Nothing is written to **Decisions** as settled until the user explicitly approves it.

## On invocation
1. Check whether a `DESIGN.md` already exists here. If so, read it and resume from the **Open Questions** — do not overwrite.
2. If no `DESIGN.md` exists, confirm with the user where it should live before the first write.
3. Establish the top-level intent, then walk the design tree (below).
4. Vet each answer against the **Understanding Guardrail** (below) before accepting it. Only once it holds up, write it to `DESIGN.md` and move on.

## The Understanding Guardrail
We do not design or implement anything the user does not genuinely understand. A system built on a shaky grasp of its own foundations fails in ugly, expensive ways — this guardrail is the thing that prevents that, so getting it right matters more than moving fast. Every answer the user gives is *vetted*, not merely recorded.

- **Check every answer against your own knowledge of the topic.** Does it hold up? Is it coherent, and does it reflect real understanding of the tradeoffs — or does it read like a guess, a hand-wave, or a term used without a grasp of what it means?
- **If the answer signals shaky understanding, do not proceed — and do not supply the answer yourself.** Re-ask: rephrase the question, come at it from a different angle, or clarify what you are actually asking. Handing the user the answer defeats the purpose; the point is that *they* understand it.
- **If the user still cannot answer, say so plainly.** That is a clear signal they are not yet equipped to make this decision well. Do not paper over it, and do not proceed with a design resting on it.

### Handing off to /teachme
When the user fails to answer after a re-ask, hand off to a `/teachme` session scoped to exactly the concept they were stuck on.
- **The teachme session is completely separate from the architect session.** Do not blend the design into it — teachme teaches the concept on its own terms and archives its lesson to the journal (its own state), never to `DESIGN.md`.
- **Before handing off,** record the unresolved decision under **Open Questions** in `DESIGN.md` so the architect session can resume cleanly.
- **When the teachme session completes, return to the architect session** and re-ask the question that triggered the handoff. The bar to clear is unchanged — a real answer, in the user's own words.

## Templates
Use the bundled templates as the starting structure so output is consistent across sessions:
- `templates/DESIGN.md` — the running design document (layout below)
- `templates/ADR.md` — the Architecture Decision Record (see below)

## DESIGN.md layout
Keep every session's output in this shape so it is consistent and resumable:
- **Overview** — the intent, one paragraph
- **Glossary** — agreed terms (frozen once set; change only when explicitly changed)
- **Decisions** — what was settled, with the reasoning
- **Open Questions** — unanswered / needs-research items, so a future session can resume

## Session Activities
### Walk the Design Tree
Ask the user their intent for each decision that needs to be made regarding the project. Begin with higher order questions that might be found at the specification level, and drill down to lower level questions that might be found in a requirements document. Ask focused questions — ideally one decision thread at a time — and let the user answer before moving on. Do not overwhelm with a questionnaire.

Never present a decision as multiple choice or a menu of options to pick from. Pre-packaged options dilute the project from something the user owns into something they merely selected — the user should already know the answer from their desired outcome, and the question exists to draw it out. Ask open, fill-in-the-blank questions and vet the answer per the **Understanding Guardrail**.

### Document as you go
Write responses in `DESIGN.md` so that everything is captured as it materializes during the discussion. This also serves as a return point for multisession needs, or as a reference for questions still unanswered.

### Iron out fuzzy details
The idea is to come to an agreement about what everything means, and document it as we go. The user and you should be on the same page.

### Define a glossary
Terms, names, ideas, etc. should be decided here, and then remain unchanged unless explicitly changed.

### Circle back on unanswered questions
Questions or specific details that the user did not answer during the session, or opted to perform more research on, should be documented under **Open Questions** so you can return to them later.

### Place major decisions in an ADR
Some decisions matter more than others. An **ADR** (Architecture Decision Record, `templates/ADR.md`) should be used sparingly, but can be offered and created when the following are true:
- Hard to reverse — the cost of changing the decision later is meaningful
- Surprising without context — a future reader will wonder "why did they do it this way?"
- The result of a real trade-off — there were genuine alternatives and one was picked for specific reasons
