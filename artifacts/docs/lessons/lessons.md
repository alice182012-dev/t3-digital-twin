---
date_captured: 2026-10-10
type: lesson
status: active
tags: [lesson]
related: ["[[decision-log]]"]
---

# Lessons

Short, checkable rules distilled from resolved blockers. One section per lesson. The full incident of each is in the archive and is not read in normal sessions. Add a lesson as a new `## L-nnn` section here when closing a blocker whose cause would generalize past one subsystem.

## L-001

**After a scope change, check every document that cross-references the one that changed.**

When editing a document that another document's Dependencies section names by link, open the
linking document too and check whether its assumption still holds. Fixing the edited document
alone can leave a second document silently wrong.

**How to apply.** Before considering a scope-changing edit finished, grep the vault for `[[wikilinks]]` to the file
just edited (`grep -rl '\[\[filename\]\]' artifacts/docs/`), open each hit, and check whether the
specific claim it makes about the edited file (an endpoint name, a table name, a decision) still
holds. This is the vault-level version of propagating a change through one document's own
sections: the same discipline, one level up, across files instead of within one.

Full incident: [[L-001-check-cross-referencing-documents-after-a-scope-change|L-001 original]].

## L-002

**Check for a registry move before blaming local auth or proxy on a Docker Hub pull denial.**

When a `docker pull` of a known-public image returns "pull access denied ... may require 'docker
login'", test a different public image from the same registry before assuming the problem is local
(auth, proxy, Registry Access Management). If the other image pulls fine, the specific image likely
moved off Docker Hub or restricted anonymous pulls; check the vendor's current recommended registry.

**How to apply.** On any "access denied" or "repository does not exist" pull error for an image that's supposed to be
public: pull a different, unrelated public image from the same registry as a control test before
touching local proxy settings, Docker Desktop sign-in state, or Registry Access Management. A
control-test failure means it's local; a control-test success narrows it to that one image or
namespace, which usually means a vendor-side registry or licensing change, not a local
misconfiguration.

Full incident: [[L-002-check-for-a-registry-move-before-blaming-local-auth-or-proxy|L-002 original]].

## L-003

**Confirm a background process is dead before retrying in parallel.**

Before relaunching a command you believe stalled or died, confirm it actually exited by checking
its effect (output file still growing, containers appearing, the resource it was creating), not by
`pgrep -f "<command line>"` alone on Windows/Git Bash.

**How to apply.** When a long-running build or deploy command looks stalled: check whether its output file is still
growing (`ls -la` the log, compare timestamps across a wait), or whether the resource it's building
toward exists yet, before concluding it's dead. If `pgrep -f` is the only signal available, treat a
negative result as inconclusive on this environment rather than confirmed, and check `ps aux` output
format first to see whether it even carries arguments. Never launch a second instance of the same
mutating command (build, migration, `up`, deploy) against the same target while unsure whether the
first is still running — a race on shared names/resources is a likely outcome, not an edge case.

Full incident: [[L-003-confirm-a-process-is-dead-before-retrying-in-parallel|L-003 original]].

## L-004

**Load technical-writing skills before delegating a document, not while reviewing it.**

When dispatching a subagent to draft a technical document, put "invoke `pstack:technical-writing`
and `pstack:unslop` before writing" in the subagent's own instructions. Do not plan to run the
style pass on the finished output instead.

**How to apply.** Any Agent dispatch whose task is "write a PRD / concept page / plan / lesson" needs the skill
invocation stated as a numbered step in the prompt, the same way the prompt states which template
and directory to use. Reviewing prose for style after a subagent hands it back is a safety net, not
a substitute for the subagent following the rule from its first sentence.

Full incident: [[L-004-load-writing-skills-before-delegating-not-after|L-004 original]].

## L-005

**When a PRD's Goals change, propagate the change through every other section.**

After editing a PRD's Goals to add or remove scope, re-read Problem, Non-goals, Dependencies and
assumptions, Definition of done, and Rollback for sentences that assumed the old scope. A Goals
edit alone leaves the rest of the document telling a story that no longer matches it.

**How to apply.** Treat a Goals-list edit that adds or removes an item as a trigger to re-read the whole PRD, not
just confirm the edit landed. Grep the PRD for the removed or added goal's key terms (an endpoint
name, a service name) across every other section, and update or delete each hit. This is slower
than editing Goals alone, but a PRD with a stale Definition of done is worse than one that took
longer to update, since it will still read as authoritative for years and no error message reports
a stale sentence.

Full incident: [[L-005-propagate-scope-changes-through-every-prd-section|L-005 original]].

## L-006

**When a shared convention file changes mid-session, recheck files already created against it.**

After noticing a project convention file (`.claude/CLAUDE.md`, `Home.md`) changed on disk mid-
session, check files already created earlier in the same session against the new rule, not only
files created after noticing the change.

**How to apply.** A "file changed on disk" notice is a prompt to ask "does anything I already wrote need to change
too," not only "does my next edit need to account for this." Grep for the artifact kind the
convention covers (here, `type: user-story` with a Simple shape) and check each one's frontmatter
or structure against the updated rule before moving on.

Full incident: [[L-006-recheck-existing-files-after-convention-changes|L-006 original]].

## L-007

**Test locale-scoped behavior with real target-language input, not English placeholders.**

When testing a feature meant for a specific country or language, type a real query in that
language, with its actual diacritics or script, not an English stand-in. An English test can pass
while a locale-relevance bug stays invisible.

**How to apply.** For a feature scoped to a specific country or language, include at least one test query in that
language's own script or diacritics, chosen to be ambiguous with a same-name place elsewhere (a
landmark name, not just a city name), since ambiguity is what surfaces a locale-relevance bug that
an unambiguous query hides. An English-only test suite for a non-English-market product checks
encoding at best, not relevance.

Full incident: [[L-007-test-with-real-target-language-input|L-007 original]].

## L-008

**Verify a stated answer resolves the question before recording it as a Decision.**

When a user answers a Risk or open question with a short pointer ("A: flood_road_values"), check
that the thing they named can actually do what the question asked, before writing it into the
PRD's Decisions table as settled. A short answer can name the wrong noun in good faith.

**How to apply.** Before writing a stated answer into a Decisions table, restate the original question in one clause
and check the answer against it directly: does "flood_road_values" cover "depth at an arbitrary
tapped point", not "depth somewhere in this general area" or "depth on the nearest road". If the
check takes more than a sentence to confirm, that's a sign the answer needs verifying against the
actual schema or code before transcribing it, not after.

Full incident: [[L-008-verify-decisions-resolve-the-stated-question|L-008 original]].

## L-009

**Verify a table's capability against its write path, not a summary or its current query.**

Before concluding a data store can't serve a need, read the code that writes rows into it, not
just a one-line schema summary or the query code that happens to read it today. A table can hold
more than its current consumers ask of it.

**How to apply.** Before writing "no data source" or "would need a new table/endpoint" into a PRD's Risks section,
find the function that writes rows into the candidate table (not just the function that reads it
today) and read its loop structure. A `WHERE column = single_value` in existing query code is
evidence about that query's current need, not evidence about what the column or table holds across
all its rows. This applies whenever a table's own description ("keyed by X") could mean either "one
row per X" or "many rows spanning X," since both read the same in a one-line schema summary.

Full incident: [[L-009-verify-table-capability-against-write-path-not-summary-or-current-query|L-009 original]].

## L-010

**Recreate remote services on the remote host.**

To start, rebuild, or recreate a service, run `docker compose` on the remote host over SSH, and
add `--no-deps`. Use `docker --context remote-server compose` from the Mac only for read-only
commands such as `ps`, `logs`, and `exec`.

**How to apply.** The rule is live whenever a task needs `up`, `build`, `restart`, or `--force-recreate` for a service
with a bind mount or a build context. From a PowerShell session on the server (SSH's default
shell, which rejects `&&`), run:

`cd C:\Users\TECOTEC\airflow_new; docker compose up -d --no-deps <service>`

Then run `docker --context remote-server ps` and confirm that every service the task touched is
`Up`, not `Created`. A build context is also read on the client, so a rebuild from the Mac sends the
Mac's files. Keep the checkout on the server at the same commit first.

Full incident: [[L-010-recreate-remote-services-on-the-remote-host|L-010 original]].

## L-011

**Patch the plugin before upgrading a library inside QGIS's Python.**

When a QGIS plugin raises `AttributeError` on a field of an API model, compare the plugin's
expected client version with the client that QGIS loads. If they differ, make the smallest
change to the plugin (a `getattr` with a default) before you upgrade the library. Upgrading the
library inside QGIS's Python changes what every other 3Di plugin imports, and it is hard to
predict from outside QGIS.

**How to apply.** 1. Read the traceback, then compare the model in the bundled client with the model in a client
   that has the field. Use `grep` on `openapi/models/<model>.py` in both.
2. Patch the plugin so a missing field falls back to a default:

   ```python
   getattr(settings_overview.output_settings, "create_debug_hydro_results", False)
   ```

3. Do not install into `profiles/default/python` unless you can afford to lose the plugin
   for a session. If you do, list what the install added first, so you can delete exactly those
   folders. The install added `openapi_client`, `threedi_api_client`, and
   `threedi_api_client-5.0.6.dist-info`.
4. Expect a plugin update to overwrite the patch. Reapply it after every Rana update until the
   bundled client reaches 5.x.

Open item: `simulation/workers.py:1015` sends `create_debug_hydro_results` to the API through the
same 4.2.4 client. A simulation start may still reject the field. Record the result here once
someone starts a real simulation.

Full incident: [[L-011-patch-the-plugin-before-upgrading-the-client-in-qgis-python|L-011 original]].
