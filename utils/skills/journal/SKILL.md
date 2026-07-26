---
name: journal
description: Record and summarize the current conversation into Matthew's Obsidian journal at ~/journal. Use when the user says "journal this", "add this to my journal / daily notes", "write this up in Obsidian", "log this session", or asks to capture what was learned/done into their notes. Produces vault-native Markdown — [[wikilinks]], #tags, and generous ```rust code blocks — following the conventions below.
---

# journal — capture a session into the Obsidian vault

Turn the conversation (or a requested slice of it) into notes that fit Matthew's existing Obsidian vault so cleanly they look hand-written. The goal is a durable, linkable record — not a transcript. Summarize, distill the lessons, and keep the code.

## Vault location & layout

Root: `/home/matthew/journal`

- `daily/` — one note per day, filename `YYYY-MM-DD.md`. Day-to-day log: tasks, what happened, quick reflections grouped under `## Topic` headings.
- `notes/` — durable **concept** notes (e.g. `Rust.md`, `async.md`, `ownership.md`, `Microlib.md`). Evergreen knowledge, aggregated over time.
- `templates/` — `daily.md`, `note.md`. Don't edit these; use them as the shape for new files.

**Get the date first.** Run `date +%F` (don't assume). The daily note is `daily/<that>.md`.

## Where does this session go?

**Always the daily note (`daily/YYYY-MM-DD.md`), and only the daily note.** Append the full write-up — reflection, code, backlinks, tags — under a new H2 `## <Topic>` heading (e.g. `## Software`, `## Microlib`, `## Rust`). Adding that H2 heading every time is non-negotiable.

**Do NOT touch concept notes in `notes/`.** Matthew relocates content from the daily note into concept notes himself as a morning ritual — that placement is his job, not the skill's. Don't split the write-up across files, don't create concept notes, don't edit existing ones. Put everything the user asked for in the daily note and leave the rest of the vault alone.

**Always append; never overwrite.** Read the daily note first. If a matching `## <Topic>` heading already exists for today, add under it rather than duplicating.

## Formatting conventions (match these exactly)

- **Backlinks, liberally.** Wrap concepts in `[[wikilinks]]` inline as they appear in prose — `[[trait]]`, `[[async]]`, `[[ownership]]`, `[[Option]]`. Use piped links for grammar: `[[iterator|iterators]]`, `[[borrow|borrowed]]`. A link to a not-yet-existing note is fine and encouraged — it seeds future notes. Prefer linking to notes that already exist in `notes/` when the concept matches.
- **Tags** where the vault uses them: `#rust`, `#microlib`, `#nixos`, `#artificer`, `#testing`. Tags ride at the end of task lines and section intros.
- **Code snippets — do not skimp.** Matthew's own note says "code for reference" and pastes whole modules. Use fenced ```rust blocks. Prefer showing the *shape* of a fix, a minimal failing example, or a compiler message over describing it in prose. When a bug hinged on a detail (a unit conversion, a borrow, an assert), show the before/after or the actual error text.
- **Voice.** Match the surrounding notes: concept notes are instructional/descriptive (like `async.md`); daily reflections are first-person and candid. Keep it his voice, not a chatbot summary. Distill — bullets and short sections beat walls of text.
- **Frontmatter.** New concept notes may start with the `note.md` template frontmatter (`uplinks:` / `created:` with today's date). Daily notes have no frontmatter.
- **Headings.** Daily topic sections are `## Topic`. Within concept notes, dated sections are `# YYYY-MM-DD` then `## Topic`, with `###` for sub-points.

## Process

1. `date +%F` for today; locate `daily/<date>.md`.
2. Skim 2–3 existing notes near the topic (`notes/<Topic>.md`, recent dailies) to match tone, tags, and which `[[links]]` already exist.
3. Distill the conversation into lessons/decisions/next-steps — not a transcript.
4. Read the target file, then append (create only if needed).
5. Weave in `[[backlinks]]`, `#tags`, and ```rust snippets. End open threads as `- [ ]` tasks where that fits the vault's habit.
6. Tell the user exactly which files you touched and what you added.
