"""Deterministic stepping inspired by the BSGSD random walk."""

from __future__ import annotations

import random

from coincurve import utils

# Functions
# ---------
# - step_params_from_seed
# - next_scalar


def step_params_from_seed(seed: int, r: int, base: int) -> dict[str, object]:
    """Build a jump table used by the stepping function."""

    order = utils.GROUP_ORDER_INT
    rng = random.Random(seed)
    jumps: list[int] = []
    acc = pow(base % order, seed % order, order)
    for _ in range(max(2, r)):
        tweak = rng.randrange(1, order)
        jump = (acc + tweak) % order
        jumps.append(jump)
        acc = (acc * base) % order
    mask = (1 << (len(jumps).bit_length())) - 1
    return {"jumps": jumps, "mask": mask, "order": order}


def next_scalar(d: int, params: dict[str, object]) -> int:
    """Return the next scalar using the deterministic jump table."""

    order = params["order"]
    jumps = params["jumps"]
    mask = params["mask"]
    idx = d & mask
    jump = jumps[idx % len(jumps)]
    return (d + jump) % order


__all__ = ["step_params_from_seed", "next_scalar"]
