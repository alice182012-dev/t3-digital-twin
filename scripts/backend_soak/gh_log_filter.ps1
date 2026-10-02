# Runs on the Docker host, fed to PowerShell on stdin. Keep the command on one line, because PowerShell prints nothing for a block that spans lines on stdin.
# It prints the lines of the GraphHopper log that the soak scan needs, cut to 300 characters.
# GraphHopper writes the whole custom model of each flood-graded request on one log line, up to about 450 KB, so copying the raw log to another machine can take minutes.
# run_soak.sh replaces SINCE_PLACEHOLDER with the soak start.
docker logs --timestamps --since SINCE_PLACEHOLDER airflow_new-graphhopper-1 2>&1 | ForEach-Object { $l = [string]$_; if ($l -match 'RouteResource|MultiExceptionMapper| ERROR | WARN |OutOfMemory|Caused by:|Exception in thread') { $l.Substring(0, [Math]::Min(300, $l.Length)) } }
