//! Parse a single board's `TRACKER.md` text into ordered [`Task`] records.
//!
//! The record boundary and field grammar are the shared contract (SPEC,
//! "TRACKER.md format & parse contract"): a new record begins ONLY where a `# `
//! header is immediately followed by an `ID:` line and a `State:` line — so a
//! stray `# ` line inside a Description is not a new record. Fields appear in a
//! fixed order (Title, ID, State, Blocker, the terminal Completed:/Cancelled:
//! slot, Description), and the Description is unrestricted and runs until the
//! next valid header.

/// A task's lifecycle state.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum State {
    Todo,
    InProgress,
    Blocked,
    Complete,
    Cancelled,
    Archived,
}

/// One reference in a task's `Blocker:` list. The colon is the discriminator:
/// a bare integer is an internal ref; `path:id` names another project's board.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum BlockerRef {
    /// A ticket ID on this same board.
    Internal(u64),
    /// A `<repo-relative project path>:<ticket-id>` reference to another board.
    Cross { path: String, id: u64 },
}

/// The terminal timestamp slot — present only on a terminal task. Holds the raw
/// ISO 8601 UTC text; timestamp arithmetic belongs to the archive sweep, not here.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Terminal {
    Completed(String),
    Cancelled(String),
}

/// A single parsed task record.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Task {
    pub title: String,
    pub id: u64,
    pub state: State,
    /// The `Blocker:` references in file order; empty for `Blocker: None`.
    pub blocker: Vec<BlockerRef>,
    /// The terminal `Completed:`/`Cancelled:` slot, if the task is terminal.
    pub terminal: Option<Terminal>,
    /// The unrestricted, possibly multi-line Description.
    pub description: String,
}

/// Parse a single board's text into ordered task records (file order preserved).
///
/// The contract is well-formed board text. As a provisional policy a record
/// whose fields don't parse (e.g. a non-integer `ID:`, an unknown `State:`) is
/// skipped rather than panicking, so one bad block can't crash the viewer;
/// surfacing malformed input properly belongs to the `load` seam (task ID 3).
pub(crate) fn parse(text: &str) -> Vec<Task> {
    let lines: Vec<&str> = text.lines().collect();
    // A record starts ONLY at a `# ` header immediately followed by `ID:` then
    // `State:` — so a stray `# ` line inside a Description is not a boundary.
    let starts: Vec<usize> = (0..lines.len())
        .filter(|&i| is_record_start(&lines, i))
        .collect();
    starts
        .iter()
        .enumerate()
        .filter_map(|(n, &start)| {
            let end = starts.get(n + 1).copied().unwrap_or(lines.len());
            parse_record(&lines[start..end])
        })
        .collect()
}

fn is_record_start(lines: &[&str], i: usize) -> bool {
    lines.get(i).is_some_and(|l| l.starts_with("# "))
        && lines.get(i + 1).is_some_and(|l| l.starts_with("ID:"))
        && lines.get(i + 2).is_some_and(|l| l.starts_with("State:"))
}

/// Parse one record's slice: header, ID, State, Blocker, an optional terminal
/// slot, then the Description running to the end of the slice. `None` if a
/// required field is malformed.
fn parse_record(rec: &[&str]) -> Option<Task> {
    let title = rec.first()?.strip_prefix("# ")?.trim().to_string();
    let id = rec.get(1)?.strip_prefix("ID:")?.trim().parse().ok()?;
    let state = parse_state(rec.get(2)?.strip_prefix("State:")?.trim())?;
    let blocker = parse_blocker(rec.get(3)?.strip_prefix("Blocker:")?.trim())?;

    // The terminal slot is optional; when absent, `rest` starts at the Description.
    let mut rest = rec.get(4..).unwrap_or(&[]);
    let terminal = take_terminal(&mut rest);

    Some(Task {
        title,
        id,
        state,
        blocker,
        terminal,
        description: parse_description(rest),
    })
}

/// Take an optional terminal line (`Completed:`/`Cancelled:`) off the front of
/// `rest`, advancing it past the line when one is present.
fn take_terminal(rest: &mut &[&str]) -> Option<Terminal> {
    let line = rest.first()?;
    let terminal = if let Some(ts) = line.strip_prefix("Completed:") {
        Terminal::Completed(ts.trim().to_string())
    } else {
        Terminal::Cancelled(line.strip_prefix("Cancelled:")?.trim().to_string())
    };
    *rest = &rest[1..];
    Some(terminal)
}

fn parse_state(s: &str) -> Option<State> {
    Some(match s {
        "TODO" => State::Todo,
        "IN PROGRESS" => State::InProgress,
        "BLOCKED" => State::Blocked,
        "COMPLETE" => State::Complete,
        "CANCELLED" => State::Cancelled,
        "ARCHIVED" => State::Archived,
        _ => return None,
    })
}

/// `None` for `Blocker: None`; otherwise each comma-separated ref. The colon
/// discriminates a cross-project `path:id` from a bare internal ID. Returns
/// `None` if any ref's integer part is malformed.
fn parse_blocker(s: &str) -> Option<Vec<BlockerRef>> {
    if s == "None" {
        return Some(Vec::new());
    }
    s.split(',')
        .map(|r| {
            let r = r.trim();
            match r.split_once(':') {
                Some((path, id)) => Some(BlockerRef::Cross {
                    path: path.trim().to_string(),
                    id: id.trim().parse().ok()?,
                }),
                None => Some(BlockerRef::Internal(r.parse().ok()?)),
            }
        })
        .collect()
}

/// Reassemble the Description from its `Description:` line onward. The first
/// line's prefix is stripped; subsequent lines (blank lines included) are kept
/// verbatim, and trailing whitespace before the next record is trimmed away.
fn parse_description(rest: &[&str]) -> String {
    let Some((first, tail)) = rest.split_first() else {
        return String::new();
    };
    let first = first
        .strip_prefix("Description:")
        .unwrap_or(first)
        .trim_start();
    let mut out = String::from(first);
    for line in tail {
        out.push('\n');
        out.push_str(line);
    }
    out.trim_end().to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    // Build a one-task board that varies only its `Blocker:` line, so a blocker
    // test asserts the grammar and nothing else.
    fn board_with_blocker(blocker: &str) -> String {
        format!("# T\nID: 1\nState: BLOCKED\nBlocker: {blocker}\nDescription: d\n")
    }

    // Parse a board expected to hold exactly one task, and return it.
    fn parse_one(board: &str) -> Task {
        let tasks = parse(board);
        assert_eq!(
            tasks.len(),
            1,
            "expected exactly one task, got {}",
            tasks.len()
        );
        tasks.into_iter().next().unwrap()
    }

    #[test]
    fn parses_multiple_tasks_in_file_order() {
        let board = "\
# First
ID: 1
State: TODO
Blocker: None
Description: the first task

# Second
ID: 2
State: IN PROGRESS
Blocker: None
Description: the second task
";
        let tasks = parse(board);
        assert_eq!(tasks.len(), 2);
        assert_eq!(tasks[0].id, 1);
        assert_eq!(tasks[0].title, "First");
        assert_eq!(tasks[0].state, State::Todo);
        assert_eq!(tasks[1].id, 2);
        assert_eq!(tasks[1].title, "Second");
        assert_eq!(tasks[1].state, State::InProgress);
    }

    #[test]
    fn a_hash_line_inside_a_description_is_not_a_new_record() {
        // The `# ...` line is NOT followed by `ID:`/`State:`, so it is prose
        // inside the Description — the board still holds exactly one record.
        let board = "\
# Only task
ID: 1
State: TODO
Blocker: None
Description: intro line
# Not a header, just prose
more prose
";
        let task = parse_one(board);
        assert_eq!(task.id, 1);
        assert!(task.description.contains("# Not a header, just prose"));
        assert!(task.description.contains("more prose"));
    }

    #[test]
    fn a_multiline_description_runs_until_the_next_header() {
        let board = "\
# Verbose
ID: 1
State: TODO
Blocker: None
Description: line one

line two after a blank line

# Next
ID: 2
State: TODO
Blocker: None
Description: other
";
        let tasks = parse(board);
        assert_eq!(tasks.len(), 2);
        assert!(tasks[0].description.contains("line one"));
        assert!(tasks[0].description.contains("line two after a blank line"));
        // The next record's content must not bleed into the first's Description.
        assert!(!tasks[0].description.contains("other"));
    }

    #[test]
    fn blocker_none_parses_as_no_refs() {
        let task = parse_one(&board_with_blocker("None"));
        assert!(task.blocker.is_empty());
    }

    #[test]
    fn a_bare_integer_blocker_is_an_internal_ref() {
        let task = parse_one(&board_with_blocker("3"));
        assert_eq!(task.blocker, vec![BlockerRef::Internal(3)]);
    }

    #[test]
    fn a_path_colon_id_blocker_is_a_cross_project_ref() {
        let task = parse_one(&board_with_blocker("apps/foo:5"));
        assert_eq!(
            task.blocker,
            vec![BlockerRef::Cross {
                path: "apps/foo".to_string(),
                id: 5
            }],
        );
    }

    #[test]
    fn a_comma_list_parses_each_ref_in_order() {
        let task = parse_one(&board_with_blocker("3, apps/foo:5, 7"));
        assert_eq!(
            task.blocker,
            vec![
                BlockerRef::Internal(3),
                BlockerRef::Cross {
                    path: "apps/foo".to_string(),
                    id: 5
                },
                BlockerRef::Internal(7),
            ],
        );
    }

    #[test]
    fn a_complete_task_captures_its_completed_timestamp() {
        let board = "\
# Done
ID: 4
State: COMPLETE
Blocker: None
Completed: 2026-07-26T14:03:00Z
Description: finished
";
        let task = parse_one(board);
        assert_eq!(task.state, State::Complete);
        assert_eq!(
            task.terminal,
            Some(Terminal::Completed("2026-07-26T14:03:00Z".to_string())),
        );
    }

    #[test]
    fn a_cancelled_task_captures_its_cancelled_timestamp() {
        let board = "\
# Abandoned
ID: 4
State: CANCELLED
Blocker: None
Cancelled: 2026-07-26T14:03:00Z
Description: thrown away
";
        let task = parse_one(board);
        assert_eq!(task.state, State::Cancelled);
        assert_eq!(
            task.terminal,
            Some(Terminal::Cancelled("2026-07-26T14:03:00Z".to_string())),
        );
    }

    #[test]
    fn a_non_terminal_task_has_no_terminal_timestamp() {
        let task = parse_one(&board_with_blocker("None"));
        assert_eq!(task.terminal, None);
    }
}
