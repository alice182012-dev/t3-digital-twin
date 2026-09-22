---
title: "Architecture in the Age of AI Agents"
source: "https://adityabawankule.substack.com/p/architecture-in-the-age-of-ai-agents"
author:
  - "[[Aditya Bawankule]]"
published: 2025-07-07
created: 2026-09-23
description: "Avoiding tech debt disasters caused by coding agents"
tags:
  - "clippings"
---
I recently created a couple of Electron/Tauri projects with Claude Code that ended up as total disasters. Every time I added a new feature, the basic functionality of the app would break.

![](https://substackcdn.com/image/fetch/$s_!0u1B!,w_1456,c_limit,f_webp,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F565fa96a-36af-40f6-87b4-e6d7d8418c22_1536x1024.png)

After doing some reflection, I came to realize that this was because I didn't clearly define an architecture for the repository. I only defined the MVP spec which had the features and a little bit of pseudocode in there, but not enough of a strict architecture for the agent to stick to while building. Because of that, every time I built a new feature it was built in a different way. While going back and forth and debugging a new feature, it would change a bunch of things which would inevitably break the core functionality.

Interestingly enough, this never happened when working in Next.js because the architecture there is quite opinionated and forces the AI to work within its patterns. But Electron is pretty open-ended with the way it works, and because of that, everything just turns into a mess unless you clearly plan and define the architecture ahead of time.

So here's how to set up a project so you don't run into the same issue.

The number one most important step is to have an architecture document and to force the AI agent to keep this architecture in memory so it always knows when to write that. For Claude, you would put it in claude.md, for Cursor you put that in cursor rule, and for the other tools like Gemini and Codex you would put them put that in agents.md. You could also write out architecture.md and in all caps tell it to reference that file and read it every time before it starts working on a project. That way it has the rules in its context when working.  
  
But that will inevitably not be enough. Eventually, the context window will get too large, and it'll start writing some stuff that are not following the architecture. So you'll also need to set up linter rules to enforce this architecture. Which is pretty easy to do, just feed the architecture docs the AI agent, and tell it to set up a linter to enforce the architecture.

Here's an example of what an architecture doc could look like:

## AI-Agent-Driven Application Architecture

## Overview

This document defines the core architecture, patterns, and enforcement rules for applications built or maintained by AI agents. It is designed to enable safe, parallel, and extensible development by independent agents or teams, while minimizing accidental breakage and ensuring maintainability.

---

## 1\. Principles

1. **Explicit Boundaries**  
	All communication between modules must use shared, type-safe contracts.
2. **Isolation by Design**  
	Features are developed as independent modules with no hidden coupling.
3. **Automated Enforcement**  
	Architecture rules are enforced by CI/CD, static analysis, and test contracts.
4. **Composable and Replaceable**  
	Every module can be swapped, updated, or versioned without affecting unrelated features.
5. **Minimal, Documented Integration Points**  
	Shared interfaces and extension points are always documented and versioned.

---

## 2\. Folder Structure

`/src `

`/core # Pure domain/business logic (NO dependencies on infrastructure, UI, DB) `

`/features `

`/<feature> # Each feature (chat, tools, settings, etc) is isolated; exports its interface `

`/infrastructure # DB, storage, network, AI providers, etc (implementations) `

`/ui `

`/components # Base UI `

`/features # Feature-specific UI, matches `

`/features `

`/hooks # Shared React hooks `

`/shared `

`/types # All shared types/interfaces (the contract) `

`/events # Event bus, events, handlers `

`/di # Dependency injection container & registration `

`/plugins # (Optional) Community or 3rd-party plugins `

`/tests # Test data builders, contract tests, e2e `

`/docs # Architecture docs, interface specs, changelogs`

---

## 3\. Communication & Contracts

### 3.1 Type Contracts

- All inter-module and API communication uses interfaces/types in `/shared/types`.
- Only types in `/shared/types` may be used for cross-feature imports.
- All changes to shared contracts must be PR-reviewed and versioned.

### 3.2 Event Bus

- Asynchronous communication between modules via an event bus in `/events`.
- All events and handlers are strongly typed.
- Event names and payload types are declared in `/events/events.ts`.

### 3.3 Dependency Injection

- All services (including those from `/features` and `/infrastructure`) must register themselves via the DI container in `/di/container.ts`.
- No direct imports of implementations—only import interfaces/types.

### 3.4 API/IPC

- IPC between main/renderer (Electron), or API endpoints (if fullstack), must use contracts defined in `/shared/types` or OpenAPI specs in `/docs`.

---

## 4\. Feature Module Pattern

- Each feature is a folder in `/features/<feature>`.
- Exports only:
	- `register(container: Container): void` (for DI)
		- `getFeatureInterface(): FeatureInterface` (for runtime contracts)
- No internal dependencies between features except via events or shared interfaces.
- All side effects (logging, analytics, DB, etc.) are handled via injected dependencies.

---

## 5\. Plugin System

- Plugins are drop-in modules in `/plugins` with a single entry point:
	- `register(app: AppContext): void`
- Plugins may declare new event types, commands, or UI components via published extension points.
- Plugins run in sandboxes if they have side-effectful or privileged operations.

---

## 6\. Automated Enforcement

- **Linting:** ESLint + TypeScript strict mode; import rules to prevent cross-feature imports outside `/shared/types`.
- **Arch linting:** Use tools like `eslint-plugin-architecture` to enforce boundaries.
- **Contract Testing:** Every feature must have contract tests that validate compliance with `/shared/types` and event payloads.
- **CI Checks:** Block PRs that violate boundaries, types, or contract coverage.
- **Automated Docs:** Use tools (e.g., Typedoc, SpectaQL) to generate up-to-date contract and API docs in `/docs`.

---

## 7\. Example: Adding a New Feature (By AI Agent)

1. **Create Folder:**  
	`/features/summarizer`
2. **Define Interface:**
	In `/shared/types/feature-summarizer.ts`:
	1. `export interface SummarizerRequest { ... } export interface SummarizerResponse { ... }`
3. **Register in DI:**
	In `/features/summarizer/register.ts`:
	1. `import { container } from '../../di/container' import { SummarizerService } from './service' container.register('Summarizer', SummarizerService)`
4. **Implement Event Handlers (if needed):**
	In `/features/summarizer/events.ts`
5. - `import { eventBus } from '../../events/event-bus' eventBus.on('document:uploaded', async (event) => { ... })`
6. **Write Contract Tests:**
	In `/tests/features/summarizer.contract.test.ts`  
	(Tests that service matches interface in `/shared/types`)
7. **Update Docs:**
	- Document feature, contract, and extension points in `/docs/features.md`

---

## 8\. How Agents Should Work

- **Never edit another feature’s code directly.**
- **All communication is through shared contracts, events, or plugin APIs.**
- **All features, plugins, and infrastructure components are registered with the DI container.**
- **Any breaking contract change requires a version bump and cross-feature review.**
- **Use automated tests and linting to verify architectural compliance.**

---

## 9\. Event Bus Contract Example

`// /events/events.ts export type AppEvent = | { type: 'chat:messageSent'; payload: ChatMessage } | { type: 'tool:executed'; payload: ToolExecutionResult } | { type: 'summarizer:summaryReady'; payload: SummarizerResponse } // ...more // /events/event-bus.ts type EventHandler<T extends AppEvent['type']> = (event: Extract<AppEvent, { type: T }>) => void; export class EventBus { on<T extends AppEvent['type']>(type: T, handler: EventHandler<T>) { ... } emit<E extends AppEvent>(event: E) { ... } }`

---

## 10\. Versioning & Backwards Compatibility

- All public contracts (in `/shared/types` and `/events/events.ts`) are versioned.
- Breaking changes require deprecation period and migration strategy.
- Optional: Use semantic versioning in contract files (e.g., `feature-v2.ts`).

---

## 11\. Documentation & Discoverability

- Every shared contract/interface must be documented in `/docs/interfaces.md`.
- Every feature documents its contract, events, and extension points in `/docs/features.md`.
- Plugins and extension points are documented in `/docs/plugins.md`.

---

## 12\. Testing & Validation

- Each feature provides contract and integration tests (with mocks for dependencies).
- End-to-end tests verify interaction across modules only via shared contracts/events.
- Static analysis runs on every push/PR to block violations.

---

## 13\. Tech Stack Recommendations

- **TypeScript:** For end-to-end type safety and contract enforcement.
- **ESLint + Architecture Plugins:** For boundary enforcement.
- **Jest/Vitest + ts-auto-mock:** For contract and integration testing.
- **Typedoc or SpectaQL:** For automated documentation.
- **Tsyringe/Inversify:** For dependency injection.
- **Simple Event Bus Library:** For in-memory or distributed event handling.

---

## 14\. Extension Points (for AI Agents)

- **Feature Contracts:** Add new features by creating new modules and defining contracts in `/shared/types`.
- **Event Types:** Extend by publishing/listening to events in `/events`.
- **UI Components:** Expose extension points in the UI (`/ui/components/FeatureSlot.tsx`).
- **Plugins:** Drop-in modules for extra tools or integrations.

---

## 15\. Key Anti-Patterns (DO NOT DO):

- Do **not** import implementation code from other features.
- Do **not** modify or reference another feature’s state directly.
- Do **not** change shared types/contracts without versioning and review.
- Do **not** bypass DI or event bus for cross-feature communication.
- Do **not** implement "secret" APIs or integration points.

---

## 16\. Example Development Workflow

1. **Agent clones repo, checks** `/docs/architecture.md`
2. **Agent implements new feature in isolated folder**
3. **Defines types/interfaces only in** `/shared/types`
4. **Registers service in DI container**
5. **Implements event handlers if needed**
6. **Adds contract tests and updates docs**
7. **Runs linter/CI for compliance**
8. **Submits PR for review**
9. **PR passes architectural and contract checks before merge**

---

## Summary

This architecture is designed so that **independent AI agents** (or human devs) can:

- Safely add and modify features
- Never break each other’s code
- Rely on clear, versioned contracts
- Communicate through safe, decoupled channels

**Result:**  
You get extensibility, reliability, and a codebase that scales with the number of (human or AI) contributors.