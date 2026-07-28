# AGENTS.md

Roadmap for agents working in **Artificer** — Matthew's robotics lab monorepo.
Read this first. It describes the *shape* of the repo and the conventions that
hold across it, so you can find what you're looking for without an inventory of
every project (which changes constantly — this file intentionally does not).

## What this repo is

A **Nix-first monorepo**. NixOS and Nix flakes are the source of truth for both
system configuration and per-project dev environments. Assume anything you build
or run happens inside a Nix-provided shell, not against ambient system tooling.

Version control: both **git** and **jj** (jujutsu) are initialized here (`.git`,
`.jj`). Use the workflow the user asks for; don't assume plain git-only.

## Top-level map

The top-level directories are stable; their *contents* are not. Learn what each
directory is *for*, then look inside for current projects.

| Directory | What it is for |
|-----------|----------------|
| `apps/`   | Deployable applications — the things that actually run. |
| `libs/`   | Shared libraries consumed by `apps/`. Check here before writing a new helper. |
| `utils/`  | Dev environment & system config — NixOS hosts, editor/WM dotfiles, agent skills. |
| `tests/`  | Cross-`apps/` end-to-end tests only. A single project's tests live *with* that project (see Testing below). |
| `docs/`   | Cross-cutting documentation. |
| `flake.nix` | Root flake — defines **NixOS host configs only**, not dev shells. |

## Conventions that hold repo-wide

- **Nix-first, always.** Don't reach for globally-installed toolchains. If a
  project needs a runtime, it comes from a Nix shell.
- **Per-project dev shells via direnv + flake.** A project's dev environment is
  defined by *its own* `flake.nix` and auto-loaded by its `.envrc` (direnv).
  Workflow: `cd` into the project and direnv loads the shell (or run
  `nix develop` there). Presence of `flake.nix` + `.envrc` marks a project as set
  up; their absence means the dev shell isn't wired up yet (treat as WIP) — so
  check before assuming a toolchain exists.
- **Root flake ≠ dev shells.** The root `flake.nix` builds
  `nixosConfigurations` (the machine hosts under `utils/nixos/`). Don't look
  there for how to build an app.
- **Tests live with the thing they test, at the runtime's native seam.** A
  project's tests sit *with* that project, not in a separate mirrored tree. For
  Rust: unit tests in-file (`#[cfg(test)] mod tests`), integration tests in the
  crate's own `tests/` directory (sibling to `src/`, compiled against the public
  API). The repo-level `tests/` tree is reserved for **cross-`apps/` end-to-end**
  tests that span more than one project — never a single project's tests. When you
  touch code, look for its tests beside it (in the file, or the crate's `tests/`),
  not under the repo-level `tests/`. Writing the failing tests first is the
  `/tdd` skill's job (`utils/skills/tdd/`).
- **ADRs live with the thing they decide.** Architecture Decision Records sit in
  an `adr/` folder inside the relevant project. Consult them before reworking a
  design — they explain the *why*.
- **System config lives in `utils/nixos/`.** Shared config, per-machine hosts
  (each with its own `hardware-configuration.nix`), reusable profiles, and users
  are organized there. Machine-specific questions start with that host's folder.

## Finding things fast

- **"Where does an app build/run?"** → look inside that app's folder for
  `flake.nix` + `.envrc`; `cd` there and let direnv load, then use that shell.
- **"Where are the tests for this?"** → with the thing: for Rust, unit tests
  in-file and integration tests in the crate's own `tests/`. The repo-level
  `tests/` is only for cross-`apps/` end-to-end tests.
- **"Why was this designed this way?"** → check the project's `adr/` folder.
- **"What shared helper already exists?"** → scan `libs/` before writing a new one.
- **"How is a machine configured?"** → `utils/nixos/hosts/<machine>/`.
- **"What agent skills exist?"** → `utils/skills/*/SKILL.md`.

## Exploration playbook

When mapping unfamiliar territory (this mirrors the `/architect` workflow in
`utils/skills/architect/`), walk top-down: this file → the relevant top-level
directory → the project's `flake.nix`/`.envrc` for its toolchain → its `adr/` for
intent → the project's own tests (in-file unit tests and the crate's `tests/`) for
expected behavior. Confirm the dev shell before running anything.
