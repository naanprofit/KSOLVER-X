from core.secp_backend import scalar_to_pubkey_compressed
from filters import apply_filter_cascade, cheap_tag128, endomix_tag, passes_bitplane


def test_filters_basic():
    pub = scalar_to_pubkey_compressed(2)
    tag_a, tag_b = cheap_tag128(pub)
    assert tag_a != tag_b
    assert passes_bitplane(pub, [0])
    end_a, end_b = endomix_tag(pub, "coincurve")
    assert end_a != 0
    assert apply_filter_cascade(pub, backend="coincurve") in {True, False}


def test_filter_cascade_can_be_disabled():
    pub = scalar_to_pubkey_compressed(1)
    assert not apply_filter_cascade(pub, backend="coincurve")
    assert apply_filter_cascade(
        pub,
        backend="coincurve",
        masks=(),
        use_cheap_tag=False,
        use_endomix=False,
    )
