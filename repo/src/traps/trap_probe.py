"""Trap probing utilities combining tag checks and bucket hints."""

from __future__ import annotations

from pathlib import Path

from .trapgen import RECORD_STRUCT, fingerprint64

# Functions
# ---------
# - pubkey_tags
# - probe_traps


def pubkey_tags(pub: bytes) -> tuple[int, int]:
    """Return (tag1, tag2) pairs matching the trap format."""

    return fingerprint64(pub), fingerprint64(pub[::-1])


def probe_traps(
    pub: bytes,
    traps_dir: Path,
    index: dict[str, object],
    bucket_hint_bits: int,
) -> list[tuple[int, int]]:
    """Return candidate (bucket_start, bucket_log2) matches."""

    tag1, tag2 = pubkey_tags(pub)
    pub_fp = fingerprint64(pub)
    candidates = []
    for file_path, offset in probe_tag1(index, tag1):  # type: ignore[name-defined]
        with file_path.open("rb") as fh:
            fh.seek(offset)
            data = fh.read(RECORD_STRUCT.size)
            if not data:
                continue
            bucket_bytes, bucket_log2, file_tag1, file_tag2, anchor = RECORD_STRUCT.unpack(data)
            if file_tag2 != tag2:
                continue
            bucket_start = int.from_bytes(bucket_bytes, "big")
            if bucket_hint_bits:
                bits = max(0, 64 - bucket_hint_bits)
                anchor_fp = fingerprint64(anchor)
                if (pub_fp >> bits) != (anchor_fp >> bits):
                    continue
            candidates.append((bucket_start, bucket_log2))
    return candidates


from .trap_index import probe_tag1  # noqa: E402  (avoid circular import)

__all__ = ["pubkey_tags", "probe_traps"]
