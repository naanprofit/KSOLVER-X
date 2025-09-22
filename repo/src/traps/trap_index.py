"""Sharded trap index mapping tag prefixes to file offsets."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from .trapgen import RECORD_STRUCT

logger = logging.getLogger(__name__)


# Functions
# ---------
# - build_sharded_index
# - open_sharded_index
# - probe_tag1


def build_sharded_index(
    traps_dir: Path, shard_bits: int, *, dedupe: bool = False
) -> None:
    """Build text-based shard files for trap lookup.

    Parameters
    ----------
    traps_dir:
        Directory containing ``traps_*.bin`` files.
    shard_bits:
        Number of high-order tag bits used to form the shard identifier.
    dedupe:
        When ``True`` duplicate trap records (matching tag, bucket metadata and
        anchor fingerprint) are skipped while constructing the index. Dedupe is
        disabled by default to preserve legacy behaviour.
    """

    index_dir = traps_dir / "index"
    index_dir.mkdir(parents=True, exist_ok=True)
    shard_maps: dict[int, list[tuple[int, str, int]]] = {}
    total_records = 0
    unique_records = 0
    duplicates_dropped = 0
    # Using a ``set`` of tuples keeps the dedupe logic deterministic while
    # remaining reasonably compact compared to storing the original anchor.
    seen_records: set[tuple[int, int, int, int]] = set()

    for trap_file in sorted(traps_dir.glob("traps_*.bin")):
        with trap_file.open("rb") as fh:
            offset = 0
            while True:
                data = fh.read(RECORD_STRUCT.size)
                if not data:
                    break
                total_records += 1
                bucket_bytes, bucket_log2, tag1, tag2, _anchor = RECORD_STRUCT.unpack(data)
                bucket_start = int.from_bytes(bucket_bytes, "big")
                record_key = (tag1, bucket_start, bucket_log2, tag2)
                if dedupe:
                    if record_key in seen_records:
                        duplicates_dropped += 1
                        offset += RECORD_STRUCT.size
                        continue
                    seen_records.add(record_key)
                unique_records += 1
                shard = tag1 >> max(0, 64 - shard_bits)
                shard_maps.setdefault(shard, []).append((tag1, trap_file.name, offset))
                offset += RECORD_STRUCT.size

    for shard, rows in shard_maps.items():
        rows.sort(key=lambda row: (row[0], row[1], row[2]))
        shard_path = index_dir / f"shard_{shard:04x}.idx"
        with shard_path.open("w", encoding="utf8") as fh:
            for tag1, file_name, offset in rows:
                fh.write(f"{tag1:016x},{file_name},{offset}\n")

    meta = {
        "shard_bits": shard_bits,
        "total_records": total_records,
        "unique_records": unique_records,
        "duplicates_dropped": duplicates_dropped,
        "dedupe": dedupe,
        "shards": {
            f"{shard:04x}": len(rows) for shard, rows in sorted(shard_maps.items())
        },
    }
    (index_dir / "meta.json").write_text(json.dumps(meta), encoding="utf8")
    logger.info(
        "trap_index_built",
        extra={
            "shards": len(shard_maps),
            "shard_bits": shard_bits,
            "total_records": total_records,
            "duplicates_dropped": duplicates_dropped,
        },
    )


def open_sharded_index(traps_dir: Path) -> dict[str, object]:
    """Load the index into memory for quick lookups."""

    index_dir = traps_dir / "index"
    meta_path = index_dir / "meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(meta_path)
    shard_bits = int(json.loads(meta_path.read_text(encoding="utf8")).get("shard_bits", 0))
    shards: dict[int, list[tuple[int, Path, int]]] = {}
    for shard_file in sorted(index_dir.glob("shard_*.idx")):
        shard_hex = shard_file.stem.split("_")[1]
        shard = int(shard_hex, 16)
        entries: list[tuple[int, Path, int]] = []
        with shard_file.open("r", encoding="utf8") as fh:
            for line in fh:
                tag_hex, file_name, offset_str = line.strip().split(",")
                entries.append((int(tag_hex, 16), traps_dir / file_name, int(offset_str)))
        shards[shard] = entries
    return {"shard_bits": shard_bits, "shards": shards}


def probe_tag1(index: dict[str, object], tag1: int) -> list[tuple[Path, int]]:
    """Return candidate file offsets matching the provided tag1."""

    shard_bits = int(index.get("shard_bits", 0))
    shards = index.get("shards", {})
    assert isinstance(shards, dict)
    shard = tag1 >> max(0, 64 - shard_bits)
    matches = []
    for entry_tag, file_path, offset in shards.get(shard, []):
        if entry_tag == tag1:
            matches.append((file_path, offset))
    return matches


__all__ = ["build_sharded_index", "open_sharded_index", "probe_tag1"]
