"""Cheap filter cascade to reduce expensive trap and Bloom lookups."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence

from core.secp_backend import apply_glv_negation

# Functions
# ---------
# - cheap_tag128
# - passes_bitplane
# - endomix_tag
# - apply_filter_cascade


def cheap_tag128(pub: bytes) -> tuple[int, int]:
    """Return a pair of 64-bit tags derived from BLAKE2b."""

    digest = hashlib.blake2b(pub, digest_size=16).digest()
    a = int.from_bytes(digest[:8], "big")
    b = int.from_bytes(digest[8:], "big")
    return a, b


def passes_bitplane(pub: bytes, masks: Sequence[int]) -> bool:
    """Return False if any bitplane mask rejects the point."""

    for i, mask in enumerate(masks):
        if i + 2 > len(pub):
            break
        chunk = int.from_bytes(pub[i : i + 2], "big")
        if chunk & mask:
            return False
    return True


def endomix_tag(pub: bytes, backend: str) -> tuple[int, int]:
    """Mix GLV and negation images into a simple tag pair."""

    glv, neg = apply_glv_negation(pub)
    digest = hashlib.blake2b(glv + neg, digest_size=16).digest()
    return int.from_bytes(digest[:8], "big"), int.from_bytes(digest[8:], "big")


def apply_filter_cascade(
    pub: bytes,
    backend: str = "coincurve",
    masks: Sequence[int] | None = None,
    use_cheap_tag: bool = True,
    use_endomix: bool = True,
) -> bool:
    """Run the full cascade returning True for likely matches."""

    if masks is None:
        masks = (0xFFF, 0xFFFF)
    if masks:
        if not passes_bitplane(pub, masks):
            return False
    if use_cheap_tag:
        tag_a, tag_b = cheap_tag128(pub)
        if (tag_a ^ tag_b) & 0xFFFF:
            return False
    if use_endomix and backend:
        end_a, end_b = endomix_tag(pub, backend)
        if (end_a ^ end_b) & 0xFF:
            return False
    return True


__all__ = ["cheap_tag128", "passes_bitplane", "endomix_tag", "apply_filter_cascade"]
