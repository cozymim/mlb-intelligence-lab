from datetime import date

import pandas as pd
import pytest

from src.data.ingestion.statcast_client import (
    find_existing_snapshots,
    project_root,
    snapshot_path,
)


def test_project_root_finds_claude_md():
    root = project_root()
    assert (root / "CLAUDE.md").exists()


def test_snapshot_path_encodes_both_dates():
    p = snapshot_path("2024-04-15", ingested="2026-08-31")
    assert p.name == "statcast_2024-04-15_ingested_2026-08-31.parquet"


def test_snapshot_path_defaults_to_today():
    p = snapshot_path("2024-04-15")
    assert date.today().isoformat() in p.name


def test_finds_the_day_2_snapshot():
    """The snapshot pulled on Day 2 must still be discoverable."""
    found = find_existing_snapshots("2024-04-15")
    assert len(found) >= 1
    assert all("2024-04-15" in p.name for p in found)


def test_snapshots_are_sorted_oldest_first():
    found = find_existing_snapshots("2024-04-15")
    names = [p.name for p in found]
    assert names == sorted(names)
