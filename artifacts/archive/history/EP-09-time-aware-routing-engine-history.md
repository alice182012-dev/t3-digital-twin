---
date: 2026-10-10
type: archive
status: archived
tags: [archive, history]
related: ["[[EP-09-time-aware-routing-engine]]"]
---

# EP-09-time-aware-routing-engine: archived story-level history

Lines moved out of the Status history of [[EP-09-time-aware-routing-engine]] on 2026-10-10 under the rule "Write each fact once". Each fact is also in its story file. Not read in normal sessions.

- **2026-10-01, draft.** Story R2 (`US-047`) is `Done`: the reference and checker pass 54 tests, and all 16 scenario runs on real Hanoi roads match the sticky column with no crossing. Output rendered as `us-047-reference-check-output.png`. See [[sticky-routing-reference]].
- **2026-10-01, draft.** Story R1 (`US-046`) is `In progress`. The edge count (67,833), the source revision (commit `d7dc1b06`), and the step length and count (15 minutes, 8 steps) are recorded in [[BL-011-routing-not-time-aware|routing-not-time-aware]]. The p50 and p95 wait for the `US-037` knob.
- **2026-10-02, draft.** Story R1 (`US-046`) is `Done`: the p50 and p95 of `POST /route` are recorded after the `US-037` knob settled, next to the edge count, the image revision, and the step length and count. Evidence: `us-046-baselines-check-output.png`.
- **2026-10-02, draft.** The gates of Stories R5 and R10 are cleared. The user confirmed the sticky-from-departure wording and set the latency factor to 2 (see [[PRD-004-time-aware-routing-engine|time-aware-routing-engine]]).
- **2026-10-05, draft.** Story R4 (`US-049`) is `Reviewed`. The module, `Dockerfile`, entrypoint, and CI workflow are written, and the 9 tests pass on the Mac side (Maven, JDK 21 running the Java 17 target). LM stays valid for a raise-only weighting (see [[BL-011-routing-not-time-aware|routing-not-time-aware]]). Not done: a green CI run, and the image built and started on the server. The acceptance check reads "when CI runs".
- **2026-10-05, draft.** Story R4 (`US-049`) is `Done`: CI run 1 passed and the image smoke test passed on the server (12 of 12 routes equal to the live service, `TimeAwareGraphHopper active` in the log). Evidence: `us-049-image-smoke-test-output.png`.
- **2026-10-09, active.** New story R11 (`US-096`) from the blocker [[BL-026-sticky-closure-clock-anchored-at-floored-departure|sticky-closure-clock-anchored-at-floored-departure]], found while writing the proof of `US-090`.
- **2026-10-09, active.** R11 (`US-096`) is `Done` in code: 129 Java tests on GitHub Actions, the Python suites, evidence `us-096-fix-check-output.png`. The server image is rebuilt at the next rollout.
