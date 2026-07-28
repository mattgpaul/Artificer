//! task_tracker — a consolidated viewer over per-project `TRACKER.md` boards.
//!
//! Real modules land incrementally via `/tdd`. Currently implemented surface:
//! the single-board parser (task ID 2). Discovery, the archive/unblock sweeps,
//! and the ratatui TUI arrive in later tasks.

// `parse` is internal (the settled public seam is `load`, task ID 3). Until
// `load` consumes it, its only non-test caller is absent, so allow dead_code.
#[allow(dead_code)]
pub mod parse;

pub use parse::{BlockerRef, State, Task, Terminal};
