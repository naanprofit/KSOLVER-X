from __future__ import annotations

import json

from core import bloom


def test_murmurhash3_fallback_known_vectors(monkeypatch) -> None:
    """Ensure the pure Python fallback matches reference values."""

    monkeypatch.setattr(bloom, "_murmurhash3_x86_32_native", None)
    assert bloom._murmurhash3_x86_32(b"hello", seed=0, signed=False) == 0x248BFA47
    assert bloom._murmurhash3_x86_32(b"", seed=0, signed=False) == 0x0
    assert bloom._murmurhash3_x86_32(b"abc", seed=123, signed=False) == 0x1B7C6698


def test_build_bloom_from_json(tmp_path, monkeypatch) -> None:
    """Building a Bloom filter from JSON works even without the C extension."""

    monkeypatch.setattr(bloom, "_murmurhash3_x86_32_native", None)
    targets = [
        "751e76e8199196d454941c45d1b3a323f1433bd6",
        "0000000000000000000000000000000000000001",
    ]
    json_path = tmp_path / "targets.json"
    json_path.write_text(json.dumps(targets), encoding="utf8")
    bloom_path = tmp_path / "bloom.dat"

    bloom.build_bloom_from_csv(json_path, bloom_path, m_bits=64, k_hashes=3)

    with bloom.MMapBloom(bloom_path, m_bits=64, k_hashes=3) as filter_:
        for target in targets:
            assert filter_.contains(bytes.fromhex(target))
        assert not filter_.contains(bytes.fromhex("ffffffffffffffffffffffffffffffffffffffff"))


def test_bloom_reopen_with_larger_mapping(tmp_path, monkeypatch) -> None:
    """Opening an existing Bloom filter with a larger mapping size extends the file."""

    monkeypatch.setattr(bloom, "_murmurhash3_x86_32_native", None)
    bloom_path = tmp_path / "filter.dat"
    with bloom.MMapBloom(bloom_path, m_bits=32, k_hashes=2) as filter_:
        filter_.add(b"abc")

    # Reopen with a larger mapping size; this previously raised ValueError.
    with bloom.MMapBloom(bloom_path, m_bits=32, k_hashes=2, mapped_size=1 << 12) as filter_:
        assert filter_.contains(b"abc")
