---
date: 2026-10-02
type: plan
branch: front-end-according-to-mock-up
status: active
tags: [plan, research, requirements, refresh-interval, us-062]
related: ["[[map-refresh-requirement-research]]", "[[sprint-plan-2]]", "[[map-shows-forecast-not-now]]", "[[five-minute-tile-freshness]]", "[[2026-10-02]]"]
---

# Plan: how fast must a user react to the flood map

This is Phase 1 (scoping) of the `academic-research-skills:deep-research` skill, for story `US-062` ([[map-refresh-requirement-research]]). The skill's rule is that Phase 2 (investigation) starts only after the user confirms this page.

## Context

The map refreshes every 15 minutes. A tile for time t is built from rain forecast fetched at t minus 15 minutes, and it stays on screen from t to t plus 15 minutes. So the content is 15 to 30 minutes old by the clock ([[2026-10-02]]). On 2026-10-02 the user asked whether that is "real-time". The honest answer is "near real-time", and whether it is enough depends on a number nobody has: the shortest time in which a person must react to the map. The user said they do not know and that research is needed.

## Research question

**How many minutes does each kind of map user have to act on what the map shows, and does a 15-minute refresh (15 to 30 minutes of age) meet that time?**

### Sub-questions

1. **Water.** In our own model, how fast does depth rise on a road piece? What share of pieces cross a vehicle limit (motorbike 20 cm, car 30 cm, truck 35 cm, foot 40 cm) within 15 minutes?
2. **Evidence.** What do published sources say about the warning time people have in urban flash floods, and what refresh interval flood maps and traffic or navigation apps use for the same kind of decision?
3. **Users.** Who uses the map, what do they decide from it, and how long do they have: a rider choosing a route, a driver already on the road, a resident, council or dispatch staff?
4. **Cost.** If the answer is shorter than 15 minutes, what does the next step cost? [[five-minute-tile-freshness]] and `marie-curie/idea-24h-five-minute-preview-run.md` already price a 5-minute map, and the cheap options are a label for the age and a coarse preview tile.

### FINER check

| Criterion | Assessment |
| --------- | ---------- |
| Feasible | Sub-questions 1 and 4 use data we hold. Sub-question 2 is a literature scan. Sub-question 3 needs access to a few people, which is not yet confirmed. |
| Interesting | It sets the refresh target for the whole pipeline. |
| Novel | Not novel as science. It is new for this product and this city. |
| Ethical | Interviews need informed consent and no personal data in the vault. The map is a flood-safety tool, so an answer that is too loose has a safety cost. |
| Relevant | Decides whether the 15-minute cycle, the cost of the tile build, and the "real-time" wording are right. |

### Scope

- **In:** the Hanoi pilot area, the four vehicle modes, the map in Flood mode, and the time from a new tile to a user's action.
- **Out:** building any faster pipeline, the alert channel (push alerts are not built), and rain forecast quality.

## Method blueprint

A mixed design. Paradigm: pragmatist, because the output is a product decision. Three strands, each answering one sub-question.

| Strand | Sub-question | Data | Output |
| ------ | ------------ | ---- | ------ |
| A. Our own data | 1 | `flood_road_values` (8 steps per run, 15-minute spacing) and `flood_depth_raster_tile`. Depth change between consecutive steps per piece, by vehicle limit. | A distribution table. The storm is the test storm of 50 mm/h, so it is a stress case, not a measured event. |
| B. Literature scan | 2 | Sources on urban flash flood onset and warning time, flood map and traffic app refresh. Run in `lit-review` or `three-way-scan` mode of the same skill. | An annotated list graded by source tier, with the numbers quoted and a note on how each applies to Hanoi. |
| C. People | 3 | 5 to 8 short interviews or a short survey: riders, drivers, a resident, and council or dispatch staff. Questions on the decision, the time they have, and what age of map they would accept. | A table of user group, decision, minutes available, and the quote. No personal data stored. |

### Validity and bias rules

- The test storm is not real rain. Strand A answers "how fast can water rise in this model", and it must not be quoted as a measured Hanoi rate.
- The team hopes 15 minutes is enough. Strand B must search for counter-evidence on purpose, and the findings must show what contradicts 15 minutes.
- Interview answers are stated preferences. Treat them as a range, and mark each as a quote, not a measurement.
- Every number in the findings carries its source. A number without one does not go in.

## Devil's advocate check of this plan (checkpoint 1)

1. **Is the question answerable?** Yes in two parts: the water and the cost from data we hold. The user's reaction time may have no single answer, so the findings will give a range per group.
2. **Is the method suited?** Strand C is the weak point, because it depends on reaching users. If it cannot happen, the findings will say the user side is unanswered, and strands A and B still give a defensible floor.
3. **Is the scope too wide or too narrow?** One refresh interval is a narrow decision, and the plan keeps the scope to it. The risk is drift into building a faster pipeline, which is out of scope.
4. **Verdict:** PASS, with the condition that strand C's access is settled before Phase 2 starts.

## Steps

1. **Today (2026-10-02):** this plan, the story `US-062`, and the sprint plan and `TODOS.md` rows. Done when the user confirms the plan.
2. **Strand A, about half a day:** one SQL analysis of the depth rise per 15 minutes by vehicle limit, with a table and a short note on its limits. It needs no one else.
3. **Strand B, about a day:** the literature scan in `lit-review` or `three-way-scan` mode of the deep-research skill, with a verification pass on every source.
4. **Strand C, about two days of calendar time:** needs the user to name who can be asked. Write the interview questions first and review them.
5. **Synthesis:** one findings page with the reaction time per group in minutes, the 15-minute verdict, and the decision (keep 15 minutes, label the age, or open a story for a faster refresh).
6. **Close:** the findings go in the epic file and the sprint plan with evidence and numbered details.

## Questions for the user before Phase 2

1. Who can we ask in strand C, and may we approach them? Without names, strand C stays empty.
2. Which user group matters most: riders, drivers, residents, or council and dispatch staff? It sets the interview order.
3. Is a published source in English enough, or do you need Vietnamese sources too?

## Status history

- **2026-10-02, active.** Plan written as Phase 1 of the deep-research skill. Waiting for the user's confirmation and the answers to the three questions.

## Revision 1, 2026-10-02: the user's answers

The user answered the three questions and changed the method. This section replaces strands A and C above. The rest of the page is the record of the first version.

1. **No interviews.** Strand C is dropped. The research is internet research only.
2. **Real rates, not the test storm.** The test storm of 50 mm/h is a stress case. The research must find the real Hanoi rate of flood rise for two cases: the usual case (a normal heavy rain) and the extreme case (a record or typhoon event).
3. **Two kinds of source.** Academic works (papers, reports) on urban flood onset, warning time, and refresh intervals, and web sources (news, agency reports, measurements) on how quickly water rises on Vietnamese streets.
4. **Languages.** English and Vietnamese.
5. **A claim to test, not a source.** The user's own understanding is that in Vietnam the flood arrives about 30 minutes after the rain starts. The findings must say whether the sources support it, for which rain, and where.

### Questions the research answers now

- **Q1 (onset).** After the rain starts, how many minutes pass before the streets flood in Hanoi, in the usual and the extreme case?
- **Q2 (rate).** Once flooding starts, how fast does the water rise, in cm per 10 to 15 minutes? What depths are reached, and how fast, against our vehicle limits (20, 30, 35, 40 cm)?
- **Q3 (academia).** What do published works say about the time between rain and flooding in cities, the warning time people have, and the refresh interval that urban flood maps and nowcasts need?
- **Q4 (verdict).** Given Q1 to Q3, what is the shortest time a person has to act on the map, per case, and does a map that is 15 to 30 minutes old meet it?

### Method

- Mode: `lit-review` and `three-way-scan` of the deep-research skill, plus a fact-check pass on every number.
- English search: Google Scholar style and agency sources. Vietnamese search: terms such as "ngập úng Hà Nội sau mưa bao lâu", "mực nước ngập tăng", "mưa lớn Hà Nội thời gian ngập", and agency pages from the national hydro-meteorological service.
- Each source is graded by tier (peer-reviewed, agency or institutional report, news). A number from news is marked as a report, not a measurement.
- A number without a verified source does not go in. A source I cannot open counts as FAIL.
- Counter-evidence is searched on purpose (cases where flooding came faster than 30 minutes, or where 15 minutes of age would have been too slow).
- Our own data (strand A) becomes a check only: compare the rise per 15 minutes in our model with the real rates found, to say how realistic the test storm is. It is a step after the search.

### Steps now

1. Search and open sources in English and Vietnamese, for Q1 and Q2 (Hanoi and Vietnam, usual and extreme).
2. Search the academic side for Q3.
3. Write the findings page with a table: case, onset, rise rate, depth, source, source tier, language.
4. Answer Q4 and record the decision for `US-062`.
5. Compare with our model's rise rates.

## Status history (continued)

- **2026-10-02, active.** Revision 1: no interviews, internet research only, English and Vietnamese, real Hanoi rates for the usual and the extreme case, and the user's 30-minute understanding to test. Phase 2 (investigation) starts now.
- **2026-10-02, active.** Steps 1 to 4 of Revision 1 are done. The findings page is [[flood-map-reaction-time-findings]], with 12 sources read. Step 5 (compare with our model's rise rates) is not done, because no measured Hanoi rate of rise was found to compare with. Waiting for the user's decision.
