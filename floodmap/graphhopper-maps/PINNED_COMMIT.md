Vendored from https://github.com/graphhopper/graphhopper-maps at commit
`95f1fc19d8f0c72846cfc0656632f4ee71519fa2` (2026-09-08). Upstream has no
release tags, so this is pinned by commit SHA instead — re-vendor
deliberately, don't `git pull`.

Diff from upstream, for Workstream C of the Phase 2 plan (see
`/Users/maianhtran/.claude/plans/okay-now-lets-plan-iterative-fiddle.md`):
- `config.js` -> replaced by `config-local.js` at build time (see
  `config-local.js.example`); untouched otherwise.
- New: the `src/floodmap/` directory. It holds the flood store
  (`FloodStore.ts`, `useFloodState.ts`), the flood extent map layer
  (`FloodExtentLayer.tsx`, `floodExtentTiles.ts`), the map and flood mode toggle
  (`MapModeToggle.tsx`), the legend (`FloodLegend.tsx`), the depth badges and
  forecast chart (`RouteDepthBadges.tsx`, `DepthForecastChart.tsx`), the place
  depth popup (`PlaceDepthPopup.tsx`), and the helpers they use.
- `src/App.tsx` imports `useFloodExtentLayer`, `useFloodBootstrap`,
  `useFloodState`, `MapModeToggle`, `FloodLegend`, `RouteDepthBadges`,
  `PlaceDepthPopup`, and `destinationForPlace` from `src/floodmap/`.
- `src/sidebar/RoutingResults.tsx` imports `DepthForecastChart` from
  `src/floodmap/`. `src/sidebar/instructions/Instructions.tsx` imports
  `stepDepthText` and `useStepDepths` from it.
- New: `test/floodmap/`, the unit tests for the flood helpers.
- New: `Dockerfile`, `nginx.conf` (not part of upstream, which ships as a
  library-style webpack app with no server of its own).

Git history shows other upstream files changed after the import, for example
`src/App.module.css`, `src/map/map.ts`, `src/index.tsx`, `webpack.dev.js`, and the
stores under `src/stores/`. Their edits are not listed here, because they were
not compared with the pinned upstream commit. To list them, diff this directory
against upstream at the commit above.
