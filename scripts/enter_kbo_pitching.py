"""Terminal entry for KBO pitching lines.

Editing a 73-row CSV in a spreadsheet is error-prone: it is easy to
land a number in the wrong column and not notice. This walks one row at
a time, validates each entry as it is typed, and saves after every row
so the work survives an interruption.

Required: bf (batters faced), so, bb. Everything else is optional.
K% = SO / BF, not K/9 — per-batter rates mean the same thing for a
starter and a reliever, which is why Day 31 chose them.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

import os
PATH = Path(os.environ.get("KBO_PITCHING_FILE",
                           "data/external/kbo_pitching.csv"))
REQUIRED = ["bf", "so", "bb"]
OPTIONAL = ["g", "gs", "ip", "h", "hr", "ibb", "hbp", "er"]

PROMPTS = {
    "g": "G  (games)", "gs": "GS (games started)", "ip": "IP (e.g. 181.1)",
    "bf": "BF (batters faced) *required", "h": "H  (hits allowed)",
    "hr": "HR (home runs allowed)",
    "bb": "BB (walks, incl. intentional) *required", "ibb": "IBB",
    "so": "SO (strikeouts) *required", "hbp": "HBP", "er": "ER",
}


def ask(label: str, required: bool) -> str:
    """Empty input is allowed for optional fields; 's' skips the row."""
    while True:
        raw = input(f"    {label}: ").strip()
        if raw.lower() == "s":
            return "SKIP"
        if raw == "":
            if required:
                print("      required — press s to skip this row")
                continue
            return ""
        try:
            float(raw)
            return raw
        except ValueError:
            print("      numbers only")


def row_problems(vals: dict) -> list[str]:
    """Catch the mistakes that matter before they reach the file."""
    def num(k):
        v = vals.get(k, "")
        return float(v) if v not in ("", None) else None

    bf, so, bb = num("bf"), num("so"), num("bb")
    out = []
    if so is not None and bf and so > bf:
        out.append(f"SO({so:.0f}) > BF({bf:.0f})")
    if bb is not None and bf and bb > bf:
        out.append(f"BB({bb:.0f}) > BF({bf:.0f})")
    h, hbp = num("h"), num("hbp")
    if bf and all(x is not None for x in [so, bb]):
        total = so + bb + (h or 0) + (hbp or 0)
        if total > bf:
            out.append(f"SO+BB+H+HBP({total:.0f}) > BF({bf:.0f})")
    g, gs = num("g"), num("gs")
    if g is not None and gs is not None and gs > g:
        out.append(f"GS({gs:.0f}) > G({g:.0f})")
    ip = num("ip")
    if ip and bf:
        r = bf / ip
        if not 3.5 <= r <= 5.5:
            out.append(f"BF/IP = {r:.1f} (typically about 4.3)")
    return out


def main() -> None:
    df = pd.read_csv(PATH, dtype=str).fillna("")
    todo = df[df["bf"] == ""]

    print(f"{len(todo)} of {len(df)} rows remaining")
    print("Enter = blank, s = skip row, Ctrl+C = quit\n")

    only = sys.argv[1] if len(sys.argv) > 1 else None
    if only:
        todo = todo[todo["player_en"].str.contains(only, case=False)]
        print(f"filter '{only}': {len(todo)} rows\n")

    for i, (idx, r) in enumerate(todo.iterrows(), 1):
        print(f"[{i}/{len(todo)}] {r['player_ko']} ({r['player_en']}) "
              f"{r['season']} {r['team']}")

        vals, skipped = {}, False
        for col in ["g", "gs", "ip", "bf", "h", "hr", "bb", "ibb", "so", "hbp", "er"]:
            v = ask(PROMPTS[col], col in REQUIRED)
            if v == "SKIP":
                skipped = True
                break
            vals[col] = v

        if skipped:
            print("    skipped\n")
            continue

        problems = row_problems(vals)
        if problems:
            print("    ⚠ " + "; ".join(problems))
            if input("    save anyway? (y/N): ").strip().lower() != "y":
                print("    not saved\n")
                continue

        for col, v in vals.items():
            df.loc[idx, col] = v
        df.loc[idx, "source"] = "koreabaseball"
        df.loc[idx, "verified_on"] = pd.Timestamp.today().strftime("%Y-%m-%d")
        df.to_csv(PATH, index=False)

        bf, so = float(vals["bf"]), float(vals["so"])
        print(f"    saved — K% {so / bf:.1%}\n")

    done = (pd.read_csv(PATH, dtype=str).fillna("")["bf"] != "").sum()
    print(f"done: {done}/{len(df)} rows")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nstopped. rows already entered are saved.")
