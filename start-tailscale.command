#!/bin/bash
# Double-click in Finder to start Pipeline Studio on this Mac, reachable over Tailscale.
# Defaults are for maxs-macbook-air. Override TS_IP / TS_NAME if the host changes.
cd "$(dirname "$0")"

TS_IP="${TS_IP:-100.67.212.42}"
TS_NAME="${TS_NAME:-maxs-macbook-air.taile46ae8.ts.net}"

export PIPELINE_BIND="$TS_IP"
export PIPELINE_ALLOWED_HOSTS="$TS_IP,$TS_NAME,maxs-macbook-air"

echo "Open from any device on your tailnet:"
echo "  http://$TS_IP:8000"
echo "  http://$TS_NAME:8000"
echo "Close this window (or press Ctrl+C) to stop."
echo
exec caffeinate -s ./run.sh
