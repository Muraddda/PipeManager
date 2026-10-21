#!/bin/bash
# Double-click in Finder to start Pipeline Studio on this Mac, reachable over Tailscale.
# Detects this machine's Tailscale IP and name automatically. Override with TS_IP / TS_NAME if needed.
cd "$(dirname "$0")"

TS_CLI="$(command -v tailscale || true)"
[ -z "$TS_CLI" ] && TS_CLI="/Applications/Tailscale.app/Contents/MacOS/Tailscale"

if [ -z "$TS_IP" ]; then
  TS_IP="$("$TS_CLI" ip -4 2>/dev/null | head -n1)"
fi
if [ -z "$TS_NAME" ]; then
  TS_NAME="$("$TS_CLI" status --json 2>/dev/null | python3 -c 'import sys,json; print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))' 2>/dev/null)"
fi

if [ -z "$TS_IP" ]; then
  echo "Could not find a Tailscale IP. Open the Tailscale app, make sure it is Connected, then try again."
  read -r -p "Press Enter to close."
  exit 1
fi

SHORT="${TS_NAME%%.*}"
export PIPELINE_BIND="$TS_IP"
export PIPELINE_ALLOWED_HOSTS="$TS_IP,$TS_NAME,$SHORT"

echo "Open from any device on your tailnet:"
echo "  http://$TS_IP:8000"
[ -n "$TS_NAME" ] && echo "  http://$TS_NAME:8000"
echo "Close this window (or press Ctrl+C) to stop."
echo
exec caffeinate -s ./run.sh
