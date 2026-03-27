from __future__ import annotations

import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT / "pdf-agent-frontend"
FRONTEND_NODE_MODULES = FRONTEND_DIR / "node_modules"
VENV_DIR = ROOT / ".venv"
SECRET_KEY_FILE = ROOT / ".secrets" / "openrouter_api_key.txt"
DEFAULT_FRONTEND_PORT = os.environ.get("PDF_AGENT_FRONTEND_PORT", "5173")
DEFAULT_BACKEND_PORT = os.environ.get("PDF_AGENT_BACKEND_PORT", "8000")


def ensure_openrouter_api_key() -> None:
    if os.environ.get("OPENROUTER_API_KEY") or SECRET_KEY_FILE.exists() or (ROOT / ".env").exists():
        return
    raise RuntimeError(
        "Missing OpenRouter API key. Set OPENROUTER_API_KEY, add it to .env, or create .secrets/openrouter_api_key.txt."
    )


def resolve_venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def ensure_virtualenv() -> str:
    venv_python = resolve_venv_python()
    if venv_python.exists():
        return str(venv_python)

    print("[setup] Creating Python virtual environment...")
    subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], cwd=ROOT, check=True)
    return str(resolve_venv_python())


def ensure_command(command: str) -> None:
    if shutil.which(command):
        return
    raise RuntimeError(f"Missing required command: {command}")


def has_backend_dependencies(python_cmd: str) -> bool:
    result = subprocess.run(
        [
            python_cmd,
            "-c",
            (
                "import fastapi, uvicorn, PyPDF2, sentence_transformers, httpx; "
                "parts = tuple(int(x) for x in httpx.__version__.split('.')[:2]); "
                "raise SystemExit(0 if parts < (0, 28) else 1)"
            ),
        ],
        cwd=ROOT,
    )
    return result.returncode == 0


def ensure_backend_dependencies(python_cmd: str) -> None:
    if has_backend_dependencies(python_cmd):
        return

    print("[setup] Installing backend dependencies...")
    subprocess.run(
        [python_cmd, "-m", "pip", "install", "-r", "requirements.txt"],
        cwd=ROOT,
        check=True,
    )


def ensure_frontend_dependencies() -> None:
    if FRONTEND_NODE_MODULES.exists():
        return

    print("[setup] Installing frontend dependencies...")
    subprocess.run(
        ["npm", "install"],
        cwd=FRONTEND_DIR,
        check=True,
    )


def spawn_process(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.Popen:
    kwargs = {
        "cwd": cwd,
        "env": env or os.environ.copy(),
    }

    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["preexec_fn"] = os.setsid

    return subprocess.Popen(command, **kwargs)


def is_port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return sock.connect_ex(("127.0.0.1", port)) != 0


def find_available_port(preferred_port: str) -> int:
    port = int(preferred_port)
    while not is_port_available(port):
        port += 1
    return port


def terminate_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return

    try:
        if os.name == "nt":
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    except Exception:
        process.terminate()


def read_backend_health(backend_port: int) -> dict | None:
    url = f"http://127.0.0.1:{backend_port}/health"
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None


def wait_for_backend_index(backend: subprocess.Popen, backend_port: int, timeout_seconds: int = 900) -> bool:
    deadline = time.time() + timeout_seconds
    last_status = None

    while time.time() < deadline:
        code = backend.poll()
        if code is not None:
            print(f"[stop] backend exited with code {code} before startup completed.")
            return False

        health = read_backend_health(backend_port)
        if not health:
            time.sleep(1)
            continue

        if health.get("index_ready"):
            print("[ready] Backend is healthy and the PDF index is ready.")
            return True

        status = health.get("index_status", "unknown")
        error = health.get("index_error")
        message = f"[wait] Backend is up. Index status: {status}."
        if error:
            message += f" Last error: {error}"
        if message != last_status:
            print(message)
            last_status = message
        time.sleep(2)

    print("[error] Timed out while waiting for the PDF index to become ready.")
    return False


def main() -> int:
    try:
        ensure_command("npm")
        ensure_openrouter_api_key()
        python_cmd = ensure_virtualenv()
        ensure_backend_dependencies(python_cmd)
        ensure_frontend_dependencies()
    except Exception as exc:
        print(f"[error] {exc}")
        return 1

    backend_port = find_available_port(DEFAULT_BACKEND_PORT)
    frontend_port = find_available_port(DEFAULT_FRONTEND_PORT)

    backend_command = [
        python_cmd,
        "-m",
        "uvicorn",
        "api:app",
        "--host",
        "0.0.0.0",
        "--port",
        str(backend_port),
    ]
    frontend_command = [
        "npm",
        "run",
        "dev",
        "--",
        "--host",
        "0.0.0.0",
        "--port",
        str(frontend_port),
        "--strictPort",
    ]

    print("[start] Launching backend...")
    print(f"[start] Backend:  http://127.0.0.1:{backend_port}")
    print("[hint] Press Ctrl+C once to stop both services.")

    backend_env = os.environ.copy()
    backend_env.setdefault("TOKENIZERS_PARALLELISM", "false")
    backend = spawn_process(backend_command, ROOT, env=backend_env)
    processes = [backend]

    if not wait_for_backend_index(backend, backend_port):
        return 1

    frontend_env = os.environ.copy()
    frontend_env["VITE_API_URL"] = f"http://127.0.0.1:{backend_port}"
    print(f"[start] Frontend: http://127.0.0.1:{frontend_port}")
    frontend = spawn_process(frontend_command, FRONTEND_DIR, env=frontend_env)
    processes.append(frontend)

    try:
        while True:
            for process, name in ((backend, "backend"), (frontend, "frontend")):
                code = process.poll()
                if code is not None:
                    print(f"[stop] {name} exited with code {code}. Stopping the other service...")
                    return code
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[stop] Shutting down services...")
        return 0
    finally:
        for process in processes:
            terminate_process(process)

        deadline = time.time() + 5
        while time.time() < deadline:
            if all(process.poll() is not None for process in processes):
                break
            time.sleep(0.2)

        for process in processes:
            if process.poll() is None:
                process.kill()


if __name__ == "__main__":
    raise SystemExit(main())
