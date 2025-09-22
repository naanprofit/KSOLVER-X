"""Trap generation and indexing CLI.

Examples:
  python -m cli.trap_tools generate \
      --out-dir traps --total-traps 1024 --bucket-log2 10 --base 0x1000 --stride 17
  python -m cli.trap_tools index --traps-dir traps --shard-bits 8
  python -m cli.trap_tools build-bloom \
      --csv tests/data/sample_targets.json --out bloom.dat --m-bits 20 --k-hashes 4
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from core.bloom import build_bloom_from_csv
from traps import trapgen
from traps.trap_index import build_sharded_index

logger = logging.getLogger(__name__)


def _parse_int(value: str) -> int:
    return int(value, 0)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Trap table tooling")
    sub = parser.add_subparsers(dest="cmd", required=True)

    gen = sub.add_parser("generate", help="Generate trap tables")
    gen.add_argument("--out-dir", type=Path, required=True)
    gen.add_argument("--total-traps", type=int, required=True)
    gen.add_argument("--bucket-log2", type=int, required=True)
    gen.add_argument("--base", type=_parse_int, required=True)
    gen.add_argument("--stride", type=_parse_int, required=True)
    gen.add_argument("--backend", default="coincurve")
    gen.add_argument("--jobs", type=int, default=1)

    idx = sub.add_parser("index", help="Build trap shard index")
    idx.add_argument("--traps-dir", type=Path, required=True)
    idx.add_argument("--shard-bits", type=int, default=12)
    idx.add_argument(
        "--dedupe",
        action="store_true",
        help="Skip duplicate trap anchors when building the shard index",
    )

    bloom_cmd = sub.add_parser("build-bloom", help="Build a Bloom filter from CSV")
    bloom_cmd.add_argument("--csv", type=Path, required=True)
    bloom_cmd.add_argument("--out", type=Path, required=True)
    bloom_cmd.add_argument("--m-bits", type=int, required=True)
    bloom_cmd.add_argument("--k-hashes", type=int, required=True)

    parser.add_argument("--verbose", action="store_true")

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    if args.cmd == "generate":
        trapgen.generate_traps(
            args.out_dir,
            args.total_traps,
            args.base,
            args.stride,
            args.bucket_log2,
            args.backend,
            args.jobs,
        )
    elif args.cmd == "index":
        build_sharded_index(args.traps_dir, args.shard_bits, dedupe=args.dedupe)
    elif args.cmd == "build-bloom":
        build_bloom_from_csv(args.csv, args.out, args.m_bits, args.k_hashes)
    else:  # pragma: no cover
        raise ValueError(args.cmd)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
