---
date: 2026-09-25
type: plan
status: active
tags: [plan, airflow, tomorrow-io, rain, alerting, feasibility]
related: ["[[3di-simulation-orchestration]]"]
---

# Rain alert from Tomorrow.io

This note is a read-only feasibility study. Nobody changed code, called the Tomorrow.io API, or
touched the remote host while writing it.

## The question

The user asked whether we can create an alert about rain from Tomorrow.io, starting from tomorrow.
"Alert" can mean any of the following things, and the options later in this note cover each one:

1. A message to people (Slack, Telegram, email, or SMS) when heavy rain is forecast for the study
   point in the next few hours.
2. A message to people with tomorrow's rain outlook, sent once a day. "Starting from tomorrow" can
   also be read this way: a day-ahead forecast, not a start date.
3. A machine signal that starts `flood_mapping_full` when rain is forecast, in place of the
   15-minute poll.

The user needs to say which meaning they want. The recommendation covers meanings 1 and 2.

## What exists in the repo

### The forecast call

- `scripts/create_simulation.py:82-111` (`get_rain_forecast`) calls
  `GET https://api.tomorrow.io/v4/timelines` with one field, `precipitationIntensity`, in
  `metric` units (mm/h). It asks for `15m` timesteps from now to now plus
  `FLOOD_RAIN_LOOKAHEAD_HOURS` (default 2, line 34 and `compose.yml`).
- The location is one point, `LOCATION_LAT`,`LOCATION_LON`, default `21.0285,105.804817` in Hanoi
  (lines 27-28). Neither name is in `.env.example` or in the `compose.yml` environment list. The
  services load the whole `.env` file (`compose.yml:5-6`), so the server may override the default.
  That value was not checked.
- `FLOOD_TEST_RAIN_MM_HR` skips the API call and returns a fixed series (lines 89-93).
- Error handling: any exception, including an HTTP 429, prints `Lỗi Weather API` and returns
  `None` (lines 106-111). `requests.get` has no `timeout` (line 104), so a hung connection holds
  the task until Airflow kills it.
- `rain_intensity_mm_hr` (lines 114-121) reads `precipitationIntensity` and falls back to
  `rainIntensity`. Missing or bad values count as 0.
- `evaluate_rain_gate` (lines 124-133) returns `should_run` when the largest interval value is at
  least the threshold. It also returns `max_intensity_mm_hr`, `threshold_mm_hr`, and
  `interval_count`.

### The rain gate in the DAG

- `dags/flood_mapping_dag.py:68-69` reads `FLOOD_RAIN_THRESHOLD_MM_HR` (default `5`) and
  `FLOOD_RAIN_CHECK_INTERVAL_SECONDS` (default `900`).
- `task_check_forecast_rain` (lines 72-91) raises `ValueError` when the forecast is empty, so a
  failed Tomorrow.io call fails the cycle. It is not a dry cycle. It pushes `rain_intervals` and
  `rain_gate_decision` to XCom and returns `1_trigger_simulation` or
  `wait_before_next_rain_check`.
- The docstring on line 73 says "0.01 mm/h". The code uses the 5 mm/h default. The docstring is
  stale.
- `wait_before_next_rain_check` is a `TimeDeltaSensor` in `reschedule` mode with a
  `RAIN_CHECK_INTERVAL_SECONDS` delta (lines 384-388).
- `default_args` sets `email_on_failure: False`, `retries: 1`, and a one-minute `retry_delay`
  (lines 362-368). `max_active_runs=1` (line 377).
- No DAG in `dags/` has an `on_failure_callback`, an `on_success_callback`, a notifier, or an
  email, Slack, or Telegram call. A search for those names in `dags/` found nothing.

### How often the DAG runs

- The schedule is `VNContinuousTimetable()` (line 374), imported from `vn_timetable`.
- `plugins/vn_timetable.py` is not in the repo. `.gitignore:48` ignores `/plugins/`, and the file
  exists only on the server. The concept page [[3di-simulation-orchestration]] says the next cycle
  starts when the previous one finishes. This note relies on that page for the timetable.

### Calls per day to Tomorrow.io

- A dry cycle makes one call and then waits 900 seconds. The upper bound for
  `flood_mapping_full` is 86,400 / 900 = 96 calls per day. The real number is a little lower
  because each cycle also spends scheduler time.
- A wet cycle makes one call and then runs a 7,200-second simulation plus processing, so rainy
  days use fewer calls.
- A failed call can cost 2 calls per cycle because of `retries: 1`.
- Two other DAGs also call Tomorrow.io. `dags/test_dag.py:219` runs every 30 minutes and calls
  `create_simulation.run_forecast_process`, which calls `get_rain_forecast` when no intervals are
  passed (`scripts/create_simulation.py:215`). `dags/initial_wl_dag.py:199` runs every 30 minutes
  and reaches `scripts/initial_wl/simulation_initial_wl.py:52-75`, a separate copy with `1h`
  timesteps. If both are unpaused, each adds up to 48 calls per day. `compose.yml:13` sets
  `AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION: 'false'`. Whether these DAGs are paused on the
  server is unconfirmed.

### Environment variables (names only)

`.env.example` defines `TOMORROW_API_KEY`, `FLOOD_RAIN_THRESHOLD_MM_HR`,
`FLOOD_RAIN_CHECK_INTERVAL_SECONDS`, `FLOOD_RAIN_LOOKAHEAD_HOURS`, `FLOOD_RAIN_TIMESTEP_MINUTES`,
`FLOOD_TEST_RAIN_MM_HR`, and `AIRFLOW_PORT`, among others. No variable exists for a Slack webhook,
a Telegram bot, SMTP, or alert recipients.

### Airflow image and providers

- `Dockerfile` builds `FROM apache/airflow:3.1.7`. `requirements.txt` adds `requests` but no
  Airflow provider packages.
- Which providers the base image ships (for example `slack` or `smtp`) is unconfirmed. Nobody ran
  `airflow providers list` on the server for this note. Option C does not need a provider, because
  `requests` is already installed.

### Network reachability

- The server address `100.67.84.55` is in `100.64.0.0/10`, the shared address space from
  RFC 6598. The public internet does not route to it. It is probably a private overlay network.
  Which overlay (for example Tailscale) is unconfirmed, and the vault has no note about it.
- `compose.yml` publishes these ports on every host interface: `8000` (storage-backend, line 193),
  `5173` (storage-frontend, line 204), `8080` (Airflow API server, lines 237-238), `8989`
  (GraphHopper, line 365), `8010` (floodmap-backend, line 394), and `8082` (flood-routing-frontend,
  line 415). MinIO, PostGIS, and TimescaleDB bind to `127.0.0.1` only (lines 80-81, 127, 146).
- `floodmap/graphhopper-maps/nginx.conf:2-3` listens on port 80 with `server_name _`. It has no TLS
  and no route for an inbound webhook. Its proxied paths are `/flood-extent/`, `/api/gh/`, and
  `/api/geocode/` (lines 19-50).
- An inbound webhook from Tomorrow.io cannot reach any of these services unless we add a public
  HTTPS entry point. A tunnel or a cloud-hosted receiver would work. Whether the host has any
  public entry point today is unconfirmed.

### Airflow REST API (config only)

- `compose.yml:9` sets `AIRFLOW__CORE__AUTH_MANAGER` to the FAB auth manager. The healthcheck calls
  `/api/v2/version` (line 240).
- In Airflow 3, `/api/v2` calls need a bearer token. With the FAB auth manager, a client gets the
  token by posting a username and password to the token endpoint. This comes from the Airflow 3
  documentation and was not re-read for this note, so treat it as unconfirmed.
- `AIRFLOW_CONFIG` points at `/opt/airflow/config/airflow.cfg`, mounted from `./config`
  (`compose.yml:19, 55`). `/config/` is ignored (`.gitignore:47`), so API settings in that file
  were not visible.

## What Tomorrow.io offers

Every page in this section was read on 2026-09-25, through the `.md` form of each page that
`https://docs.tomorrow.io/llms.txt` lists.

### Alert features

- Alerts API, `https://docs.tomorrow.io/reference/overview-alerts`. An Alert watches an Insight.
  When the Insight produces an Event, Tomorrow.io sends webhook notifications. An Insight is either
  a Custom Insight (your own conditions on more than 80 data points) or an Insight Category (hazard
  warnings from national authorities).
- Insights API, `https://docs.tomorrow.io/reference/insights-overview`. A Custom Insight is a rule
  such as `rainIntensity > 10`, written in the Rules language or as an AST of `OPERATOR`,
  `PARAMETER`, and `CONST` nodes. The page's AST example uses `precipitationIntensity`. Insights
  support metric units only.
- Insight Categories, `https://docs.tomorrow.io/reference/insights-categories-overview`. The
  `floods` category and every other category cover only the United States, Canada, and Europe.
  Vietnam is not covered, so for Hanoi only a Custom Insight applies.
- Notification types, from the Alerts page. `PRIOR` fires a set number of minutes (`value`) before
  the forecast event starts. `START` fires at the start of the event. `END` is the all-clear, with
  `value` as the number of minutes that conditions must stay unmet. `PUBLISH` is for Insight
  Categories only.
- Create an Alert, `https://docs.tomorrow.io/reference/post-alerts`. `POST /v4/alerts` takes
  `name`, `insight`, `isActive`, and `notifications`. A recipe links locations to an alert with
  `POST /v4/alerts/{alertId}/locations/link`
  (`https://docs.tomorrow.io/recipes/set-up-severe-weather-alerts-around-a-geofence`).
- Plans. Which plans include Alerts and Insights is unconfirmed. The docs do not say, and
  `https://www.tomorrow.io/pricing/` and `https://www.tomorrow.io/weather-api/pricing/` returned
  HTTP 403 to the browser. The errors page (`https://docs.tomorrow.io/reference/api-errors`) lists
  `403002` "The plan limit for a resource has been reached" and `403003` "The plan is restricted
  and cannot perform this action". So plans do gate some resources. Which plan our key is on is
  also unconfirmed.

### Notification channels

- Webhook, `https://docs.tomorrow.io/reference/api-webhooks`. You set one webhook per account in
  the Tomorrow.io web app, under the Development section's Webhooks tab. The page says "At the
  moment, only 'Alerts' are possible". The URL must be publicly accessible. If it uses HTTPS, it
  must have a valid SSL certificate.
- Delivery. The receiver must answer with a 2xx status quickly. On a 4xx, a 5xx, or a timeout,
  Tomorrow.io retries up to two times, a few minutes apart, and then discards the call.
- Signing. Each request carries an `X-Signature` header of the form `t={timestamp},sig={signature}`.
  The signature is an HMAC-SHA256 of the timestamp string, keyed with the account's webhook secret.
  The page also gives the sender IP `35.231.166.26` for an allowlist.
- Payload, from the Alerts page. The JSON body has `data.alert`, `data.insight.id`,
  `data.locations` (one location for a Custom Insight), `data.notification` (`type`, `value`,
  `title`, `description`), and `data.event` with `startTime`, `endTime`, `eventValues`, and
  `triggerValues`.
- Email, SMS, and push. The API docs describe no email, SMS, or push delivery for alerts. The
  Notifications API (`https://docs.tomorrow.io/reference/overview-notifications` and
  `https://docs.tomorrow.io/reference/list-notifications-get`) lists sent notifications, with
  `recipients` as user IDs and a `sent` or `acknowledged` status. That hints at in-app delivery to
  platform users, but email or SMS delivery is unconfirmed.
- No-code relays. `https://docs.tomorrow.io/reference/alert-listeners` suggests Zapier, IFTTT,
  Tray.io, and Slack incoming webhooks as receivers. Tomorrow.io's payload has no top-level `text`
  field, and Slack incoming webhooks expect one. So a direct Slack hookup probably fails. That is
  unconfirmed.

### Locations

- Locations API, `https://docs.tomorrow.io/reference/locations-overview`. Tomorrow.io checks each
  location linked to an alert for the Insight conditions. A location is a GeoJSON `Point`,
  `Polygon`, or `LineString`, with coordinates in `[lon, lat]` order. The standard polygon limit is
  500 km², the standard polyline limit is 70 km, and larger areas are a premium feature
  (`https://docs.tomorrow.io/reference/release-notes`).
- A polygon field without a suffix defaults to `Max` over the area
  (`https://docs.tomorrow.io/reference/timeline-overview`).
- The number of alerts or locations a plan allows is unconfirmed. The docs give no number.

### Rate limits and the forecast we already call

- `https://docs.tomorrow.io/reference/rate-limiting`. Limits are per plan, per hour and per day.
  Over the limit, the API returns HTTP 429. Only Enterprise accounts get the
  `X-RateLimit-*` headers. The docs give no numbers for any plan, so our limit is unconfirmed.
- `https://docs.tomorrow.io/reference/weather-data-layers`. The `15m` timestep covers from 6 hours
  back to 6 hours ahead on the free plan, and from 7 days back to 6 hours ahead on premium. The
  `1m`, `5m`, and `15m` timesteps are limited to 24 hours per call.
- `https://docs.tomorrow.io/reference/data-layers-core`. `precipitationIntensity` is in mm/hr,
  available worldwide, and forecast up to 14 days ahead at coarser timesteps.
- Our usage is at most 96 calls per day from `flood_mapping_full`, plus up to 96 more if the two
  30-minute DAGs are unpaused.

### Lead time

- A `PRIOR` notification fires `value` minutes before the forecast event starts. The docs give no
  upper limit for `value` and do not say how often Tomorrow.io re-evaluates a Custom Insight. Both
  are unconfirmed.
- For our own poll, the lead time is at most `FLOOD_RAIN_LOOKAHEAD_HOURS` (2 hours by default). A
  `15m` request can go no further than 6 hours ahead. A day-ahead outlook needs `1h` or `1d`
  timesteps.

## Options

| Option | Effort | What it needs from us | Failure modes |
| --- | --- | --- | --- |
| A. Native alert, webhook to a receiver we host | L | A plan that includes Alerts. A Location, a Custom Insight, an Alert, and a link, created through the API. A public HTTPS endpoint (tunnel or cloud) with signature checks. A receiver service that forwards to people. | The server has no public entry point. Plan support is unconfirmed. Tomorrow.io gives up after two retries. A new public service adds exposure. The evaluation frequency is unknown. |
| B. Native alert to people only | M | The same Tomorrow.io setup as A. A no-code relay (for example a Zapier hook that sends email). | Email or SMS from Tomorrow.io is unconfirmed. A relay adds an account and a cost. Plan support is unconfirmed. |
| C. Notify from our rain gate | S | A channel token in `.env` (Telegram bot token and chat ID, or a Slack incoming webhook URL). About 30 lines in `task_check_forecast_rain`, sent with `requests`. A lower heads-up threshold. Deduplication so one rain event sends one message. | Alerts stop when Airflow is down or the DAG is paused. Lead time is 2 hours by default. No checks run during a wet cycle, because of `max_active_runs=1`. Without deduplication, it sends a message every 15 minutes. |
| D. Alert triggers `flood_mapping_full` through the REST API | L | Everything in A. A relay that turns the signed Tomorrow.io call into an authenticated `POST /api/v2/dags/flood_mapping_full/dagRuns`. A change to the continuous timetable. | Everything in A. The webhook config has no documented way to add an `Authorization` header, so a relay is required. A triggered run queues behind the running cycle. The simulation still calls the Timelines API for its rain series, so at most 96 calls a day are saved. |

The daily outlook (meaning 2) fits option C as a second small task. A cron-scheduled task would
request `1h` steps for the next day once each evening, which costs 1 call per day.

## Recommendation

Build option C. The rain gate already fetches the forecast every 15 minutes, so a message from that
task costs no extra API calls, needs no public endpoint, and does not depend on a plan feature we
cannot confirm. Options A, B, and D all need a Tomorrow.io plan with Alerts, and A and D also need
a public HTTPS entry point that the server does not have. D saves at most 96 calls a day and adds
the most moving parts, so it does not pay for itself.

A first version can ship tomorrow (2026-09-26) if the user answers the decisions in the next
section today. Send one message when the gate decides to run, and one heads-up message when the
forecast first crosses a lower threshold. Store the last alert time in an Airflow Variable so one
event sends one message.

Revisit option A only if we need alerts while Airflow is down, or a lead time longer than our
poll's lookahead.

## Decisions for the user

1. Which meaning of "alert": short-range heavy-rain warnings, a daily outlook for tomorrow, both,
   or a trigger for the simulation.
2. The channel: Telegram, Slack, email, or SMS. Email needs an SMTP server, and SMS needs a paid
   gateway.
3. The recipients: one group chat or channel, or named people.
4. The threshold in mm/h. The gate uses 5 mm/h. A heads-up threshold could be lower, for example
   2 mm/h. The user picks the number.
5. The location: the single default point `21.0285,105.804817`, other points, or a polygon.
6. Quiet hours and repeat rules. For example, no messages from 23:00 to 06:00, and at most one
   message per rain event.
7. For options A, B, or D only: the Tomorrow.io plan, and whether a public HTTPS endpoint is
   acceptable.

## Next steps

1. Get the user's answers to the decisions.
2. Run these read-only checks on the server. The lead decides whether to run them.
   - `docker --context remote-server compose exec airflow-worker airflow providers list`, to see
     whether `slack` or `smtp` providers exist.
   - `docker --context remote-server compose exec airflow-worker airflow dags list`, to see whether
     `test_dag` and `initial_wl_dag` are paused. Each unpaused one adds up to 48 Tomorrow.io calls
     per day.
   - Read `plugins/vn_timetable.py` on the server, to confirm the continuous timetable.
3. Ask the user to check the Tomorrow.io web app, under the Development section. If the Webhooks
   tab lets them add a URL, the plan includes webhooks. The plan name and its daily limit are on
   the account page. This settles options A, B, and D without calling the API.
4. If the user picks option C, write the feature plan: the message format, the deduplication
   state, the new `.env` names, a `timeout` on `requests.get`, and a fix for the stale docstring on
   `dags/flood_mapping_dag.py:73`.
5. After the change ships, update [[3di-simulation-orchestration]] with the alert behavior.
