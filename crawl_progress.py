#!/usr/bin/env python3
"""Show progress for a scheduled Goodreads crawl."""
import argparse
import csv
import time
from datetime import datetime, timedelta
from pathlib import Path

from tqdm import tqdm



PRESETS = {
    "original": (
        "data/sample_topn5_1996_2016.csv",
        "data/books_topn5_1996_2016.csv",
    ),
    "more": (
        "data/sample_topn5_more_1996_2015.csv",
        "data/books_topn5_more_1996_2015.csv",
    ),
}


def count_rows(path, key):
    if not Path(path).exists():
        return set()
    with open(path, encoding="utf-8", newline="") as file:
        return {row[key] for row in csv.DictReader(file) if row.get(key)}


def completed_books(sample, books):
    total = len(count_rows(sample, "sample_id"))
    complete = len(count_rows(books, "sample_id"))
    return complete, total


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preset", choices=PRESETS, default="original")
    parser.add_argument("--sample")
    parser.add_argument("--books")
    parser.add_argument("--interval", type=float, default=5)
    args = parser.parse_args()

    sample, books = PRESETS[args.preset]
    sample, books = args.sample or sample, args.books or books
    complete, total = completed_books(sample, books)
    progress = tqdm(total=total, initial=complete, unit="book", dynamic_ncols=True)
    try:
        last_complete, last_checked = complete, time.monotonic()
        while complete < total:
            time.sleep(args.interval)
            complete, total = completed_books(sample, books)
            progress.update(complete - progress.n)
            now = time.monotonic()
            completed_since_last_check = complete - last_complete
            elapsed = now - last_checked
            if completed_since_last_check and elapsed:
                eta = timedelta(seconds=(total - complete) * elapsed / completed_since_last_check)
                finish = datetime.now() + eta
                progress.set_postfix_str(f"finishes ~{finish:%b %d %H:%M}")
            last_complete, last_checked = complete, now
    except KeyboardInterrupt:
        pass
    finally:
        progress.close()


if __name__ == "__main__":
    main()
