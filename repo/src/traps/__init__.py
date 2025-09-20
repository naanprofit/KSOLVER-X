"""Trap generation, indexing, and probing utilities."""

from .trap_index import build_sharded_index, open_sharded_index, probe_tag1
from .trap_probe import probe_traps, pubkey_tags
from .trapgen import (
    build_index,
    fingerprint64,
    generate_trap_sequence,
    generate_traps,
    int_to_32b,
    trap_entry,
    write_trap_file,
)

__all__ = [
    "int_to_32b",
    "fingerprint64",
    "generate_trap_sequence",
    "trap_entry",
    "write_trap_file",
    "generate_traps",
    "build_index",
    "build_sharded_index",
    "open_sharded_index",
    "probe_tag1",
    "pubkey_tags",
    "probe_traps",
]
