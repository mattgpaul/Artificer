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
pub(crate) fn parse(text: &str) -> Vec<Task> {
    let _ = text;
    todo!("parse a single board's text into ordered Task records")
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
        assert_eq!(tasks.len(), 1, "expected exactly one task, got {}", tasks.len());
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
            vec![BlockerRef::Cross { path: "apps/foo".to_string(), id: 5 }],
        );
    }

    #[test]
    fn a_comma_list_parses_each_ref_in_order() {
        let task = parse_one(&board_with_blocker("3, apps/foo:5, 7"));
        assert_eq!(
            task.blocker,
            vec![
                BlockerRef::Internal(3),
                BlockerRef::Cross { path: "apps/foo".to_string(), id: 5 },
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
