#!/usr/bin/env python3
"""Select the next-ranked NYT books for historical years with zero usable labels."""

import argparse
import collections
import csv
import glob
import sys
from pathlib import Path


HERE = Path(__file__).parent
ROOT = HERE.parent
DATA = ROOT / "raw_data"
RAW = DATA / "raw"
sys.path.insert(0, str(HERE))

import build_report


FIELDS = [
    "sample_id", "stratum", "source", "post45_title_id", "title", "author",
    "year", "first_week", "isbn", "oclc", "best_rank", "weeks_on_list",
]


def zero_label_years():
    rows, *_ = build_report.load()
    usable = collections.Counter(
        row["year"] for row in rows
        if 1931 <= row["year"] <= 1995 and row["label"] in {"PAST", "PRESENT", "OTHER"}
    )
    return [year for year in range(1931, 1996) if not usable[year]]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-year", type=int, default=5)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    lists = list(csv.DictReader((RAW / "lists.csv").open(encoding="utf-8", errors="replace")))
    titles = {
        row["id"]: row
        for row in csv.DictReader((RAW / "titles.csv").open(encoding="utf-8", errors="replace"))
    }
    weeks = collections.Counter()
    best_rank = collections.defaultdict(lambda: 99)
    for row in lists:
        weeks[row["title_id"]] += 1
        try:
            best_rank[row["title_id"]] = min(best_rank[row["title_id"]], int(row["rank"]))
        except ValueError:
            pass

    used = set()
    for path in glob.glob(str(DATA / "sample_top3_1931_1995*.csv")):
        used.update(
            row["post45_title_id"]
            for row in csv.DictReader(open(path, encoding="utf-8"))
            if row.get("post45_title_id")
        )

    selected = []
    for year in zero_label_years():
        pool = [row for row in titles.values() if row.get("first_week", "")[:4] == str(year)]
        pool.sort(key=lambda row: (-weeks[row["id"]], best_rank[row["id"]]))
        available = [row for row in pool if row["id"] not in used]
        take = available[:args.per_year]
        if len(take) < args.per_year:
            raise SystemExit(f"{year}: only {len(take)} unused ranked candidates remain")
        for row in take:
            selected.append({
                "sample_id": f"top{year}:{row['id']}",
                "stratum": f"top{year}",
                "source": "post45_topn",
                "post45_title_id": row["id"],
                "title": row["title"],
                "author": row["author"],
                "year": year,
                "first_week": row.get("first_week", ""),
                "isbn": row.get("oclc_isbn", ""),
                "oclc": row.get("oclc", ""),
                "best_rank": best_rank[row["id"]],
                "weeks_on_list": weeks[row["id"]],
            })
            used.add(row["id"])
        print(f"{year}: " + "; ".join(row["title"] for row in take))

    output = Path(args.out)
    with output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(selected)
    print(f"wrote {len(selected)} candidates -> {output}")


if __name__ == "__main__":
    main()
