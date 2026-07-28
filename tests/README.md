# tests/ — cross-`apps/` end-to-end tests

This tree is reserved for **end-to-end tests that span more than one project** —
scenarios that exercise several `apps/` (and/or `libs/`) wired together, where no
single crate is the right home.

It is **not** where a single project's tests go. Tests live *with* the thing they
test, at the runtime's native seam:

- **Rust** — unit tests in-file (`#[cfg(test)] mod tests`); integration tests in
  the crate's own `tests/` directory (sibling to `src/`), against the public API.
- **Other runtimes** — the language's native test location, beside the code.

See `AGENTS.md` for the repo-wide convention and `utils/skills/tdd/` for the
`/tdd` skill that writes the failing (red) tests first.

Empty for now — the repo is young. The first cross-project e2e suite lands here.
