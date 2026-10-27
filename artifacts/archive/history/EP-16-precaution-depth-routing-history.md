---
date: 2026-10-10
type: archive
status: archived
tags: [archive, history]
related: ["[[EP-16-precaution-depth-routing]]"]
---

# EP-16-precaution-depth-routing: archived story-level history

Lines moved out of the Status history of [[EP-16-precaution-depth-routing]] on 2026-10-10 under the rule "Write each fact once". Each fact is also in its story file. Not read in normal sessions.

- **2026-10-09, reviewed.** The user approved the response contract. Built on `modular`: path 0 is the recommended route, path 1 the through-water route, hints `td.kinds`, `td.limit_cm`, `td.precaution_cm`, profile hint `td_precaution_fraction` (default 0.5), second search only when the limit route touches the precaution depth. 137 Java tests passed on GitHub Actions (run 37885851481). The server image is rebuilt at the next rollout, and the flag is off at rest. `US-098` can read the contract.
- **2026-10-09, done.** The rollout rebuilt the server images from `modular` (`11f6373`) and every script check passed. With the flag on, `POST /route` for the "long" trip with the truck and foot profiles returned 2 paths and `td.kinds: "recommended,through_water"`; the same trip with motorbike and car returned 1 path, `td.kinds: "recommended"`. Evidence: `us-097-through-water-route-output.png`.
