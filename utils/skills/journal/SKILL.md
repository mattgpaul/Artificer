---
name: journal
description: Record and summarize the current conversation into Matthew's Obsidian journal at ~/journal. Use when the user says "journal this", "add this to my journal / daily notes", "write this up in Obsidian", "log this session", or asks to capture what was learned/done into their notes.
---

# Journal
The objective is to turn the conversation — or a requested slice of it — into notes that fit Matthew's existing Obsidian vault so cleanly they look hand-written. The goal is a durable, linkable record, not a transcript: summarize, distill the lessons, and keep the code. Everything goes into today's daily note and nowhere else; Matthew relocates content into permanent concept notes himself as a morning ritual.

## On invocation
1. Run `date +%F` to get today (don't assume). The daily note is `daily/<that>.md`.
2. Skim 2–3 existing notes near the topic (`notes/<Topic>.md`, recent dailies) to match tone, tags, and which `[[links]]` already exist.
3. Distill the conversation into lessons / decisions / next-steps — not a transcript.
4. Read the target daily note, then append under a new or existing `## <Topic>` H2 heading (create the file only if needed).
5. Weave in `[[backlinks]]`, `#tags`, and fenced code blocks; end open threads as `- [ ]` tasks where that fits the vault's habit.
6. Tell the user exactly which files you touched and what you added.

## Vault location & layout
Root: `/home/matthew/journal`
- `daily/` — one note per day, filename `YYYY-MM-DD.md`. Day-to-day log: tasks, what happened, quick reflections grouped under `## Topic` headings.
- `notes/` — durable **concept** notes (e.g. `Rust.md`, `async.md`, `ownership.md`, `Microlib.md`). Evergreen knowledge, aggregated over time. Large topics get their own subdirectory (e.g. `notes/SciFi Book/`).
- `templates/` — `daily.md`, `note.md`. Don't edit these; use them as the shape for new files.

## Session Activities
### Write only to the daily note
**Always the daily note (`daily/YYYY-MM-DD.md`), and only the daily note.** Append the full write-up — reflection, code, backlinks, tags — under a new H2 `## <Topic>` heading (e.g. `## Software`, `## Microlib`, `## Rust`). Adding that H2 heading every time is non-negotiable.

**Do NOT touch concept notes in `notes/`.** Matthew relocates content from the daily note into concept notes himself — that placement is his job, not the skill's. Don't split the write-up across files, don't create concept notes, don't edit existing ones. Put everything the user asked for in the daily note and leave the rest of the vault alone.

**Always append; never overwrite.** Read the daily note first. If a matching `## <Topic>` heading already exists for today, add under it rather than duplicating.

### Backlink liberally
Wrap concepts in `[[wikilinks]]` inline as they appear in prose — `[[trait]]`, `[[async]]`, `[[ownership]]`, `[[Option]]`. Use piped links for grammar: `[[iterator|iterators]]`, `[[borrow|borrowed]]`. A link to a not-yet-existing note is fine and encouraged — it seeds future notes. Prefer linking to notes that already exist in `notes/` when the concept matches.

### Tag where the vault does
Use tags where the vault uses them: `#rust`, `#microlib`, `#nixos`, `#artificer`, `#testing`. Tags ride at the end of task lines and section intros.

### Keep the code
Do not skimp on code. Matthew's own note says "code for reference" and pastes whole modules. Use fenced ```rust blocks. Prefer showing the *shape* of a fix, a minimal failing example, or a compiler message over describing it in prose. When a bug hinged on a detail (a unit conversion, a borrow, an assert), show the before/after or the actual error text.

### Match the voice
Match the surrounding notes: concept notes are instructional/descriptive (like `async.md`); daily reflections are first-person and candid. Keep it his voice, not a chatbot summary. Distill — bullets and short sections beat walls of text.

### Frontmatter and headings
New concept notes may start with the `note.md` template frontmatter (`uplinks:` / `created:` with today's date). Daily notes have no frontmatter. Daily topic sections are `## Topic`. Within concept notes, dated sections are `# YYYY-MM-DD` then `## Topic`, with `###` for sub-points.
