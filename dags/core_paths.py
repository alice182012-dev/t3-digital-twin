"""Folders that `flood_mapping_full` writes and `flood_tiles` reads and cleans, so both DAG files share one layout."""
import os


BASE_PATH = "/opt/airflow"
DATA_PATH = os.path.join(BASE_PATH, "data/mapping")
RESULT_DIR = os.path.join(DATA_PATH, "results")
DEPTH_ROOT_DIR = os.path.join(DATA_PATH, "output_depths")
