# 0002 — Ratatui TUI dashboard over SSE

- **Date:** 2026-07-25
- **Status:** accepted
- **Decision:** The Dashboard is a **Ratatui terminal UI**, built as a standalone client binary. The Collector exposes a **Server-Sent Events (SSE)** stream of Node snapshots over HTTP; the Dashboard is an SSE client that renders it. Full data path: Node → Collector is pull HTTP+JSON; Collector → Dashboard is SSE push. Three binaries total (`node`, `collector`, `dashboard`).
- **Why:** Live-first — SSE push beats polling for real-time. Single-language Rust ethos — a TUI avoids a web frontend + build pipeline; Ratatui's `Chart`/`Sparkline`/`Gauge` widgets cover the meters and detail graphs the old web dashboard left stubbed. A separate client binary can run anywhere and point at the Collector. WebSocket was passed over because the UI is read-only for now; revisit if the Dashboard needs to command Nodes (v2).
- **Consequences:** No browser assets or JS build to maintain. Charting is limited to terminal widgets (acceptable; the same SSE endpoint can feed a browser UI later without Collector changes). The Dashboard is a network client and shares the schema types from `libs/computer_telemetry`.
