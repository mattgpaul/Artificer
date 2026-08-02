---
name: coffee
description: "Explicit command only (/coffee). Do not auto-invoke. Runs a morning spaced-repetition review over concepts captured in the Obsidian daily notes: quizzes what's due on a Leitner schedule, logs results to ~/journal/coffee/LEDGER.md, graduates well-retained concepts into notes/, and hands knowledge gaps to /teachme."
---

# Coffee
The objective is a morning spaced-repetition ritual over what the user is currently learning. New knowledge lands in the Obsidian daily notes (`~/journal/daily/YYYY-MM-DD.md`) under `## <Topic>` headings; `coffee` quizzes the concepts that are *due* on a Leitner schedule, and a concept that survives enough spaced reviews **graduates** into the permanent `~/journal/notes/<Topic>.md`. Review is gated on *demonstrated retention*, not calendar age: a concept only earns its permanent note by being recalled correctly across widening intervals.

**The unit of review is the concept, not the heading.** A single `## <Topic>` section is a *container* — one morning's `## Rust` heading might capture three separate ideas (say `peekable`, the `?` operator, and trait objects). Each of those is its own Leitner item with its own box and due date, and gets its own question. It is **one question per concept, never one per header**. So when you read a daily section, decompose it into the distinct concepts it holds before enrolling or quizzing.

`coffee` is the scheduler these skills lacked: `/teachme` imparts understanding and archives lessons to the daily note; `/testme` measures understanding with a retrieval-not-recognition bar; `/journal` distills sessions into the daily note. `coffee` reuses `/testme`'s grading posture and hands the gaps it finds to `/teachme` — it never teaches inline.

The workflow is **capture-first**: concepts enter through the daily and only reach `notes/` by passing reviews. Existing `notes/` files are already-graduated and out of scope. Treat a first run as square one — build the ledger from what is in the dailies now.

## On invocation
1. Run `date +%F` to get today (don't assume it).
2. Read the ledger at `~/journal/coffee/LEDGER.md`. If it does not exist, create it from `templates/LEDGER.md` (and create `~/journal/coffee/` if needed).
3. **Enroll new concepts.** Scan recent `daily/*.md`. For each `## <Topic>` section, **decompose it into the distinct concepts it captures** (see *Decompose a section into concepts*) and enroll each concept not already in the ledger. Add each to **Active** at **box 1**, `last_reviewed = today`, `due = today + 1` — the first review falls due *tomorrow*, never the day it was captured. Record its `Topic` (the heading / future `notes/<Topic>.md`) and `Source` (the daily file it lives in). **Skip anything opted out of review** — a section tagged `#no-coffee` (excludes every concept under it), an individual concept the user has opted out, or anything already in the ledger's **Excluded** list (see *Skip what isn't for review*). Never enroll an excluded concept, even if it reappears in a later daily.
4. **Compute the due queue** — every Active item whose `due` date ≤ today, ordered oldest-due first. If the queue is empty, say so plainly and stop; the ritual is done.
5. **Quiz each due concept** (see *Quiz to the concept, removed from the note*), grade it (see *Grade honestly*), move its box and reset its due date (see *Move the box*), and persist the ledger. Clear the whole queue — being stuck on one concept is not a reason to stop; log it and move on.
6. **Graduate** any concept that passes out of box 5 (see *Graduation*).
7. **Debrief** — report the run: passes, misses, promotions, graduations, and what is due next. Offer `/teachme` on each miss (see *Hand gaps to /teachme*).

## Templates
Use the bundled template as the starting shape so the ledger is consistent and resumable:
- `templates/LEDGER.md` — the running Leitner ledger (layout below). The live copy lives in the vault at `~/journal/coffee/LEDGER.md`, not in this repo — it is personal review state tied to the journal.

## LEDGER.md layout
Keep the ledger in this shape so it stays legible and resumable:
- **Box schedule** — the fixed Leitner intervals, in days: box 1 → 1, 2 → 3, 3 → 7, 4 → 16, 5 → 35.
- **Active** — one row per **concept** in review: `Topic` (the heading it lives under, = its future `notes/<Topic>.md`), `Concept` (the specific idea under test), `Box`, `Last reviewed`, `Due`, `Source` (the daily note), and a short `History`. `due = last_reviewed + interval[box]`. Several concepts can share a `Topic` and each carries its own box and due date. For a single-idea heading, `Topic` and `Concept` may be the same name.
- **Graduated** — one row per concept that has left the rotation by passing: `Topic`, `Concept`, `Graduated` (date), `Passes`, and the `notes/<Topic>.md` it landed in.
- **Excluded** — concepts (or whole topics) the user opted out of review: `Topic`, `Concept` (or `—` for a whole-topic opt-out), and a one-line `Reason`. Never enrolled, however often it reappears.

## Session Activities

### Decompose a section into concepts
Before enrolling or quizzing a `## <Topic>` section, break it into the distinct **concepts** it holds. A concept is a single testable idea — one mechanism, rule, equation, distinction, or claim — the kind of thing you could write one good question about. Often each `###` sub-point or each substantive bullet is its own concept; a short heading may hold just one.

Judge the grain honestly:
- **Don't under-split.** A `## Rust` heading covering `peekable`, the `?` operator, and trait objects is *three* concepts, three ledger rows, three questions on their own schedules — not one "Rust" item. Collapsing them hides two-thirds of what needs review.
- **Don't over-split.** Not every sentence is a concept. Restatements, context, and the motivating story around one idea stay part of that one concept. If two "ideas" always have to be recalled together to make sense, they are one concept.

Give each concept a short, stable name (e.g. `Rust › peekable`, `Rust › ? operator`) so it is recognizable across sessions and its ledger row is easy to find. When new concepts show up under a heading already partly tracked, enroll just the new ones — leave the existing rows on their own schedules.

### Quiz to the concept, removed from the note
This is the heart of the ritual. Quiz **one concept at a time** — never roll a whole `## <Topic>` section into a single question. Every question must make the user *apply* that one concept to a fresh case — never something they can answer by re-reading the note they wrote.

**Build ground truth first, and keep it to yourself.** Before you ask, know the correct answer cold (borrow `/testme`'s method): for a **code** concept, read the relevant code or work out a runnable check; for an **engineering or general** concept, verify any checkable claim against a real, high-trust source. Do not grade from a shaky memory. Never paste, echo, or summarize the ground truth into the chat — it coaches the answer.

**Format follows the concept** — the quiz conforms to the thing it tests:
- **Code / syntax** → have the user write a short script or function, and name the specific construct the concept is about (the `peek()`, the trait bound, the lifetime). Then *run it yourself* with Bash to confirm the behavior — but **passing behavior is necessary, not sufficient**. The concept under test is the *mechanism*, so require it: an answer that reaches the right output by sidestepping the mechanism (an index or `len()` where the point was `peek()`; a clone where the point was a borrow) is a **miss**, however green it runs. Grade the mechanism, verify with the run.
- **Engineering / math** → pose a numeric problem or an equation to solve; check the number.
- **Architecture / design** → ask for a short applied answer — a tradeoff, a failure mode, "what breaks if…" — graded against ground truth.
- **Pure factual recall** → multiple choice is allowed here when it genuinely fits (unlike `/testme`, which bans it). Keep every option the same length in words and characters so formatting leaks no clue.

**Removed from the note.** Change the numbers, the context, or the language; ask for a *consequence*, an *edge case*, or an *application*, not the definition the note already states. If the answer is sitting in the note verbatim, the question is wrong — rewrite it so recall of the concept is the only way through.

### Grade honestly
Reuse `/testme`'s Assessment Bar. **Default to unconvinced.** An answer earns a pass only once the user has shown the *mechanism* and the *why* — not because it sounds plausible or names the right term. Push past the first right-sounding response to the load-bearing detail beneath it; if they cannot go a level deeper in their own words, it is not a pass. Do not reveal the answer mid-quiz — if an answer is shaky, re-ask from a different angle to tell "doesn't know" from "phrased it poorly." A miss is honest, not a failure of the session.

### Move the box, set the next due date
When a concept settles:
- **Pass** → promote one box (box 5 pass → *graduate*, see below). 
- **Miss** → reset to **box 1**.

Then set `last_reviewed = today` and `due = today + interval[new box]`, append the outcome to `History`, and persist the ledger. Due dates are calendar days: if `coffee` is skipped for days, due items simply pile up, and a run clears the whole accumulated queue.

### Graduation
When a concept **passes out of box 5**, it has survived the full spaced schedule — retire *that concept* from the rotation and give it a permanent home. Graduation is **per concept**, not per heading: siblings under the same `## <Topic>` graduate whenever each one earns it, and they all land in the same `notes/<Topic>.md`. `coffee` does this automatically (the user chose full automation; `/journal` will not touch `notes/`, so `coffee` owns graduation):
1. **Land the concept in `~/journal/notes/<Topic>.md`.** If the file doesn't exist, create it in the vault's concept-note shape — `note.md` frontmatter (`uplinks:` / `created:` with today's date), a dated `# YYYY-MM-DD` section, `## <Topic>` with `###` sub-points, liberal `[[wikilinks]]`, fenced code. If it already exists (an earlier sibling graduated, or it's an evergreen note), **append** this concept as its own `###` sub-section under the topic rather than overwriting — `notes/` files aggregate over time. Match the existing notes (`notes/Concurrency.md`, `notes/async.md`) for tone. Source the content from this concept's part of its daily `## <Topic>` section.
2. **Prune the daily.** Remove just this concept's content from its daily `## <Topic>` section, leaving the not-yet-graduated siblings in place. Only when the **last** concept under that heading graduates does the whole section collapse to a bare `[[Topic]]` stub — the shape the vault uses for fully-migrated topics.
3. Move the concept's ledger row from **Active** to **Graduated** (`Graduated = today`, `Passes`, `Note = notes/<Topic>.md`).
4. Report exactly which files and which concept changed.

### Skip what isn't for review
Not everything captured in a daily is something to be quizzed on — personal notes (`taxes`, `family`), reference material, or a passing thought all live in the daily too. Give the user a clean escape hatch so `coffee` never drills them on those, at either grain:
- **Whole-topic opt-out (inline).** A `## <Topic>` section tagged `#no-coffee` (on the heading line or its intro) is skipped entirely — none of its concepts are ever enrolled. This is the pre-emptive marker for a section that is all personal/reference, like `## Taxes`.
- **Single-concept opt-out (interactive).** When one concept surfaces (at enrollment, or when it comes up due) and the user says it isn't a coffee item — "skip this", "not a coffee item", "don't test me on this" — add just that concept to the ledger's **Excluded** list with a one-line reason and drop it from rotation, while its siblings under the same heading keep their schedules. Tag the daily to record it: `#no-coffee` on the heading if the *whole* topic is out, or an inline `#no-coffee` on the concept's bullet/sub-point if only that one concept is.

An excluded concept stays put in its daily note untouched — it is simply invisible to review. The exclusion is durable: once excluded it is never re-enrolled, even if the same concept is captured again later. If the user ever wants it back, they remove the `#no-coffee` tag and delete its **Excluded** row.

### Hand gaps to /teachme
Every miss becomes a candidate carrying its **subject** and its **mission** — why the user is learning it, the same two things a `/teachme` session needs. At the debrief, **offer** to launch `/teachme` on one candidate or the set; pose the subject and mission as conversational context, not parameters. Never auto-run `/teachme`, and never teach the concept inline — that is `/teachme`'s job, and it keeps its own state. The missed concept stays in box 1 in the ledger regardless of whether the user takes the lesson now.

## Doctrine
The point is **storage strength** — long-term retention — not fluency in the moment. Fluency feels like mastery and isn't; only retrieval that is effortful, spaced, and applied builds durable memory. So `coffee` leans into desirable difficulty: it tests by **retrieval, not recognition**, spaces reviews across widening intervals, and interleaves whatever the day's queue happens to mix.

"Removed from the note" is the load-bearing rule. A question answerable from the note measures recognition — the user pattern-matches their own words back. A question that forces the concept onto a *new* case measures whether the idea actually transferred. Transfer is the thing worth having; the note is scaffolding, not the answer key.

Graduation is **earned, not scheduled.** A concept reaches `notes/` because it was recalled correctly across the full box schedule — roughly five spaced passes over about two months — not because enough calendar time elapsed. The permanent note is a record of something that stuck, which is exactly why the vault keeps concept prose in `notes/` and leaves `[[stubs]]` in the dailies.

## Do / Don't
- **DO** decompose a `## <Topic>` section into its distinct concepts and enroll/quiz **one per concept** — a multi-idea heading is several Leitner items, not one.
- **DO** quiz by application, removed from the note — a fresh case, a consequence, an edge case.
- **DO** let the format follow the concept: run code, check numbers, ask applied prose, use fair multiple choice only where it fits.
- **DO** grade code on the *mechanism*, not just a green run — passing output that dodges the construct under test is a miss.
- **DO** clear the whole due queue each run; log a stuck concept and move on.
- **DO** write to `notes/` only on graduation, and report every file you touch.
- **DON'T** collapse a whole heading into one question, or graduate a heading wholesale — concepts under it are enrolled, quizzed, and graduated independently.
- **DON'T** quiz a concept the day it was captured — its first review is due tomorrow.
- **DON'T** reveal the answer or the ground truth mid-quiz; grade silently, re-ask from another angle when shaky.
- **DON'T** teach inline — hand gaps to `/teachme`, never auto-run it.
- **DON'T** touch `notes/` except to graduate a concept; the daily note is `coffee`'s workspace otherwise.
- **DON'T** enroll a `#no-coffee` or **Excluded** concept — respect the escape hatch, and honor "not a coffee item" the moment the user says it.
