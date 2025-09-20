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
