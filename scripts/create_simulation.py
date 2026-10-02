"""3Di simulation trigger, built on the official threedi-api-client (ThreediApi).

Auth/config is read by threedi_client.get_client() from THREEDI_API_HOST /
THREEDI_API_PERSONAL_API_TOKEN. Status polling is bounded (timeout +
exponential backoff + max consecutive-error cap) rather than an unbounded
retry loop.
"""

import json
import os
import time
from datetime import datetime, timedelta, timezone

from threedi_api_client.openapi import (
    Action,
    ApiException,
    FromTemplate,
    TimedSavedState,
    TimeseriesRain,
)

import requests

import rain_replay
from threedi_client import get_client

TOMORROW_API_KEY = os.getenv("TOMORROW_API_KEY")
LOCATION_LAT = os.getenv("LOCATION_LAT", "21.0285")
LOCATION_LON = os.getenv("LOCATION_LON", "105.804817")

ORG_UUID = os.getenv("ORG_UUID")
TEMPLATE_ID = int(os.getenv("TEMPLATE_ID", "40921"))

SIMULATION_DURATION = int(os.getenv("SIMULATION_DURATION", "7200"))
RAIN_LOOKAHEAD_HOURS = float(os.getenv("FLOOD_RAIN_LOOKAHEAD_HOURS", "2"))
RAIN_TIMESTEP_MINUTES = int(os.getenv("FLOOD_RAIN_TIMESTEP_MINUTES", "15"))
RAIN_THRESHOLD_MM_HR = float(os.getenv("FLOOD_RAIN_THRESHOLD_MM_HR", "5"))
CYCLE_MINUTES = 15
# The state saved at one cycle is where the next run starts; the one at two cycles is the backup
# for when the next run fails.
HOTSTART_SAVE_SECONDS = int(os.getenv("HOTSTART_SAVE_SECONDS", str(CYCLE_MINUTES * 60)))
SAVED_STATES_KEPT = 8

# Bounded-polling config.
POLL_INTERVAL_SECONDS = int(os.getenv("THREEDI_POLL_INTERVAL_SECONDS", "10"))
POLL_MAX_INTERVAL_SECONDS = int(os.getenv("THREEDI_POLL_MAX_INTERVAL_SECONDS", "60"))
POLL_TIMEOUT_SECONDS = int(os.getenv("THREEDI_POLL_TIMEOUT_SECONDS", str(SIMULATION_DURATION + 1800)))


def load_saved_states(state_file_path):
    """Read the saved states [{"id", "valid_at"}] from the state file. A missing, broken, or old-format file has none."""
    try:
        with open(state_file_path, "r") as f:
            states = json.load(f).get("states", [])
        return [{"id": s["id"], "valid_at": s["valid_at"]} for s in states]
    except Exception:
        return []


def save_saved_states(state_file_path, new_states):
    """Merge new states into the state file, keeping the newest SAVED_STATES_KEPT by valid_at.

    Merging, not replacing, because two runs can overlap and finish out of order: the older run
    must not erase the newer run's states.
    """
    by_valid_at = {s["valid_at"]: s for s in load_saved_states(state_file_path)}
    by_valid_at.update({s["valid_at"]: s for s in new_states})
    states = sorted(by_valid_at.values(), key=lambda s: parse_iso(s["valid_at"]))[-SAVED_STATES_KEPT:]
    try:
        os.makedirs(os.path.dirname(state_file_path), exist_ok=True)
        with open(state_file_path, "w") as f:
            json.dump({"states": states, "updated_at": iso_utc(datetime.now(timezone.utc))}, f)
    except Exception as e:
        print(f"⚠️ Không thể lưu state file: {e}")


def choose_saved_state(states, slot):
    """Pick the state a run starting at `slot` hotstarts from, or None for a cold start.

    An exact valid_at == slot first, else the newest state at most 2 cycles before the slot.
    """
    max_age = timedelta(minutes=2 * CYCLE_MINUTES)
    usable = [s for s in states if timedelta(0) <= slot - parse_iso(s["valid_at"]) <= max_age]
    if not usable:
        print(f"🆕 [Coldstart] No saved state within {max_age} before {iso_utc(slot)}")
        return None
    chosen = max(usable, key=lambda s: parse_iso(s["valid_at"]))
    offset_minutes = (slot - parse_iso(chosen["valid_at"])).total_seconds() / 60
    case = "exact" if offset_minutes == 0 else "fallback"
    print(f"🔗 [Hotstart, {case}] Saved state {chosen['id']} valid at {chosen['valid_at']}, offset {offset_minutes:g} min")
    return chosen


def clock_slot(moment):
    """Floor a datetime to the start of its CYCLE_MINUTES slot, in UTC. A naive datetime is read as UTC."""
    utc = moment.astimezone(timezone.utc) if moment.tzinfo else moment.replace(tzinfo=timezone.utc)
    minute = utc.minute - utc.minute % CYCLE_MINUTES
    return datetime(utc.year, utc.month, utc.day, utc.hour, minute, tzinfo=timezone.utc)


def iso_utc(moment):
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(value):
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def build_fixed_rain_intervals(rain_mm_hr, duration_hours=RAIN_LOOKAHEAD_HOURS, timestep_minutes=RAIN_TIMESTEP_MINUTES, start_time=None):
    """Build a deterministic rain series at a fixed intensity, for manual/local testing."""
    now = start_time or datetime.now(timezone.utc)
    interval_count = int((duration_hours * 60) / timestep_minutes)
    return [
        {
            "startTime": (now + timedelta(minutes=timestep_minutes * index))
            .isoformat()
            .replace("+00:00", "Z"),
            "values": {"precipitationIntensity": rain_mm_hr},
        }
        for index in range(interval_count + 1)
    ]


def get_rain_forecast(start=None):
    """Fetch the configured Tomorrow.io rain lookahead at 15-minute cadence, from `start` (default: the current slot)."""
    print("📡 1. Lấy dữ liệu mưa Tomorrow.io...")
    start = start or clock_slot(datetime.now(timezone.utc))
    end_time = start + timedelta(hours=RAIN_LOOKAHEAD_HOURS)

    replay_file = os.getenv("FLOOD_TEST_RAIN_CSV", "").strip()
    replay_start = os.getenv("FLOOD_TEST_RAIN_START", "").strip()
    test_rain = os.getenv("FLOOD_TEST_RAIN_MM_HR", "").strip()
    if bool(replay_file) != bool(replay_start) or (replay_file and test_rain):
        raise ValueError(
            "Set FLOOD_TEST_RAIN_CSV together with FLOOD_TEST_RAIN_START and without FLOOD_TEST_RAIN_MM_HR, "
            "or set none of them"
        )
    if replay_file:
        print(f"🧪 Replaying {replay_file} from {replay_start}")
        return rain_replay.replay_intervals(
            rain_replay.load_event(replay_file), parse_iso(replay_start), start, RAIN_LOOKAHEAD_HOURS, RAIN_TIMESTEP_MINUTES
        )
    if test_rain:
        rain_mm_hr = float(test_rain)
        print(f"🧪 Using FLOOD_TEST_RAIN_MM_HR={rain_mm_hr:g} mm/h")
        return build_fixed_rain_intervals(rain_mm_hr, start_time=start)

    url = "https://api.tomorrow.io/v4/timelines"
    params = {
        "location": f"{LOCATION_LAT},{LOCATION_LON}",
        "fields": ["precipitationIntensity"],
        "timesteps": f"{RAIN_TIMESTEP_MINUTES}m",
        "units": "metric",
        "startTime": iso_utc(start),
        "endTime": iso_utc(end_time),
        "apikey": TOMORROW_API_KEY,
    }

    try:
        res = requests.get(url, params=params)
        res.raise_for_status()
        return res.json()["data"]["timelines"][0]["intervals"]
    except Exception as e:
        print(f"❌ Lỗi Weather API: {e}")
        return None


def rain_intensity_mm_hr(interval):
    """Read Tomorrow.io precipitation intensity, accepting the URD alias too."""
    values = interval.get("values", {}) if isinstance(interval, dict) else {}
    value = values.get("precipitationIntensity", values.get("rainIntensity", 0))
    try:
        return max(0.0, float(value or 0))
    except (TypeError, ValueError):
        return 0.0


def evaluate_rain_gate(intervals, threshold_mm_hr=RAIN_THRESHOLD_MM_HR):
    """Return the deterministic decision used before any 3Di API call."""
    intensities = [rain_intensity_mm_hr(interval) for interval in intervals or []]
    max_intensity = max(intensities, default=0.0)
    return {
        "should_run": bool(intensities) and max_intensity >= float(threshold_mm_hr),
        "threshold_mm_hr": float(threshold_mm_hr),
        "max_intensity_mm_hr": max_intensity,
        "interval_count": len(intensities),
    }


def build_rain_values(intervals, start=None):
    """Convert forecast intervals to 3Di [seconds, metres/second] values, offset from `start` or the first interval."""
    if not intervals:
        return []

    first_time = start
    if first_time is None:
        try:
            first_time = parse_iso(intervals[0]["startTime"])
        except (KeyError, TypeError, ValueError):
            first_time = None

    values = []
    for index, interval in enumerate(intervals):
        offset_seconds = index * RAIN_TIMESTEP_MINUTES * 60
        if first_time is not None:
            try:
                offset_seconds = max(0, int((parse_iso(interval["startTime"]) - first_time).total_seconds()))
            except (KeyError, TypeError, ValueError):
                pass
        rain_m_s = rain_intensity_mm_hr(interval) / (1000 * 3600)
        values.append([offset_seconds, rain_m_s])
    return values


def _log_if_auth_expired(e, context):
    """Fire a distinct, non-self-resolving alert for a 401/403 from the 3Di API.

    Unlike a timeout or transient error, an expired/invalid token will fail
    identically on every subsequent cycle until it's rotated, so this needs
    its own signal instead of blending into the generic error log below it.
    """
    if isinstance(e, ApiException) and e.status in (401, 403):
        print(
            f"🔒 ALERT [3di-auth-expired, will-not-self-resolve] {context}: "
            f"status={e.status} {e}"
        )


def monitor_simulation(api, sim_id):
    """Bounded status polling: timeout + exponential backoff + max attempts."""
    print("⏳ 7. Đang chạy...")
    deadline = time.monotonic() + POLL_TIMEOUT_SECONDS
    interval = POLL_INTERVAL_SECONDS
    consecutive_errors = 0
    max_consecutive_errors = 5

    while time.monotonic() < deadline:
        try:
            status = api.simulations_status_list(sim_id)
            consecutive_errors = 0
            name = status.name

            if name == "finished":
                print("\n🏁 Hoàn tất!")
                return True
            if name in ("crashed", "timeout", "shut_down"):
                print(f"\n❌ Simulation bị lỗi giữa chừng: {name}")
                return False

            interval = POLL_INTERVAL_SECONDS
        except Exception as e:
            consecutive_errors += 1
            print(f"\n⚠️ Lỗi đọc status ({consecutive_errors}/{max_consecutive_errors}): {e}")
            if consecutive_errors >= max_consecutive_errors:
                print("❌ Quá nhiều lỗi liên tiếp khi poll status. Dừng.")
                return False
            interval = min(interval * 2, POLL_MAX_INTERVAL_SECONDS)

        time.sleep(interval)

    print(f"❌ Poll timeout sau {POLL_TIMEOUT_SECONDS}s. Simulation {sim_id} chưa hoàn tất.")
    return False


def run_forecast_process(
    state_file_path,
    rain_intervals=None,
    use_saved_state=True,
    slot_start=None,
    state_save_seconds=None,
    hotstart=True,
):
    """Run one 3Di forecast that starts at its clock slot and hotstarts from the state saved for that slot.

    The slot is `slot_start` if given, else the slot of the first rain interval, else the current slot.
    With use_saved_state, it registers one timed saved state per `state_save_seconds` (default one and
    two cycles) and records them in the state file once the run finishes. Returns (sim_id, saved states).
    With hotstart False, the run cold-starts but still registers and records its saved states, so the
    next run can hotstart from it.
    """
    print(f"🚀 Bắt đầu quy trình Simulation (State: {state_file_path})")

    if rain_intervals is None:
        slot = slot_start or clock_slot(datetime.now(timezone.utc))
        intervals = get_rain_forecast(start=slot)
    else:
        intervals = rain_intervals
        slot = slot_start or (clock_slot(parse_iso(intervals[0]["startTime"])) if intervals else None)
    if not intervals:
        print("❌ Không lấy được dữ liệu mưa. Dừng.")
        return None, None
    print(f"🕒 Slot: {iso_utc(slot)}")
    if state_save_seconds is None:
        state_save_seconds = (HOTSTART_SAVE_SECONDS, 2 * HOTSTART_SAVE_SECONDS)

    print("🔄 2. Xử lý dữ liệu mưa...")
    rain_values = build_rain_values(intervals, start=slot)

    api = get_client()

    if use_saved_state and hotstart:
        hotstart_state = choose_saved_state(load_saved_states(state_file_path), slot)
    else:
        hotstart_state = None

    print("🚀 3. Tạo Simulation...")
    from_template_kwargs = dict(
        template=TEMPLATE_ID,
        name=f"Forecast_{slot:%Y%m%dT%H%M}",
        organisation=ORG_UUID,
        start_datetime=iso_utc(slot),
        duration=SIMULATION_DURATION,
        tags=["airflow-forecast"],
        clone_settings=True,
        clone_events=False,
        clone_initials=hotstart_state is None,
    )
    try:
        simulation = api.simulations_from_template(FromTemplate(**from_template_kwargs))
    except Exception as e:
        _log_if_auth_expired(e, "Tạo Sim")
        print(f"❌ Lỗi tạo Sim: {e}")
        return None, None

    sim_id = simulation.id
    print(f"✅ Simulation ID: {sim_id}")

    if hotstart_state is not None:
        print(f"🔗 3b. Gắn saved state {hotstart_state['id']} làm trạng thái ban đầu...")
        try:
            existing = api.simulations_initial_saved_state_list(simulation_pk=sim_id)
            for initial in existing.results:
                api.simulations_initial_saved_state_delete(id=initial.id, simulation_pk=sim_id)
            api.simulations_initial_saved_state_create(
                simulation_pk=sim_id, data={"saved_state": hotstart_state["id"]}
            )
        except Exception as e:
            # A run that meant to hotstart but starts dry would publish a wrong flood map as if valid.
            _log_if_auth_expired(e, "Gắn saved state")
            print(f"❌ Lỗi gắn saved state {hotstart_state['id']}: {e}")
            return None, None

    print("🌧️ 4. Nạp mưa...")
    try:
        api.simulations_events_rain_timeseries_create(
            sim_id,
            TimeseriesRain(values=rain_values, units="m/s", interpolate=True, offset=0),
        )
    except Exception as e:
        _log_if_auth_expired(e, "Nạp mưa")
        print(f"❌ Lỗi nạp mưa: {e}")
        return None, None

    new_states = []
    if use_saved_state:
        expiry_date = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        for seconds in state_save_seconds:
            print(f"💾 5. Đăng ký lưu state tại giây thứ {seconds}...")
            try:
                saved_state = api.simulations_create_saved_states_timed_create(
                    sim_id,
                    TimedSavedState(
                        name=f"RollingState_{slot:%Y%m%dT%H%M}_{seconds}s",
                        time=seconds,
                        expiry=expiry_date,
                        tags=["rolling-forecast"],
                    ),
                )
                valid_at = iso_utc(slot + timedelta(seconds=seconds))
                new_states.append({"id": saved_state.id, "valid_at": valid_at})
                print(f"✅ Đã đăng ký thành công (ID tương lai: {saved_state.id}, valid at {valid_at})")
            except Exception as e:
                _log_if_auth_expired(e, "Đăng ký lưu state")
                print(f"❌ Lỗi đăng ký lưu state: {e}")
    else:
        print("⏭️ 5. Bỏ qua đăng ký lưu state (use_saved_state=False)")

    print("▶️ 6. Gửi lệnh start...")
    try:
        api.simulations_actions_create(sim_id, Action(name="start"))
    except Exception as e:
        _log_if_auth_expired(e, "Start Simulation")
        print(f"❌ LỖI NGHIÊM TRỌNG: Không thể Start Simulation! {e}")
        return None, None

    if not monitor_simulation(api, sim_id):
        return None, None

    if new_states:
        save_saved_states(state_file_path, new_states)
    return sim_id, new_states


if __name__ == "__main__":
    run_forecast_process("flood_system_state.json")
