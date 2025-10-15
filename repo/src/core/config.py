"""Central configuration dataclasses for the KSOLVER-X pipeline."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

# Functions
# ---------
# - TrapConfig
# - CRTConfig
# - FilterConfig
# - BloomConfig
# - WorkerConfig
# - MetricsConfig
# - load_targets


@dataclass(slots=True)
class TrapConfig:
    """Configuration parameters used when generating and probing traps."""

    directory: Path
    bucket_log2: int
    shard_bits: int = 12
    backend: str = "coincurve"
    bucket_hint_bits: int = 12


@dataclass(slots=True)
class CRTConfig:
    """CRT tiling parameters for the deterministic lane scheduler."""

    lower: int
    upper: int
    bits_per_mod: int
    mod_count: int


@dataclass(slots=True)
class FilterConfig:
    """Parameters controlling the filter cascade."""

    bitplane_masks: Sequence[int] = (0xFFF, 0xFFFF)
    enable_cheap_tag: bool = True
    enable_endomix: bool = True
    enabled: bool = True


@dataclass(slots=True)
class BloomConfig:
    """Memory mapped Bloom filter configuration."""

    path: Path
    m_bits: int
    k_hashes: int
    mapped_size: int = 1 << 26


@dataclass(slots=True)
class MetricsConfig:
    """Metrics output paths and periodicity."""

    path: Path
    interval_steps: int = 100_000


@dataclass(slots=True)
class WorkerConfig:
    """Configuration bundle consumed by the probe worker."""

    backend: str
    seed: int
    r: int
    base: int
    dp_bits: int
    lanes: list[int]
    worker_id: int
    trap_config: TrapConfig
    bloom: BloomConfig | None
    filter_config: FilterConfig
    metrics: MetricsConfig | None
    target_rmd160: bytes | None = None
    target_address: str | None = None
    steps_per_batch: int = 100_000
    checkpoint_path: Path | None = None
    save_path: Path | None = None
    use_gpu: bool = False

    def lane_iter(self) -> Iterable[int]:
        """Yield lane identifiers in a deterministic order."""

        yield from self.lanes


def load_targets(path: Path) -> list[bytes]:
    """Load target RIPEMD-160 hashes from a JSON or newline-delimited file."""

    if not path.exists():
        raise FileNotFoundError(path)
    text = path.read_text().strip()
    if not text:
        return []
    if text.startswith("["):
        import json

        raw = json.loads(text)
    else:
        raw = [line.strip() for line in text.splitlines() if line.strip()]
    out: list[bytes] = []
    for item in raw:
        item_str = str(item).strip()
        if item_str.startswith("0x"):
            item_str = item_str[2:]
        out.append(bytes.fromhex(item_str))
    return out


__all__ = [
    "TrapConfig",
    "CRTConfig",
    "FilterConfig",
    "BloomConfig",
    "WorkerConfig",
    "MetricsConfig",
    "load_targets",
]
