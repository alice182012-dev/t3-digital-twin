---
date: 2026-10-10
type: archive
status: archived
tags: [archive, history]
related: ["[[EP-14-routing-paper-experiments]]"]
---

# EP-14-routing-paper-experiments: archived story-level history

Lines moved out of the Status history of [[EP-14-routing-paper-experiments]] on 2026-10-10 under the rule "Write each fact once". Each fact is also in its story file. Not read in normal sessions.

- **2026-10-09, active.** Story 1 (`US-090`) is `Done`: [[sticky-closure-proof]], two new tests, evidence `us-090-proof-check-output.png`. The proof found the clock error of the engine, now `US-096` ([[BL-026-sticky-closure-clock-anchored-at-floored-departure|sticky-closure-clock-anchored-at-floored-departure]]).
- **2026-10-09, active.** Story 2 (`US-091`): the harness is built (`scripts/routing_experiments/`, 42 tests). After `US-096` the runner walks engine routes from the time of the request and starts the sticky window at `td.departure` (`88c151c`). The server run and the storm stages wait for the second replay (D-020).
- **2026-10-09, active.** Stories 3 and 4 (`US-092`, `US-093`) are `In progress`. The offline code is merged on `modular` (`fc14d81` to `bb00594`): `arrival_only.py`, `sticky_cost.py`, `limit_sweep.py`. The first hour of `US-093` did not need more than a label-correcting search, so the estimate stays S. Open: the cost-band sweep of `US-092` (the reference has no cost factors) and a graph with node ids for a real run.
- **2026-10-09, active.** [[BL-024-edge-export-has-no-node-ids|edge-export-has-no-node-ids]] is `resolved`. `scripts/routing_experiments/real_graph.py` builds the reference `Graph` from the format-2 export of the server (67,833 edges, `b34cd0e`), and a smoke sweep of `sweep_fraction` ran on it with a replay table. Stories 3 and 4 now wait only for the second replay (D-020). Any real result must state that one-way roads are open both ways and that travel time is length at one speed.
- **2026-10-09, active.** D-021 replaces the cost band of Story 3 with the precaution fraction. The sweep records, for each fraction, the share of pairs with a recommended route, the share that fall back to the hard-limit route, and the extra time of the recommended route. The engine change is `US-097` ([[EP-16-precaution-depth-routing|US-097-098-precaution-depth-routing-stories]]).
