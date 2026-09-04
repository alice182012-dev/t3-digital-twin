"""3Di simulation trigger for the initial-waterlevel pipeline, built on the
official threedi-api-client. Reuses monitor_simulation from create_simulation.py
instead of a separate copy of the bounded-polling loop.

BASE_URL/MODEL_ID are kept as module attributes for backward compatibility:
initial_wl_dag.py reads them directly to reconstruct the initial-waterlevel
resource URL it passes into run_simulation().
"""

import os
import sys
from datetime import datetime, timedelta, timezone

import requests
from threedi_api_client.openapi import Action, FromTemplate, OneDWaterLevelFile, TimeseriesRain

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from create_simulation import monitor_simulation  # noqa: E402
from threedi_client import get_client  # noqa: E402

TOMORROW_API_KEY = os.getenv("TOMORROW_API_KEY")
LOCATION_LAT = os.getenv("LOCATION_LAT", "21.0285")
LOCATION_LON = os.getenv("LOCATION_LON", "105.804817")

ORG_UUID = os.getenv("ORG_UUID")
MODEL_ID = os.getenv("MODEL_ID", "83022")

SIMULATION_DURATION = int(os.getenv("SIMULATION_DURATION", 7200))

# Kept for initial_wl_dag.py, which builds the initial-waterlevel resource
# URL as f"{BASE_URL}/threedimodels/{MODEL_ID}/initial_waterlevels/{id}/".
BASE_URL = "https://api.3di.live/v3"


def get_simulation_template_id(api, model_id=MODEL_ID):
    print(f"🔍 Đang tìm Template cho Model {model_id}...")
    try:
        results = api.simulation_templates_list(
            simulation__threedimodel__id=model_id, limit=1
        ).results
        if results:
            template_id = results[0].id
            print(f"✅ Đã tìm thấy Template ID: {template_id}")
            return template_id
        print("❌ Không tìm thấy Template nào!")
        return None
    except Exception as e:
        print(f"❌ Lỗi lấy Template: {e}")
        return None


def get_rain_forecast():
    print("📡 1. Lấy dữ liệu mưa Tomorrow.io...")

    now = datetime.now(timezone.utc)
    end_time = now + timedelta(seconds=SIMULATION_DURATION)

    url = "https://api.tomorrow.io/v4/timelines"
    params = {
        "location": f"{LOCATION_LAT},{LOCATION_LON}",
        "fields": ["precipitationIntensity"],
        "timesteps": "1h",
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


def build_rain_values(intervals):
    print("🔄 2. Xử lý dữ liệu mưa...")

    rain_values = []
    for i, interval in enumerate(intervals):
        val_mm_hr = interval["values"].get("precipitationIntensity", 0)
        rain_m_s = val_mm_hr / (1000 * 3600)
        rain_values.append([i * 3600, rain_m_s])

    print(f"✅ Đã xử lý {len(rain_values)} timestep mưa")
    return rain_values


def create_simulation(api, template_id, start_time_str):
    print("🚀 3. Tạo Simulation...")
    try:
        simulation = api.simulations_from_template(
            FromTemplate(
                template=template_id,
                name=f"Forecast_{datetime.now().strftime('%H%M')}",
                organisation=ORG_UUID,
                start_datetime=start_time_str,
                duration=SIMULATION_DURATION,
                tags=["airflow-forecast", "initial-wl"],
                clone_settings=True,
                clone_events=False,
                clone_initials=False,
            )
        )
    except Exception as e:
        print(f"❌ Lỗi tạo Sim: {e}")
        return None

    print(f"✅ Simulation ID: {simulation.id}")
    return simulation.id


def apply_initial_waterlevels_to_simulation(api, sim_id, initial_waterlevel_resource_url):
    print("🌊 4. Apply initial water level...")
    print(f"🔗 Initial WL resource: {initial_waterlevel_resource_url}")
    try:
        api.simulations_initial1d_water_level_file_create(
            sim_id, OneDWaterLevelFile(initial_waterlevel=initial_waterlevel_resource_url)
        )
    except Exception as e:
        print(f"❌ Lỗi apply initial water level: {e}")
        return False

    print("✅ Đã apply initial water level")
    return True


def add_rain_event(api, sim_id, rain_values):
    print("🌧️ 5. Nạp mưa...")
    try:
        api.simulations_events_rain_timeseries_create(
            sim_id,
            TimeseriesRain(values=rain_values, units="m/s", interpolate=True, offset=0),
        )
    except Exception as e:
        print(f"❌ Lỗi nạp mưa: {e}")
        return False

    print("✅ Đã nạp mưa")
    return True


def start_simulation(api, sim_id):
    print("▶️ 6. Gửi lệnh start...")
    try:
        api.simulations_actions_create(sim_id, Action(name="start"))
    except Exception as e:
        print(f"❌ LỖI NGHIÊM TRỌNG: Không thể Start Simulation! {e}")
        return False

    print("✅ Đã gửi lệnh start")
    return True


def run_simulation(initial_waterlevel_resource_url):
    print("🚀 Bắt đầu quy trình Simulation với Initial Water Level")

    api = get_client()

    template_id = get_simulation_template_id(api, MODEL_ID)
    if not template_id:
        return None

    intervals = get_rain_forecast()
    if not intervals:
        print("❌ Không lấy được dữ liệu mưa. Dừng.")
        return None

    rain_values = build_rain_values(intervals)
    start_time_str = intervals[0]["startTime"]

    sim_id = create_simulation(api, template_id, start_time_str)
    if not sim_id:
        return None

    if not apply_initial_waterlevels_to_simulation(api, sim_id, initial_waterlevel_resource_url):
        return None

    if not add_rain_event(api, sim_id, rain_values):
        return None

    if not start_simulation(api, sim_id):
        return None

    if not monitor_simulation(api, sim_id):
        return None

    print(f"✅ Simulation hoàn tất với ID: {sim_id}")
    return sim_id


if __name__ == "__main__":
    test_initial_wl_url = os.getenv("INITIAL_WATERLEVEL_RESOURCE_URL")
    if not test_initial_wl_url:
        raise ValueError("Missing INITIAL_WATERLEVEL_RESOURCE_URL")
    run_simulation(test_initial_wl_url)
