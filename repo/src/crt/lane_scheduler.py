"""Lane scheduler distributing CRT residue lanes across workers."""

from __future__ import annotations

import csv
from pathlib import Path

# Functions
# ---------
# - assign_lanes
# - emit_schedule_csv


def assign_lanes(lanes: list[int], workers: int, lanes_per_worker: int) -> dict[int, list[int]]:
    """Evenly distribute lanes among workers."""

    mapping: dict[int, list[int]] = {idx: [] for idx in range(workers)}
    worker = 0
    for lane in lanes:
        mapping[worker].append(lane)
        if len(mapping[worker]) >= lanes_per_worker:
            worker = (worker + 1) % workers
    return mapping


def emit_schedule_csv(mapping: dict[int, list[int]], out_path: Path) -> None:
    """Write worker to lane assignments as CSV."""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["worker_id", "lane"])
        for worker, lanes in mapping.items():
            for lane in lanes:
                writer.writerow([worker, lane])


__all__ = ["assign_lanes", "emit_schedule_csv"]
