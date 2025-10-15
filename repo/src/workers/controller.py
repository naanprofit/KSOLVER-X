"""Controller helpers for orchestrating probe workers."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


# Functions
# ---------
# - build_worker_commands
# - main


def build_worker_commands(workers: int, lanes_path: Path, template: str) -> list[str]:
    """Construct shell commands for all workers."""

    commands = []
    for worker_id in range(workers):
        args = f"--worker-id {worker_id} --lanes-csv {lanes_path}"
        commands.append(template.format(args=args))
    return commands


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate worker launch commands")
    parser.add_argument("--workers", type=int, required=True)
    parser.add_argument("--lanes", type=Path, required=True)
    parser.add_argument("--template", type=str, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    commands = build_worker_commands(args.workers, args.lanes, args.template)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(commands) + "\n", encoding="utf8")
    logger.info("controller_commands_written", extra={"count": len(commands), "out": str(args.out)})
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
