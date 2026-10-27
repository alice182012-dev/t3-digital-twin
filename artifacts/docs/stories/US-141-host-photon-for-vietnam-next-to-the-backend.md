---
date_drafted: 2026-10-13
type: user-story
us_id: "US-141"
title: "Host Photon for Vietnam next to the backend"
epic: ""
status: Not started
kind: story
priority: P2
estimate: M
sprint: 
subsystem: floodmap-backend, deploy
source_ideas: []
related: ["[[BL-021-place-name-slow-after-map-tap|BL-021]]", "[[graphhopper-backend]]", "[[BL-008-photon-rejects-vi-locale|BL-008]]"]
tags: [user-story]
---

# US-141 Host Photon for Vietnam next to the backend

As a user, I want the name of a tapped place to come back in well under a second, so the popup is complete when it opens.

The backend asks the public instance `photon.komoot.io` for every place name and every search ([[BL-021-place-name-slow-after-map-tap|BL-021]]).
On 2026-10-13 that instance needed 4 to 6.5 s to answer from the server, and 11 of 12 calls of `GET /places/reverse` timed out at the 5 s limit, so the popup often has no name.
A public instance has no promise of speed, and a cache of recent answers only helps a second tap of the same point.
The story runs Photon as a service of `compose.yml` with a Vietnam index, and it points `PHOTON_BASE_URL` of `floodmap-backend` at it.

Two routes give the index, and the first task of the story chooses one by trying both on the server in a throwaway container.
Route 1 is the Vietnam extract of GraphHopper (`photon-db-vn-250720.tar.bz2`, 142 MB, July 2025 format), which needs the Photon version that reads it.
Route 2 is Photon 1.x with an index that it builds from the planet JSON dump (27 GB) for Vietnam only, if its import can filter by country.
The service needs Java (21 or later for Photon 1.x), a volume for the index, a heap of a few GB, and no published port.
The server has 585 GB of free disk and about 9 GB of free memory while the pipeline runs.

Given the new service on the server, when `GET /places/reverse` is called for a point inside the model border, then the answer comes in under 1 s at the median over 20 calls, and no call times out.
Given `GET /places/search` with a Vietnamese query with diacritics (for example "Hoàn Kiếm"), then the results are the same kind as before ([[BL-008-photon-rejects-vi-locale|BL-008]]).
Given the service stopped, then the backend answers 503 with its existing message and does not hang.
Given the licence of the data, then the story records it (the OpenStreetMap data of the index needs its attribution).

Dependencies: None. The owner decides the deploy of a new service.

## Status history

- **2026-10-13, draft.** Raised by the measurement of [[BL-021-place-name-slow-after-map-tap|BL-021]]. It is in the backlog and has no `sprint`.
- **2026-10-13, Not started.** The product owner put it on hold and will come back to it later. It stays in the backlog with no `sprint`, and nothing is built. [[BL-021-place-name-slow-after-map-tap|BL-021]] keeps the measurement of 2026-10-13.

## Evidence and details

Fill this when the story reaches `Done`.
