# KSOLVER-X

KSOLVER-X is a modular pipeline for distributed searches on the secp256k1 elliptic curve discrete logarithm problem (ECDLP). The design combines bucketized Fractal Rainbow Table (FRT) traps, deterministic Chinese Remainder Theorem (CRT) lane scheduling, and a staged filter cascade to minimise expensive lookups. The worker integrates BSGSD-style stepping with GLV/negation optimisations and Bloom-filter backed target probes.

```
+-------------------------+        +------------------+        +------------------+
| CRT Tiler & Scheduler  | -----> | Worker (BSGSD)   | -----> | Verify & Metrics |
+-------------------------+        |  Filters + Bloom |        +------------------+
           ^                       |  Trap Probe      |
           |                       +------------------+
           |                               |
+-------------------------+                v
| Trap Generator & Index | <----- bucketised traps -----+
+-------------------------+
```

## Why traps?

Trap tables capture contiguous scalar buckets so that once a walk lands near a trap anchor, the remaining search space shrinks dramatically. Bucketisation keeps storage practical while the sharded trap index enables fast tag-based lookups without scanning full files.

## Deterministic CRT lanes

The CRT tiler builds small prime moduli and enumerates residue combinations. The scheduler assigns mixed-radix lane identifiers to workers, guaranteeing non-overlapping scalar coverage. Deterministic lanes ensure reproducible work partitioning for both local and cluster deployments.

## Filter cascade

The worker applies very cheap bit-plane masks and GLV/negation-derived tags before touching the Bloom filter or trap index. These inexpensive rejections dramatically reduce memory-mapped IO and expensive cryptographic operations.

## Quickstart

1. **Install dependencies**
   ```bash
   python3 -m pip install -r requirements.txt
   ```

2. *(Optional but recommended)* **Install KSOLVER-X in editable mode** so the
   CLI entry points are available anywhere on your system:
   ```bash
   python3 -m pip install -e .
   ```

3. **Create a Bloom filter** (using sample targets)
   ```bash
   python3 -m cli.trap_tools build-bloom --csv tests/data/sample_targets.json --out bloom.dat --m-bits 20 --k-hashes 4
   ```

4. **Generate demo traps**
   ```bash
   python3 -m cli.trap_tools generate --out-dir traps_out --total-traps 1024 --bucket-log2 10 --base 0x1 --stride 2
   python3 -m cli.trap_tools index --traps-dir traps_out --shard-bits 8
   ```

5. **Schedule lanes**
   ```bash
   python3 -m cli.crt_tools schedule --L 0 --U 0x100000 --bits-per-mod 8 --mods 3 --workers 1 --lanes-per-worker 4 --out lanes.csv
   ```

6. **Run a worker** (toy configuration that locates the known Genesis target)
   ```bash
   python3 -m cli.run_worker \
       --backend coincurve \
       --seed 1337 --r 8 --base 1 \
       --lanes-csv lanes.csv --worker-id 0 \
       --traps-dir traps_out --bucket-hint-bits 8 \
       --bloom bloom.dat --m-bits 20 --k-hashes 4 --mapped-size 1<<20 \
       --target-rmd 751e76e8199196d454941c45d1b3a323f1433bd6 \
       --save SAVES.TXT --metrics worker.jsonl --steps-per-batch 1000
   ```

The worker prints progress metrics and writes candidate hits to `SAVES.TXT`. The demo operates on a 40-bit toy range in `scripts/demo_small_range.sh`.

## Usage

### End-to-end demo

A complete toy pipeline is available via:

```bash
make run-demo
```

This script wires together trap generation, index creation, Bloom filter
building and a single worker pass. It automatically exports the repository's
`src` directory on `PYTHONPATH`, so you can run it directly from the source tree
without first installing the package.

Artifacts are written to the repository root:

* `demo_traps/` – generated trap shards.
* `demo_lanes.csv` – CRT lane schedule for worker `0`.
* `demo_bloom.dat` – memory-mapped Bloom filter populated from
  `tests/data/sample_targets.json`.
* `demo_saves.txt` – candidate scalars that passed the verification stage.
* `demo_metrics.jsonl` – periodic worker metrics in JSON lines format.

The script now prints a short summary of the latest metrics flush so you can
see counters such as `steps`, `trap_hits`, and any accumulated timer buckets at
a glance. The full JSONL file remains available if you want to ingest the
metrics into other tooling.

### Manual invocation

The CLI modules can be called individually once dependencies are installed:

```bash
python3 -m cli.trap_tools generate --help
python3 -m cli.trap_tools index --help
python3 -m cli.trap_tools build-bloom --help
python3 -m cli.crt_tools schedule --help
python3 -m cli.run_worker --help
python3 -m cli.run_controller --help
```

Each command prints its supported arguments. To run the pipeline manually from
the source tree without installing the package, prepend `PYTHONPATH=src` to the
invocation, for example:

```bash
PYTHONPATH=src python3 -m cli.run_worker --help
```

## Low-value target example

The repository ships with a low-difficulty test target representing the Bitcoin
Genesis address RIPEMD-160 hash: `751e76e8199196d454941c45d1b3a323f1433bd6`. It
is stored in `tests/data/sample_targets.json` and used by the demo pipeline.

To probe the value explicitly with a worker, point the Bloom filter and target
flags at the JSON file:

```bash
PYTHONPATH=src python3 -m cli.run_worker \
    --backend coincurve --seed 1337 --r 8 --base 1 \
    --lanes-csv demo_lanes.csv --worker-id 0 \
    --traps-dir demo_traps --bucket-hint-bits 8 \
    --bloom demo_bloom.dat --m-bits 20 --k-hashes 4 --mapped-size $((1<<20)) \
    --target-rmd 751e76e8199196d454941c45d1b3a323f1433bd6 \
    --steps-per-batch 1000 --verbose
```

The worker reports any matches it observes and appends successful scalars to
`demo_saves.txt`, allowing you to sanity-check end-to-end behaviour against a
known low-value target before launching larger jobs.

### Scaling to larger ranges

The repository also includes helper scripts for heavier workloads:

* `scripts/gen_traps_10M.sh OUT_DIR` – generate and index a 10 million trap
  bundle suitable for 48-bit-scale experiments.
* `scripts/schedule_24k_cores.sh OUT_CSV` – emit a lane schedule covering
  24,000 workers with 16 lanes each (roughly 384k concurrent lanes).

To aim at a bigger target list, build a Bloom filter from your own JSON file of
RIPEMD-160 hashes, e.g. `python3 -m cli.trap_tools build-bloom --csv targets.json --out large.bloom --m-bits 28 --k-hashes 6`.
With the larger trap set and schedule generated above you can launch a worker by swapping the
artifact paths in the demo command line:

```bash
python3 -m cli.run_worker \
    --backend coincurve --seed 42 --r 8 --base 1 \
    --lanes-csv large_lanes.csv --worker-id 123 \
    --traps-dir large_traps --bucket-hint-bits 12 \
    --bloom large.bloom --m-bits 28 --k-hashes 6 --mapped-size $((1<<26)) \
    --target-rmd YOUR_TARGET_HASH --steps-per-batch 5000 --metrics large_metrics.jsonl
```

This mirrors the `make run-demo` flow but swaps in the higher-capacity trap and
schedule artifacts so you can exercise larger search spaces or cluster
deployments.

## CLI overview

* `python -m cli.trap_tools --help` — trap generation, sharded index building, and Bloom filter creation.
* `python -m cli.crt_tools --help` — CRT tiling utilities and lane scheduler.
* `python -m cli.run_worker --help` — probe worker with BSGSD stepping and filter cascade.
* `python -m cli.run_controller --help` — emit orchestration commands for clusters.

## Development

* Format & lint: `ruff check src tests`
* Run tests: `pytest`
* Demo pipeline: `make run-demo`

The codebase targets Python 3.11+, relies on `coincurve` (libsecp256k1) by default, and can fall back to an optional ICE shared object if available.
