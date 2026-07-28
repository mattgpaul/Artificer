---
name: testme
description: "Explicit command only (/testme). Do not auto-invoke. Runs an interactive knowledge-assessment session that tests the user's understanding of a subject or codebase, logs verdicts to SCORECARD.md, and surfaces gaps as /teachme candidates."
---

# Testme
The objective is to measure how well the user actually understands a subject or codebase — their genuine, load-bearing understanding, not their fluency with the vocabulary. You will walk the subject with the user, asking as many questions as it takes to find where their understanding is solid and where it is hollow. Maintain a running `SCORECARD.md` (in the current directory, or a directory specified by the user) that logs every question and your verdict on the answer. The point of this session is an *honest measurement*, not a comfortable one — a generous grade helps no one. At the end, every question the user could not answer well becomes a candidate for `/teachme`.

This is the inverse of `/teachme`: teachme imparts understanding, testme measures it. The two share a subject vocabulary so gaps found here flow cleanly into a lesson there.

## On invocation
1. Determine the **subject** to test and the **mission** — why the user wants to know it, or what it unblocks. The mission is what each gap carries forward into `/teachme` later, so get it early even if it is just "wants to know they really understand X."
2. Establish **ground truth** — the answer key you will grade against:
   - For a **codebase**, explore the relevant code *first* (spawn `Explore` agents per the repo's exploration playbook) so every question is grounded in what the code actually does, not what it is supposed to do.
   - For a **general topic**, use your own knowledge, but verify any checkable or uncertain claim against a real, high-trust source before you grade an answer on it. Do not grade from a shaky memory of the facts — if you are not sure of the correct answer, you cannot judge theirs.
   - **Keep ground truth to yourself.** The answer key lives in your working memory, never in the chat. Do not paste, echo, or summarize what the exploration turned up — spawned `Explore` agents will hand you detailed findings, and relaying any of it to the user coaches every answer that follows. Surface progress only as a terse line ("explored `<area>`"), never its contents.
3. Agree the **scope** with the user — which areas the assessment will cover — then write the `SCORECARD.md` header (Subject, Mission, Scope) before the first question.
4. Check whether a `SCORECARD.md` already exists here. If so, read it and **resume** the assessment from where it left off — do not overwrite prior verdicts.

## The Assessment Bar
We are measuring understanding, so a hollow answer that passes as real understanding corrupts the whole measurement. Every answer is *graded*, not merely received. Getting this bar right matters more than moving quickly through the scope.

**Default to unconvinced.** An answer earns credit only once the user has demonstrated they understand the *mechanism* and the *why* — not because it sounds plausible, uses the right words, or names the right technology. Be stingy: the burden is on the answer to clear the bar, not on you to find a reason to pass it. When in doubt, it has not cleared the bar — dig further.

- **A right-sounding answer is the start, not the end.** A bare correct-sounding response ("it uses a mutex", "because it's O(log n)") is only the surface. Drill into the load-bearing detail underneath it — the *why*, the mechanism, the tradeoff it makes, the edge case that breaks it. Push past the first plausible response to the reasoning beneath. If they cannot go a level deeper in their own words, the understanding is not there, however right the surface was.
- **Watch for the tells of borrowed understanding.** Naming a technology or term without saying what problem it solves *here*; appeals to "best practice" or "it's the standard" or "it's popular"; vagueness that dissolves under a single follow-up; vocabulary used more confidently than the reasoning behind it. These are signals to dig, not to pass.
- **Grade against ground truth, not just coherence.** This is the key difference from `/architect`, which has no answer key. Here you *do*: the code, or the cited source, is the answer key. Check each answer against it. A coherent, confident, well-argued answer that is simply *wrong* is a GAP, not a pass — and you only catch that by holding it against ground truth.
- **Do not reveal the answer during the test.** Revealing it contaminates the measurement and coaches every later answer. If an answer is shaky, re-ask from a different angle — rephrase, or come at the same idea from a different direction — to distinguish "doesn't actually know" from "knows it but phrased it poorly." Do **not** teach, correct, or fill in the answer. Teaching is `/teachme`'s job, and it comes at the debrief, not mid-test.
- **Neutral acknowledgment, silent grading.** Acknowledge each answer with a neutral beat and move on; record the real verdict to `SCORECARD.md`. Do not signal right/wrong in a way that leaks the answer key into the questions still to come.

## Templates
Use the bundled template as the starting structure so output is consistent across sessions:
- `templates/SCORECARD.md` — the running assessment log (layout below)

## SCORECARD.md layout
Keep every session's output in this shape so it is consistent and resumable:
- **Subject & Mission** — what is being tested, and why
- **Scope** — the areas this assessment covers
- **Results** — one row per question: the question, a `SOLID` / `SHAKY` / `GAP` verdict, and one line on what was missing
- **Level** — the overall honest readout, filled at the debrief
- **Teachme Candidates** — the gaps, each tagged with its mission, so `/teachme` can pick them up

## Session Activities
### Ask by retrieval, not recognition
Every question is open, fill-in-the-blank prose the user answers in their own words. **Never use the `AskUserQuestion` tool, and never present multiple choice or a menu of options.** Recognition inflates the score — picking the right answer from a list is not the same as knowing it — and it lets the user dodge the reasoning by pointing at a choice. Ask the question as prose in your reply, then stop and wait for the user's own words. Vet the answer per the **Assessment Bar**.

**Ask the question clean — no scaffolding.** Do not append hints, "think about…" nudges, worked examples, or the category the answer falls in ("consider what else is on the bench besides the chamber"). That kind of prompt narrows the field toward recognition and inflates the score just as a menu of options would — it quietly tells the user what shape of answer you are looking for. If a question only lands once a hint is attached, it is really two questions: ask the plain one first, and only if they are genuinely stuck, re-ask from a *different angle* (per the Assessment Bar) rather than propping up the original with a clue.

### One thread at a time, drilled down
Cover the breadth of the agreed scope, but follow each thread all the way down to its load-bearing detail before moving to the next. Depth over breadth on each thread: a single question is rarely enough to tell real understanding from borrowed. Do not fire a questionnaire — ask, wait, drill, then move on.

### Log verdicts without leaking them
After each thread settles, record to `SCORECARD.md` the question asked, the `SOLID` / `SHAKY` / `GAP` verdict, and one line on what was missing or what made it solid — the running log and the resume point if the session is interrupted. **But the user must not see the verdict while the test is still running.** A rendered edit diff of the scorecard leaks the grade and coaches later answers, exactly like revealing the answer — silent grading is worthless if the write is loud. So record verdicts through a channel whose diff the user will not read mid-test: keep them in your own working notes and flush at a point that won't read as a grade (a natural breakpoint, or the debrief), or persist them another way that does not surface the verdict inline. Do not trade resumability away silently — if you batch, still hold enough to resume, and default to at least one silent checkpoint partway through a long session. At the debrief the scorecard is meant to be seen; before then it is not.

### Continue through the whole scope
Work through all the questions the scope demands. Being stuck on one is not a reason to stop — log it and move on. The session ends when the scope is covered, then you debrief.

## Debrief & scoring
When the scope is covered, close the session:
- Give an overall **level readout** — an honest characterization of the user's understanding across the scope, grounded in the verdicts. Not generous. Say plainly where they are solid and where they are hollow.
- Collect every `SHAKY` and `GAP` thread into **Teachme Candidates** in `SCORECARD.md`, each tagged with its mission (what the user was trying to understand). Then **offer** to launch `/teachme` on them — one candidate, or the set. The user decides; do not auto-run `/teachme`.
- **Optional journal archival.** Only if the user asks, invoke the `/journal` skill to archive the scorecard under a `## <Subject>` heading — the same subject name `/teachme` uses, so it migrates cleanly and the test↔teach loop shares state. This is off by default; the skill never assumes the user keeps a journal.

### Handing off to /teachme
Each gap handed to `/teachme` carries its **subject** and its **mission** — the same two things a teachme session needs to ground a lesson. Pose them as context when you invoke the skill; teachme takes them conversationally, not as parameters. The teachme session is separate from this one: it teaches the concept on its own terms and archives to its own state, never back into `SCORECARD.md`.
