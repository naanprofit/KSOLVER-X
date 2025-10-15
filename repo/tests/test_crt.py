from crt import crt_tiler, lane_scheduler


def test_build_moduli_and_product():
    mods = crt_tiler.build_moduli_list(5, 3)
    assert len(mods) == 3
    assert all(mod.bit_length() >= 5 for mod in mods)
    prod = crt_tiler.product(mods)
    assert prod == mods[0] * mods[1] * mods[2]


def test_lane_iterator():
    moduli = [3, 5]
    residues = [1, 2]
    values = list(crt_tiler.lane_iterator(0, 100, moduli, residues))
    for v in values:
        assert v % 3 == 1
        assert v % 5 == 2
    lanes = crt_tiler.residue_enumerator(moduli, limit=4)
    assert lanes == [0, 1, 2, 3]


def test_lane_scheduler_assignments(tmp_path):
    lanes = [0, 1, 2, 3]
    mapping = lane_scheduler.assign_lanes(lanes, workers=2, lanes_per_worker=2)
    assert mapping[0] == [0, 1]
    assert mapping[1] == [2, 3]
    out = tmp_path / "lanes.csv"
    lane_scheduler.emit_schedule_csv(mapping, out)
    assert out.read_text().strip().splitlines()[1] == "0,0"


def test_lane_key_roundtrip():
    moduli = [3, 5, 7]
    value = 123
    key = crt_tiler.lane_key(value, moduli)
    residues = [
        key % moduli[0],
        (key // moduli[0]) % moduli[1],
        (key // (moduli[0] * moduli[1])) % moduli[2],
    ]
    val = list(crt_tiler.lane_iterator(0, 1000, moduli, residues))[0]
    assert val % moduli[0] == value % moduli[0]
