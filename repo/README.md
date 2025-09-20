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

2. **Create a Bloom filter** (using sample targets)
   ```bash
   python3 -m cli.trap_tools build-bloom --csv tests/data/sample_targets.json --out bloom.dat --m-bits 20 --k-hashes 4
   ```

3. **Generate demo traps**
   ```bash
   python3 -m cli.trap_tools generate --out-dir traps_out --total-traps 1024 --bucket-log2 10 --base 0x1 --stride 2
   python3 -m cli.trap_tools index --traps-dir traps_out --shard-bits 8
   ```

4. **Schedule lanes**
   ```bash
   python3 -m cli.crt_tools schedule --L 0 --U 0x100000 --bits-per-mod 8 --mods 3 --workers 1 --lanes-per-worker 4 --out lanes.csv
   ```

5. **Run a worker** (toy configuration that locates the known Genesis target)
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
