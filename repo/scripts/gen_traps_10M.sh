#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 OUT_DIR" >&2
  exit 1
fi

OUT_DIR=$1
python3 -m cli.trap_tools generate --out-dir "$OUT_DIR" --total-traps 10000000 --bucket-log2 12 --base 0x100000000 --stride 0x12345 --jobs 8
python3 -m cli.trap_tools index --traps-dir "$OUT_DIR" --shard-bits 12
