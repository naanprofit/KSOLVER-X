"""Memory-mapped Bloom filter with deterministic hashing."""

from __future__ import annotations

import csv
import json
import logging
import mmap
from collections.abc import Iterable
from pathlib import Path

from xxhash import xxh64

try:  # pragma: no cover - exercised in fallback tests
    from murmurhash3 import murmurhash3_x86_32 as _murmurhash3_x86_32_native
except ModuleNotFoundError:  # pragma: no cover - handled by runtime fallback
    _murmurhash3_x86_32_native = None


def _rotl32(x: int, r: int) -> int:
    """Rotate a 32-bit integer left by ``r`` bits."""

    x &= 0xFFFFFFFF
    return ((x << r) & 0xFFFFFFFF) | (x >> (32 - r))


def _murmurhash3_x86_32_fallback(
    data: bytes | bytearray | memoryview, seed: int = 0, *, signed: bool = False
) -> int:
    """Pure-Python MurmurHash3 implementation used when the C extension is absent."""

    if isinstance(data, str):  # defensive: callers always pass bytes
        data = data.encode("utf8")
    view = memoryview(bytes(data))
    length = len(view)

    c1 = 0xCC9E2D51
    c2 = 0x1B873593
    h1 = seed & 0xFFFFFFFF

    # Body
    nblocks = length // 4
    for offset in range(0, nblocks * 4, 4):
        k1 = (
            view[offset]
            | (view[offset + 1] << 8)
            | (view[offset + 2] << 16)
            | (view[offset + 3] << 24)
        )
        k1 = (k1 * c1) & 0xFFFFFFFF
        k1 = _rotl32(k1, 15)
        k1 = (k1 * c2) & 0xFFFFFFFF

        h1 ^= k1
        h1 = _rotl32(h1, 13)
        h1 = (h1 * 5 + 0xE6546B64) & 0xFFFFFFFF

    # Tail
    k1 = 0
    tail = view[nblocks * 4 :]
    if len(tail) >= 3:
        k1 ^= tail[2] << 16
    if len(tail) >= 2:
        k1 ^= tail[1] << 8
    if len(tail) >= 1:
        k1 ^= tail[0]
        k1 = (k1 * c1) & 0xFFFFFFFF
        k1 = _rotl32(k1, 15)
        k1 = (k1 * c2) & 0xFFFFFFFF
        h1 ^= k1

    # Finalisation
    h1 ^= length
    h1 &= 0xFFFFFFFF
    h1 ^= h1 >> 16
    h1 = (h1 * 0x85EBCA6B) & 0xFFFFFFFF
    h1 ^= h1 >> 13
    h1 = (h1 * 0xC2B2AE35) & 0xFFFFFFFF
    h1 ^= h1 >> 16

    if signed and h1 & 0x80000000:
        return h1 - (1 << 32)
    return h1


def _murmurhash3_x86_32(data: bytes, seed: int = 0, *, signed: bool = False) -> int:
    """Dispatch to the native MurmurHash3 or fallback implementation."""

    if _murmurhash3_x86_32_native is not None:
        return _murmurhash3_x86_32_native(data, seed, signed=signed)
    return _murmurhash3_x86_32_fallback(data, seed=seed, signed=signed)

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
        current_size = self._fh.seek(0, 2)
        if current_size < mapped_size:
            self._fh.truncate(mapped_size)
        self._fh.seek(0)
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
        h2 = _murmurhash3_x86_32(data, 0, signed=False)
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
