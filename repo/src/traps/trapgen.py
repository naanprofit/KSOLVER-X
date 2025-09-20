"""Trap generation utilities for bucketized Fractal Rainbow Tables."""

from __future__ import annotations

import struct
from collections.abc import Iterable
from itertools import islice
from pathlib import Path

from xxhash import xxh64

from core.secp_backend import scalar_to_pubkey_compressed

RECORD_STRUCT = struct.Struct(">32sBQQ33s")


# Functions
# ---------
# - int_to_32b
# - fingerprint64
# - generate_trap_sequence
# - trap_entry
# - write_trap_file
# - generate_traps
# - build_index


def int_to_32b(i: int) -> bytes:
    """Serialize an integer to 32 big-endian bytes."""

    return i.to_bytes(32, "big")


def fingerprint64(b: bytes) -> int:
    """Return a 64-bit fingerprint using xxHash."""

    return xxh64(b).intdigest()


def generate_trap_sequence(base: int, stride: int, count: int) -> Iterable[int]:
    """Yield deterministic bucket starts for traps."""

    for idx in range(count):
        yield base + idx * stride


def trap_entry(bucket_start: int, bucket_log2: int, backend: str) -> dict:
    """Construct a dictionary representing a trap record."""

    anchor = scalar_to_pubkey_compressed(bucket_start, backend=backend)
    tag1 = fingerprint64(anchor)
    tag2 = fingerprint64(anchor[::-1])
    return {
        "bucket_start": bucket_start,
        "bucket_log2": bucket_log2,
        "tag1": tag1,
        "tag2": tag2,
        "anchor": anchor,
    }


def write_trap_file(path: Path, entries: Iterable[dict]) -> int:
    """Write traps to a binary file, returning the number of records."""

    count = 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        for entry in entries:
            record = RECORD_STRUCT.pack(
                int_to_32b(entry["bucket_start"]),
                entry["bucket_log2"],
                entry["tag1"],
                entry["tag2"],
                entry["anchor"],
            )
            fh.write(record)
            count += 1
    return count


def generate_traps(
    out_dir: Path,
    total_traps: int,
    base: int,
    stride: int,
    bucket_log2: int,
    backend: str,
    jobs: int = 1,
) -> None:
    """Generate traps and store them in sequentially numbered files."""

    out_dir.mkdir(parents=True, exist_ok=True)
    per_file = max(1, total_traps // max(1, jobs))
    seq = generate_trap_sequence(base, stride, total_traps)
    for shard, offset in enumerate(range(0, total_traps, per_file)):
        shard_count = min(per_file, total_traps - offset)
        entries = (
            trap_entry(bucket_start, bucket_log2, backend=backend)
            for bucket_start in islice(seq, shard_count)
        )
        path = out_dir / f"traps_{shard:04d}.bin"
        write_trap_file(path, entries)


def build_index(out_dir: Path, shard_bits: int = 12) -> None:
    """Build a sharded index alongside the generated traps."""

    from .trap_index import build_sharded_index

    build_sharded_index(out_dir, shard_bits)


__all__ = [
    "int_to_32b",
    "fingerprint64",
    "generate_trap_sequence",
    "trap_entry",
    "write_trap_file",
    "generate_traps",
    "build_index",
]
