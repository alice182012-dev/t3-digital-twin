---
date_drafted: 2026-10-07
type: user-story
us_id: "US-079"
story_label: "4"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Reviewed
priority: P3
estimate: XS
sprint: 15
subsystem: floodmap-frontend
related: ["[[EP-11-frontend-mockup-recheck]]", "[[SP-04-frontend-recheck|sprint-plan-4]]"]
title: "Name the page \"Floodmap\" and remove the \"Powered by GraphHopper\" line and its links"
---

# US-079 Name the page "Floodmap" and remove the "Powered by GraphHopper" line and its links

As a user, I want the page to carry the product's name, so the tab and the shared link do not say GraphHopper.
Given the app is open, when the tab, the empty panel, and the settings box render, then the page title and `og:title` read "Floodmap", the empty panel has no "Powered by GraphHopper" line, and the settings box has no links to `graphhopper.com` (info, imprint, privacy, terms).
`og:url` and `og:image` no longer point at `graphhopper.com`.
`NOTICE.md` and `LICENSE.txt` stay in the repository, and the OpenStreetMap attribution on the map stays.
GraphHopper Maps is Apache 2.0 (`NOTICE.md`).
That license does not require a badge in the UI.
It does require the license and notice files to stay with the code.
The settings box links to `graphhopper.com` pages for info, imprint, privacy, and terms.
They describe GraphHopper GmbH's service and not this app, so they go too.
Decided by the user on 2026-10-07: delete "Powered by" if possible, and delete the settings links ([[decision-log]] D-010).
Dependencies: None.
Covers G4.
Evidence: see below.

## Status history

- **2026-10-13, Ready.** Passes the INVEST check at refinement and is picked for [[SPR-015-match-the-frontend-to-the-mockup|SPR-015]].
- **2026-10-14, In progress.** Started after [[US-144-use-the-mockup-thumbnails-for-the-map-and-flood-tiles|US-144]] was `Reviewed`, within the limit of two.
- **2026-10-14, Reviewed.** Built and checked in a local dev build against the server backend. It waits for the one frontend rebuild on the server and the owner's acceptance.
- **2026-10-14, owner answer.** The `homepage` field in `package.json` and the `graphhopper.com` text in the GPX export metadata do not change.

## Evidence and details

![[live-settings-box.jpg|420]]

1. What: the tab title and `og:title` read "Floodmap", the empty routing panel has no "Powered by GraphHopper" line, and the settings box has no info, imprint, privacy, or terms link, only "Feedback" (a GitHub link). `og:url` and `og:image` are removed, and the served page has no match for "graphhopper". The OpenStreetMap attribution stays. `NOTICE.md` and `LICENSE.txt` are untouched.
2. How: `src/index.html`, `src/manifest.json` (name and short name), `src/App.tsx`, and `src/sidebar/SettingsBox.tsx` changed, and `PoweredBy.tsx`, its CSS, and `header.svg` are deleted because nothing else used them. `test/IndexHtml.test.ts` reads `index.html` and asserts the literal title and `og:title` and that the file has no `graphhopper.com`. The whole jest suite (320 tests) and `tsc --noEmit` pass on the merged tree.
3. Left in place: the translation keys for the removed UI in `tr.json` (a large generated diff), the `homepage` field in `package.json`, and the GPX export metadata in `RoutingResults.tsx`, which writes `graphhopper.com` into exported files. The owner decides whether either of the last two goes.
4. Not checked: the small-screen layout and the PWA manifest in a browser.
5. Left for `Done`: the server rebuild, a server screenshot, and the update of [[floodmap-frontend]].
