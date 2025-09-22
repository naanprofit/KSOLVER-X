import json

from core.secp_backend import scalar_to_pubkey_compressed
from traps import trapgen
from traps.trap_index import build_sharded_index, open_sharded_index, probe_tag1
from traps.trap_probe import probe_traps


def test_trap_generation_and_index(tmp_path):
    out_dir = tmp_path / "traps"
    trapgen.generate_traps(
        out_dir,
        total_traps=4,
        base=1,
        stride=2,
        bucket_log2=4,
        backend="coincurve",
    )
    build_sharded_index(out_dir, shard_bits=4)
    index = open_sharded_index(out_dir)
    assert index["shards"]
    pub = scalar_to_pubkey_compressed(1)
    hits = probe_traps(pub, out_dir, index, bucket_hint_bits=4)
    assert hits
    tag1 = trapgen.fingerprint64(pub)
    locations = probe_tag1(index, tag1)
    assert locations


def test_index_dedupe_and_metadata(tmp_path):
    out_dir = tmp_path / "traps"
    out_dir.mkdir()

    entry_a = trapgen.trap_entry(1, bucket_log2=4, backend="coincurve")
    entry_b = trapgen.trap_entry(3, bucket_log2=4, backend="coincurve")

    trapgen.write_trap_file(out_dir / "traps_0000.bin", [entry_b, entry_a, entry_a])

    build_sharded_index(out_dir, shard_bits=4, dedupe=True)

    index_dir = out_dir / "index"
    meta = json.loads((index_dir / "meta.json").read_text(encoding="utf8"))
    assert meta["dedupe"] is True
    assert meta["total_records"] == 3
    assert meta["unique_records"] == 2
    assert meta["duplicates_dropped"] == 1
    assert meta["shards"]

    shard_file = next(index_dir.glob("shard_*.idx"))
    tags = []
    with shard_file.open("r", encoding="utf8") as fh:
        for line in fh:
            tag_hex, *_ = line.strip().split(",")
            tags.append(int(tag_hex, 16))
    assert tags == sorted(tags)

    index = open_sharded_index(out_dir)
    assert probe_tag1(index, entry_a["tag1"])  # dedupe keeps one location
    assert probe_tag1(index, entry_b["tag1"])  # unique entry preserved
