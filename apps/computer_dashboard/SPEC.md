# computer_dashboard — Specification

## Problem Statement
Matthew has two telemetry MVPs that between them prove the idea but neither ships
it. `apps/telemetry` (Python collectors + Prometheus/Grafana/JS dashboard) works
but drags in a whole external stack; `apps/telemetry_rust` (Rust collector)
collects but exports nothing. He wants a single, self-contained, production-quality
way to watch live host metrics — CPU, GPU, memory, network, storage, processes,
system info — across a small fleet of his own Linux boxes (and possibly a few
friends'), without depending on Prometheus or Grafana, and without a box going
dark or a missing sensor taking the whole view down. Real-time is the point:
history and long-term retention are not the problem being solved here.

## Solution
A three-part Rust system, `localhost`-first and self-owned:

- A **Telemetry Node** runs on each monitored box, samples the defined host
  metrics on an interval, and exposes the latest reading as JSON over HTTP.
- A **Collector** pulls from a configured list of Nodes on an interval, holds the
  latest snapshot per Node in memory, and streams the combined state out over
  Server-Sent Events (SSE).
- A **Dashboard**, a standalone Ratatui terminal client, connects to the
  Collector's SSE stream and renders live meters and detail graphs.

The user gets a live, terminal-based view of their fleet that keeps working when a
box is off, a Node is unreachable, or a sensor has no reading — those show as
`stale` / `unknown` / missing, never as a crash or an error. It binds to
`localhost` only in v1, with a defined (but unimplemented) seam for turning on
auth as exposure widens to LAN and WAN later. The whole thing is packaged as
NixOS services (Nodes and Collector) and a home-manager tool (Dashboard) across
the existing fleet. Once it reaches parity, the two MVP apps are deleted.

## Glossary
| Term | Meaning |
|------|---------|
| Telemetry Node (Node) | The service on each monitored box that collects and exposes the defined metrics. |
| Collector | The central service that pulls from Nodes, holds latest state, and streams it out over SSE. |
| Dashboard | The Ratatui TUI client that connects to the Collector's SSE stream and renders it. |

## User Stories
1. As a fleet owner, I want each box to run a Node that exposes its host metrics as JSON over HTTP, so that a central service can collect them uniformly.
2. As a fleet owner, I want a Collector that pulls from a configured list of Nodes on an interval, so that I have one place that knows the whole fleet's current state.
3. As a fleet owner, I want the Collector to stream the combined latest state over SSE, so that a client connecting mid-stream immediately sees current state and then live updates.
4. As a fleet owner, I want a Dashboard TUI that connects to the Collector's SSE stream and renders live meters and detail graphs, so that I can watch my boxes in real time from a terminal.
5. As a fleet owner, I want the system to prove itself on a single box over `localhost` before any network exposure, so that I trust the single-box case first.
6. As a fleet owner, I want an unreachable Node, missing data, or a NaN value to be treated as a normal state rather than an error, so that one bad box never collapses the whole view.
7. As a Dashboard user, I want each Node marked `live`, `stale`, or `unknown`, so that I can tell a healthy box from one that has gone quiet or was never reached.
8. As a Dashboard user, I want a metric with no reading to show as explicitly missing rather than as a fabricated or zero value, so that I don't misread absent data as real data.
9. As a fleet owner, I want CPU metrics (vendor, model, max frequency, temperature, per-core usage %, overall usage %), so that I can see processor load and health.
10. As a fleet owner, I want GPU metrics (vendor/device, edge/junction/memory temps with critical/emergency thresholds, fan rpm and max, usage %, VRAM used/total, power and max, clock current/max, thermal throttle) for AMD cards first, so that I can monitor my GPUs in detail.
11. As a fleet owner, I want memory metrics (total, available/free), so that I can see memory pressure.
12. As a fleet owner, I want network metrics for the autodetected primary NIC (IPv4, max port speed, rx/tx bytes total, rx/tx bps, link carrier), so that I can see connectivity and throughput.
13. As a fleet owner, I want storage metrics (root disk size and available, disk read/write B/s), so that I can see disk capacity and activity.
14. As a fleet owner, I want the top 5 processes by CPU or by RAM (name, cpu%, mem%) with a selectable sort key, so that I can see what is consuming the box.
15. As a fleet owner, I want system metrics (hostname, OS pretty name, kernel release, uptime, logged-in user), so that I can identify and contextualize each box.
16. As a fleet owner with mixed hardware, I want machine-specific parameters (primary NIC, GPU card/hwmon, CPU temp sensor, root disk) autodetected at runtime, so that nothing is hardcoded to one box and heterogeneous boxes just report what they can.
17. As a fleet owner, I want portable metrics collected via a cross-platform baseline and Linux-only richness collected behind Linux-gated code, so that future Windows/macOS Nodes are nearly free while Linux detail stays available now.
18. As a maintainer, I want the collection library to stay pure and synchronous (traits + data model + collection functions, no async runtime or timing), so that it remains generic and portable across platforms.
19. As a maintainer, I want the Node binary to own the background sampling loop that writes the latest snapshot into a shared cell, so that the HTTP handler is a cheap read and rate-dependent deltas (net/CPU) stay correct regardless of pull rate.
20. As a fleet owner, I want the Collector to hold only the single latest, timestamped snapshot per Node with a TTL, so that memory stays O(#Nodes) and stale data past the TTL is never served as fresh.
21. As a fleet owner, I want collection, pull, and staleness intervals configurable with sensible defaults (Node collection 1s, Collector pull 1s, stale_after 3s), so that I can tune responsiveness versus load.
22. As a fleet owner, I want the Collector to expose `GET /snapshot` (combined one-shot) and `GET /nodes` (Nodes with their live/stale/unknown state) in addition to the SSE stream, so that I can query fleet state without holding a stream open.
23. As a fleet owner, I want each Node to expose `GET /snapshot` and `GET /healthz`, and the Collector `GET /healthz`, so that health and current data are queryable over plain HTTP.
24. As a client author, I want the Collector to send a full combined snapshot per SSE event rather than deltas, so that reconnects and dropped events self-heal without special handling.
25. As a maintainer, I want every snapshot to carry an integer `schema_version` tied to the library, so that components can tolerate unknown fields and warn-and-degrade on a major mismatch instead of crashing.
26. As a maintainer, I want the shared JSON schema types to live in `libs/computer_telemetry` and be imported by path from Node, Collector, and Dashboard, so that all three agree on one data model.
27. As a fleet owner, I want the Node's list of endpoints supplied by a static TOML list defaulting to a single localhost entry, so that the single-box case needs no configuration and adding boxes is a config edit.
28. As a fleet owner, I want each binary configured by a TOML file with CLI and environment overrides, so that I can run it standalone or have a NixOS module render its config.
29. As a fleet owner, I want three independently built and deployed binaries (`node`, `collector`, `dashboard`) in separate directories, so that each can be built, versioned, and shipped on its own.
30. As a fleet operator, I want Nodes and the Collector packaged as NixOS services (a host imports `node` always, `collector` only where wanted) and the Dashboard delivered via home-manager, so that deployment matches how the fleet is actually run.
31. As a fleet operator, I want the app flakes' packages and NixOS modules wired into the root flake as path inputs following `nixpkgs`, so that there is a single nixpkgs evaluation with no glibc/version skew across the fleet.
32. As a maintainer, I want a pluggable auth layer with a config slot defined on both hops (Node→Collector, Collector→Dashboard) but left unimplemented in v1, so that exposure beyond localhost can be enabled later without restructuring.
33. As a maintainer, I want the two MVP apps (`apps/telemetry`, `apps/telemetry_rust`) removed once `computer_dashboard` reaches parity, so that there is a single source of truth (git history preserves the old ones).

## Implementation Decisions

### Structure & crates
- Standalone crates, **no workspace** (Option A): `libs/computer_telemetry` (own
  flake) plus `apps/computer_dashboard/{node,collector,dashboard}`, each with its
  own flake, lock, and target, path-depending on the lib. This follows the repo's
  per-directory-flake convention and keeps the Dashboard's TUI-only dependencies
  (ratatui/crossterm) out of the Collector service. Topology per ADR 0001;
  three-binary split and SSE transport per ADR 0002.
- Currently `libs/computer_telemetry` is a devshell-only flake with no `src`, and
  `tests/` is empty — this is greenfield. Prior art for model/trait shapes exists
  in `apps/telemetry_rust/monitor/src` and may be mined, but is not authoritative.

### Library (`libs/computer_telemetry`)
- Holds the **neutral data model / schema structs** and a **generic trait per
  metric family**; OS-/hardware-specific collection sits behind those traits.
- Stays **pure and synchronous** — no `tokio`, no timing (per ADR 0003). The lib
  provides collection functions; timing belongs to the Node binary.
- Two collection paths on Linux that must agree on the shared model: a
  cross-platform **`sysinfo`** baseline (CPU%, mem, disk, net, processes) and
  hand-rolled **sysfs/procfs** enrichment gated by `#[cfg(linux)]` + feature flags
  (e.g. `linux`, `amd-gpu`) for AMD GPU sensors, per-core %, link carrier, precise
  temps. New platforms are added as new gated modules with no API change (ADR 0003).
- **Missing = `Option`** throughout the model — absent readings are first-class
  `Option` values (serialized as `null`), never NaN or error. Graceful degradation
  is carried from the collection source up.
- Every collector that reads sysfs/procfs threads an **injectable base path**
  (default `/`), so parsing and autodetection are exercisable against fixture
  trees (see Testing Decisions). Autodetection (primary NIC, GPU card/hwmon, CPU
  temp sensor, root disk) runs at runtime; nothing hardcoded.
- Exposes the shared JSON schema types imported by path from all three binaries.

### Node binary
- Owns a background **`tokio`** loop that samples every `collection_interval` and
  writes the latest `Snapshot` into a shared cell (`tokio::sync::watch` / `ArcSwap`).
  The HTTP handler only reads the cell, so pulls are cheap and rate-dependent
  deltas stay correct regardless of pull rate.
- **`axum`** HTTP server exposing:
  - `GET /snapshot` — latest cached JSON: identity + timestamp + metric families,
    missing = `null`, carrying `schema_version`.
  - `GET /healthz` — liveness.
- Config (TOML + CLI/env via `clap`): bind/port, collection interval, enabled
  metric features, processes top-N sort default.

### Collector binary
- Pulls each configured Node per `pull_interval` over HTTP with **`reqwest`**,
  holding a **bounded, TTL'd cache**: the single latest timestamped snapshot per
  Node, overwritten in place. Memory is O(#Nodes); no history (v2).
- Computes per-Node state **`live` / `stale` / `unknown`**: `stale` = missed pulls
  past `stale_after`; `unknown` = never reached. Neither is an error; a down/stale
  Node yields a null/stale snapshot.
- **`axum`** HTTP server exposing:
  - `GET /stream` — SSE live feed. Emits a **full combined snapshot per event**
    (`event: snapshot`), not deltas, so reconnect/drop self-heals. Fan-out via
    `tokio::sync::broadcast`. One SSE event per pull cycle.
  - `GET /snapshot` — combined all-Nodes one-shot JSON.
  - `GET /nodes` — Nodes with their `live`/`stale`/`unknown` state.
  - `GET /healthz` — liveness.
- Config (TOML + CLI/env): bind/port, Node endpoint list (static TOML, default a
  single `127.0.0.1:<node-port>` entry), pull interval, SSE settings.

### Dashboard binary
- Standalone **`ratatui` + `crossterm`** TUI client. Connects to the Collector's
  SSE stream via **`reqwest`/`reqwest-eventsource`**, deserializes snapshots using
  the shared lib types, and renders live meters and detail graphs with built-in
  `Chart` / `Sparkline` / `Gauge` widgets (ADR 0002).
- Config (TOML + CLI/env): Collector URL, render prefs.

### Schema versioning & compatibility
- Integer `schema_version` in every snapshot, tied to the lib, bumped only on
  breaking changes. Components tolerate unknown fields (serde) and warn + degrade
  on a major mismatch — never crash.

### Metric catalog
The v1 superset to model and collect (missing values are `Option`): CPU, GPU (AMD
first), Memory, Network, Storage, Processes, System — as enumerated in
DESIGN.md's Metric Catalog. `fps` is dropped (no real data source). GPU clock
current/max is noted "to implement."

### Deployment & packaging
- **Nix builder:** `rustPlatform.buildRustPackage`, derivation inline in each app
  `flake.nix`; no new third-party flake inputs. Whole-crate rebuilds accepted.
- **NixOS integration:** one module per service — `node` flake exports
  `nixosModules.node`, `collector` exports `nixosModules.collector`, each with
  `enable`/bind/port/config options, wired into `utils/nixos/`. A host imports
  `node` always; `collector` only on one box. Target hosts: cerebro, sevro, and
  future boxes (not swordfish).
- **Package → fleet wiring (Option 1):** each app flake owns its `packages` and
  `nixosModules.<svc>` outputs; the root `flake.nix` adds each app flake as a
  **path input** (`path:./apps/computer_dashboard/<svc>`) with
  `inputs.nixpkgs.follows = "nixpkgs"` (mandatory — single nixpkgs eval, no skew).
  `mkHost` imports the module; the module's `package` option defaults to that
  flake's package. `nix build ./apps/.../node` also works standalone. This closes
  the current gap where the root flake references no app/lib flakes.
- **Node service hardening:** systemd sandbox with read access to `/sys` + `/proc`;
  exact directives (DynamicUser, ProtectSystem, sensor-path access) decided during
  implementation once collectors exist and sandbox-blocked paths can be tested.
- **Dashboard delivery:** home-manager — package added to the user profile on
  boxes it's driven from; run interactively, not a systemd unit.
- **Build distribution:** nothing for v1 — accept per-host compilation. Revisit
  order when it hurts: cerebro as remote builder, then self-hosted binary cache
  (attic/harmonia). Cachix rejected.

### Security / auth seam (defined, not implemented)
- v1 binds `localhost`-only; no auth. Define a **pluggable auth layer + config
  slot on both hops** (Node→Collector, Collector→Dashboard) so exposure can be
  turned on without restructuring. Do not implement token/TLS in v1. Anticipated
  (uncommitted) fill-in: shared bearer token for LAN, token-over-TLS for WAN;
  mTLS considered overkill.

## Testing Decisions
A good test here exercises **observable external behavior and real parsing**, not
internal wiring, and drives graceful degradation (missing / stale / unreachable)
as a first-class path rather than a special case. The design settles three seams;
the spec commits to them as written — preferring the highest boundary in each
area, with the fake-Node → SSE test as the single most end-to-end seam.

**Seams:**
1. **Fixture root-path seam (collection).** Every sysfs/procfs collector threads
   the injectable base path (default `/`). Tests point it at checked-in fixture
   `/sys` + `/proc` trees captured from real boxes (cerebro's AMD GPU, sevro,
   etc.) to exercise real parsing **and** autodetection (primary NIC, GPU hwmon,
   CPU temp sensor, root disk) deterministically and hardware-independent. Tests
   the `libs/computer_telemetry` Linux collectors.
2. **Metric-trait mock seam (wiring).** Node and Collector wiring — the sample
   loop, the shared-cell read, the HTTP handlers — tested against mock impls of
   the metric traits returning canned data, so no hardware is touched. Tests the
   Node and Collector binaries' assembly around the lib.
3. **Fake-Node → SSE seam (integration, highest).** Spin up an in-process `axum`
   server returning canned `/snapshot` JSON — including missing, stale, and
   unreachable cases — run the **real** Collector against it, connect an SSE
   client, and assert the emitted combined snapshots plus per-node
   `live`/`stale`/`unknown` states. This is the end-to-end graceful-degradation
   test.

**Location.** Tests are centralized under the repo's `tests/` tree, mirroring the
source path rather than sitting beside the code (per AGENTS.md). Lib collector +
autodetection tests and their fixture trees mirror `libs/computer_telemetry`; Node
and Collector wiring and the fake-Node → SSE integration test mirror
`apps/computer_dashboard/{node,collector}`. `tests/` is currently empty, so this
establishes the layout for the project.

**Prior art.** None in `tests/` yet. `apps/telemetry_rust/monitor/src` (existing
models + a `Telemetry` refresh trait) is reference material for model/trait shapes
but is not a test model to copy.

## Out of Scope
- **Windows / macOS Nodes** — designed-for via the `cfg` seam, not built in v1.
- **Long-term history / persistent retention** — v2; Grafana may be explored then
  for stored data. v1 is live-view only.
- **mDNS / zeroconf Node autodiscovery** — v2; v1 uses a static TOML list.
- **Prometheus text-format endpoint** — v2, for the optional Grafana path.
- **Deltas over SSE** — v2 optimization; v1 sends full snapshots.
- **Remote / NAT reachability (push/tunnel/VPN)** — v2, alongside wider exposure.
- **Auth implementation (token / TLS / mTLS)** — only the seam is defined in v1.
- **Non-NixOS Linux packaging** — deferred until a friend actually wants in.
- **Build distribution (remote builder / binary cache)** — nothing in v1.
- **WebSocket / Dashboard-commands-Nodes** — v2 (UI is read-only now).
- **Open Question — secrets mechanism (agenix vs sops-nix):** deferred. The Nix
  store is world-readable, so a bearer token can't live in a store-rendered TOML;
  the choice is reserved and tracks the auth rollout, not v1.

## Further Notes
- **Open Question — NixOS VM integration test (`nixosTest`):** optional Nix-native
  integration layer that would boot the `node` + `collector` modules in a
  throwaway VM and assert the SSE path end-to-end at the real-systemd level, above
  the fake-Node → SSE test. Recorded as a possible future addition to the testing
  strategy, not a v1 commitment.
- **MVP removal is gated on parity:** delete `apps/telemetry` and
  `apps/telemetry_rust` only once `computer_dashboard` reaches feature parity; git
  history preserves them.
- **GPU clock current/max** is flagged "to implement" in the metric catalog —
  carry that caveat into task breakdown.
- **Root-flake gap:** today the root flake's inputs are only nixpkgs +
  home-manager, and the app/lib flakes are devshell-only islands with independent
  nixos-unstable pins. The Package → fleet wiring decision is what bridges them;
  expect the root flake and each app flake to change together.
- ADRs: 0001 (Collector + Node pull topology), 0002 (Ratatui TUI over SSE), 0003
  (Linux-first collection with cross-platform seam).
