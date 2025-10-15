from core.verify import pubkey_to_address, verify_address_match, verify_rmd160_match

TARGET_HASH = bytes.fromhex("751e76e8199196d454941c45d1b3a323f1433bd6")
TARGET_ADDRESS = "1BgGZ9tcN4rm9KBzDn7KprQz87SZ26SAMH"


def test_verify_rmd160_match():
    assert verify_rmd160_match(1, TARGET_HASH)


def test_verify_address_match():
    assert verify_address_match(1, TARGET_ADDRESS)


def test_pubkey_to_address_roundtrip():
    from core.secp_backend import scalar_to_pubkey_compressed

    pub = scalar_to_pubkey_compressed(1)
    assert pubkey_to_address(pub) == TARGET_ADDRESS
