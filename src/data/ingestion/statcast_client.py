"""Single point of contact with pybaseball / Baseball Savant.

No notebook, feature module, or model may import pybaseball directly.
If the upstream library changes or breaks, exactly one file changes.

Rules enforced here:
  - raw snapshots are immutable and never overwritten
  - filenames record BOTH the game date and the ingestion date,
    because Statcast is revised retroactively
  - an existing snapshot is reused instead of re-downloading
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

RAW_SUBDIR = Path("data") / "raw"


def project_root(start: Path | None = None) -> Path:
    """Walk upward until CLAUDE.md is found. Never hardcode absolute paths."""
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "CLAUDE.md").exists():
            return candidate
    raise FileNotFoundError("CLAUDE.md not found in any parent directory")


def snapshot_path(game_date: str, ingested: str | None = None,
                  root: Path | None = None) -> Path:
    """Path for one day's raw snapshot.

    game_date : "YYYY-MM-DD", the day the games were played
    ingested  : "YYYY-MM-DD", the day we pulled it (defaults to today)
    """
    root = root or project_root()
    ingested = ingested or date.today().isoformat()
    name = f"statcast_{game_date}_ingested_{ingested}.parquet"
    return root / RAW_SUBDIR / name


def find_existing_snapshots(game_date: str, root: Path | None = None) -> list[Path]:
    """All snapshots we hold for a game date, oldest ingestion first.

    More than one is normal and meaningful: Statcast revises data, so two
    pulls of the same day taken months apart may legitimately differ.
    """
    root = root or project_root()
    matches = sorted((root / RAW_SUBDIR).glob(f"statcast_{game_date}_ingested_*.parquet"))
    return matches


def fetch_day(game_date: str, force: bool = False,
              root: Path | None = None) -> pd.DataFrame:
    """Return one day of Statcast data, downloading only if necessary.

    Reuses the most recent existing snapshot unless `force=True`.
    Raw files are never overwritten — a forced re-pull writes a new file
    stamped with today's ingestion date.
    """
    root = root or project_root()
    existing = find_existing_snapshots(game_date, root=root)

    if existing and not force:
        newest = existing[-1]
        logger.info("reusing snapshot %s", newest.name)
        return pd.read_parquet(newest)

    from pybaseball import statcast  # imported late: only needed on a real pull

    logger.info("downloading statcast for %s", game_date)
    df = statcast(start_dt=game_date, end_dt=game_date)

    out = snapshot_path(game_date, root=root)
    if out.exists():
        logger.info("snapshot already written today: %s", out.name)
        return pd.read_parquet(out)

    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    logger.info("wrote %s (%d rows, %.2f MB)",
                out.name, len(df), out.stat().st_size / 1e6)
    return df


def fetch_days(game_dates: list[str], root: Path | None = None) -> pd.DataFrame:
    """Fetch several dates and concatenate. Cached days cost nothing."""
    frames = [fetch_day(d, root=root) for d in game_dates]
    return pd.concat(frames, ignore_index=True)
