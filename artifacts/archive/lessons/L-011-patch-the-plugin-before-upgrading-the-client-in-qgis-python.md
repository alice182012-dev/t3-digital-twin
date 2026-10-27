---
date_captured: 2026-09-26
type: lesson
status: active
subsystem: qgis-rana-plugin
source_blockers: []
tags: [lesson, qgis, rana, threedi-api-client]
related: []
---

# Patch the plugin before upgrading a library inside QGIS's Python

## Rule

When a QGIS plugin raises `AttributeError` on a field of an API model, compare the plugin's
expected client version with the client that QGIS loads. If they differ, make the smallest
change to the plugin (a `getattr` with a default) before you upgrade the library. Upgrading the
library inside QGIS's Python changes what every other 3Di plugin imports, and it is hard to
predict from outside QGIS.

## Why

Starting a simulation in the Rana QGIS plugin 1.2.19 failed with:

```
AttributeError: 'OutputSettings' object has no attribute 'create_debug_hydro_results'
```

The plugin reads that field at `simulation/simulation_wizard.py:4215`. QGIS bundles
`threedi_api_client` 4.2.4 at `/Applications/QGIS.app/Contents/Resources/python3.12/site-packages`,
and its `OutputSettings` model has no such field. Version 5.0.6 has it, so the plugin was
written against 5.x.

The upgrade route cost four attempts and did not work:

1. `/Applications/QGIS.app/Contents/MacOS/bin/python3` does not exist. The interpreter is
   `MacOS/python3.12`.
2. `MacOS/python3.12` fails on start with `No module named 'encodings'`, because it looks for
   its standard library under the build machine's path. The bundle has no pip.
3. `pip install --target` into the bundle's `site-packages` fails with `Operation not permitted`.
   macOS protects the app bundle.
4. `pip install --target` into `profiles/default/python` succeeded, but Rana disappeared from
   QGIS. The install had also added a top-level `openapi_client` package next to
   `threedi_api_client`. The cause of the disappearance was never confirmed. Removing both
   folders and restarting QGIS brought the plugin back.

The fix that worked was a patch of one line in the plugin.

## How to apply

1. Read the traceback, then compare the model in the bundled client with the model in a client
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

## Source blockers

- None. Surfaced while starting a simulation from the Rana plugin on 2026-09-26.

## Status history

- **2026-09-26, active.** Captured after the `getattr` patch cleared the wizard error. The
  client upgrade was rolled back.
