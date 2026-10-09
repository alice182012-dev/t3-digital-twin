---
date: 2026-10-10
type: archive
status: archived
tags: [archive, history]
related: ["[[EP-10-routing-first-consumer]]"]
---

# EP-10-routing-first-consumer: archived story-level history

Lines moved out of the Status history of [[EP-10-routing-first-consumer]] on 2026-10-10 under the rule "Write each fact once". Each fact is also in its story file. Not read in normal sessions.

- **2026-10-06, draft.** Story C3 changed from a TaskGroup (S) to a separate DAG triggered by an asset event (M), at the user's request. The earlier reason for one DAG, the 9c timing limit, does not need it: 9c depends only on `9b_load_depth_raster`, so an asset trigger adds seconds. The TaskGroup stays as the fallback.
- **2026-10-09, draft.** Story C3 (`US-073`) is `Done`. 45 of 45 simulating runs of the replay triggered `routing_adapter`, and 9c ended within 3.91 minutes of `3_calculate_depth`. A routing failure leaving the core run green was not observed. The user accepted the DAG structure and its tests as proof.
