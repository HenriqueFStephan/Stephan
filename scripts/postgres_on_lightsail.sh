#!/bin/bash
# Install PostgreSQL on the existing Lightsail instance.
# Listens on 127.0.0.1 only. Does not create a Lightsail managed database.
# Run on the server as root: sudo bash postgres_on_lightsail.sh
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root on the Lightsail instance." >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y postgresql postgresql-contrib

conf=$(sudo -u postgres psql -tAc "SHOW config_file")
python3 - "$conf" << 'PY'
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
lines = path.read_text(encoding="utf-8").splitlines()
out = []
written = False
for line in lines:
    if re.match(r"\s*listen_addresses\s*=", line):
        if not written:
            out.append("listen_addresses = 'localhost'")
            written = True
        continue
    out.append(line)
if not written:
    out.append("listen_addresses = 'localhost'")
path.write_text("\n".join(out) + "\n", encoding="utf-8")
PY

hba=$(sudo -u postgres psql -tAc "SHOW hba_file")
if grep -E '^[^#]*0\.0\.0\.0/0|^[^#]*::/0' "$hba" >/dev/null; then
  echo "pg_hba.conf allows a non-local client. Refusing to continue." >&2
  exit 1
fi

systemctl restart postgresql

map=$(ss -ltnH 'sport = :5432' || true)
printf '%s\n' "$map"
if printf '%s\n' "$map" | grep -E '0\.0\.0\.0:5432|\[::\]:5432|\*:5432' >/dev/null; then
  echo "PostgreSQL is not localhost-only." >&2
  exit 1
fi
if ! printf '%s\n' "$map" | grep -E '127\.0\.0\.1:5432|\[::1\]:5432' >/dev/null; then
  echo "PostgreSQL is not listening on the loopback interface." >&2
  exit 1
fi

debt=/opt/stephan/debt.txt
if [[ -f "$debt" ]] && grep -q '^DATABASE_URL=postgresql' "$debt"; then
  echo "DATABASE_URL already set; password left unchanged"
else
  pass=$(openssl rand -hex 24)
  sudo -u postgres psql -v ON_ERROR_STOP=1 << SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'stephan') THEN
    CREATE ROLE stephan LOGIN PASSWORD '${pass}';
  ELSE
    ALTER ROLE stephan WITH LOGIN PASSWORD '${pass}';
  END IF;
END
\$\$;
SQL
  if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname = 'stephan'" | grep -q 1; then
    sudo -u postgres createdb -O stephan stephan
  fi
  sudo -u postgres psql -d stephan -v ON_ERROR_STOP=1 -c "ALTER SCHEMA public OWNER TO stephan;"
  sudo -u postgres psql -d stephan -v ON_ERROR_STOP=1 -c "GRANT ALL ON SCHEMA public TO stephan;"
  python3 - "$pass" << 'PY'
import sys
from pathlib import Path

password = sys.argv[1]
path = Path("/opt/stephan/debt.txt")
text = path.read_text(encoding="utf-8") if path.exists() else ""
lines = [line for line in text.splitlines() if not line.startswith("DATABASE_URL=")]
lines.append(f"DATABASE_URL=postgresql://stephan:{password}@127.0.0.1:5432/stephan")
path.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
  unset pass
fi

# The API runs as www-data. Root-only mode 600 makes settings load fail
# and nginx answer /api/v1 with 502.
if [[ -f "$debt" ]]; then
  chown www-data:www-data "$debt"
  chmod 600 "$debt"
fi

if systemctl list-unit-files stephan-api.service >/dev/null 2>&1; then
  systemctl restart stephan-api || true
fi

echo "postgres-listening-on-localhost"
