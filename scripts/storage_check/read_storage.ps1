# Reads the storage numbers of the server for US-069 (and the state check before the replay window).
# Read-only. Run it in PowerShell on the server, in the repo folder:
#   .\scripts\storage_check\read_storage.ps1 -Label "0h"
#   .\scripts\storage_check\read_storage.ps1 -Label "24h"
#   .\scripts\storage_check\read_storage.ps1 -Label "48h"
# It prints the readings and appends them to C:\Users\TECOTEC\storage-readings.log, so the three readings sit side by side.
param([string]$Label = "reading")

$ErrorActionPreference = "Continue"
$postgres = "airflow_new-storage-postgres-1"
$timescale = "airflow_new-timescaledb-1"
$scheduler = "airflow_new-airflow-scheduler-1"
$worker = "airflow_new-airflow-worker-1"
$vhdx = "C:\Users\TECOTEC\AppData\Local\Docker\wsl\disk\docker_data.vhdx"
$logFile = "C:\Users\TECOTEC\storage-readings.log"

function Section($title) { "`n== $title" }

$out = & {
    "storage reading '$Label' at $((Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')) UTC ($((Get-Date).ToString('yyyy-MM-dd HH:mm')) local)"

    Section "1. Disk"
    $c = Get-PSDrive C
    "C: used {0:N1} GiB, free {1:N1} GiB" -f ($c.Used / 1GB), ($c.Free / 1GB)
    if (Test-Path $vhdx) { "docker_data.vhdx {0:N2} GiB" -f ((Get-Item $vhdx).Length / 1GB) } else { "docker_data.vhdx not found at $vhdx" }
    docker system df

    Section "2. Volumes (size inside Docker)"
    docker system df -v | Select-String -Pattern "storage-postgres-data|timescaledb-data|minio-data|edge-depth-tables|airflow-logs|graphhopper-graph-cache"

    Section "3. Database sizes (storage-postgres, database minio_custom)"
    docker exec $postgres psql -U minio_custom -d minio_custom -At -F " | " -c "select 'minio_custom total', pg_size_pretty(pg_database_size('minio_custom'))"
    docker exec $postgres psql -U minio_custom -d minio_custom -At -F " | " -c "select 'flood_extent_polygon', pg_size_pretty(pg_total_relation_size('flood_extent_polygon')), count(*) || ' rows', count(distinct run_ts) || ' runs' from flood_extent_polygon"
    docker exec $postgres psql -U minio_custom -d minio_custom -At -F " | " -c "select 'flood_depth_raster_tile', pg_size_pretty(pg_total_relation_size('flood_depth_raster_tile')), count(*) || ' rows', count(distinct run_ts) || ' runs' from flood_depth_raster_tile"
    docker exec $postgres psql -U minio_custom -d minio_custom -At -F " | " -c "select 'graph_edge', pg_size_pretty(pg_total_relation_size('graph_edge')), count(*) || ' rows' from graph_edge"

    Section "4. Database size (timescaledb, database flood_metrics)"
    docker exec $timescale psql -U flood_metrics -d flood_metrics -At -F " | " -c "select 'flood_metrics total', pg_size_pretty(pg_database_size('flood_metrics'))"

    Section "5. Containers that Docker or the host paused or stopped"
    docker ps -a --filter "status=paused" --filter "status=exited" --filter "status=dead" --format "{{.Names}}  {{.Status}}"

    Section "6. DAG and replay"
    docker exec $scheduler airflow dags list -o json 2>$null | Select-String -Pattern '"dag_id": "flood_mapping_full"|"is_paused"' | Select-Object -First 4
    "dag rows named flood_mapping_full: " + ((docker exec $scheduler airflow dags list -o json 2>$null | Select-String -Pattern '"dag_id": "flood_mapping_full"' | Measure-Object).Count)
    docker exec $scheduler airflow dags list-import-errors 2>$null | Select-String -Pattern "No data found|Error"
    docker exec $worker printenv FLOOD_TEST_RAIN_CSV FLOOD_TEST_RAIN_START FLOOD_TEST_RAIN_MM_HR FLOOD_RAIN_THRESHOLD_MM_HR EDGE_TABLE_KEEP_RUNS FLOOD_EXTENT_KEEP_RUNS

    Section "7. The edge depth tables"
    docker exec $worker sh -c 'ls -l /opt/airflow/edge_depth_tables; echo "--- latest:"; cat /opt/airflow/edge_depth_tables/latest'

    Section "8. Leftovers from the checks"
    docker ps -a --filter name=graphhopper-time-aware --format "container {{.Names}}  {{.Status}}"
    docker volume ls --filter name=graphhopper-time-aware --format "volume {{.Name}}"
    if (Test-Path D:\airflow_new_data\data\mapping\edge_depth) { "old table folder still there: D:\airflow_new_data\data\mapping\edge_depth" } else { "old table folder removed" }
    if (Test-Path .\dags\zz_cold_start_probe_dag.py) { "probe DAG still there: dags\zz_cold_start_probe_dag.py" } else { "probe DAG removed" }
} 2>&1 | ForEach-Object { "$_" }

$out
$out | Add-Content -Path $logFile -Encoding ascii
"`n(appended to $logFile)"
