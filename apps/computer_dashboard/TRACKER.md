<!--
TRACKER.md — this project's task/issue board. Source of truth for THIS project.
See the `task-tracker` skill for the full format rules. A new task begins ONLY
where a `# ` header is immediately followed by an `ID:` line and a `State:` line.
-->

# Scaffold computer_telemetry lib + Snapshot envelope + System family
ID: 1
State: TODO
Blocker: None
Description: Foundation / prefactor for the whole pipeline. Turn the currently
devshell-only `libs/computer_telemetry` flake into a real crate (Cargo.toml,
src/lib.rs) and establish the shared data model that Node, Collector, and
Dashboard all import by path.

Define the neutral `Snapshot` envelope: node identity, timestamp, an integer
`schema_version` tied to the lib, and `Option` fields per metric family (missing
= `null`, never NaN or error). serde Serialize/Deserialize throughout. Define the
generic per-metric-family collection trait shape, and the injectable base-path
convention (every future sysfs/procfs collector threads a base path defaulting to
`/`) so later collectors are testable against fixture trees.

Land the System family end-to-end to prove the shape: hostname, OS pretty name,
kernel release, uptime, logged-in user, collected via the cross-platform
`sysinfo` baseline (no sysfs, no fixtures needed yet). Keep the lib pure and
synchronous — no `tokio`, no timing (ADR 0003); timing lives in the Node binary.

Verifiable: a serde round-trip test serializes a Snapshot to JSON carrying
`schema_version` with absent families as `null`; the System collection function
returns a populated System struct. Prior art for model/trait shapes exists in
`apps/telemetry_rust/monitor/src` but is reference only, not authoritative.

# Node binary tracer bullet: sampling loop + shared cell + HTTP
ID: 2
State: BLOCKED
Blocker: 1
Description: The Node binary's thin end-to-end path. Owns a background `tokio` loop that
samples every `collection_interval` and writes the latest `Snapshot` into a
shared cell (`tokio::sync::watch` / `ArcSwap`), so the HTTP handler is a cheap
read and rate-dependent deltas stay correct regardless of pull rate. `axum` HTTP
server exposing `GET /snapshot` (latest cached JSON: identity + timestamp +
metric families, missing = `null`, carrying `schema_version`) and `GET /healthz`
(liveness). Config via TOML with CLI/env overrides (`clap`): bind/port,
collection interval, enabled metric features, processes top-N sort default.

The Node is generic over the whole `Snapshot`, so later metric families flow
through without Node changes. Metric-trait mock wiring test (seam 2): drive the
sample loop + shared-cell read + HTTP handler against mock trait impls returning
canned data, no hardware touched.

Verifiable: run the Node, `curl /snapshot` returns live System JSON that updates
each interval; `/healthz` returns 200.

# Collector binary: pull loop + TTL cache + live/stale/unknown + plain HTTP
ID: 3
State: BLOCKED
Blocker: 2
Description: The Collector's pull-and-serve core (SSE added in task 4). Pulls each configured
Node per `pull_interval` over HTTP with `reqwest`, holding a bounded, TTL'd cache:
the single latest timestamped snapshot per Node, overwritten in place — memory
O(#Nodes), no history. Computes per-Node state `live` / `stale` / `unknown`:
`stale` = missed pulls past `stale_after`; `unknown` = never reached. Neither is
an error; a down/stale Node yields a null/stale snapshot, never a crash.

`axum` HTTP server exposing `GET /snapshot` (combined all-Nodes one-shot JSON),
`GET /nodes` (Nodes with their `live`/`stale`/`unknown` state), and
`GET /healthz`. Config via TOML with CLI/env: bind/port, Node endpoint list
(static TOML, default a single `127.0.0.1:<node-port>` entry), pull interval,
stale_after. Defaults: collection 1s, pull 1s, stale_after 3s.

Verifiable: point the Collector at a Node; `/snapshot` returns combined state and
`/nodes` reports live/stale/unknown; stopping the Node flips it to stale then the
snapshot degrades rather than erroring.

# Collector SSE /stream + fake-Node to SSE integration test
ID: 4
State: BLOCKED
Blocker: 3
Description: Add the SSE live feed — the headline transport. `GET /stream` emits a full
combined snapshot per event (`event: snapshot`), not deltas, so reconnect/drop
self-heals without special handling. Fan-out via `tokio::sync::broadcast`, one
SSE event per pull cycle.

Includes the fake-Node -> SSE integration test (seam 3, the single most
end-to-end seam): spin up an in-process `axum` server returning canned
`/snapshot` JSON — including missing, stale, and unreachable cases — run the real
Collector against it, connect an SSE client, and assert the emitted combined
snapshots plus per-node `live`/`stale`/`unknown` states. This is the end-to-end
graceful-degradation test.

Verifiable: an SSE client sees a full combined snapshot each pull cycle; the
integration test is green across missing/stale/unreachable.

# Dashboard tracer bullet: Ratatui SSE client + System panel
ID: 5
State: BLOCKED
Blocker: 4
Description: Completes the end-to-end tracer bullet. Standalone `ratatui` + `crossterm` TUI
client that connects to the Collector's SSE stream via `reqwest` /
`reqwest-eventsource`, deserializes snapshots using the shared lib types, and
renders live. For this slice: a System panel plus per-Node `live`/`stale`/
`unknown` state badges. Config via TOML with CLI/env: Collector URL, render prefs.

The Dashboard deserializes the whole shared `Snapshot`, so later metric families
add panels without transport changes.

Verifiable: run the Dashboard against a running Collector and watch live System
info and per-Node state badges update in real time from the SSE feed.

# CPU metric family + fixture test + Dashboard CPU panel
ID: 6
State: BLOCKED
Blocker: 1, 5
Description: Vertical slice for CPU. Lib: model + collection for vendor, model, max frequency,
temperature (sysfs), per-core usage %, overall usage % — portable bits via
`sysinfo`, precise temp/per-core via `#[cfg(linux)]` sysfs/procfs enrichment
behind the injectable base path, both agreeing on the shared model. Fixture-tree
test (seam 1): point the base path at a checked-in `/sys` + `/proc` fixture
captured from a real box and assert real parsing (this establishes the fixture
layout under `tests/` mirroring `libs/computer_telemetry`). Dashboard: CPU panel
with overall/per-core gauges and load sparkline. Flows through Node/Collector
unchanged.

Verifiable: fixture test parses CPU metrics deterministically; the CPU panel
renders live in the Dashboard against a real Node.

# Memory metric family + Dashboard memory panel
ID: 7
State: BLOCKED
Blocker: 1, 5
Description: Vertical slice for Memory (small). Lib: model + collection for total and
available/free via the cross-platform `sysinfo` baseline — portable, no sysfs, no
fixtures. Dashboard: memory panel showing pressure (used vs total gauge). Flows
through Node/Collector unchanged.

Verifiable: the memory panel renders live used/available in the Dashboard against
a real Node.

# Network metric family + autodetect/fixture test + Dashboard net panel
ID: 8
State: BLOCKED
Blocker: 1, 5
Description: Vertical slice for Network on the autodetected primary NIC. Lib: model +
collection for IPv4, max port speed, rx/tx bytes total, rx/tx bps, link carrier —
`sysinfo` baseline plus `#[cfg(linux)]` sysfs enrichment (carrier, max speed)
behind the injectable base path; primary-NIC autodetection at runtime, nothing
hardcoded. rx/tx bps are rate-dependent deltas derived from consecutive samples
owned by the Node's sampling loop (the loop keeps the prior reading), so they stay
correct regardless of pull rate. Fixture-tree test exercising parsing and NIC
autodetection deterministically. Dashboard: network panel with throughput
sparklines and link/carrier state.

Verifiable: fixture test autodetects the primary NIC and parses its metrics; the
net panel renders live throughput in the Dashboard.

# Storage metric family + fixture test + Dashboard storage panel
ID: 9
State: BLOCKED
Blocker: 1, 5
Description: Vertical slice for Storage. Lib: model + collection for root-disk size and
available, plus disk read/write B/s — `sysinfo` baseline plus `#[cfg(linux)]`
enrichment behind the injectable base path; root-disk autodetection at runtime.
Read/write B/s are rate-dependent deltas derived from consecutive samples owned by
the Node's sampling loop. Fixture-tree test for parsing and root-disk
autodetection. Dashboard: storage panel with capacity gauge and I/O sparklines.

Verifiable: fixture test autodetects the root disk and parses capacity + I/O; the
storage panel renders live in the Dashboard.

# Processes metric family + Dashboard processes panel with sort toggle
ID: 10
State: BLOCKED
Blocker: 1, 5
Description: Vertical slice for Processes. Lib: model + collection for the top 5 processes by
CPU or by RAM (name, cpu%, mem%) with a selectable sort key, via the `sysinfo`
baseline. The Node config carries the default sort key. Dashboard: processes panel
listing the top 5 with an in-TUI toggle between CPU-sorted and RAM-sorted.

Verifiable: the processes panel lists the top 5 and switches ordering when the
sort key is toggled, live against a real Node.

# GPU metric family (AMD) + cerebro fixture + Dashboard GPU panel
ID: 11
State: BLOCKED
Blocker: 1, 5
Description: Vertical slice for GPU, AMD first — the heaviest family. Lib: model + collection
behind `#[cfg(linux)]` and an `amd-gpu` feature flag, reading `/sys` + hwmon via
the injectable base path with card/hwmon autodetection. Metrics: vendor/device,
edge/junction/memory temps with critical/emergency thresholds, fan rpm and max,
usage %, VRAM used/total, power and max, thermal throttle, and clock current/max
— carry the "to implement" caveat on GPU clock current/max from the spec/metric
catalog (model it, leave the source stubbed if no reliable read). `fps` is
dropped. Fixture-tree test using a `/sys` tree captured from cerebro's AMD card.
Mine `apps/telemetry_rust/monitor/src/models/gpu.rs` for the sysfs/hwmon parsing
shapes (reference, not authoritative). Dashboard: GPU panel with temp/power/usage
gauges and threshold indicators.

Verifiable: fixture test parses cerebro's AMD sensors including the crit/emergency
thresholds; the GPU panel renders live in the Dashboard; clock current/max shows
missing where unimplemented rather than fabricated.

# schema_version compatibility: tolerate unknown fields + warn-and-degrade
ID: 12
State: BLOCKED
Blocker: 3, 5
Description: Cross-cutting (small). Every snapshot carries an integer `schema_version` tied to
the lib. Make the Collector and Dashboard tolerate unknown fields (serde) and, on
a major `schema_version` mismatch, warn and degrade rather than crash. No behavior
change on match; the point is that a version skew across the fleet never collapses
the view.

Verifiable: feeding a snapshot with extra unknown fields and/or a bumped major
`schema_version` produces a warning and continued rendering, not a panic.

# Auth seam: pluggable auth layer + config slot on both hops (unimplemented)
ID: 13
State: BLOCKED
Blocker: 2, 3
Description: Cross-cutting seam, defined but NOT implemented in v1. v1 binds localhost-only
with no auth. Define a pluggable auth layer plus a config slot on both hops
(Node->Collector and Collector->Dashboard) so exposure beyond localhost can be
turned on later without restructuring. Do not implement token/TLS/mTLS.
Anticipated (uncommitted) fill-in: shared bearer token for LAN, token-over-TLS
for WAN.

Verifiable: both hops carry an auth config slot and a trait/seam that is a no-op
pass-through in v1; wiring compiles and the localhost path is unchanged.

# Root-flake wiring (path inputs) + buildRustPackage for all three binaries
ID: 14
State: BLOCKED
Blocker: 2, 3, 5
Description: Deployment prefactor; closes the current root-flake gap (root inputs are only
nixpkgs + home-manager today, and the app/lib flakes are devshell-only islands
with independent pins). Add each app flake as a path input to the root
`flake.nix` (`path:./apps/computer_dashboard/<svc>`) with
`inputs.nixpkgs.follows = "nixpkgs"` (mandatory — single nixpkgs eval, no glibc/
version skew). Give each app flake an inline `rustPlatform.buildRustPackage`
derivation (no new third-party flake inputs; whole-crate rebuilds accepted). Each
app flake owns its `packages` output. Expect the root flake and each app flake to
change together.

Verifiable: `nix build ./apps/computer_dashboard/{node,collector,dashboard}`
each produce a binary standalone, and the root flake evaluates with a single
nixpkgs.

# NixOS module for Node + import on cerebro and sevro
ID: 15
State: BLOCKED
Blocker: 14
Description: Deployment slice for the Node service. The `node` flake exports
`nixosModules.node` with `enable`/bind/port/config options; the module's `package`
option defaults to that flake's package. `mkHost` imports it. Every target host
imports `node` (here: cerebro and sevro; not swordfish). Systemd sandbox hardening
with read access to `/sys` + `/proc`; exact directives (DynamicUser,
ProtectSystem, sensor-path access) decided here against the real collectors, once
sandbox-blocked paths can be tested.

Verifiable: cerebro and sevro evaluate with the Node service enabled and the
service starts under the sandbox with sensor paths readable.

# NixOS module for Collector + import on cerebro
ID: 16
State: BLOCKED
Blocker: 14
Description: Deployment slice for the Collector service. The `collector` flake exports
`nixosModules.collector` with `enable`/bind/port/config options defaulting its
`package` to that flake's package. Imported on one box only (cerebro). Config
renders the Node endpoint list, pull interval, stale_after, and SSE settings.

Verifiable: cerebro evaluates with the Collector service enabled and it serves
/snapshot, /nodes, /stream, /healthz on localhost.

# Dashboard home-manager delivery
ID: 17
State: BLOCKED
Blocker: 14
Description: Deployment slice for the Dashboard. Delivered via home-manager — the package is
added to the user profile on the boxes it is driven from, run interactively, not a
systemd unit.

Verifiable: on a driven-from box the user profile provides the `dashboard` binary,
which launches and connects to the Collector.

# Remove MVP apps once parity reached
ID: 18
State: BLOCKED
Blocker: 6, 7, 8, 9, 10, 11, 15, 16, 17
Description: Cleanup, gated strictly on parity. Once `computer_dashboard` matches the two MVPs'
feature coverage and is deployed, delete `apps/telemetry` (Python collectors +
Prometheus/Grafana/JS) and `apps/telemetry_rust` (Rust collector). Git history
preserves both — this leaves a single source of truth.

Verifiable: both MVP app directories are removed, the repo builds, and no
remaining reference points at them.
