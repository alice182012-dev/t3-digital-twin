---
date_captured: 2026-09-23
type: lesson
status: active
subsystem: floodmap-frontend
source_blockers: []
tags: [lesson, i18n, testing]
related: ["[[PRD-001-flood-routing-mockup-frontend-gap|flood-routing-mockup-frontend-gap]]"]
---

# Test locale-scoped behavior with real target-language input, not English placeholders

## Rule

When testing a feature meant for a specific country or language, type a real query in that
language, with its actual diacritics or script, not an English stand-in. An English test can pass
while a locale-relevance bug stays invisible.

## Why

The search autofill was first tested with "Hanoi", an English spelling that returned correct
results and looked done. Testing again with "Hồ Gươm", the Vietnamese spelling with diacritics,
surfaced a real bug: the geocoder's `locale=en` parameter returned correct, correctly-encoded
Vietnamese matches mixed with irrelevant same-name results outside Vietnam (Ottawa, Munich). The
English test exercised the same code path but could not have found this bug, since "Hanoi" has no
diacritics to mis-encode and is unambiguous enough that an English-locale query still ranks it
first regardless of the locale bug.

## How to apply

For a feature scoped to a specific country or language, include at least one test query in that
language's own script or diacritics, chosen to be ambiguous with a same-name place elsewhere (a
landmark name, not just a city name), since ambiguity is what surfaces a locale-relevance bug that
an unambiguous query hides. An English-only test suite for a non-English-market product checks
encoding at best, not relevance.

## Source blockers

- None. Surfaced from live UI testing via `/browse`, not a resolved blocker.

## Status history

- **2026-09-23, active.** Captured after "Hồ Gươm" found a locale-relevance bug that "Hanoi" had
  not, leading to `index.tsx`'s default locale changing from `navigator.language` to `vi`.
