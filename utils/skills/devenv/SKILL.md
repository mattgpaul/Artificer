---
name: devenv
description: "Explicit command only (/devenv). Do not auto-invoke. Reads a project's SPEC.md (and TRACKER.md if needed) and creates or updates its Nix dev shell (flake.nix + .envrc) and language manifest (e.g. Cargo.toml) so the project builds. Sets up the toolchain only — no business logic, no tests."
---

# devenv
The objective is to make a project **buildable**: read what it needs, then create
or update its per-project dev environment so `direnv`/`nix develop` drops you into
a shell where the language's build and test commands just work. This is a
prefactor step, not a feature step — you wire up the toolchain, nothing else. No
business logic, no tests (that is `/tdd`), no source beyond the minimum a manifest
needs to be valid.

## Where this sits in the pipeline
`/to-spec` → `SPEC.md` → `/devenv` → **buildable dev shell** → `/to-tasks` →
`TRACKER.md` → `/tdd`.

`/devenv` fills the gap `/tdd` refuses to fake: its step 4 requires a project's
dev shell + buildable scaffold to already exist (`flake.nix` + `.envrc`; the crate
compiles). When they don't, that is *this* skill's job. Run it once to stand a
project up, and again any time the SPEC adds a dependency the shell doesn't have
yet — it is idempotent by design.

## The convention it targets
This repo is **Nix-first**: a project's dev environment is its own `flake.nix`
(auto-loaded by `.envrc` via direnv), never ambient system tooling (see
`AGENTS.md`). The settled Rust shape, matched across `libs/computer_telemetry`,
`apps/telemetry_tdd_qwen`, and friends, is:

- **`flake.nix`** — `flake-utils.lib.eachDefaultSystem`, a `pkgs.mkShell` whose
  `buildInputs` are `rustc cargo clippy rustfmt` plus whatever *system* deps the
  SPEC calls for (e.g. `pkg-config`, `openssl`). Follow the existing files as the
  template; don't invent a new structure.
- **`.envrc`** — the single line `use flake`.
- **`Cargo.toml`** — `[package]` with the project name, `edition = "2024"`, and
  only the crate dependencies the SPEC actually names. Empty `[dependencies]` is
  fine to start.
- **`.gitignore`** — the standard Rust ignore set (`target/`, coverage artifacts,
  `.cargo/`, IDE/OS cruft); copy an existing project's verbatim.

`flake.lock` and `Cargo.lock` are **generated** — let `nix`/`cargo` write them;
don't hand-author them. Other runtimes follow the same principle at their native
seam (e.g. a Python project's `flake.nix` provides the interpreter; `apps/shortcuts`
is the precedent) — mirror the nearest existing project of that runtime rather than
generalizing from Rust.

## On invocation
1. **Find the project.** The current directory, the nearest ancestor that owns a
   `SPEC.md`, or a directory the user names.
2. **Read what it needs.** Read `SPEC.md` — the runtime, whether it's a lib or a
   binary, and any dependencies (system packages and language crates) it names.
   Read `TRACKER.md` only if the SPEC is thin and the tasks reveal a dependency.
   Don't guess at deps the project doesn't ask for.
3. **Look at the nearest precedent.** Open the `flake.nix`/`.envrc`/`Cargo.toml`
   of an existing project of the same runtime and match its structure. Consistency
   with the repo beats cleverness.
4. **Create or update — idempotently.**
   - *New project:* write `flake.nix`, `.envrc`, the manifest, and `.gitignore`
     from the convention above.
   - *Existing env:* read the current files and change only what's needed — add a
     missing `buildInput` or dependency, fix a drifted field. Preserve the user's
     edits; don't clobber a working shell to "normalize" it.
5. **Bring the shell up and prove it builds.** `direnv allow` (or `nix develop`),
   then run the runtime's cheapest build check (Rust: `cargo check` / `cargo
   metadata`) to confirm the shell resolves and the manifest is valid. Let the lock
   files generate here.
6. **Report and stop.** Say which files you created vs updated, what deps you added
   and why (tie each to the SPEC), and the proof the shell builds. Note that source,
   tests, and business logic are out of scope — `/tdd` and GREEN come next.

## Do / Don't
- DO read `SPEC.md` first and add only the dependencies it actually names; tie each
  addition back to a spec need.
- DO match the nearest existing project's `flake.nix`/`.envrc`/manifest structure —
  Nix-first, direnv-loaded, per-project.
- DO make it idempotent: on an existing env, edit surgically and preserve the user's
  changes; only add or fix what's missing.
- DO bring the shell up and run a cheap build check to prove it works; let
  `flake.lock` / `Cargo.lock` generate.
- DON'T write business logic, source modules, or tests — that's `/tdd` and GREEN.
- DON'T add speculative dependencies, a second runtime, or structure the SPEC didn't
  ask for.
- DON'T reach for ambient/global toolchains or hand-author lock files.
- DON'T re-open design/spec decisions — those are `/architect`, `/to-spec`,
  `/to-tasks`.
