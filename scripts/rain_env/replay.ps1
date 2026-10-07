# Start, stop, or show a rain replay on the server (US-089).
#
# Run it in PowerShell on the server, in C:\Users\TECOTEC\airflow_new:
#
#   .\scripts\rain_env\replay.ps1 start -Event scripts\rain_events\hanoi_20251005_48h.csv
#   .\scripts\rain_env\replay.ps1 start -Event scripts\rain_events\hanoi_20251005_48h.csv -LeadMinutes 45 -Gate 5
#   .\scripts\rain_env\replay.ps1 status
#   .\scripts\rain_env\replay.ps1 stop
#
# start picks the first 15-minute slot at least -LeadMinutes ahead and checks the replay in the worker. If the check
# passes, it saves the prior values of the four rain keys to .env.rain-replay.json, writes the replay to .env,
# recreates only airflow-worker, and reads the replay back from inside the worker. It prints the time to unpause
# flood_mapping_full and does not unpause it. stop restores the saved values.
# The command never builds an image and never touches the DAG or the databases.
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("start", "stop", "status")]
    [string]$Command,
    [Alias("Event")]
    [string]$EventFile,
    [int]$LeadMinutes = 30,
    [string]$Gate = "0.01"
)

$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$envFile = Join-Path $repo ".env"
$stateFile = Join-Path $repo ".env.rain-replay.json"
$worker = "airflow_new-airflow-worker-1"
$tool = "/opt/airflow/scripts/rain_replay.py"
$keys = @("FLOOD_TEST_RAIN_CSV", "FLOOD_TEST_RAIN_START", "FLOOD_TEST_RAIN_MM_HR", "FLOOD_RAIN_THRESHOLD_MM_HR")
$utf8 = New-Object System.Text.UTF8Encoding($false)

function Fail($message) {
    Write-Host "FAILED: $message"
    exit 1
}

# Merges stderr so a refusal's one-line reason is in the output. Check $LASTEXITCODE after the call.
function Invoke-Tool {
    & docker exec $worker python $tool @args 2>&1 | ForEach-Object { "$_" }
}

function Get-KeyValue([string]$text, [string]$key) {
    $found = [regex]::Matches($text, "(?m)^" + [regex]::Escape($key) + "=([^\r\n]*)")
    if ($found.Count -eq 0) { return $null }
    return $found[$found.Count - 1].Groups[1].Value
}

# $value is untyped so that $null, which removes the line, stays distinct from "".
function Set-KeyValue([string]$text, [string]$key, $value) {
    $pattern = "(?m)^" + [regex]::Escape($key) + "=[^\r\n]*"
    if ($null -eq $value) { return [regex]::Replace($text, $pattern + "(\r?\n)?", "") }
    $line = $key + "=" + $value
    if ([regex]::IsMatch($text, $pattern)) { return [regex]::Replace($text, $pattern, $line.Replace('$', '$$')) }
    $newline = "`n"
    if ($text.Contains("`r`n")) { $newline = "`r`n" }
    if ($text.Length -gt 0 -and -not $text.EndsWith("`n")) { $text += $newline }
    return $text + $line + $newline
}

function Read-EnvText {
    if (-not (Test-Path $envFile)) { Fail "no .env at $envFile" }
    return [System.IO.File]::ReadAllText($envFile)
}

function Write-EnvText([string]$text) {
    [System.IO.File]::WriteAllText($envFile, $text, $utf8)
}

# A rain key set in this shell overrides .env in docker compose. On 2026-10-05 an empty one left the start blank.
function Update-Worker {
    foreach ($key in $keys) { Remove-Item "Env:$key" -ErrorAction SilentlyContinue }
    Push-Location $repo
    docker compose up -d --no-deps airflow-worker
    $code = $LASTEXITCODE
    Pop-Location
    if ($code -ne 0) { Fail "docker compose up -d --no-deps airflow-worker" }
    for ($i = 0; $i -lt 24; $i++) {
        $running = docker inspect --format "{{.State.Running}}" $worker 2>$null
        if ($running -eq "true") { return }
        Start-Sleep -Seconds 5
    }
    Fail "$worker is not running 2 minutes after the recreate"
}

function Start-Replay {
    if (-not $EventFile) { Fail "start needs -Event, for example -Event scripts\rain_events\hanoi_20251005_48h.csv" }
    $full = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($EventFile)
    $scriptsDir = (Join-Path $repo "scripts") + "\"
    if (-not $full.StartsWith($scriptsDir, [System.StringComparison]::OrdinalIgnoreCase)) {
        Fail "the event must be under $scriptsDir, which the worker mounts at /opt/airflow/scripts"
    }
    $containerEvent = "/opt/airflow/scripts/" + ($full.Substring($scriptsDir.Length) -replace '\\', '/')

    $now = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ", [System.Globalization.CultureInfo]::InvariantCulture)
    $slot = @(Invoke-Tool next-slot $now $LeadMinutes)
    if ($LASTEXITCODE -ne 0) { Fail ("next-slot: " + ($slot -join " ")) }
    $slot = $slot[-1]

    $check = @(Invoke-Tool check $containerEvent $slot $Gate)
    $check
    if ($LASTEXITCODE -ne 0) { Fail "the check refused the replay. .env is unchanged." }

    $text = Read-EnvText
    if (Test-Path $stateFile) {
        "kept $stateFile from an earlier start, so stop restores the values from before the first start"
    } else {
        $saved = [ordered]@{}
        foreach ($key in $keys) { $saved[$key] = Get-KeyValue $text $key }
        [System.IO.File]::WriteAllText($stateFile, ($saved | ConvertTo-Json), $utf8)
        "saved the prior values of the four rain keys to $stateFile"
    }
    $text = Set-KeyValue $text "FLOOD_TEST_RAIN_CSV" $containerEvent
    $text = Set-KeyValue $text "FLOOD_TEST_RAIN_START" $slot
    $text = Set-KeyValue $text "FLOOD_TEST_RAIN_MM_HR" ""
    $text = Set-KeyValue $text "FLOOD_RAIN_THRESHOLD_MM_HR" $Gate
    Write-EnvText $text
    "wrote the replay to .env, recreating airflow-worker"

    Update-Worker
    "read-back from inside the worker:"
    Invoke-Tool status "--expect-mode" replay "--expect-start" $slot
    if ($LASTEXITCODE -ne 0) {
        Fail "the worker does not run the replay that .env holds. Run .\scripts\rain_env\replay.ps1 stop to restore the prior values."
    }
    "replay is on. Do the next step by hand:"
    $check[-1]
}

function Stop-Replay {
    $text = Read-EnvText
    if (Test-Path $stateFile) {
        $saved = [System.IO.File]::ReadAllText($stateFile) | ConvertFrom-Json
        foreach ($key in $keys) { $text = Set-KeyValue $text $key $saved.$key }
        Write-EnvText $text
        Remove-Item $stateFile
        "restored the four rain keys from $stateFile and deleted it"
        $expect = @()
    } else {
        $wasReplay = (Get-KeyValue $text "FLOOD_TEST_RAIN_CSV") -or (Get-KeyValue $text "FLOOD_TEST_RAIN_START")
        foreach ($key in $keys[0..2]) { $text = Set-KeyValue $text $key "" }
        if ($wasReplay) {
            $text = Set-KeyValue $text "FLOOD_RAIN_THRESHOLD_MM_HR" $null
            "no $stateFile, so blanked FLOOD_TEST_RAIN_CSV, FLOOD_TEST_RAIN_START, and FLOOD_TEST_RAIN_MM_HR, and removed the FLOOD_RAIN_THRESHOLD_MM_HR line (the gate is then the compose default of 5)"
        } else {
            "no $stateFile and no replay in .env, so the gate stays as it is"
        }
        Write-EnvText $text
        $expect = @("--expect-mode", "live")
    }
    Update-Worker
    "read-back from inside the worker:"
    Invoke-Tool status @expect
    if ($LASTEXITCODE -ne 0) { Fail "the worker does not run the rain that .env holds" }
}

switch ($Command) {
    "start" { Start-Replay }
    "stop" { Stop-Replay }
    "status" {
        Invoke-Tool status
        if ($LASTEXITCODE -ne 0) { exit 1 }
    }
}
exit 0
