"""CLI wrapper around the probe worker."""

from __future__ import annotations

from workers.probe_worker import main

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
