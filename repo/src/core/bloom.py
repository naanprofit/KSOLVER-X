"""Memory-mapped Bloom filter with deterministic hashing."""

from __future__ import annotations

import csv
import json
import logging
import mmap
from collections.abc import Iterable
from pathlib import Path

from murmurhash3 import murmurhash3_x86_32
from xxhash import xxh64

logger = logging.getLogger(__name__)


# Functions
# ---------
# - MMapBloom
# - build_bloom_from_csv


class MMapBloom:
    """Memory-mapped Bloom filter supporting concurrent read access."""

    def __init__(
        self, path: Path, m_bits: int, k_hashes: int, mapped_size: int | None = None
    ) -> None:
        self.path = path
        self.m_bits = m_bits
        self.k_hashes = k_hashes
        self.m_bytes = (m_bits + 7) // 8
        mapped_size = self.m_bytes if mapped_size is None else max(mapped_size, self.m_bytes)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            with path.open("wb") as fh:
                fh.truncate(mapped_size)
        self._fh = path.open("r+b")
        self._mm = mmap.mmap(self._fh.fileno(), mapped_size)
        logger.info(
            "bloom_open",
            extra={"path": str(path), "m_bits": m_bits, "k": k_hashes, "size": mapped_size},
        )

    def close(self) -> None:
        self._mm.flush()
        self._mm.close()
        self._fh.close()

    def __enter__(self) -> MMapBloom:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _hashes(self, data: bytes) -> Iterable[int]:
        h1 = xxh64(data).intdigest()
        h2 = murmurhash3_x86_32(data, 0, signed=False)
        for i in range(self.k_hashes):
            yield (h1 + i * h2) % self.m_bits

    def add(self, data: bytes) -> None:
        for bit in self._hashes(data):
            byte_index = bit // 8
            bit_index = bit % 8
            current = self._mm[byte_index]
            self._mm[byte_index] = current | (1 << bit_index)

    def contains(self, data: bytes) -> bool:
        for bit in self._hashes(data):
            byte_index = bit // 8
            bit_index = bit % 8
            if not (self._mm[byte_index] & (1 << bit_index)):
                return False
        return True


def build_bloom_from_csv(csv_path: Path, output: Path, m_bits: int, k_hashes: int) -> None:
    """Build a Bloom filter from a CSV containing hex hashes."""

    with MMapBloom(output, m_bits=m_bits, k_hashes=k_hashes) as bloom:
        if csv_path.suffix.lower() == ".json":
            raw = json.loads(csv_path.read_text(encoding="utf8"))
            rows = ((str(item),) for item in raw)
            for row in rows:
                value = str(row[0]).strip()
                if value.startswith("0x"):
                    value = value[2:]
                bloom.add(bytes.fromhex(value))
        else:
            with csv_path.open("r", encoding="utf8") as fh:
                reader = csv.reader(fh)
                for row in reader:
                    if not row:
                        continue
                    value = str(row[0]).strip()
                    if value.startswith("0x"):
                        value = value[2:]
                    bloom.add(bytes.fromhex(value))
    logger.info("bloom_build_complete", extra={"path": str(output)})


__all__ = ["MMapBloom", "build_bloom_from_csv"]
