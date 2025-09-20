"""Verification helpers ensuring candidate scalars satisfy target conditions."""

from __future__ import annotations

import hashlib
import logging

from .secp_backend import hash160, scalar_to_pubkey_compressed

logger = logging.getLogger(__name__)


# Functions
# ---------
# - pubkey_to_address
# - verify_rmd160_match
# - verify_address_match


_B58_ALPHABET = b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _b58encode(data: bytes) -> str:
    n = int.from_bytes(data, "big")
    out = bytearray()
    while n:
        n, rem = divmod(n, 58)
        out.append(_B58_ALPHABET[rem])
    for b in data:
        if b == 0:
            out.append(_B58_ALPHABET[0])
        else:
            break
    return bytes(reversed(out)).decode("ascii")


def _checksum(payload: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]


def pubkey_to_address(pub: bytes) -> str:
    """Return the legacy P2PKH base58-check encoded address for a compressed pubkey."""

    payload = b"\x00" + hash160(pub)
    checksum = _checksum(payload)
    return _b58encode(payload + checksum)


def verify_rmd160_match(d: int, target_rmd: bytes, backend: str = "coincurve") -> bool:
    """Verify that a private scalar's HASH160 matches the target."""

    pub = scalar_to_pubkey_compressed(d, backend=backend)
    computed = hash160(pub)
    match = computed == target_rmd
    logger.debug("verify_rmd160", extra={"match": match})
    return match


def verify_address_match(d: int, address: str, backend: str = "coincurve") -> bool:
    """Verify that a private scalar yields the requested base58 address."""

    pub = scalar_to_pubkey_compressed(d, backend=backend)
    addr = pubkey_to_address(pub)
    match = addr == address
    logger.debug("verify_address", extra={"match": match})
    return match


__all__ = ["verify_rmd160_match", "verify_address_match", "pubkey_to_address"]
