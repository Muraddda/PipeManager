@echo off
rem Double-click to start Pipeline Studio on this Windows PC, reachable over Tailscale.
rem Defaults are for the device "max". Set TS_IP / TS_NAME before running to override.
cd /d "%~dp0"

if not defined TS_IP set TS_IP=100.70.216.10
if not defined TS_NAME set TS_NAME=max.taile46ae8.ts.net

set PIPELINE_BIND=%TS_IP%
set PIPELINE_ALLOWED_HOSTS=%TS_IP%,%TS_NAME%,max

set PY=python
where py >nul 2>nul && set PY=py -3

echo Open from any device on your tailnet:
echo   http://%TS_IP%:8000
echo   http://%TS_NAME%:8000
echo Close this window (or press Ctrl+C) to stop.
echo.

%PY% db.py
%PY% server.py
echo.
echo The server stopped. See any error above.
pause
