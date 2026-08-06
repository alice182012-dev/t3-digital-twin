"""3Di simulation result download, built on the official threedi-api-client.

Uses the client's dedicated results-download endpoint
(simulations_results_files_download) instead of a manual multi-hop link
resolution, and threedi_api_client.files.download_file (streaming + retry)
instead of a raw requests.get(stream=True).
"""

import os
from pathlib import Path

import fiona
import fiona.vfs

if not hasattr(fiona, 'path'):
    fiona.path = fiona.vfs

from threedi_api_client.files import download_file

from threedi_client import get_client


def get_result_file(api, sim_id):
    """Find the first .nc result file for a simulation."""
    result_files = api.simulations_results_files_list(sim_id)
    for item in result_files.results:
        if item.filename.endswith(".nc"):
            return item
    return None


def run_download(sim_id, output_dir):
    api = get_client()

    try:
        result_file = get_result_file(api, sim_id)
        if not result_file:
            print(f"❌ Could not find valid results for Sim {sim_id}")
            return None

        download = api.simulations_results_files_download(result_file.id, sim_id)

        os.makedirs(output_dir, exist_ok=True)
        local_path = Path(output_dir) / result_file.filename

        print(f"⬇️ Downloading to {local_path}...")
        download_file(download.get_url, local_path)
        return str(local_path)
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return None
