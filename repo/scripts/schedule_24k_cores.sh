#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 OUT_CSV" >&2
  exit 1
fi

OUT=$1
python3 -m cli.crt_tools schedule --L 0 --U 0x400000000000 --bits-per-mod 10 --mods 4 --workers 24000 --lanes-per-worker 16 --out "$OUT"
