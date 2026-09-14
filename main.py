"""Single entry point for the WHOLE IROS app — backend and frontend together.

Run with:
    python main.py

Starts the FastAPI/uvicorn backend (agent/, port 8000) and the Next.js
frontend dev server (frontend/) as child processes, waits for BOTH to
actually be ready (a real TCP-connect poll, not just "the process started"),
then opens your browser straight to the running app. Ctrl+C here stops both
cleanly.

Why this exists as a separate root-level script rather than just extending
agent/main.py in place: agent/main.py's own working directory / relative-path
assumptions (./iros.db, etc.) are anchored to agent/, so it needs to keep
being independently runnable from there too — this script orchestrates it
as a child process instead of merging the two.

Notes:
  - The frontend port is NOT assumed to be 3000: Next.js silently falls back
    to the next free port if 3000 is taken (confirmed a persistent, non-killable
    process already holds 3000 in at least one real dev environment) — this
    script reads the actual bound port straight out of the frontend's own
    startup log line instead of guessing.
  - On Windows, `npm run dev` spawns `node` as a CHILD of the npm process, so
    a plain `proc.terminate()` on shutdown would kill the npm wrapper but
    leave the actual Next.js server running and still holding its port.
    Shutdown here uses `taskkill /F /T /PID` (kill the whole process tree)
    for exactly this reason — matching the same pattern agent/main.py already
    uses to clean up a stray backend process on startup.
"""
import atexit
import os
import re
import socket
import subprocess
import sys
import threading
import time
import webbrowser

ROOT = os.path.dirname(os.path.abspath(__file__))
AGENT_DIR = os.path.join(ROOT, "agent")
FRONTEND_DIR = os.path.join(ROOT, "frontend")
BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8000
DEFAULT_FRONTEND_PORT = 3000

_FRONTEND_PORT_RE = re.compile(r"Local:\s+https?://[^:\s]+:(\d+)")

_children: list[subprocess.Popen] = []
_cleaned_up = False


def _kill_stray_processes_on_ports(ports: list[int]) -> None:
    """Best-effort: clears a leftover process from a previous run of THIS
    same dev server before starting a fresh one. Never blocks/fails startup —
    some ports (e.g. one already held by an unrelated system process) can't
    be freed this way, and that's fine; the port-detection logic below copes
    with whatever port actually ends up free.
    """
    try:
        if sys.platform == "win32":
            for port in ports:
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     f"Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue "
                     "| Select-Object -ExpandProperty OwningProcess -Unique"],
                    capture_output=True, text=True, timeout=10,
                )
                pids = [line.strip() for line in result.stdout.splitlines() if line.strip().isdigit()]
                for pid in pids:
                    subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True, timeout=10)
        else:
            for port in ports:
                result = subprocess.run(
                    ["lsof", "-t", "-i", f":{port}", "-sTCP:LISTEN"],
                    capture_output=True, text=True, timeout=10,
                )
                pids = [line.strip() for line in result.stdout.splitlines() if line.strip().isdigit()]
                for pid in pids:
                    subprocess.run(["kill", "-9", pid], capture_output=True, timeout=10)
    except Exception:  # noqa: BLE001 - best-effort cleanup, never block startup over this
        pass


def _kill_process_tree(proc: "subprocess.Popen") -> None:
    if proc.poll() is not None:
        return  # already exited
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True, timeout=10)
    else:
        proc.terminate()


def _cleanup() -> None:
    global _cleaned_up
    if _cleaned_up:
        return
    _cleaned_up = True
    for proc in _children:
        _kill_process_tree(proc)


def _wait_for_port(host: str, port: int, *, timeout: float) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.3)
    return False


def _stream_frontend_output(proc: "subprocess.Popen", port_holder: dict) -> None:
    """Pipes the frontend's own stdout straight through to this console (so
    the normal `next dev` compile logs stay visible) while watching for its
    "- Local: http://localhost:XXXX" line to learn which port it actually
    bound to.
    """
    assert proc.stdout is not None
    for line in proc.stdout:
        print(f"[frontend] {line}", end="")
        match = _FRONTEND_PORT_RE.search(line)
        if match and "port" not in port_holder:
            port_holder["port"] = int(match.group(1))


def main() -> None:
    print("=" * 72)
    print(" IROS — starting backend (FastAPI, :8000) + frontend (Next.js)...")
    print("=" * 72)

    # Clear leftover runs on common backend and frontend ports
    _kill_stray_processes_on_ports([BACKEND_PORT, DEFAULT_FRONTEND_PORT, DEFAULT_FRONTEND_PORT + 1, DEFAULT_FRONTEND_PORT + 2])

    backend_env = dict(os.environ, IROS_SUPPRESS_BROWSER="1")
    
    # Use virtual environment python if it exists, falling back to sys.executable
    python_exe = sys.executable
    venv_python = os.path.join(AGENT_DIR, ".venv", "bin", "python")
    if os.path.exists(venv_python):
        python_exe = venv_python

    backend_proc = subprocess.Popen([python_exe, "main.py"], cwd=AGENT_DIR, env=backend_env)
    _children.append(backend_proc)
    atexit.register(_cleanup)

    frontend_cmd = "npm run dev" if sys.platform == "win32" else "npm run dev"
    frontend_proc = subprocess.Popen(
        frontend_cmd,
        cwd=FRONTEND_DIR,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    _children.append(frontend_proc)

    port_holder: dict[str, int] = {}
    threading.Thread(target=_stream_frontend_output, args=(frontend_proc, port_holder), daemon=True).start()

    print(f"\nWaiting for backend on http://{BACKEND_HOST}:{BACKEND_PORT} ...")
    backend_ready = _wait_for_port(BACKEND_HOST, BACKEND_PORT, timeout=60)
    print(f"Backend {'is up.' if backend_ready else 'did NOT come up in time — check its output above.'}")

    # Learn which port the frontend actually bound to (it silently falls back
    # to the next free port if the default is taken) before polling it.
    deadline = time.time() + 30
    while "port" not in port_holder and frontend_proc.poll() is None and time.time() < deadline:
        time.sleep(0.2)
    frontend_port = port_holder.get("port", DEFAULT_FRONTEND_PORT)

    print(f"Waiting for frontend on http://localhost:{frontend_port} ...")
    frontend_ready = _wait_for_port("127.0.0.1", frontend_port, timeout=60)
    frontend_url = f"http://localhost:{frontend_port}/"

    if frontend_ready:
        print(f"Frontend is up. Opening {frontend_url} ...\n")
        webbrowser.open(frontend_url)
        print("Both servers are running. Press Ctrl+C here to stop them.")
    else:
        print(f"Frontend did NOT come up in time on {frontend_url} — check the [frontend] logs above.")

    try:
        while True:
            if backend_proc.poll() is not None:
                print("\nBackend process exited on its own — shutting down.")
                break
            if frontend_proc.poll() is not None:
                print("\nFrontend process exited on its own — shutting down.")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping backend + frontend...")
    finally:
        _cleanup()


if __name__ == "__main__":
    main()
