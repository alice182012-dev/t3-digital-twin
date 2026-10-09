---
type: reference
status: active
tags: [scrum, velocity, dataview]
related: ["[[Home]]", "[[scrum-framework]]"]
---

# Velocity

Points of the stories that are `Done`, by sprint. A story's points come from its `estimate`: XS is 1, S is 2, M is 3, and L is 5. Plan a sprint from the last three rows, not from the largest. The table reads story frontmatter, so it needs no edits.

```dataview
TABLE sum(map(rows, (r) => choice(r.estimate = "XS", 1, choice(r.estimate = "S", 2, choice(r.estimate = "M", 3, 5))))) AS "Points done", length(rows) AS "Stories done"
FROM "docs/stories"
WHERE type = "user-story" AND status = "Done" AND sprint
GROUP BY sprint
SORT sprint DESC
```

## Baseline before the first two-week sprint

Sprints 1 to 12 lasted days, not two weeks. They started and ended early, so their points measure how much the team finished between two planning moments, not in 14 days. The values at the adoption of Scrum on 2026-10-10, computed from the story files with `python3 -I`, were:

| Sprint | Points | Stories |
| ------ | ------ | ------- |
| 8 | 13 | 4 |
| 9 | 8 | 3 |
| 10 | 7 | 3 |
| 11 | 15 | 6 |
| 12 | 25 | 11 |

The last three sprints give 7, 15, and 25 points, an average of 16. The spread is wide, and a two-week sprint is longer than any of these, so Sprint 13 plans between 16 points (the average) and 25 points (the best of the three). The product owner sets the number at planning. From Sprint 14 on, the forecast uses the points Done in real two-week sprints.
