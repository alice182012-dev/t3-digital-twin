import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

import render_todos
from render_todos import NEXT_ACTION_END, NEXT_ACTION_START, main, render_vault


def story(us_id, title, status, priority, estimate, sprint="", epic="EP-18-time-aware-routing-engine", kind="story"):
    return (
        f'---\ntype: user-story\nus_id: "{us_id}"\ntitle: "{title}"\nepic: "[[{epic}]]"\nstatus: {status}\n'
        f"kind: {kind}\npriority: {priority}\nestimate: {estimate}\nsprint: {sprint}\nrelated: [\"[[x]]\"]\n---\n\n# body\n"
    )


SPRINT = (
    "---\ntype: sprint\nsprint: 13\nstart_date: 2026-10-12\nend_date: 2026-10-25\nstatus: planning\n---\n\n"
    "# SPR-013\n\n## Sprint goal\n\nProve the replay.\n\n## Planning\n"
)
BLOCKER = "---\ntype: blocker\nstatus: monitoring\nseverity: P0\n---\n\n# rain gate stops the simulation\n"


class VaultCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.vault = Path(self._tmp.name)
        for folder in ("stories", "sprints", "blockers"):
            (self.vault / "docs" / folder).mkdir(parents=True)

    def write(self, folder, name, text):
        (self.vault / "docs" / folder / name).write_text(text, encoding="utf-8")


class RenderTest(VaultCase):
    def test_sprint_backlog_and_blockers(self):
        self.write("sprints", "SPR-013-prove.md", SPRINT)
        self.write("stories", "US-102-replay.md", story("US-102", "Replay the storm", "Ready", "P0", "M", "13"))
        self.write("stories", "US-089-start.md", story("US-089", "Start a replay", "In progress", "P1", "M", "13"))
        self.write("stories", "US-070-slow.md", story("US-070", "Stop a slow step", "Done", "P1", "S", "13"))
        self.write("stories", "US-091-measure.md", story("US-091", "Measure it", "Not started", "P1", "M", epic="EP-20-paper", kind="spike"))
        self.write("stories", "US-021-old.md", story("US-021", "Dropped", "Superseded", "P1", "M"))
        self.write("stories", "US-001-chart.md", story("US-001", "Chart", "Done", "P2", "L"))
        self.write("blockers", "BL-028-rain-gate.md", BLOCKER)
        self.write("blockers", "BL-027-old.md", BLOCKER.replace("monitoring", "resolved"))

        self.assertEqual(
            render_vault(self.vault),
            f"""# TODOS

{render_todos.HEADER}

{render_todos.INTRO}

## Next action

{NEXT_ACTION_START}
None.
{NEXT_ACTION_END}

## Current sprint: Sprint 13, 2026-10-12 to 2026-10-25

**Goal:** Prove the replay.

**Sprint file:** [[SPR-013-prove|SPR-013]]

**Status:** planning. 8 points picked, 2 done.

### In progress - US-089 Start a replay

**Story:** [[US-089-start|US-089]]. P1, M (3 points), [[EP-18-time-aware-routing-engine|EP-18]].

### Ready - US-102 Replay the storm

**Story:** [[US-102-replay|US-102]]. P0, M (3 points), [[EP-18-time-aware-routing-engine|EP-18]].

### Done - US-070 Stop a slow step

**Story:** [[US-070-slow|US-070]]. P1, S (2 points), [[EP-18-time-aware-routing-engine|EP-18]].

## Product backlog

1 stories. The top 1 by priority:

- [[US-091-measure|US-091]], P1, M, Not started. Measure it

## Open blockers

- [[BL-028-rain-gate|BL-028]], P0, monitoring. rain gate stops the simulation

All blockers: [[Blockers board]].
""",
        )

    def test_a_quoted_title_keeps_its_quotes(self):
        self.write("sprints", "SPR-013-prove.md", SPRINT)
        self.write("stories", "US-035-slow.md", story("US-035", 'Revalidate \\"loading is slow\\"', "Done", "P1", "S", "13"))
        self.assertIn('### Done - US-035 Revalidate "loading is slow"', render_vault(self.vault))

    def test_no_sprint_and_no_blockers(self):
        output = render_vault(self.vault)
        self.assertIn("## Current sprint\n\nNo sprint is active or in planning.", output)
        self.assertIn("## Open blockers\n\nNone.\n\nAll blockers: [[Blockers board]].", output)

    def test_the_active_sprint_wins_over_one_in_planning(self):
        self.write("sprints", "SPR-013-a.md", SPRINT.replace("planning", "active"))
        self.write("sprints", "SPR-014-b.md", SPRINT.replace("sprint: 13", "sprint: 14"))
        self.assertIn("## Current sprint: Sprint 13,", render_vault(self.vault))

    def test_an_unknown_estimate_fails_with_the_file_name(self):
        self.write("stories", "US-005-bad.md", story("US-005", "Bad", "Ready", "P1", "XL"))
        with self.assertRaisesRegex(ValueError, r"US-005-bad\.md.*estimate 'XL'"):
            render_vault(self.vault)

    def test_a_story_without_frontmatter_fails(self):
        self.write("stories", "US-005-bad.md", "# no frontmatter\n")
        with self.assertRaisesRegex(ValueError, "no frontmatter"):
            render_vault(self.vault)


class RunTest(VaultCase):
    def run_main(self, *args):
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(["--vault", str(self.vault), *args])
        return code, out.getvalue(), err.getvalue()

    def test_the_hand_written_next_action_survives_a_rerun(self):
        self.write("sprints", "SPR-013-prove.md", SPRINT)
        self.run_main()
        todos = self.vault / "TODOS.md"
        text = todos.read_text(encoding="utf-8").replace("None.\n" + NEXT_ACTION_END, "1. Replay the storm.\n2. Decide on the flag.\n" + NEXT_ACTION_END)
        todos.write_text(text, encoding="utf-8")
        self.write("stories", "US-102-replay.md", story("US-102", "Replay the storm", "Ready", "P0", "M", "13"))

        code, stdout, _ = self.run_main()

        self.assertEqual(code, 0)
        self.assertIn(f"wrote {todos}", stdout)
        rewritten = todos.read_text(encoding="utf-8")
        self.assertIn(f"{NEXT_ACTION_START}\n1. Replay the storm.\n2. Decide on the flag.\n{NEXT_ACTION_END}", rewritten)
        self.assertIn("### Ready - US-102 Replay the storm", rewritten)

    def test_a_second_run_changes_nothing(self):
        self.write("sprints", "SPR-013-prove.md", SPRINT)
        self.run_main()
        first = (self.vault / "TODOS.md").read_bytes()
        code, stdout, _ = self.run_main()
        self.assertEqual((code, stdout), (0, ""))
        self.assertEqual((self.vault / "TODOS.md").read_bytes(), first)

    def test_check_reports_a_stale_file_and_writes_nothing(self):
        self.write("sprints", "SPR-013-prove.md", SPRINT)
        self.run_main()
        self.write("stories", "US-102-replay.md", story("US-102", "Replay the storm", "Ready", "P0", "M", "13"))
        stale = (self.vault / "TODOS.md").read_bytes()

        code, _, stderr = self.run_main("--check")

        self.assertEqual(code, 1)
        self.assertIn("is out of date", stderr)
        self.assertEqual((self.vault / "TODOS.md").read_bytes(), stale)

    def test_check_passes_on_a_fresh_file(self):
        self.write("sprints", "SPR-013-prove.md", SPRINT)
        self.run_main()
        self.assertEqual(self.run_main("--check")[0], 0)


if __name__ == "__main__":
    unittest.main()
