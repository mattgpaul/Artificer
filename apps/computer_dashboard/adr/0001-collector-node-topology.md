# 0001 — Collector + Node pull topology

- **Date:** 2026-07-25
- **Status:** accepted
- **Decision:** Two components. A **Node** runs on each monitored box, collects host metrics, and exposes them over HTTP + JSON. A **Collector** pulls from Nodes on an interval and serves the dashboards. Pull/scrape model, `localhost`-first with staged network exposure.
- **Why:** Self-contained — no dependency on Prometheus/Grafana. Scale is small multi-node (own boxes + a few friends'), where pull is simple on a LAN and mirrors a proven model. Push and WAN/NAT reachability are deferred to v2 alongside wider exposure.
- **Consequences:** Collector must degrade gracefully — an unreachable Node, missing data, or NaN is a normal state, not an error. Remote/NAT reachability is unsolved until v2 (likely push/tunnel/VPN). Node owns a stable JSON schema that the Collector and dashboards depend on.
