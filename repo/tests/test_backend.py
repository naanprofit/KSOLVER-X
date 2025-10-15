from core.secp_backend import apply_glv_negation, hash160, scalar_to_pubkey_compressed


def test_scalar_to_pubkey_and_hash():
    pub = scalar_to_pubkey_compressed(1)
    assert pub.hex() == "0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798"
    digest = hash160(pub)
    assert digest.hex() == "751e76e8199196d454941c45d1b3a323f1433bd6"


def test_glv_negation_distinct():
    pub = scalar_to_pubkey_compressed(5)
    glv, neg = apply_glv_negation(pub)
    assert glv != pub
    assert neg != pub
    assert len(glv) == 33
    assert len(neg) == 33
