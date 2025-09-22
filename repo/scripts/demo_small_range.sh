#!/usr/bin/env bash
set -euo pipefail

ROOT=$(dirname "$0")/..
cd "$ROOT"

# Ensure the in-tree "src" package directory is on PYTHONPATH so ``python -m``
# can resolve the cli.* entrypoints without requiring an editable install.
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"

TRAPS_DIR="demo_traps"
LANES="demo_lanes.csv"
BLOOM="demo_bloom.dat"
TARGETS="tests/data/sample_targets.json"
METRICS="demo_metrics.jsonl"

python3 -m cli.trap_tools generate --out-dir "$TRAPS_DIR" --total-traps 256 --bucket-log2 8 --base 1 --stride 3
python3 -m cli.trap_tools index --traps-dir "$TRAPS_DIR" --shard-bits 8
python3 -m cli.trap_tools build-bloom --csv "$TARGETS" --out "$BLOOM" --m-bits 20 --k-hashes 4
python3 -m cli.crt_tools schedule --L 0 --U 0x100000 --bits-per-mod 8 --mods 3 --workers 1 --lanes-per-worker 4 --out "$LANES"
python3 -m cli.run_worker --backend coincurve --seed 1337 --r 8 --base 1 --lanes-csv "$LANES" --worker-id 0 \
    --traps-dir "$TRAPS_DIR" --bucket-hint-bits 8 --bloom "$BLOOM" --m-bits 20 --k-hashes 4 --mapped-size $((1<<20)) \
    --target-rmd 751e76e8199196d454941c45d1b3a323f1433bd6 --save demo_saves.txt --metrics "$METRICS" --steps-per-batch 1000

echo
echo "Demo metrics summary (latest flush):"
METRICS_PATH="$METRICS" python3 - <<'PY'
import json
import os
from pathlib import Path

path = Path(os.environ["METRICS_PATH"])
if not path.exists():
    print("  No metrics file produced.")
    raise SystemExit(0)

records = []
with path.open("r", encoding="utf8") as fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue

if not records:
    print("  Metrics file is empty.")
    raise SystemExit(0)

latest = records[-1]
uptime = latest.get("uptime")
if uptime is not None:
    print(f"  uptime: {uptime:.2f}s")

for bucket, values in (("counters", latest.get("counters", {})), ("timers", latest.get("timers", {}))):
    if not values:
        continue
    print(f"  {bucket}:")
    for key in sorted(values):
        value = values[key]
        if isinstance(value, (int, float)):
            if isinstance(value, float):
                print(f"    {key}: {value:.6f}")
            else:
                print(f"    {key}: {value}")
        else:
            print(f"    {key}: {value}")

print(f"\nFull metrics log saved to {path}")
PY
