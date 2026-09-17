"""Dashboard data access.

Reads ONLY from data/app/, never from data/raw/. That directory is 470
MB and cannot deploy; data/app/ is 572 KB of precomputed tables.

If a page needs something new, it goes in scripts/build_app_data.py —
never computed here. The dashboard displays; src/ computes.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

APP_DATA = Path(__file__).resolve().parents[1] / "data" / "app"


@st.cache_data
def load(name: str) -> pd.DataFrame:
    """Load one precomputed table. Cached for the session."""
    path = APP_DATA / f"{name}.parquet"
    if not path.exists():
        raise FileNotFoundError(
            f"{path.name} missing. Run: python scripts/build_app_data.py")
    return pd.read_parquet(path)


def available() -> list[str]:
    return sorted(p.stem for p in APP_DATA.glob("*.parquet"))
