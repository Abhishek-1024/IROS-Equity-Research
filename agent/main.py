"""Launcher for the IROS backend: starts the FastAPI/uvicorn server (which runs
all 25 agents (24 on-demand + 1 standing) in-process via the LangGraph graph in
src/agents/graph.py) and
opens the interactive API docs in your default browser once it's ready.

Run with:
    python main.py

This chdirs to its own directory first, so relative paths (notably the SQLite
DB at ./iros.db, see src/core/config.py) always resolve to agent/iros.db
regardless of where you launched the script from. It also kills any stray
process already listening on port 8000 before starting - a leftover process
from a previous run (e.g. a terminal that got closed without stopping the
server) otherwise silently keeps the OLD code running while this script waits
on a port that already "works", then opens the browser to stale state.

Set IROS_SUPPRESS_BROWSER=1 to skip opening the /docs tab (used by the
repo-root `python main.py`, which starts the frontend too and opens its own
single browser tab there instead of opening two tabs).
"""
import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser

import uvicorn

HOST = "127.0.0.1"
PORT = 8000
DOCS_URL = f"http://{HOST}:{PORT}/docs"


def _kill_stray_process_on_port(port: int) -> None:
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue "
                 "| Select-Object -ExpandProperty OwningProcess -Unique"],
                capture_output=True, text=True, timeout=10,
            )
            pids = [line.strip() for line in result.stdout.splitlines() if line.strip().isdigit()]
            for pid in pids:
                subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True, timeout=10)
                print(f"Killed stray process {pid} that was already listening on port {port}.")
        else:
            result = subprocess.run(
                ["lsof", "-t", "-i", f":{port}", "-sTCP:LISTEN"],
                capture_output=True, text=True, timeout=10,
            )
            pids = [line.strip() for line in result.stdout.splitlines() if line.strip().isdigit()]
            for pid in pids:
                subprocess.run(["kill", "-9", pid], capture_output=True, timeout=10)
                print(f"Killed stray process {pid} that was already listening on port {port}.")
    except Exception as exc:  # noqa: BLE001 - best-effort cleanup, never block startup over this
        print(f"(non-fatal) could not check/clean port {port}: {exc}")


def _wait_for_server_then_open_browser() -> None:
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            with socket.create_connection((HOST, PORT), timeout=0.5):
                break
        except OSError:
            time.sleep(0.3)
    else:
        print(f"Timed out waiting for the backend on {HOST}:{PORT}.")
        return
    if not os.environ.get("IROS_SUPPRESS_BROWSER"):
        webbrowser.open(DOCS_URL)


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    _kill_stray_process_on_port(PORT)
    threading.Thread(target=_wait_for_server_then_open_browser, daemon=True).start()
    uvicorn.run("src.api.main:app", host=HOST, port=PORT, log_level="info")
