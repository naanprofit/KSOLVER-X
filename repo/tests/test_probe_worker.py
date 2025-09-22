from pathlib import Path

from core import config
from workers.probe_worker import WorkerContext, _handle_candidate

TARGET_HASH = bytes.fromhex("751e76e8199196d454941c45d1b3a323f1433bd6")
TARGET_ADDRESS = "1BgGZ9tcN4rm9KBzDn7KprQz87SZ26SAMH"


def _make_worker_cfg(save_path: Path) -> config.WorkerConfig:
    trap_cfg = config.TrapConfig(directory=save_path.parent, bucket_log2=1)
    return config.WorkerConfig(
        backend="coincurve",
        seed=0,
        r=1,
        base=1,
        dp_bits=1,
        lanes=[0],
        worker_id=0,
        trap_config=trap_cfg,
        bloom=None,
        filter_config=config.FilterConfig(),
        metrics=None,
        target_rmd160=TARGET_HASH,
        target_address=None,
        steps_per_batch=10,
        checkpoint_path=None,
        save_path=save_path,
        use_gpu=False,
    )


def test_handle_candidate_persists_scalar_and_address(tmp_path):
    save_path = tmp_path / "result.txt"
    worker_cfg = _make_worker_cfg(save_path)
    ctx = WorkerContext(
        cfg=worker_cfg,
        trap_index={},
        bloom=None,
        metrics=None,
        step_params={},
        current_scalar=0,
        lane_id=0,
    )

    _handle_candidate(ctx, 1)

    contents = save_path.read_text(encoding="utf8").strip()
    assert contents == f"1,{TARGET_ADDRESS}"
