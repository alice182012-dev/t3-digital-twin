---
date_drafted: 2026-10-02
type: user-story
us_ids: ["US-062"]
status: done
subsystem: floodmap-frontend, airflow-pipeline
sprint: 5
source_ideas: []
related: ["[[flood-map-reaction-time-findings]]", "[[sprint-plan-2]]", "[[map-refresh-requirement-research-plan]]", "[[map-shows-forecast-not-now]]", "[[five-minute-tile-freshness]]", "[[carried-over-backlog]]"]
tags: [user-story, research, requirements, refresh-interval]
---

# Find out how fast a user must react to the flood map

## User story (US-062)

As the product owner, I want to know the shortest time in which a person must react to what the flood map shows, so I can decide on evidence whether a 15-minute refresh is enough or whether the pipeline needs a faster one.

## Priority

P2. It sets the refresh target for the pipeline. It blocks no build today.

## Estimate

M. The plan is one day. The evidence work is an internet and literature search in English and Vietnamese, with a comparison against our own model.

## Acceptance criteria

Given the research plan [[map-refresh-requirement-research-plan]] is confirmed, when the research is done, then the findings page states, for the usual case and the extreme case in Hanoi, how many minutes pass between the start of rain and flooding and how fast the water rises, with the source of each number (a paper, an agency report, or a news report, in English or Vietnamese). It then states the shortest time a person has to act on the map in each case. It also records one decision: keep the 15-minute refresh, label the age of the map, or open a story for a shorter refresh, with the cost from [[five-minute-tile-freshness]] and `marie-curie/idea-24h-five-minute-preview-run.md`.

The user does not know the answer today (2026-10-02), so the answer comes from internet research, not from the user. The user ruled out interviews, and asked for English and Vietnamese sources and for real Hanoi rates, not the test storm.

## Evidence

![[us-062-decision-check-output.png|700]]

## Details

1. What: the findings page [[flood-map-reaction-time-findings]] states, for the usual and the extreme case in Hanoi, how long flooding takes after rain starts and the shortest time a person has to act, with a source for each number (12 sources read, English and Vietnamese). It records one decision: keep the 15-minute refresh for now.
2. How: about 20 searches under the plan [[map-refresh-requirement-research-plan]], with no interviews, as the user asked. Each number in the evidence table carries its source, and the page marks what is inference.
3. Why: the user did not know how fast a person must react to the map, and wanted to decide on evidence whether a 15-minute refresh is enough.
4. Effect: the pipeline keeps its 15-minute cycle, so [[five-minute-tile-freshness]] stays closed and no story is opened for a shorter refresh. The map-age label and a 5-minute pipeline were not chosen. The findings page lists what would reopen the question: rain input from radar or gauges every 5 minutes. Two gaps remain: no measured cm per minute of rise for Hanoi, and no measure of how well the rain forecast predicts a 30-minute burst.

## Status history

- **2026-10-02, draft.** The user asked whether 15 minutes can be called real-time. The answer depends on the shortest time in which a person must react, which nobody knows yet. The user asked for a plan for today, and for research to follow.
- **2026-10-02, in-progress.** Scheduled in Sprint 5 as P2, size M, from the user's request for "todos for today". The plan is written with the `academic-research-skills:deep-research` skill, Phase 1 only. Phase 2 starts when the user confirms the plan.
- **2026-10-02, in-progress.** The user confirmed the plan with changes: no interviews, internet research only, English and Vietnamese sources, real Hanoi rates for the usual and the extreme case, and the user's understanding (about 30 minutes from rain to flood in Vietnam) to be tested. See Revision 1 of [[map-refresh-requirement-research-plan]]. The search starts now.
- **2026-10-02, in-progress.** The search is done: 12 sources read in English and Vietnamese, with the findings in [[flood-map-reaction-time-findings]]. Usual case: flooding within minutes of a 30-minute heavy burst. Extreme case: hours. No measured rate of rise in cm per minute was found for Hanoi. The recommended decision is to keep the 15-minute refresh and add the age of the map. The decision is the user's, so the story stays open until the user records it.
- **2026-10-02, done.** The user decided to keep the 15-minute refresh for now, so the decision of the acceptance criteria is recorded and the story is `Done`. Evidence: `us-062-decision-check-output.png`.
