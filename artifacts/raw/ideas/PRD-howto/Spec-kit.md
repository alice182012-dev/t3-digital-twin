---
title: "spec-kit: 💫 Toolkit to help you get started with Spec-Driven Development"
source: "https://github.com/github/spec-kit"
author:
published:
created: 2026-09-23
description: "💫 Toolkit to help you get started with Spec-Driven Development - github/spec-kit"
tags:
  - "clippings"
---
[![Spec Kit Logo](https://raw.githubusercontent.com/github/spec-kit/main/media/logo_large.webp)](https://raw.githubusercontent.com/github/spec-kit/main/media/logo_large.webp)

## 🌱 Spec Kit

### Build with a spec, fix a bug, or assess an idea — with your coding agent.

**English** · [简体中文](https://github.com/github/spec-kit/blob/main/README.zh-CN.md)

Spec Kit is an open source toolkit that gives AI coding agents structured processes, reusable templates, and documented outcomes. Start with one of the three processes below, customize it, or bring your own.

## Choose your process

| What you need | Process | Outcome |
| --- | --- | --- |
| Build a feature or application | [Spec-Driven Development](#spec-driven-development) | A specification carried through planning, implementation, and convergence |
| Diagnose and repair broken behavior | [Bug fixing](#bug-fixing) | An assessed cause, scoped fix, and recorded verification |
| Decide whether an idea deserves investment | [Idea assessment](#idea-assessment) | An evidence-backed go, clarify, or stop decision |

These are **independent entry points**, not three mandatory phases. SDD ships in core; bug fixing and assessment are bundled extensions you install when needed.

## Get started

You need **Python 3.11+**, **[uv](https://github.github.io/spec-kit/install/uv.html)**, and a supported AI coding agent on Linux, macOS, or Windows. For **CLI setup only**, run this in your terminal to install Spec Kit and create a project:

```
uv tool install specify-cli
specify init my-project --integration copilot
cd my-project
```

The examples use **GitHub Copilot's default skills mode**. Replace `copilot` with your [integration key](https://github.github.io/spec-kit/reference/integrations.html) to use another supported agent.

Already have code? Follow the [existing-project guide](https://github.github.io/spec-kit/guides/existing-projects.html). For pinned releases, other installers, CI, or troubleshooting, see [Installation](https://github.github.io/spec-kit/installation.html). To update an existing installation, see [Upgrade](https://github.github.io/spec-kit/upgrade.html).

Now **launch your coding agent in the project directory** and choose a process below. Invoke each `/speckit-*` **skill in your agent's chat**, one at a time, and review the result before continuing. These are agent skills, not terminal commands. Other agents and modes may use [different invocation syntax](https://github.github.io/spec-kit/reference/integrations.html#command-invocation).

## Spec-Driven Development

Define **what and why** before deciding **how** to build it. SDD turns your requirements into a specification, a technical plan, and actionable tasks, then guides implementation against those artifacts.

**Constitution once per project; specify → plan → tasks → implement → converge per feature.**

Invoke these skills in your agent's chat:

```
/speckit-constitution Create principles focused on code quality, testing, and maintainability.
/speckit-specify Build a photo organizer with albums grouped by date and a tile preview of each album.
/speckit-plan Use Vite with vanilla JavaScript. Keep images local and store metadata in SQLite.
/speckit-tasks
/speckit-implement
/speckit-converge
```

Repeat **implement → converge** until convergence reports **Converged**. Add clarification, checklists, and consistency analysis when you need extra quality gates.

[SDD walkthrough](https://github.github.io/spec-kit/quickstart.html) · [Command reference](https://github.github.io/spec-kit/reference/agentic-sdd.html)

## Bug fixing

Keep diagnosis, repair, and verification separate so the agent fixes the assessed cause and checks the original symptom. No SDD feature workflow is required first.

**CLI setup (terminal):** install the opt-in extension from the project directory:

```
specify extension add bug
```

Then invoke the **assess → fix → test** skills in your agent's chat:

```
/speckit-bug-assess "Submitting an empty password crashes the login form." slug=login-crash
/speckit-bug-fix slug=login-crash
/speckit-bug-test slug=login-crash
```

The reports live in `.specify/bugs/login-crash/`. Review the final verdict: `verified`, `partial`, or `failed`. Missing verification is not a successful fix.

[Bug-fixing walkthrough](https://github.github.io/spec-kit/guides/bugfix.html) · [Command reference](https://github.github.io/spec-kit/reference/agentic-bugfix.html)

## Idea assessment

Gather evidence before committing to an idea, whether or not it becomes software. This standalone process works even in a project with no source code.

**CLI setup (terminal):** install the opt-in extension from the project directory:

```
specify extension add assess
```

Then invoke the **intake → research → define → shape → decide** skills in your agent's chat:

```
/speckit-assess-intake "Let users work offline and sync when they reconnect." slug=offline-mode
/speckit-assess-research slug=offline-mode
/speckit-assess-define slug=offline-mode
/speckit-assess-shape slug=offline-mode
/speckit-assess-decide slug=offline-mode
```

The artifacts live in `.specify/assessments/offline-mode/`, ending in a **go / needs-clarification / kill** decision. Resolve unknowns by refining the existing Markdown artifacts directly or with the agent, rather than regenerating whole stages. A `go` decision can be handed to `/speckit-specify` if you choose to build it; stopping with a documented reason is also a useful result.

[Assessment walkthrough](https://github.github.io/spec-kit/guides/assessment.html) · [Command reference](https://github.github.io/spec-kit/reference/agentic-assessment.html)

## Customize or bring your own process

**Extensions** add capabilities, **presets** adapt existing behavior, **workflows** automate steps, and **bundles** package a role-based setup. Use project-local overrides for one-off template changes.

[Customization guide](https://github.github.io/spec-kit/guides/customization.html) · [Community extensions, presets, bundles, and walkthroughs](https://github.github.io/spec-kit/community/overview.html)

## Documentation

- [CLI reference](https://github.github.io/spec-kit/reference/overview.html) and [process commands](https://github.github.io/spec-kit/reference/agentic-sdd.html#command-overview)
- [SDD philosophy](https://github.github.io/spec-kit/concepts/sdd.html), [full methodology](https://github.com/github/spec-kit/blob/main/spec-driven.md), and [evolving existing specs](https://github.github.io/spec-kit/guides/evolving-specs.html)
- [Video overview](https://github.github.io/spec-kit/quickstart.html#video-overview) and [project history](https://github.github.io/spec-kit/history.html)
- [How Spec Kit uses Spec Kit](https://github.com/github/spec-kit/blob/main/CONTRIBUTING.md#does-spec-kit-use-spec-kit)

## Star history[![Spec Kit star history chart](https://camo.githubusercontent.com/da862e3d3bd1297d8c81ae618ee3e3d26e1bd3121e6e6d52fbf51556734615e8/68747470733a2f2f6170692e737461722d686973746f72792e636f6d2f7376673f7265706f733d676974687562253246737065632d6b697426747970653d44617465)](https://www.star-history.com/#github/spec-kit&Date)*Thanks to everyone who helps Spec Kit shine.*

## Support and contributing

[Report a bug or request a feature](https://github.com/github/spec-kit/issues/new) · [Contributing guide](https://github.com/github/spec-kit/blob/main/CONTRIBUTING.md) · [Code of conduct](https://github.com/github/spec-kit/blob/main/CODE_OF_CONDUCT.md)

Spec Kit is [MIT licensed](https://github.com/github/spec-kit/blob/main/LICENSE).