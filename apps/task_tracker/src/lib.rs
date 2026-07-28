//! task_tracker — a consolidated viewer over per-project `TRACKER.md` boards.
//!
//! Real modules land incrementally via `/tdd`. Currently implemented surface:
//! the single-board parser (task ID 2). Discovery, the archive/unblock sweeps,
//! and the ratatui TUI arrive in later tasks.

pub mod parse;

pub use parse::{BlockerRef, State, Task, Terminal};
