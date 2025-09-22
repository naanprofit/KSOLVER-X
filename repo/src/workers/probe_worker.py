"""Probe worker implementing the distributed search loop."""

from __future__ import annotations

import argparse
import json
import logging
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from core import bloom, bsgsd_steps, config, metrics, verify
from core.secp_backend import hash160, scalar_to_pubkey_compressed
from filters import apply_filter_cascade
from traps.trap_index import open_sharded_index
from traps.trap_probe import probe_traps

logger = logging.getLogger(__name__)

_LANES_PATH: Path | None = None


# Functions
# ---------
# - set_schedule_source
# - load_schedule
# - search_lane
# - maybe_checkpoint
# - emit_metrics


@dataclass(slots=True)
class WorkerContext:
    """State carried across the worker search loop."""

    cfg: config.WorkerConfig
    trap_index: dict[str, object]
    bloom: bloom.MMapBloom | None
    metrics: metrics.MetricsState | None
    step_params: dict[str, object]
    current_scalar: int
    lane_id: int
    step_counter: int = 0
    last_checkpoint: float = field(default_factory=time.time)


def set_schedule_source(path: Path) -> None:
    global _LANES_PATH
    _LANES_PATH = path


def load_schedule(row_filter: Callable[[int, int], bool]) -> list[int]:
    """Load lane identifiers filtered by a predicate."""

    if _LANES_PATH is None:
        raise RuntimeError("schedule source not configured")
    lanes: list[int] = []
    with _LANES_PATH.open("r", encoding="utf8") as fh:
        next(fh, None)
        for line in fh:
            if not line.strip():
                continue
            worker_str, lane_str = line.strip().split(",")
            worker = int(worker_str, 0)
            lane = int(lane_str, 0)
            if row_filter(worker, lane):
                lanes.append(lane)
    return lanes


def maybe_checkpoint(ctx: WorkerContext) -> None:
    """Persist progress if requested."""

    if ctx.cfg.checkpoint_path is None:
        return
    now = time.time()
    if now - ctx.last_checkpoint < 5.0:
        return
    payload = {
        "lane": ctx.lane_id,
        "scalar": ctx.current_scalar,
        "step_counter": ctx.step_counter,
    }
    ctx.cfg.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    ctx.cfg.checkpoint_path.write_text(json.dumps(payload), encoding="utf8")
    ctx.last_checkpoint = now
    logger.info("checkpoint_written", extra=payload)


def emit_metrics(ctx: WorkerContext) -> None:
    """Flush metrics to disk if configured."""

    if ctx.metrics is None:
        return
    metrics.flush_metrics(ctx.metrics)


def _handle_candidate(ctx: WorkerContext, candidate: int) -> None:
    backend = ctx.cfg.backend
    match = False
    if ctx.cfg.target_rmd160:
        if verify.verify_rmd160_match(
            candidate, ctx.cfg.target_rmd160, backend
        ):
            match = True
    if ctx.cfg.target_address:
        if verify.verify_address_match(
            candidate, ctx.cfg.target_address, backend
        ):
            match = True
    if match:
        logger.info("target_found", extra={"scalar": candidate})
        if ctx.cfg.save_path is not None:
            ctx.cfg.save_path.parent.mkdir(parents=True, exist_ok=True)
            with ctx.cfg.save_path.open("a", encoding="utf8") as fh:
                fh.write(f"{candidate}\n")


def search_lane(d0: int, params: dict[str, object], ctx: WorkerContext) -> None:
    """Search a single lane starting from d0."""

    backend = ctx.cfg.backend
    filter_cfg = ctx.cfg.filter_config
    filter_enabled = True
    filter_masks: Sequence[int] | None = None
    filter_use_cheap_tag = True
    filter_use_endomix = True
    if filter_cfg is not None:
        filter_enabled = filter_cfg.enabled
        filter_masks = filter_cfg.bitplane_masks
        filter_use_cheap_tag = filter_cfg.enable_cheap_tag
        filter_use_endomix = filter_cfg.enable_endomix
    d = d0
    bloom_filter = ctx.bloom
    for _ in range(ctx.cfg.steps_per_batch):
        pub = scalar_to_pubkey_compressed(d, backend=backend)
        ctx.step_counter += 1
        if ctx.metrics:
            ctx.metrics.inc("steps")
        if filter_enabled and not apply_filter_cascade(
            pub,
            backend=backend,
            masks=filter_masks,
            use_cheap_tag=filter_use_cheap_tag,
            use_endomix=filter_use_endomix,
        ):
            d = bsgsd_steps.next_scalar(d, params)
            continue
        rmd = hash160(pub)
        if bloom_filter is not None and not bloom_filter.contains(rmd):
            d = bsgsd_steps.next_scalar(d, params)
            continue
        trap_hits = probe_traps(
            pub,
            ctx.cfg.trap_config.directory,
            ctx.trap_index,
            ctx.cfg.trap_config.bucket_hint_bits,
        )
        if ctx.metrics:
            ctx.metrics.inc("trap_hits", len(trap_hits))
        for bucket_start, bucket_log2 in trap_hits:
            bucket_size = 1 << bucket_log2
            for candidate in range(bucket_start, bucket_start + bucket_size):
                _handle_candidate(ctx, candidate)
        d = bsgsd_steps.next_scalar(d, params)
    ctx.current_scalar = d


def _parse_int(value: str) -> int:
    return int(value, 0)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a probe worker")
    parser.add_argument("--backend", default="coincurve")
    parser.add_argument("--seed", type=_parse_int, required=True)
    parser.add_argument("--r", type=_parse_int, required=True)
    parser.add_argument("--base", type=_parse_int, required=True)
    parser.add_argument("--dp-bits", type=int, default=12)
    parser.add_argument("--lanes-csv", type=Path, required=True)
    parser.add_argument("--worker-id", type=int, required=True)
    parser.add_argument("--traps-dir", type=Path, required=True)
    parser.add_argument("--bucket-hint-bits", type=int, default=12)
    parser.add_argument("--bloom", type=Path)
    parser.add_argument("--m-bits", type=int, default=24)
    parser.add_argument("--k-hashes", type=int, default=4)
    parser.add_argument(
        "--mapped-size",
        type=lambda s: int(s.rstrip("GM")) * (1 << 30) if s.endswith("G") else int(s),
        default=1 << 26,
    )
    parser.add_argument("--target-rmd", type=str)
    parser.add_argument("--target-address", type=str)
    parser.add_argument("--save", type=Path)
    parser.add_argument("--metrics", type=Path)
    parser.add_argument("--steps-per-batch", type=int, default=1000)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--gpu", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--disable-filter-cascade", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    set_schedule_source(args.lanes_csv)
    lanes = load_schedule(lambda worker, lane: worker == args.worker_id)
    if not lanes:
        raise RuntimeError("no lanes assigned to worker")

    trap_index = open_sharded_index(args.traps_dir)
    bloom_filter = None
    if args.bloom:
        bloom_filter = bloom.MMapBloom(
            args.bloom,
            args.m_bits,
            args.k_hashes,
            mapped_size=args.mapped_size,
        )

    metrics_state = None
    if args.metrics:
        metrics_state = metrics.MetricsState(path=args.metrics)

    trap_cfg = config.TrapConfig(
        directory=args.traps_dir,
        bucket_log2=args.bucket_hint_bits,
        bucket_hint_bits=args.bucket_hint_bits,
    )
    filter_cfg = config.FilterConfig(enabled=not args.disable_filter_cascade)
    worker_cfg = config.WorkerConfig(
        backend=args.backend,
        seed=args.seed,
        r=args.r,
        base=args.base,
        dp_bits=args.dp_bits,
        lanes=lanes,
        worker_id=args.worker_id,
        trap_config=trap_cfg,
        bloom=(
            None
            if bloom_filter is None
            else config.BloomConfig(args.bloom, args.m_bits, args.k_hashes)
        ),
        filter_config=filter_cfg,
        metrics=config.MetricsConfig(args.metrics) if metrics_state else None,
        target_rmd160=bytes.fromhex(args.target_rmd) if args.target_rmd else None,
        target_address=args.target_address,
        steps_per_batch=args.steps_per_batch,
        checkpoint_path=args.checkpoint,
        save_path=args.save,
        use_gpu=args.gpu,
    )

    params = bsgsd_steps.step_params_from_seed(args.seed, args.r, args.base)

    for lane_id in lanes:
        ctx = WorkerContext(
            cfg=worker_cfg,
            trap_index=trap_index,
            bloom=bloom_filter,
            metrics=metrics_state,
            step_params=params,
            current_scalar=lane_id + args.base,
            lane_id=lane_id,
        )
        search_lane(ctx.current_scalar, params, ctx)
        maybe_checkpoint(ctx)
        emit_metrics(ctx)

    if bloom_filter is not None:
        bloom_filter.close()
    if metrics_state is not None:
        metrics.flush_metrics(metrics_state, force=True)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
