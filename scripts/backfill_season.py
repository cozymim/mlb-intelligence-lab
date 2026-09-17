"""Download one season of Statcast, one day at a time, resumably.

Run in the background:
    nohup python scripts/backfill_season.py 2024 > logs/backfill.log 2>&1 &

Days already on disk are skipped, so the script can be killed and
restarted without losing work. Failures are logged and skipped rather
than aborting the run — a single bad day should not cost the season.
"""

from __future__ import annotations

import logging
import sys
import time
from datetime import date, timedelta

sys.path.insert(0, ".")

from src.data.ingestion.statcast_client import fetch_day, find_existing_snapshots

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("backfill")

# Approximate regular season windows. Verify against the official
# schedule before treating these as exact.
SEASON_WINDOWS = {
    2014: ("2014-03-30", "2014-09-28"),
    2015: ("2015-04-05", "2015-10-04"),
    2016: ("2016-04-03", "2016-10-02"),
    2017: ("2017-04-02", "2017-10-01"),
    2018: ("2018-03-29", "2018-10-01"),
    2019: ("2019-03-28", "2019-09-29"),
    2020: ("2020-07-23", "2020-09-27"),
    2021: ("2021-04-01", "2021-10-03"),
    2022: ("2022-04-07", "2022-10-05"),
    2023: ("2023-03-30", "2023-10-01"),
    2024: ("2024-03-28", "2024-09-29"),
}

PAUSE_SECONDS = 2.0


def daterange(start: str, end: str):
    d = date.fromisoformat(start)
    last = date.fromisoformat(end)
    while d <= last:
        yield d.isoformat()
        d += timedelta(days=1)


def main(year: int) -> None:
    if year not in SEASON_WINDOWS:
        raise SystemExit(f"no window defined for {year}: {sorted(SEASON_WINDOWS)}")

    start, end = SEASON_WINDOWS[year]
    days = list(daterange(start, end))
    logger.info("season %d: %d days from %s to %s", year, len(days), start, end)

    downloaded = skipped = failed = empty = 0

    for i, day in enumerate(days, 1):
        if find_existing_snapshots(day):
            skipped += 1
            continue

        try:
            df = fetch_day(day)
            if len(df) == 0:
                empty += 1
                logger.info("[%d/%d] %s: no games", i, len(days), day)
            else:
                downloaded += 1
                logger.info("[%d/%d] %s: %d pitches", i, len(days), day, len(df))
            time.sleep(PAUSE_SECONDS)
        except Exception as exc:
            failed += 1
            logger.error("[%d/%d] %s FAILED: %s", i, len(days), day, exc)

    logger.info(
        "done. downloaded=%d skipped=%d empty=%d failed=%d",
        downloaded, skipped, empty, failed,
    )
    if failed:
        logger.warning("re-run this script to retry the %d failed days", failed)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 2024)
