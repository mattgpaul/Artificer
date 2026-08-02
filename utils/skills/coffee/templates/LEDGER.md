<!--
LEDGER.md — running Leitner ledger for /coffee. The live copy lives in the vault
at ~/journal/coffee/LEDGER.md (this file in the skill is the starting shape only).

Boxes and intervals, in days: 1→1, 2→3, 3→7, 4→16, 5→35.
Pass promotes one box; a miss resets to box 1. A pass out of box 5 graduates that
concept into notes/<Topic>.md; when the last concept under a daily ## <Topic>
heading graduates, the section collapses to a [[Topic]] stub.

due = last_reviewed + interval[box]. Due dates are calendar days — skipped days
pile up and a run clears the whole accrued queue.

The unit is the CONCEPT, not the heading. One ## <Topic> section in a daily can
hold several concepts; each is its own row with its own box and due date, and gets
its own question. Topic = the heading / future notes/<Topic>.md; Concept = the
specific idea. Siblings sharing a Topic graduate independently into the same note.
-->

# Coffee — Spaced Repetition Ledger

## Box schedule
| Box | Interval (days) |
|-----|-----------------|
| 1   | 1  |
| 2   | 3  |
| 3   | 7  |
| 4   | 16 |
| 5   | 35 |

## Active
<!-- One row per concept. Several rows can share a Topic; each has its own box/due.
     For a single-idea heading, Topic and Concept may be the same name.
     History is a short outcome trail, e.g. "enrolled; 08-02 pass→2; 08-05 miss→1". -->
| Topic | Concept | Box | Last reviewed | Due | Source | History |
|-------|---------|-----|---------------|-----|--------|---------|
|       |         |     |               |     |        |         |

## Graduated
<!-- One row per concept that passed out of box 5 and landed in a permanent note. -->
| Topic | Concept | Graduated | Passes | Note |
|-------|---------|-----------|--------|------|
|       |         |           |        |      |

## Excluded
<!-- Concepts (or whole topics) opted out of review. Never enrolled, even if
     captured again. Mirrored by a #no-coffee tag in the daily. Use "—" for
     Concept when the whole Topic is opted out. -->
| Topic | Concept | Reason |
|-------|---------|--------|
|       |         |        |
