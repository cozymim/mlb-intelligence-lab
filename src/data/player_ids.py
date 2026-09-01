"""Player identity crosswalk.

Statcast's `player_name` column is the PITCHER's name on every row,
including rows analysed from the batter's perspective. Attaching it to a
batter profile silently mislabels the player. Verified 2026-09-01:
batter 663757 carries player_name "Gausman, Kevin", who is the pitcher.

Batter names must come from the Chadwick register via MLBAM id. This
module caches that lookup in data/external/ so it is fetched once.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

CACHE_PATH = Path("data") / "external" / "player_ids.csv"


def _cache_file(root: Path | None = None) -> Path:
    from src.data.ingestion.statcast_client import project_root
    return (root or project_root()) / CACHE_PATH


def load_player_ids(mlbam_ids: list[int], root: Path | None = None,
                    refresh: bool = False) -> pd.DataFrame:
    """Return the id crosswalk for the given MLBAM ids.

    Cached to data/external/player_ids.csv. Ids not already cached
    trigger a fetch; the cache is then extended rather than replaced.

    Columns include key_mlbam, key_retro, key_bbref, key_fangraphs —
    needed later to join FanGraphs or Baseball Reference data.
    """
    path = _cache_file(root)
    wanted = set(int(i) for i in mlbam_ids)

    cached = pd.DataFrame()
    if path.exists() and not refresh:
        cached = pd.read_csv(path)
        missing = wanted - set(cached["key_mlbam"])
        if not missing:
            return cached[cached["key_mlbam"].isin(wanted)]
        logger.info("cache missing %d ids, fetching", len(missing))
        wanted = missing

    from pybaseball import playerid_reverse_lookup

    fetched = playerid_reverse_lookup(sorted(wanted), key_type="mlbam")

    combined = pd.concat([cached, fetched], ignore_index=True)
    combined = combined.drop_duplicates(subset="key_mlbam", keep="last")

    path.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(path, index=False)
    logger.info("cached %d players to %s", len(combined), path)

    return combined[combined["key_mlbam"].isin(set(int(i) for i in mlbam_ids))]


def display_name(ids_df: pd.DataFrame) -> pd.Series:
    """'Last, First' indexed by MLBAM id, for display only.

    Never use a name as a join key — names are not unique and change.
    """
    names = (
        ids_df["name_last"].str.title()
        + ", "
        + ids_df["name_first"].str.title()
    )
    return pd.Series(names.values, index=ids_df["key_mlbam"], name="name")
