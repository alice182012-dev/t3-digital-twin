# S2 recession test

This folder holds the brief for the Paper 3 test that uses a 3Di simulation with real recession.
It replaces the synthetic stress test in ledger row C-24, which imposed decay on stored tables and stopped after four arms.
The test runs on the server, in the `p3-harness` container, after the author uploads the simulation result.

## Goal

The stored replay tables show little recession.
Only 2.6% to 3.5% of the edges that reach a limit fall below it again inside one 105-minute window (ledger row C-19).
The sticky closure rule treats a closed edge as closed for the rest of the trip, so recession is the case where the rule costs the most.
The test answers one question: does the sticky rule lose more routes or lengthen more routes, compared with the exact arrival-only search, when the model produces recession?

The stored tables give the reference value.
On the 57 continuous tables, the sticky rule lengthens 3.19% of the routes that have an exact reference route (ledger row C-15).
The test reports the same quantity on the recession tables, for the same pairs, vehicles, and departure steps.

## Label

The recession comes from a drainage mechanism that the author added to the model.
Hanoi's real drainage is not calibrated in the model, so the paper calls the result a test under hypothetical drainage, not a forecast.
`RUN-NOTES.md` must name the mechanism and the source of its values.

## What the author uploads

Put these files in `input/`.
Git ignores everything in that folder, so upload them to the server directly.

1. `result.3di`, the simulation result.
2. `RUN-NOTES.md`, filled in from `RUN-NOTES.template.md`.

If the run already produced edge-depth tables, upload those instead of `result.3di`.
Use the stored format: 67,833 by 8 `uint16` depths in centimetres, the same graph hash as the stored tables, and 15-minute steps.

## Steps

Run every step in `/work/marie-curie/paper-3-result-analysis/` inside `p3-harness`, with 12 workers.

1. **Build the tables.**
   Turn the result into edge-depth tables with the existing pipeline (`scripts/calculate_depth.py`, then `scripts/edge_depth/build_edge_depth.py`).
   Cut a run longer than 105 minutes into windows of 8 steps at 15-minute spacing.
   Check each table with `scripts/edge_depth/check_tables.py`.
2. **Check the recession.**
   Run the reopening census (`T02/analyze.py`) on the new tables.
   The test is only informative if reopening is clearly higher than the stored 3%.
   If it is not, stop and report that the model change did not produce recession.
3. **Check the initial water.**
   Run `T03/analyze.py` and report how many edges are wet at the cold start.
4. **Run the main comparison.**
   Run `python3 -m harness compare` with the sticky rule at margin 600 s, all 60 pairs (`--per-class 20 --seed 1`), 4 vehicles, and departure steps 0 and 4.
   Run it twice, once with `--mask off` and once with `--mask exclude`.
5. **Run the stored-table control.**
   Run the same command on the 57 stored tables if the earlier outputs do not already cover the 60 pairs.
   Both runs must use the same pairs.
6. **Optional, check the engine.**
   Run the sticky engine verification of ledger row C-27 on the new tables, if the engine container is available.

Budget: the main comparison is about 27,360 searches for 57 tables.
The Mac ran about 1 search per second per worker, so 11 workers need about 40 minutes.
Scale that by the number of tables in the upload.

## Result format

Write the results to `results/`.

- `results/result.json`, with a `header` key (commit hash, input, host, date, command, and the harness config), then the keys below.
- `results/README.md`, with the table below, the label from the Label section, and a short reading of the result.

Keys in `result.json`:

| Key | Content |
|---|---|
| `tables` | number of tables, run names, graph hash, steps per table |
| `reopening` | per vehicle: edges that reached the limit, edges that reopened, share, median minutes to reopen |
| `cold_start_wet` | edges wet at the cold start, and how many are 5 cm or deeper |
| `compare.recession` | per vehicle and mask setting: searches, exact share, share longer, share no-route, mean extra seconds of the longer routes |
| `compare.stored` | the same fields for the 57 stored tables |
| `difference` | recession minus stored, per vehicle and mask setting |

Each share states its denominator in the field name or a neighbouring field.
Report the shares among routes that have an exact reference route, as the harness does.

## Decision rule

The paper states the result as measured.
If the share of longer routes differs from the stored value by less than 1 percentage point, the paper says that recession of this speed does not change the result.
If it is higher, the paper reports the increase per vehicle and names the recession speed from `reopening`.

## Ledger

The ledger row C-24 records the stopped stress test.
Row C-32 records this test and takes its evidence from `results/`.
The ledger lives in `marie-curie/paper-03-analysis-tracker.md`.
