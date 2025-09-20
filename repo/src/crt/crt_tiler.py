"""CRT tiler providing deterministic residue lanes."""

from __future__ import annotations

from collections.abc import Iterable
from math import prod

from sympy import nextprime

# Functions
# ---------
# - build_moduli_list
# - product
# - lane_iterator
# - residue_enumerator
# - lane_key


def build_moduli_list(bits_per_mod: int, count: int) -> list[int]:
    """Return a list of distinct primes close to the requested bit size."""

    start = 1 << (bits_per_mod - 1)
    primes: list[int] = []
    candidate = start | 1
    while len(primes) < count:
        candidate = int(nextprime(candidate))
        primes.append(candidate)
        candidate += 2
    return primes


def product(values: Iterable[int]) -> int:
    """Return the multiplicative product of an iterable."""

    return prod(values)


def _crt(moduli: list[int], residues: list[int]) -> int:
    modulus = product(moduli)
    x = 0
    for m_i, r_i in zip(moduli, residues, strict=False):
        M_i = modulus // m_i
        inv = pow(M_i, -1, m_i)
        x = (x + r_i * M_i * inv) % modulus
    return x


def lane_iterator(L: int, U: int, moduli: list[int], residues: list[int]) -> Iterable[int]:
    """Yield scalars in [L, U) matching the given CRT residues."""

    base = _crt(moduli, residues)
    modulus = product(moduli)
    if base < L:
        delta = L - base
        base += ((delta + modulus - 1) // modulus) * modulus
    for value in range(base, U, modulus):
        if value >= U:
            break
        yield value


def residue_enumerator(moduli: list[int], limit: int | None = None) -> list[int]:
    """Return lane identifiers in mixed radix order."""

    total = product(moduli)
    limit = total if limit is None else min(limit, total)
    return list(range(limit))


def lane_key(d: int, moduli: list[int]) -> int:
    """Return the mixed radix lane identifier for a scalar."""

    key = 0
    factor = 1
    for mod in moduli:
        key += (d % mod) * factor
        factor *= mod
    return key


__all__ = ["build_moduli_list", "product", "lane_iterator", "residue_enumerator", "lane_key"]
