"""ECDLP secp256k1 backend support leveraging coincurve and optional ICE bindings."""

from __future__ import annotations

import ctypes
import hashlib
import logging
from functools import lru_cache
from pathlib import Path

from coincurve import PrivateKey, PublicKey, utils

logger = logging.getLogger(__name__)

P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F


# Functions
# ---------
# - scalar_to_pubkey_compressed
# - hash160
# - apply_glv_negation


class _IceBackend:
    """Thin ctypes shim around the optional ICE shared object."""

    def __init__(self, path: Path) -> None:
        self.lib = ctypes.CDLL(str(path))
        self.lib.ice_scalar_to_pubkey.argtypes = [ctypes.c_uint64 * 4, ctypes.c_uint8 * 33]
        self.lib.ice_scalar_to_pubkey.restype = ctypes.c_int

    def scalar_to_pubkey(self, d: int) -> bytes:
        limbs = (ctypes.c_uint64 * 4)()
        for i in range(4):
            limbs[3 - i] = (d >> (64 * i)) & ((1 << 64) - 1)
        out = (ctypes.c_uint8 * 33)()
        rc = self.lib.ice_scalar_to_pubkey(limbs, out)
        if rc != 1:
            raise RuntimeError("ice backend failed to produce pubkey")
        return bytes(out)


@lru_cache(maxsize=1)
def _load_ice_backend() -> _IceBackend | None:
    candidates = [
        Path("ice_secp256k1.so"),
        Path(__file__).resolve().parent.parent.parent / "ice_secp256k1.so",
    ]
    for cand in candidates:
        if cand.exists():
            try:
                return _IceBackend(cand)
            except OSError as exc:  # pragma: no cover - depends on external lib
                logger.warning("failed_loading_ice", extra={"error": str(exc)})
    return None


@lru_cache(maxsize=1)
def _glv_beta() -> int:
    candidate = pow(2, (P - 1) // 3, P)
    if candidate == 1:
        candidate = pow(5, (P - 1) // 3, P)
    return candidate


def _decompress(pubkey_compressed: bytes) -> tuple[int, int]:
    pub = PublicKey(pubkey_compressed)
    uncompressed = pub.format(compressed=False)
    x = int.from_bytes(uncompressed[1:33], "big")
    y = int.from_bytes(uncompressed[33:], "big")
    return x, y


def _compress(x: int, y: int) -> bytes:
    prefix = 2 | (y & 1)
    return prefix.to_bytes(1, "big") + x.to_bytes(32, "big")


def scalar_to_pubkey_compressed(d: int, backend: str = "coincurve") -> bytes:
    """Return the compressed public key for the given scalar."""

    if d <= 0:
        raise ValueError("scalar must be positive")
    if backend == "ice":
        ice = _load_ice_backend()
        if ice is not None:
            return ice.scalar_to_pubkey(d)
        logger.info("ice_backend_unavailable_falling_back")
    order = utils.GROUP_ORDER_INT
    secret = d % order
    if secret == 0:
        secret = order
    priv = PrivateKey.from_int(secret)
    return priv.public_key.format(compressed=True)


def hash160(pubkey_compressed: bytes) -> bytes:
    """Compute HASH160 (SHA256 + RIPEMD160) of the public key."""

    sha = hashlib.sha256(pubkey_compressed).digest()
    ripe = hashlib.new("ripemd160", sha).digest()
    return ripe


def apply_glv_negation(pubkey_compressed: bytes) -> tuple[bytes, bytes]:
    """Return the GLV endomorphism image and the negation of a point."""

    x, y = _decompress(pubkey_compressed)
    beta = _glv_beta()
    x_glv = (x * beta) % P
    glv_pub = _compress(x_glv, y)
    y_neg = (-y) % P
    neg_pub = _compress(x, y_neg)
    return glv_pub, neg_pub


__all__ = [
    "scalar_to_pubkey_compressed",
    "hash160",
    "apply_glv_negation",
]
