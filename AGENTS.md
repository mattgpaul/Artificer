# AGENTS.md

Roadmap for agents working in **Artificer** — Matthew's robotics lab monorepo.
Read this first. It describes the *shape* of the repo and the conventions that
hold across it, so you can find what you're looking for without an inventory of
every project (which changes constantly — this file intentionally does not).

## What this repo is

A **Nix-first monorepo**. NixOS and Nix flakes are the source of truth for both
system configuration and dev environments. Assume anything you build or run
happens inside a Nix-provided shell, not against ambient system tooling.

The repo uses a **single root flake** for everything: NixOS hosts, shared
per-language dev shells, and deployable packages. It is backed by one root
**Cargo workspace** (`Cargo.toml` + one `Cargo.lock`) for Rust and one root
**uv workspace** (`pyproject.toml` + one `uv.lock`) for Python. Individual
projects do **not** carry their own `flake.nix`; they carry a one-line `.envrc`
that selects a shared dev shell from the root flake.

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
| `flake.nix` | Root flake — NixOS hosts **and** shared dev shells (`#rust`, `#python`) **and** deployable `packages.*`. |
| `Cargo.toml` | Root Rust workspace (virtual manifest). Lists every crate member; one shared `Cargo.lock`. |
| `pyproject.toml` | Root uv workspace (virtual root). Lists every Python member; one shared `uv.lock`. |

## Conventions that hold repo-wide

- **Nix-first, always.** Don't reach for globally-installed toolchains. If a
  project needs a runtime, it comes from a Nix shell.
- **Shared dev shells from the root flake.** Dev environments are defined once,
  per language, in the root `flake.nix` (`devShells.rust`, `devShells.python`).
  A project opts in with a one-line `.envrc` — e.g.
  `use flake "$(git rev-parse --show-toplevel)#rust"` — which direnv auto-loads
  when you `cd` in. Presence of `.envrc` marks a project as wired up; its absence
  means the toolchain isn't selected yet (treat as WIP). Do **not** add a
  per-project `flake.nix`; extend the shared shell (or add a `package.nix`, see
  below) instead.
- **The root flake does hosts + dev shells + packages.** One flake at the repo
  root builds `nixosConfigurations` (hosts under `utils/nixos/`), exposes the
  shared dev shells, and exposes `packages.<name>` for deployable artifacts.
  Rust packages are auto-discovered from the `Cargo.toml` workspace members;
  Python packages are built from the uv workspace via uv2nix (active once a root
  `uv.lock` exists). A NixOS host deploys a project by referencing
  `self.packages.<system>.<name>`.
- **One lock per language, at the root.** Rust deps resolve into a single root
  `Cargo.lock`; Python deps into a single root `uv.lock`. Add an internal
  dependency between projects via the workspace (Cargo `path = ...` /
  uv `{ workspace = true }`), never by publishing. Bootstrapping after a new
  member: `cargo generate-lockfile` (Rust) or `uv lock` (Python) to refresh the
  root lock; `nix flake lock` if you touched flake inputs.
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

- **"Where does an app build/run?"** → `cd` into the app's folder; its `.envrc`
  loads the shared dev shell. Build/deploy from the repo root with
  `nix build .#<name>` (packages are defined in the root `flake.nix`, members in
  the root `Cargo.toml`/`pyproject.toml`).
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
directory → the project's `.envrc` (which shared dev shell it selects) and its
entry in the root `Cargo.toml`/`pyproject.toml` for its toolchain → its `adr/` for
intent → the project's own tests (in-file unit tests and the crate's `tests/`) for
expected behavior. Confirm the dev shell before running anything.
