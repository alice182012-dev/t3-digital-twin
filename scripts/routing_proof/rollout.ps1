# One deploy and one proof run of the time-aware engine on the server (US-055).
#
# Run it in PowerShell on the server, in the repo folder, AFTER the 48-hour replay has ended and flood_mapping_full is
# paused. It builds three images (the only builds), recreates three services, and runs every check once.
#
#   .\scripts\routing_proof\rollout.ps1                 # leaves TIME_AWARE_ROUTING off at the end
#   .\scripts\routing_proof\rollout.ps1 -LeaveOn        # leaves it on, when every check passed
#   .\scripts\routing_proof\rollout.ps1 -SkipBuild      # reuse the images of an earlier run
#
# It reads and writes only: the three images, the services graphhopper, floodmap-backend, and flood-routing-frontend, and result files in
# <data>\routing_proof. It never touches the depth tables, the DAG, or the databases. The log is appended to
# C:\Users\TECOTEC\rollout-proof.log. The scenario check on the deployed image runs from the Mac:
#   java/time-aware-routing/scenario-check.sh
param(
    [switch]$SkipBuild,
    [switch]$LeaveOn,
    [switch]$Force,
    [string]$Branch = "front-end-according-to-mock-up"
)

$worker = "airflow_new-airflow-worker-1"
$scheduler = "airflow_new-airflow-scheduler-1"
$ghContainer = "airflow_new-graphhopper-1"
$tool = "/opt/airflow/scripts/routing_proof/routing_proof.py"
$outDir = "/opt/airflow/data/routing_proof"
$logFile = "C:\Users\TECOTEC\rollout-proof.log"
$failures = New-Object System.Collections.Generic.List[string]

function Section($title) { "`n== $title" }
function Fail($what) { $script:failures.Add($what); "FAILED: $what" }

function Wait-Backend {
    for ($i = 0; $i -lt 40; $i++) {
        docker exec $worker python -c "import urllib.request; urllib.request.urlopen('http://floodmap-backend:8010/health', timeout=5)" 2>$null
        if ($LASTEXITCODE -eq 0) { return $true }
        Start-Sleep -Seconds 5
    }
    return $false
}

function Wait-GraphHopper {
    for ($i = 0; $i -lt 60; $i++) {
        $health = docker inspect --format "{{.State.Health.Status}}" $ghContainer 2>$null
        if ($health -eq "healthy") { return $true }
        Start-Sleep -Seconds 5
    }
    return $false
}

& {
    "rollout proof at $((Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')) UTC ($((Get-Date).ToString('yyyy-MM-dd HH:mm')) local)"

    Section "0. Preconditions: the replay window is over and the DAG is paused"
    $dags = docker exec $scheduler airflow dags list -o json 2>$null | Out-String
    if ($dags -match '"dag_id": "flood_mapping_full"[^}]*"is_paused": "False"') {
        if ($Force) { "WARNING: flood_mapping_full is unpaused, continuing because of -Force" }
        else { Fail "flood_mapping_full is unpaused. No image builds while the replay runs. Pause it, or use -Force."; return }
    } else { "flood_mapping_full is paused" }
    docker exec $worker ls /opt/airflow/edge_depth_tables

    Section "1. Pull the branch"
    git pull alice $Branch
    if ($LASTEXITCODE -ne 0) { Fail "git pull"; return }
    git log --oneline -1

    if (-not $SkipBuild) {
        Section "2. Build the three images (the only builds). The graphhopper build runs every module test, and the frontend build compiles the alert of US-054."
        docker compose build graphhopper floodmap-backend flood-routing-frontend
        if ($LASTEXITCODE -ne 0) { Fail "docker compose build"; return }
    }

    Section "3. Recreate graphhopper, floodmap-backend, and the frontend with TIME_AWARE_ROUTING off"
    Remove-Item Env:TIME_AWARE_ROUTING -ErrorAction SilentlyContinue
    docker compose up -d --no-deps graphhopper floodmap-backend flood-routing-frontend
    if ($LASTEXITCODE -ne 0) { Fail "docker compose up"; return }
    if (-not (Wait-GraphHopper)) { Fail "graphhopper did not become healthy in 5 minutes"; docker logs --tail 60 $ghContainer; return }
    if (-not (Wait-Backend)) { Fail "floodmap-backend did not answer in 3 minutes"; return }

    Section "4. What the engine logged at start (the module, the graph hash, the table)"
    docker logs $ghContainer 2>&1 | Select-String -Pattern "TimeAwareGraphHopper active|time-aware routing: following|edge depth table|refused" | Select-Object -Last 8
    $following = docker logs $ghContainer 2>&1 | Select-String -Pattern "time-aware routing: following /tables"
    if (-not $following) { Fail "the engine did not log that it follows /tables" }
    $loaded = docker logs $ghContainer 2>&1 | Select-String -Pattern "edge depth table .* loaded"
    if (-not $loaded) { Fail "the engine did not load a depth table (is a table published, and does its graph hash match the live graph?)" }

    Section "5. Today's model: the pairs with the flag off"
    docker exec $worker mkdir -p $outDir
    docker exec $worker python $tool pairs --out "$outDir/pairs-off.json"
    if ($LASTEXITCODE -ne 0) { Fail "pairs with the flag off" }

    Section "6. Turn the flag on for the proof (the backend only)"
    $env:TIME_AWARE_ROUTING = "true"
    docker compose up -d --no-deps floodmap-backend
    if ($LASTEXITCODE -ne 0) { Fail "docker compose up with the flag on"; return }
    if (-not (Wait-Backend)) { Fail "floodmap-backend did not answer with the flag on"; return }

    Section "7. The engine: the pairs with the flag on"
    docker exec $worker python $tool pairs --out "$outDir/pairs-on.json"
    if ($LASTEXITCODE -ne 0) { Fail "pairs with the flag on" }

    Section "8. How many routes change, and the median detour ratio"
    docker exec $worker python $tool compare "$outDir/pairs-off.json" "$outDir/pairs-on.json"
    if ($LASTEXITCODE -ne 0) { Fail "compare" }

    Section "9. The checker: no engine route crosses a road that is closed on arrival (today's model shown for contrast)"
    docker exec $worker python $tool crossings --a "$outDir/pairs-off.json" --b "$outDir/pairs-on.json"
    if ($LASTEXITCODE -ne 0) { Fail "crossings" }

    Section "10. POST /route/departures for each trip"
    docker exec $worker python $tool departures
    if ($LASTEXITCODE -ne 0) { Fail "departures" }

    Section "11. Latency of POST /route against the baseline of US-046 (factor 2)"
    docker exec $worker python $tool latency --out "$outDir/latency-on.json"
    if ($LASTEXITCODE -ne 0) { Fail "latency" }

    Section "12. The flag at the end"
    if ($LeaveOn -and $failures.Count -eq 0) {
        "Leaving TIME_AWARE_ROUTING on. Put TIME_AWARE_ROUTING=true in .env so it survives a recreate."
    } else {
        Remove-Item Env:TIME_AWARE_ROUTING -ErrorAction SilentlyContinue
        docker compose up -d --no-deps floodmap-backend
        "TIME_AWARE_ROUTING is off again."
    }

    Section "Result"
    if ($failures.Count -eq 0) { "PASS: every check passed. Run java/time-aware-routing/scenario-check.sh from the Mac for the scenarios." }
    else { "FAIL: " + ($failures -join "; ") }
} *>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $logFile -Append

exit $(if ($failures.Count -eq 0) { 0 } else { 1 })
