"""CRT tiling and lane scheduling CLI.

Examples:
  python -m cli.crt_tools moduli --bits-per-mod 8 --count 3
  python -m cli.crt_tools schedule \
      --L 0 --U 0x10000 --bits-per-mod 8 --mods 3 --workers 4 \
      --lanes-per-worker 2 --out lanes.csv
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from crt import crt_tiler, lane_scheduler

logger = logging.getLogger(__name__)


def _parse_int(value: str) -> int:
    return int(value, 0)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CRT tiling tools")
    sub = parser.add_subparsers(dest="cmd", required=True)

    mod_cmd = sub.add_parser("moduli", help="Generate primes for CRT tiling")
    mod_cmd.add_argument("--bits-per-mod", type=int, required=True)
    mod_cmd.add_argument("--count", type=int, required=True)

    sched = sub.add_parser("schedule", help="Emit lane schedule CSV")
    sched.add_argument("--L", type=_parse_int, required=True)
    sched.add_argument("--U", type=_parse_int, required=True)
    sched.add_argument("--bits-per-mod", type=int, required=True)
    sched.add_argument("--mods", type=int, required=True)
    sched.add_argument("--workers", type=int, required=True)
    sched.add_argument("--lanes-per-worker", type=int, required=True)
    sched.add_argument("--out", type=Path, required=True)

    parser.add_argument("--verbose", action="store_true")

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    if args.cmd == "moduli":
        primes = crt_tiler.build_moduli_list(args.bits_per_mod, args.count)
        print(" ".join(str(p) for p in primes))
    elif args.cmd == "schedule":
        moduli = crt_tiler.build_moduli_list(args.bits_per_mod, args.mods)
        lanes = crt_tiler.residue_enumerator(moduli)
        limit = args.workers * args.lanes_per_worker
        lanes = lanes[:limit]
        mapping = lane_scheduler.assign_lanes(lanes, args.workers, args.lanes_per_worker)
        lane_scheduler.emit_schedule_csv(mapping, args.out)
    else:  # pragma: no cover
        raise ValueError(args.cmd)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
