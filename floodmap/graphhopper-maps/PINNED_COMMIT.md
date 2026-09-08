Vendored from https://github.com/graphhopper/graphhopper-maps at commit
`95f1fc19d8f0c72846cfc0656632f4ee71519fa2` (2026-09-08). Upstream has no
release tags, so this is pinned by commit SHA instead — re-vendor
deliberately, don't `git pull`.

Diff from upstream, for Workstream C of the Phase 2 plan (see
`/Users/maianhtran/.claude/plans/okay-now-lets-plan-iterative-fiddle.md`):
- `config.js` -> replaced by `config-local.js` at build time (see
  `config-local.js.example`); untouched otherwise.
- `src/App.tsx`: two added lines (`useFloodLayer(...)` and `<TimeSlider/>`).
- New: `src/floodmap/FloodStore.ts`, `src/floodmap/FloodLayer.tsx`,
  `src/floodmap/TimeSlider.tsx`, `src/floodmap/TimeSlider.module.css`.
- New: `Dockerfile`, `nginx.conf` (not part of upstream, which ships as a
  library-style webpack app with no server of its own).

No other upstream files were touched.
