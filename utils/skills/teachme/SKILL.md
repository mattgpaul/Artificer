---
name: teachme
description: "Explicit command (/teachme), or direct session call from /architect. Do not auto-invoke. Runs a stateful teaching session on a topic and archives the lesson to the journal via /journal."
---

# Teachme
The objective is to pass on genuine, durable understanding of a topic the user chooses — or one they need to grasp more deeply to make progress on an ongoing `/architect` design. Teach for deep understanding, not superficial fluency. Sessions are stateful: a topic may be taught over many sessions, and the journal is the archive that carries state between them. Ground every lesson in *why* the user wants to learn it, teach only what serves that goal, and confirm understanding before you close.

## On invocation
1. Determine the **subject** the user wants to understand, and their **mission** — the real reason they need it. If invoked from `/architect`, the mission is the design decision they are blocked on; carry that context in. If the mission is unclear, ask before teaching — ungrounded lessons feel abstract and you cannot judge what to teach next.
2. Retrieve **prior state** for this subject from the journal (see *Retrieve prior state*). If prior lessons exist, summarize the points from them that are pertinent to this session before continuing.
3. Locate the user's **zone of proximal development** — the next thing that challenges them just enough — from the prior state and the mission.
4. Impart the knowledge the lesson requires, grounded in trusted sources (see *Impart knowledge*).
5. Have the user practice until the skill sticks, then **test understanding** with a tight feedback loop.
6. Invoke the `/journal` skill to **archive the lesson** so the next session can resume from it.

## Templates
Use the bundled template so archived lessons are consistent and resumable across sessions:
- `templates/LESSON-RECORD.md` — the distilled record handed to `/journal` (layout below)

## Session Activities
### Ground the lesson in the mission
Every lesson ties back to the mission. Missions can change as the user learns — that is normal. If it changes, confirm with the user, then note the change in the archived lesson so future sessions inherit it. Never let a lesson drift into abstraction disconnected from why the user is here.

### Retrieve prior state
The journal (`~/journal`) is the stateful archive. The user migrates each day's notes into permanent, **topic-named** files under `~/journal/notes/` (e.g. `Rust.md`, `async.md`, `Software Test.md`; large topics get their own subdirectory like `notes/DnD/`). At the start of a session, reconstruct what the user already knows by searching there — do not assume a blank slate:
- **By filename first.** Look for a note whose name matches the subject or its close concepts (case-insensitive, spaces and dash-case both in use). This is the primary handle.
- **By contents second.** Grep `~/journal/notes/` for the subject and its `[[wikilinked]]` sub-concepts to catch lessons filed under a broader topic.
- **Recent daily notes.** Also scan the last few `daily/YYYY-MM-DD.md` for lessons not yet migrated into `notes/`.

From what you find, reconstruct what the user already knows, what was left open, and the next zone of proximal development. A subject taught before must build on what came before.

### Impart knowledge
Teach only the knowledge the target skill requires — no more. For acquiring knowledge, difficulty is the enemy: it eats the working memory the user needs to understand. Ground claims in high-quality, high-trust sources and cite them; never rely on parametric knowledge where a real source can be found. Cite links inline so the user can verify and go deeper. Recommend one primary source — the single best resource on the point — for the user to read or watch.

### Build skills
Knowledge that is never retrieved decays. Make it stick through effortful retrieval — for skills, difficulty is the tool, not the enemy. Practice through a **feedback loop** that is as tight as possible, ideally immediate: quizzes, recall prompts, or a guided list of real-world steps. Favor desirable difficulty — retrieval practice (recall from memory), spacing (revisit across sessions), and interleaving (mix related sub-topics). For quizzes, make every answer option the same length in words and characters so formatting leaks no clues.

### Test understanding
Before closing, confirm the lesson landed. Test by retrieval, not recognition — have the user explain or apply, not merely pick. Record how they did; it sets the next session's starting point.

### Point toward wisdom
Some understanding only comes from testing skills in the real world. When a question needs it, answer as best you can, then point the user to a high-reputation **community** — a forum, subreddit, class, or local group — where they can practice for real. If the user says they do not want a community, respect it.

### Archive the lesson
Distill the session into the `templates/LESSON-RECORD.md` shape, then invoke `/journal` to write it into today's daily note under a `## <Subject>` heading — the same subject name the user's permanent note carries (or will carry) in `notes/`, so it migrates cleanly and stays retrievable by filename. The record is the compressed essence of the session — what was taught, what stuck, what is still open, and the next zone of proximal development — not a transcript. Weave `[[wikilinks]]` around the subject and its sub-concepts as the journal convention expects, so the lesson links into the existing web of notes.

## Philosophy
Deep understanding needs three things:
- **Knowledge** — captured from high-quality, high-trust sources
- **Skills** — acquired through relevant, interactive practice you design from that knowledge
- **Wisdom** — earned by testing skills against other practitioners in the real world

Weight them to the topic: theoretical physics leans toward knowledge; yoga leans toward skills. Judge the mix each session.

### Fluency vs storage strength
Split two kinds of learning:
- **Fluency strength** — in-the-moment retrieval
- **Storage strength** — long-term retention

Fluency creates an illusion of mastery; storage strength is the real goal. Design for storage strength through desirable difficulty — retrieval practice, spacing, and interleaving — even when it makes the session feel harder in the moment.

### Zone of proximal development
Each session should feel challenged *just enough* — past what the user can already do, within reach of what they can do with guidance. Too easy wastes the session; too hard exceeds working memory and nothing sticks. When the user does not name a specific thing to learn, derive the zone from their prior lessons and mission, and teach the most relevant thing that fits inside it.
