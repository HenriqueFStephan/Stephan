"""Start PostgreSQL for local /tool work.

Listens on 127.0.0.1:5432 only. Does not install a Windows service and does not
create a hosted database. Data stays in %LOCALAPPDATA%\\Stephan\\postgres.

Uses the binaries shipped with the Python package ``pgserver`` when Docker is
not available. That package is not an API dependency.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
from pathlib import Path


def binaries() -> Path:
    try:
        from pgserver._commands import POSTGRES_BIN_PATH
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "pgserver"])
        from pgserver._commands import POSTGRES_BIN_PATH
    path = Path(POSTGRES_BIN_PATH)
    if not (path / "initdb.exe").exists() and not (path / "initdb").exists():
        raise SystemExit(f"PostgreSQL binaries not found in {path}")
    return path


def exe(folder: Path, name: str) -> str:
    windows = folder / f"{name}.exe"
    return str(windows if windows.exists() else folder / name)


def data_dir() -> Path:
    root = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".local" / "share")
    return Path(root) / "Stephan" / "postgres"


def port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.4)
        return sock.connect_ex((host, port)) == 0


def listening_hosts(port: int) -> list[str]:
    try:
        import psutil
    except ImportError:
        return []
    hosts: list[str] = []
    for conn in psutil.net_connections(kind="inet"):
        if conn.laddr and conn.laddr.port == port and conn.status == "LISTEN":
            hosts.append(conn.laddr.ip)
    return hosts


def ensure_cluster(folder: Path, data: Path) -> None:
    if (data / "PG_VERSION").exists():
        return
    data.parent.mkdir(parents=True, exist_ok=True)
    password = data.parent / "stephan-pg-password.txt"
    password.write_text("stephan", encoding="ascii")
    try:
        subprocess.check_call(
            [
                exe(folder, "initdb"),
                "-D",
                str(data),
                "-U",
                "stephan",
                "-E",
                "UTF8",
                "--locale=C",
                f"--pwfile={password}",
                "--auth=scram-sha-256",
            ]
        )
    finally:
        password.unlink(missing_ok=True)
    tighten(data)


def tighten(data: Path) -> None:
    conf = (data / "postgresql.conf").read_text(encoding="utf-8")
    lines = []
    written = False
    for line in conf.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("listen_addresses"):
            if not written:
                lines.append("listen_addresses = '127.0.0.1'")
                written = True
            continue
        lines.append(line)
    if not written:
        lines.append("listen_addresses = '127.0.0.1'")
    (data / "postgresql.conf").write_text("\n".join(lines) + "\n", encoding="utf-8")

    hba = (data / "pg_hba.conf").read_text(encoding="utf-8")
    for line in hba.splitlines():
        body = line.split("#", 1)[0].strip()
        if not body:
            continue
        if "0.0.0.0/0" in body or "::/0" in body:
            raise SystemExit("pg_hba.conf allows a non-local client")


def start(folder: Path, data: Path) -> None:
    if port_open("127.0.0.1", 5432):
        hosts = listening_hosts(5432)
        if hosts and any(host not in {"127.0.0.1", "::1"} for host in hosts):
            raise SystemExit(f"port 5432 is public: {hosts}")
        print("postgres-already-listening-on-127.0.0.1")
        return
    subprocess.check_call(
        [
            exe(folder, "pg_ctl"),
            "-D",
            str(data),
            "-l",
            str(data / "server.log"),
            "-w",
            "-o",
            "-h 127.0.0.1 -p 5432",
            "start",
        ]
    )


def ensure_database(folder: Path) -> None:
    env = os.environ.copy()
    env["PGPASSWORD"] = "stephan"
    exists = subprocess.run(
        [
            exe(folder, "psql"),
            "-h",
            "127.0.0.1",
            "-p",
            "5432",
            "-U",
            "stephan",
            "-d",
            "postgres",
            "-tAc",
            "SELECT 1 FROM pg_database WHERE datname = 'stephan'",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    if "1" in exists.stdout:
        return
    subprocess.check_call(
        [
            exe(folder, "createdb"),
            "-h",
            "127.0.0.1",
            "-p",
            "5432",
            "-U",
            "stephan",
            "stephan",
        ],
        env=env,
    )


def main() -> None:
    folder = binaries()
    data = data_dir()
    ensure_cluster(folder, data)
    start(folder, data)
    hosts = listening_hosts(5432)
    if hosts and any(host not in {"127.0.0.1", "::1"} for host in hosts):
        raise SystemExit(f"PostgreSQL is not localhost-only: {hosts}")
    ensure_database(folder)
    print("postgres-listening-on-127.0.0.1")
    print(data)


if __name__ == "__main__":
    main()
