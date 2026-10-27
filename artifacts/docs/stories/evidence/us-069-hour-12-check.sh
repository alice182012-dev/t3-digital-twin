#!/usr/bin/env bash
# Read-only storage readings for US-069, from the Mac over --context remote-server.
set -u
d() { docker --context remote-server "$@"; }
p() { d exec airflow_new-storage-postgres-1 psql -U minio_custom -d minio_custom -At -c "$1"; }
echo "captured: $(date '+%F %T %z') on $(hostname -s), reading server 100.67.84.55"
echo "minio_custom bytes:            $(p "select pg_database_size('minio_custom')")"
echo "netcdf_values rows | size:     $(p "select count(*) || ' | ' || pg_size_pretty(pg_total_relation_size('netcdf_values')) from netcdf_values")"
echo "storage-postgres-data bytes:   $(d exec airflow_new-storage-postgres-1 du -sb /var/lib/postgresql/data | cut -f1)"
echo "flood_extent_polygon rows:     $(p "select count(*) from flood_extent_polygon")"
echo "paused containers:             $(d ps --filter status=paused -q | wc -l | tr -d ' ')"
PS='$c=[math]::Round((Get-PSDrive C).Free/1GB,1); "C: free GiB:                    $c"; $v=[math]::Round((Get-Item C:\Users\TECOTEC\AppData\Local\Docker\wsl\disk\docker_data.vhdx).Length/1GB,2); "docker_data.vhdx GiB:            $v"'
ENC=$(printf '%s' "$PS" | iconv -f UTF-8 -t UTF-16LE | base64 | tr -d '\n')
ssh tecotec@100.67.84.55 "powershell -NoProfile -EncodedCommand $ENC" 2>&1 | grep -v -e "^#< CLIXML" -e "^<Objs"
