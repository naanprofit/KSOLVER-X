#!/usr/bin/env bash
set -euo pipefail

ROOT=$(dirname "$0")/..
cd "$ROOT"

TRAPS_DIR="demo_traps"
LANES="demo_lanes.csv"
BLOOM="demo_bloom.dat"
TARGETS="tests/data/sample_targets.json"

python3 -m cli.trap_tools generate --out-dir "$TRAPS_DIR" --total-traps 256 --bucket-log2 8 --base 1 --stride 3
python3 -m cli.trap_tools index --traps-dir "$TRAPS_DIR" --shard-bits 8
python3 -m cli.trap_tools build-bloom --csv "$TARGETS" --out "$BLOOM" --m-bits 20 --k-hashes 4
python3 -m cli.crt_tools schedule --L 0 --U 0x100000 --bits-per-mod 8 --mods 3 --workers 1 --lanes-per-worker 4 --out "$LANES"
python3 -m cli.run_worker --backend coincurve --seed 1337 --r 8 --base 1 --lanes-csv "$LANES" --worker-id 0 \
    --traps-dir "$TRAPS_DIR" --bucket-hint-bits 8 --bloom "$BLOOM" --m-bits 20 --k-hashes 4 --mapped-size $((1<<20)) \
    --target-rmd 751e76e8199196d454941c45d1b3a323f1433bd6 --save demo_saves.txt --metrics demo_metrics.jsonl --steps-per-batch 1000
