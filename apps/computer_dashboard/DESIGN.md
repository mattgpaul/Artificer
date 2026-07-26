# computer_dashboard — Design

## Overview
Production Rust replacement for the two telemetry MVPs (`apps/telemetry` = Python collectors + Prom/Grafana/JS; `apps/telemetry_rust` = Rust collector with no export). Same host metrics collected today. Reusable code → `libs/`.

## Glossary
| Term | Meaning |
|------|---------|
| Telemetry Node (Node) | The service on each monitored box that collects and exposes the defined metrics. |
| Collector | The central service that pulls from Nodes, holds latest state, and streams it out over SSE. |
| Dashboard | The Ratatui TUI client that connects to the Collector's SSE stream and renders it. |

## Decisions
- **Topology: Collector + Node** (→ ADR) — each Node exposes the defined metrics; the Collector pulls from Nodes and serves the dashboards. Pull/scrape model.
- **Graceful degradation** — Collector must not collapse when a Node is unreachable, data is missing, or values are NaN (applies even locally, e.g. a box powered off). Missing/stale is a normal state, not an error.
- **localhost first** — build and prove the single-box case before any network exposure.
- **Staged exposure** — works on `localhost` first, then local network, then wider LAN/WAN. Bind/auth defaults follow this progression.
- **Node interface: HTTP + JSON** — Node exposes a JSON endpoint over HTTP; Collector pulls it. Our own schema (typed, per-core arrays, device labels, explicit missing). Prometheus text format deferred to v2 for the optional Grafana path.
- **Shared code → `libs/computer_telemetry`, kept generic** — lib holds portable, platform-agnostic abstractions; OS-/hardware-specific collection sits *behind* those abstractions.
  - **Lib design:** generic trait per metric family + neutral data-model/schema structs in the lib; Linux/AMD implementations gated by `#[cfg]` + feature flags (e.g. `linux`, `amd-gpu`). New platforms = new gated module, no API change. Node enables the features it needs.
  - **OS scope: Linux-only now, designed for more** — build/ship only the Linux backend in v1; keep trait/`cfg` seams so Windows/macOS modules can be added later with no API change. localhost-first already implies Linux-first.
  - **Collection backend: `sysinfo` baseline + Linux enrichment** — cross-platform `sysinfo` crate supplies the portable floor (CPU%, mem, disk, net, processes) on any OS; hand-rolled sysfs/procfs stays behind `#[cfg(linux)]` for Linux-only richness (AMD GPU temps/power/clocks, per-core %, link carrier, precise sensors). Makes future Win/macOS support nearly free; heterogeneous fleets just report less (missing = `Option`).
  - **Missing = `Option`** — absent/unavailable readings are first-class `Option` values in the model (never NaN/error), carrying graceful degradation from the source up.
  - **Autodetection** — machine-specific parameters (primary NIC, GPU card/hwmon, CPU temp sensor, root disk) are autodetected at runtime; nothing hardcoded to one box.
- **Three separate binaries in separate directories** under `apps/computer_dashboard` — `node`, `collector`, `dashboard` — distinguished and deployed independently.
- **Dashboard is a Ratatui TUI**, a standalone *client* binary (not a browser, not bundled in the Collector). Uses built-in `Chart`/`Sparkline`/`Gauge` widgets for the live meters and detail graphs.
- **Collector → Dashboard transport: SSE** — Collector exposes an SSE stream of snapshots over HTTP; Dashboard is an SSE client. Same endpoint could feed a browser UI later.
- **Collector holds latest snapshot per Node in memory** (live window) — a client connecting mid-stream gets current state immediately; a down/stale Node yields a null/stale snapshot, never a crash.
- **Decoupled timing** — Node samples in a background loop into a cached latest snapshot; the HTTP handler returns that cache, so pulls are cheap reads and deltas (net/CPU) stay correct regardless of pull rate. Collector pulls each Node per `pull_interval` and emits an SSE snapshot per cycle.
- **Sample loop lives in the Node binary** — lib stays pure/sync (traits + data model + collection fns, no `tokio`/timing). Node owns the background `tokio` loop that samples every `collection_interval` and writes the latest `Snapshot` into a shared cell (`tokio::sync::watch`/`ArcSwap`); the HTTP handler only reads that cell. Keeps the lib generic/portable per the OS-scope + `cfg`-seam decisions. Duplication is minimal — the Collector's loop does remote HTTP pulls, not local sampling, so a shared runner wouldn't serve it anyway.
- **Bounded, TTL'd caching** — cache holds only the single latest snapshot per source (overwritten in place, timestamped) with a TTL; past the TTL it's treated as stale, never served as fresh. Memory is O(#Nodes); no unbounded buffering (history is v2).
- **Intervals configurable**; defaults: Node `collection_interval` 1s, Collector `pull_interval` 1s, `stale_after` 3s.
- **Node states for Dashboard: `live` / `stale` / `unknown`** (stale = missed pulls past threshold; unknown = never reached). Neither is an error.
- **Node discovery: static TOML list** of Node endpoints; default is a single `127.0.0.1:<node-port>` entry (localhost-first). mDNS/zeroconf autodiscovery deferred to v2.
- **Config: TOML file + CLI/env overrides** per binary. Node: bind/port, collection interval, enabled metric features, processes top-N sort default. Collector: bind/port, Node endpoint list, pull interval, SSE settings. Dashboard: Collector URL, render prefs. On NixOS a module can render the TOML later; the app just reads a file.
- **Structure: standalone crates (Option A)** — no workspace. `libs/computer_telemetry` (own flake) + `apps/computer_dashboard/{node,collector,dashboard}` (each own flake/lock/target), path-dep on the lib. Follows the repo's per-dir-flake convention; matches the binaries' divergent deps (dashboard's TUI-only ratatui/crossterm shouldn't burden the collector service) + possible cross-arch profiles.
- **Shared JSON schema types live in the lib** — both Node and Collector import the data model from `libs/computer_telemetry` by path.
- **ADR 0001** — Collector + Node pull topology accepted (`adr/0001-collector-node-topology.md`).
- **ADR 0002** — Ratatui TUI dashboard over SSE accepted (`adr/0002-ratatui-tui-over-sse.md`).
- **ADR 0003** — Linux-first collection with a cross-platform seam (`sysinfo` baseline + `cfg`-gated sysfs enrichment) accepted (`adr/0003-linux-first-cross-platform-seam.md`).
- **Self-contained** — own the stack in Rust; no hard dependency on Prometheus/Grafana.
- **Live view is the product** — real-time metrics are a hard requirement.
- **Long-term history = v2** — persistent retention deferred; Grafana may be explored then for viewing stored data.
- **Scale: small multi-node** — a handful of the user's own boxes plus possibly a few friends'.
- **MVP apps removed once dashboard works** — delete `apps/telemetry` (Python+Prom/Grafana) and `apps/telemetry_rust` (Rust collector) after `computer_dashboard` reaches parity. Single source of truth; git history preserves them.
- **DESIGN.md at `apps/computer_dashboard/DESIGN.md`** — the app's natural home.

## Tech Stack
- **Async:** `tokio`. **HTTP server (Node + Collector):** `axum` (uniform; axum SSE for the stream). **SSE fan-out:** `tokio::sync::broadcast`.
- **HTTP client (Collector→Nodes):** `reqwest`. **SSE client (Dashboard):** `reqwest`/`reqwest-eventsource`.
- **TUI:** `ratatui` + `crossterm`. **Serde:** `serde` + `serde_json` + `toml`.
- **CLI/env:** `clap` (derive, `env`). **Logging:** `tracing` + `tracing-subscriber`. **Errors:** `thiserror` (lib) + `anyhow` (binaries).
- **Metric collection:** `sysinfo` (cross-platform baseline) + direct sysfs/procfs reads behind `#[cfg(linux)]` for enrichment.

## API Contract
- **Node:** `GET /snapshot` (latest cached JSON: identity + timestamp + families, missing = `null`), `GET /healthz`.
- **Collector:** `GET /stream` (SSE live feed), `GET /snapshot` (combined all-Nodes one-shot JSON), `GET /nodes` (Nodes + `live`/`stale`/`unknown`), `GET /healthz`.
- **SSE framing:** full combined snapshot per event (`event: snapshot`), not deltas — self-healing on reconnect/drop. Deltas = v2 optimization.
- **Schema versioning:** integer `schema_version` in every snapshot, tied to the lib, bumped only on breaking changes. Components tolerate unknown fields (serde) and warn + degrade on major mismatch, never crash.

## Metric Catalog
First-pass superset (the MVPs were minimal, not the scope). Extensible later. Missing values are `Option`.

- **CPU** — vendor, model, max_freq; temp (°C); per-core usage %; overall usage %.
- **GPU** (AMD first) — vendor/device; temps edge/junction/memory + critical/emergency; fan rpm + max; usage %; VRAM used + total; power W + max; clock current + max *(to implement)*; thermal_throttle.
- **Memory** — total; available/free.
- **Network** — primary NIC (autodetected), IPv4, max port speed; rx/tx bytes total; rx/tx bps; link up/carrier.
- **Storage** — root disk size, available; disk read/write B/s.
- **Processes** — top 5 (name, cpu%, mem%); sort key selectable: by CPU or by RAM.
- **System** — hostname, OS/pretty_name, kernel release, uptime, logged-in user.
- Dropped: `fps` (no real data source).

## Deployment & Packaging
Context: fleet is real `nixosConfigurations`: **sevro, cerebro, swordfish** (root flake → `utils/nixos/common.nix` + `utils/nixos/hosts/<host>/`). Intended shape: Nodes as systemd services on each box, Collector as a service on one, Dashboard launched interactively.
- **Nix builder: `rustPlatform.buildRustPackage`** — stdlib nixpkgs, no new *third-party* flake inputs (unlike crane/naersk), lean; matches the repo's keep-it-simple bent. Accepts whole-crate rebuilds (no per-dep caching layer). Each app flake gains a `packages` output alongside the existing devshell. (Root flake does gain path inputs to consume these — see Package→fleet wiring.)
- **NixOS integration: one module per service** — `node` flake exports `nixosModules.node`, `collector` flake exports `nixosModules.collector`, each with `enable`/bind/port/config options; wired into `utils/nixos/`. A host imports `node` always; `collector` only where wanted (one box). Mirrors the three-binary split. Target hosts: cerebro, sevro, and future boxes (not swordfish).
- **Node service hardening** — systemd sandbox with read access to `/sys`+`/proc`; exact directives (DynamicUser, ProtectSystem, sensor-path access) decided during implementation once collectors exist and sandbox-blocked sysfs paths can be tested. Hardening is Linux/systemd-only by definition.
- **Non-NixOS Linux: ignored for v1** — v1 targets the NixOS fleet only. Portable binary + generic systemd unit revisited later if a friend actually wants in. (Windows/macOS also deferred — see OS scope.)
- **Dashboard delivery: home-manager** — `dashboard` package added to the home-manager profile (user `PATH`) on boxes you drive it from. Per-user, no root, run interactively — not a systemd unit.
- **Package→fleet wiring: app flake owns its package, machine imports it as a flake input (Option 1)** — each app flake (`node`/`collector`/`dashboard`) gains a `packages` output (`rustPlatform.buildRustPackage`, derivation **inline in `flake.nix`**) + a `nixosModules.<svc>` output. The root `flake.nix` adds each app flake as a **path input** (`path:./apps/computer_dashboard/<svc>`) with `inputs.nixpkgs.follows = "nixpkgs"` (mandatory — kills nixpkgs skew / glibc mismatch, single nixpkgs eval). `mkHost` imports `inputs.<svc>.nixosModules.<svc>`; the module's `package` option defaults to that flake's package. Consistent with the standalone-per-dir-flake convention; `nix build ./apps/.../node` also works standalone.
  - **Current state (gap being closed):** root flake presently references *no* app/lib flakes (inputs = nixpkgs + home-manager only); app/lib flakes are devshell-only islands with their own independent nixos-unstable pins. This decision is what bridges them.
- **Build distribution: nothing for v1** — accept per-host compilation. With `buildRustPackage` (whole-crate rebuild, no dep-layer cache) each host compiles the Rust crate on `nixos-rebuild`, but at 2–3 boxes with infrequent changes that's tolerable. Conscious defer, not an oversight. **Revisit when rebuild times hurt or host count grows**, in this order: (1) register **cerebro as a remote builder** (`nix.buildMachines`, SSH — no new services) so lighter boxes offload compilation; (2) self-hosted binary cache (**attic**/**harmonia** on cerebro, the true "registry" analog) so artifacts are built once and substituted fleet-wide. Cachix (hosted) rejected — keep the stack self-owned.

## Security / Auth
- **Design seam now, defer impl** — v1 binds localhost-only (no auth needed). Define a pluggable auth layer + a config slot on both hops (Node→Collector, Collector→Dashboard) so exposure can be turned on without restructuring; don't implement token/TLS until actually exposing beyond localhost. Keeps v1 lean, avoids premature crypto choices.
  - **Anticipated fill-in (not committed):** shared bearer token for the LAN stage, token-over-TLS for the WAN stage. mTLS considered overkill for a handful of boxes. Revisit when the LAN/WAN stage is reached.

## Testing Strategy
- **Linux collectors: fixtures for parsing, mocks for wiring** —
  - **Fixtures:** collectors read from an injectable base path (default `/`); tests point it at checked-in fixture `/sys`+`/proc` trees captured from real boxes (cerebro's AMD GPU, sevro, etc.) to exercise real parsing + autodetection deterministically, hardware-independent. Every sysfs/procfs collector threads the root path.
  - **Mocks:** test Node/Collector wiring (sample loop, HTTP, SSE) against mock impls of the metric traits returning canned data — no hardware touched.
- **Pull→SSE integration: fake Node server → assert SSE** — spin up an in-process `axum` server returning canned `/snapshot` JSON (incl. missing / stale / unreachable cases), run the real Collector against it, connect an SSE client, and assert emitted snapshots + node states (`live`/`stale`/`unknown`). Exercises graceful degradation for real.
- **Autodetection** covered via the fixture trees (primary NIC, GPU hwmon, CPU temp sensor, root disk selection).

## Open Questions
_Design is implementation-ready; these are deferred Nix-deployment items, not blockers._
- [ ] **Secrets mechanism** — when auth leaves localhost, the bearer token can't live in a store-rendered TOML (Nix store is world-readable). Decide **agenix** vs **sops-nix** to feed the token to the Node/Collector services. Reserve the seam now; impl tracks the auth rollout.
- [ ] **NixOS VM integration test** — optionally fold `nixosTest` (boot `node`+`collector` modules in a throwaway VM, assert the SSE path end-to-end at the real-systemd level) into the testing strategy as a Nix-native integration layer above the fake-Node→SSE test.
