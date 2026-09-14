"""Launcher for the IROS frontend: starts the Next.js dev server (`npm run
dev`) as a subprocess and opens it in your default browser once it's ready.

Run with:
    python main.py

This is a plain Python launcher for a Node.js project (there is no Python code
in the frontend itself) - it just wraps `npm run dev` with a wait-for-port +
auto-open-browser convenience, matching agent/main.py's UX for the backend.
Requires Node.js/npm already installed and on PATH. Also kills any stray
process already listening on port 3000 before starting - otherwise a leftover
dev server from a previous run keeps running OLD code while Next.js falls
back to port 3001 for the new one, and the browser opens to the stale page.
"""
import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser

# Used for the internal port-check socket (127.0.0.1 is the most reliable
# loopback address to connect to). The browser is opened to "localhost"
# specifically, NOT "127.0.0.1" - the backend's CORS policy
# (agent/src/api/main.py) allows both, but keeping this consistent avoids
# ever depending on that fallback again.
CHECK_HOST = "127.0.0.1"
BROWSER_HOST = "localhost"
PORT = 3000
URL = f"http://{BROWSER_HOST}:{PORT}/"


def _kill_stray_process_on_port(port: int) -> None:
    if sys.platform != "win32":
        return
    try:
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
    except Exception as exc:  # noqa: BLE001 - best-effort cleanup, never block startup over this
        print(f"(non-fatal) could not check/clean port {port}: {exc}")


def _wait_for_server_then_open_browser() -> None:
    deadline = time.time() + 60
    while time.time() < deadline:
        try:
            with socket.create_connection((CHECK_HOST, PORT), timeout=0.5):
                break
        except OSError:
            time.sleep(0.5)
    else:
        print(f"Timed out waiting for the frontend on {CHECK_HOST}:{PORT}.")
        return
    webbrowser.open(URL)


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    _kill_stray_process_on_port(PORT)
    threading.Thread(target=_wait_for_server_then_open_browser, daemon=True).start()

    npm_executable = "npm.cmd" if sys.platform == "win32" else "npm"
    process = subprocess.Popen([npm_executable, "run", "dev"])
    try:
        process.wait()
    except KeyboardInterrupt:
        process.terminate()
        process.wait()
