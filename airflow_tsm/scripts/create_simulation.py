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

# Bounded-polling config.
POLL_INTERVAL_SECONDS = int(os.getenv("THREEDI_POLL_INTERVAL_SECONDS", "10"))
POLL_MAX_INTERVAL_SECONDS = int(os.getenv("THREEDI_POLL_MAX_INTERVAL_SECONDS", "60"))
POLL_TIMEOUT_SECONDS = int(os.getenv("THREEDI_POLL_TIMEOUT_SECONDS", str(SIMULATION_DURATION + 1800)))


def load_last_state(state_file_path):
    """Đọc ID saved state cũ (Nhận đường dẫn từ tham số)"""
    if os.path.exists(state_file_path):
        try:
            with open(state_file_path, "r") as f:
                return json.load(f).get("last_saved_state_id")
        except Exception:
            return None
    return None


def save_new_state(state_file_path, state_id):
    """Lưu ID saved state mới"""
    try:
        os.makedirs(os.path.dirname(state_file_path), exist_ok=True)
        with open(state_file_path, "w") as f:
            json.dump(
                {"last_saved_state_id": state_id, "updated_at": str(datetime.now())}, f
            )
    except Exception as e:
        print(f"⚠️ Không thể lưu state file: {e}")


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


def get_rain_forecast():
    """Fetch the configured Tomorrow.io rain lookahead at 15-minute cadence."""
    print("📡 1. Lấy dữ liệu mưa Tomorrow.io...")
    now = datetime.now(timezone.utc)
    end_time = now + timedelta(hours=RAIN_LOOKAHEAD_HOURS)

    test_rain = os.getenv("FLOOD_TEST_RAIN_MM_HR", "").strip()
    if test_rain:
        rain_mm_hr = float(test_rain)
        print(f"🧪 Using FLOOD_TEST_RAIN_MM_HR={rain_mm_hr:g} mm/h")
        return build_fixed_rain_intervals(rain_mm_hr)

    url = "https://api.tomorrow.io/v4/timelines"
    params = {
        "location": f"{LOCATION_LAT},{LOCATION_LON}",
        "fields": ["precipitationIntensity"],
        "timesteps": f"{RAIN_TIMESTEP_MINUTES}m",
        "units": "metric",
        "startTime": now.isoformat().replace("+00:00", "Z"),
        "endTime": end_time.isoformat().replace("+00:00", "Z"),
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


def build_rain_values(intervals):
    """Convert forecast intervals to 3Di [seconds, metres/second] values."""
    if not intervals:
        return []

    def parse_time(value):
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))

    try:
        first_time = parse_time(intervals[0]["startTime"])
    except (KeyError, TypeError, ValueError):
        first_time = None

    values = []
    for index, interval in enumerate(intervals):
        offset_seconds = index * RAIN_TIMESTEP_MINUTES * 60
        if first_time is not None:
            try:
                offset_seconds = max(0, int((parse_time(interval["startTime"]) - first_time).total_seconds()))
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


def run_forecast_process(state_file_path, rain_intervals=None, use_saved_state=True):
    print(f"🚀 Bắt đầu quy trình Simulation (State: {state_file_path})")

    intervals = rain_intervals if rain_intervals is not None else get_rain_forecast()
    if not intervals:
        print("❌ Không lấy được dữ liệu mưa. Dừng.")
        return None, None

    print("🔄 2. Xử lý dữ liệu mưa...")
    rain_values = build_rain_values(intervals)
    start_time_str = intervals[0]["startTime"]

    api = get_client()

    last_state_id = load_last_state(state_file_path) if use_saved_state else None
    is_hotstart = False
    if last_state_id:
        print(f"🔗 [Hotstart] Sẽ dùng Saved State ID: {last_state_id}")
        is_hotstart = True
    else:
        print("🆕 [Coldstart] Chạy mới từ Template")

    print("🚀 3. Tạo Simulation...")
    from_template_kwargs = dict(
        template=TEMPLATE_ID,
        name=f"Forecast_{datetime.now().strftime('%H%M')}",
        organisation=ORG_UUID,
        start_datetime=start_time_str,
        duration=SIMULATION_DURATION,
        tags=["airflow-forecast"],
        clone_settings=True,
        clone_events=False,
        clone_initials=not is_hotstart,
    )
    try:
        simulation = api.simulations_from_template(FromTemplate(**from_template_kwargs))
    except Exception as e:
        _log_if_auth_expired(e, "Tạo Sim")
        print(f"❌ Lỗi tạo Sim: {e}")
        return None, None

    sim_id = simulation.id
    print(f"✅ Simulation ID: {sim_id}")

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

    future_saved_state_id = None
    if use_saved_state:
        print(f"💾 5. Đăng ký lưu state tại giây thứ {SIMULATION_DURATION}...")
        expiry_date = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        try:
            saved_state = api.simulations_create_saved_states_timed_create(
                sim_id,
                TimedSavedState(
                    name=f"RollingState_{datetime.now().strftime('%H%M')}",
                    time=SIMULATION_DURATION,
                    expiry=expiry_date,
                    tags=["rolling-forecast"],
                ),
            )
            future_saved_state_id = saved_state.id
            print(f"✅ Đã đăng ký thành công (ID tương lai: {future_saved_state_id})")
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

    is_success = monitor_simulation(api, sim_id)

    if is_success and future_saved_state_id:
        if use_saved_state:
            save_new_state(state_file_path, future_saved_state_id)
        return sim_id, future_saved_state_id

    if is_success:
        return sim_id, None

    return None, None


if __name__ == "__main__":
    run_forecast_process("flood_system_state.json")
