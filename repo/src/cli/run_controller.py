"""CLI entry for the worker controller."""

from __future__ import annotations

from workers.controller import main

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
