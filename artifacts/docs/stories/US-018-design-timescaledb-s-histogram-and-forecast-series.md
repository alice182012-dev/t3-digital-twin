---
date_drafted: 2026-09-23
type: user-story
us_id: "US-018"
story_label: "1"
epic: "[[EP-04-timescaledb-and-flood-metrics]]"
status: Done
priority: P1
estimate: S
sprint: 1
subsystem: architecture-backend
related: ["[[EP-04-timescaledb-and-flood-metrics]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
---

# US-018 Design TimescaleDB's histogram and forecast-series schema

As an engineer, I want a settled schema for institution histograms, `background_cycle` forecast
series, and depth history, so I can populate real data instead of guessing a shape mid-build.
Given the architecture doc's §4.9 describes the histogram split this schema must support, when the
schema design is reviewed against that section, then it accounts for both `constant_cycle` and
`background_cycle` data sources without needing a later migration.
Priority: P1. Status: Done. Estimate: S. Sprint: 1. Dependencies: None.
Evidence: ![[timescaledb-schema.png|420]]
Details:
1. What: three hypertables and a `simulation_cycle` enum.
2. How: `create_timescale_tables.py`, with a `CHECK` that ties bars 1 to 6 to `constant_cycle` and bars 7 to 24 to `background_cycle`.
3. Why: no migration when `background_cycle` data arrives.
4. Effect: Story 4 loads into these tables, and must first choose a segment key, since road segments have no stable ID.
