"""Utilities for loading and chunking raw log files."""

from __future__ import annotations

from pathlib import Path

import yaml


def load_incident(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def load_log_lines(path: Path) -> list[str]:
    """Load log file, skipping # comments but keeping blank lines as chunk boundaries."""
    lines: list[str] = []
    for raw in path.read_text().splitlines():
        stripped = raw.strip()
        if stripped.startswith("#"):
            continue
        lines.append("" if not stripped else raw)
    return lines


def chunk_by_line_count(lines: list[str], lines_per_chunk: int = 4) -> list[tuple[str, str]]:
    """Split into fixed-size chunks. Returns list of (chunk_id, content)."""
    chunks: list[tuple[str, str]] = []
    for i in range(0, len(lines), lines_per_chunk):
        block = lines[i : i + lines_per_chunk]
        chunk_id = f"chunk_{i // lines_per_chunk + 1:02d}"
        chunks.append((chunk_id, "\n".join(block)))
    return chunks


def chunk_by_blank_lines(lines: list[str]) -> list[tuple[str, str]]:
    """Split on empty lines (natural log paragraph boundaries)."""
    chunks: list[tuple[str, str]] = []
    current: list[str] = []
    idx = 0
    for line in lines:
        if not line.strip():
            if current:
                idx += 1
                chunks.append((f"chunk_{idx:02d}", "\n".join(current)))
                current = []
        else:
            current.append(line)
    if current:
        idx += 1
        chunks.append((f"chunk_{idx:02d}", "\n".join(current)))
    return chunks
