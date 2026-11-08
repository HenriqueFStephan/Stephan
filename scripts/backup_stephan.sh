#!/bin/bash
# Consistent copy of the campaign database and the contact/order files.
# Keeps 14 days in /var/backups/stephan, mode 600. Does not print the database URL.
# Run on the server as root: sudo bash backup_stephan.sh
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root on the Lightsail instance." >&2
  exit 1
fi

debt=/opt/stephan/debt.txt
dest=/var/backups/stephan
if [[ ! -f "$debt" ]]; then
  echo "no debt.txt; backup skipped"
  exit 0
fi

url=$(python3 - "$debt" << 'PY'
from pathlib import Path
import sys

for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    if line.startswith("DATABASE_URL="):
        print(line.split("=", 1)[1].strip())
        break
PY
)
if [[ -z "$url" || "$url" != postgresql://* ]]; then
  echo "no local database url; backup skipped"
  exit 0
fi

install -d -m 700 "$dest"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
python3 - "$url" "$work" << 'PY'
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

parts = urlsplit(sys.argv[1])
host = parts.hostname or "127.0.0.1"
port = parts.port or 5432
user = unquote(parts.username or "")
password = unquote(parts.password or "")
database = (parts.path or "").lstrip("/") or "stephan"
root = Path(sys.argv[2])
(root / "pgpass").write_text(f"{host}:{port}:{database}:{user}:{password}\n", encoding="utf-8")
(root / "meta").write_text(f"{host}\n{port}\n{user}\n{database}\n", encoding="utf-8")
PY
chmod 600 "$work/pgpass"
mapfile -t meta < "$work/meta"
export PGPASSFILE="$work/pgpass"
pg_dump \
  -h "${meta[0]}" \
  -p "${meta[1]}" \
  -U "${meta[2]}" \
  -d "${meta[3]}" \
  --format=custom \
  --file="$work/stephan.dump"
unset PGPASSFILE

data=/opt/stephan/backend/data
files=(stephan.dump)
for name in messages.jsonl orders.jsonl; do
  if [[ -f "$data/$name" ]]; then
    cp "$data/$name" "$work/$name"
    files+=("$name")
  fi
done

stamp=$(date -u +%Y%m%dT%H%M%SZ)
archive="$dest/stephan-$stamp.tar.gz"
tar -C "$work" -czf "$archive" "${files[@]}"
chmod 600 "$archive"
find "$dest" -type f -name 'stephan-*.tar.gz' -mtime +14 -delete
echo "backup-written"
