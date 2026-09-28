#!/bin/bash
# Runs on the Lightsail instance as root. The key arrives in /tmp/blockwall.key
# and is removed here. The rest of /opt/stephan/debt.txt is left in place.
set -euo pipefail

key_file=/tmp/blockwall.key
key=$(tr -d '\r\n' < "$key_file")
rm -f "$key_file"
if [ -z "$key" ]; then
  echo "empty key" >&2
  exit 1
fi

python3 - "$key" << 'PY'
import sys
from pathlib import Path

key = sys.argv[1]
path = Path("/opt/stephan/debt.txt")
text = path.read_text(encoding="utf-8") if path.exists() else ""
lines = [line for line in text.splitlines() if not line.startswith("BLOCKWALL_KEY=")]
lines.append("BLOCKWALL_KEY=" + key)
path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("blockwall-key-installed")
PY

systemctl restart stephan-api
for _ in 1 2 3 4 5 6 7 8 9 10 11 12; do
  if curl -sf http://127.0.0.1:8000/api/v1/blockwall/status | grep -q '"enabled":true'; then
    echo wall-enabled
    exit 0
  fi
  sleep 1
done
echo wall-not-enabled >&2
curl -sf http://127.0.0.1:8000/api/v1/blockwall/status || true
exit 1
