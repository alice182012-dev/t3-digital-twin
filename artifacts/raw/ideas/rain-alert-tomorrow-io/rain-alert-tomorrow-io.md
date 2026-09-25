---
date_captured: 2026-09-25
type: idea
status: exploring
source: the user, 2026-09-25 ("create an alert of raining from tomorrow.io")
subsystem: airflow-pipeline
tags: [idea, tomorrow-io, rain, alerting]
related: ["[[rain-alert-tomorrow-io]]", "[[3di-simulation-orchestration]]"]
---

# Rain alert from Tomorrow.io

## Idea

Tell people when rain is forecast, using the Tomorrow.io forecast data the pipeline already reads. Today the
rain gate decides silently. An alert would send a message when the gate decides to run the flood pipeline, and a
heads-up when the forecast first crosses a lower threshold.

## Why it might be worth it

`0_check_forecast_rain` polls Tomorrow.io every 15 minutes (at most 96 calls a day) and decides whether to run
the simulation, but nobody is told. No DAG has a notification callback, and `email_on_failure` is `False`. People
find out that a flood run started only by opening the UI or Airflow.

## Cost-benefit summary

| Option | Effort | Needs | Main risk |
| --- | --- | --- | --- |
| A. Tomorrow.io alert with a webhook to a receiver we host | M to L | A plan that includes Alerts (unconfirmed) and a public HTTPS URL | The server is `100.67.84.55`, a private overlay address, and nginx has no TLS |
| B. Tomorrow.io alert by email or SMS | S to M | A plan with Alerts, and a channel other than webhook | The API docs describe only webhook delivery |
| C. Notify from our own rain-gate task (Telegram or Slack) | S | A bot token, a channel, and an Airflow Variable for dedupe | Adds a notification step to a task that must never fail the gate |
| D. Alert triggers `flood_mapping_full` through the Airflow REST API | L | A public endpoint and a relay for the bearer token | Saves at most 96 calls a day |

The research recommends C: no extra Tomorrow.io calls, no public endpoint, no unconfirmed plan feature.
Tomorrow.io's ready-made flood insight covers only the US, Canada, and Europe, so Hanoi would need a custom rule.

## What's already covered

The rain gate already reads the forecast (2 hours ahead, threshold 5 mm/h) and branches to run or wait. The
forecast call has no timeout (`scripts/create_simulation.py:104`), which is worth fixing with any of the options.

## Trigger to revisit

The user names the channel, the recipients, the thresholds (5 mm/h for the gate and a lower one for the
heads-up), the location (default `21.0285,105.804817`), and quiet hours. Or a public HTTPS endpoint appears, which
would make options A and D possible.

## Status history

- **2026-09-25, exploring.** Captured from the user's request. The feasibility study is
  [[rain-alert-tomorrow-io]]. Unconfirmed: which Tomorrow.io plan includes Alerts, and whether email or SMS is
  available.
