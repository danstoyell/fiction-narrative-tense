"""Build the stratified sample frame -> raw_data/sample.csv

Strata: one per decade 1931-2015, then one per YEAR 2016-2026.
Post45 covers 1931-2020; 2021-2026 comes from the NYT Books API.
"""
import csv, os, json, random, time, argparse, urllib.request
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "raw_data", "raw")
SEED = 20260803
PER_STRATUM = 80        # oversample: ~50% of books yield too few quotes to label
MIN_YEAR = 1990        # pre-1990 bestsellers are too forgotten to have quotes (see PLAN.md)

FIELDS = ["sample_id", "stratum", "source", "post45_title_id", "title", "author",
          "year", "first_week", "isbn", "oclc", "best_rank", "weeks_on_list"]


def post45_rows():
    p = os.path.join(RAW, "titles.csv")
    if not os.path.exists(p):
        raise SystemExit(f"missing {p} -- see PLAN.md for the curl command")
    return list(csv.DictReader(open(p, encoding="utf-8", errors="replace")))


def nyt_titles(years, api_key, weeks_per_year=12):
    """Sample ~monthly lists per year and dedupe to distinct titles."""
    out = {}
    for y in years:
        for m in range(1, 13, max(1, 12 // weeks_per_year)):
            url = (f"https://api.nytimes.com/svc/books/v3/lists/{y}-{m:02d}-15/"
                   f"hardcover-fiction.json?api-key={api_key}")
            try:
                d = json.load(urllib.request.urlopen(url, timeout=40))
            except Exception as e:
                print(f"   {y}-{m:02d}: {type(e).__name__}")
                time.sleep(13)
                continue
            for b in d.get("results", {}).get("books", []):
                key = (b["title"].strip().upper(), b["author"].strip())
                out.setdefault(key, dict(
                    title=b["title"].strip(), author=b["author"].strip(), year=y,
                    first_week=d["results"].get("published_date", f"{y}-{m:02d}-15"),
                    isbn=b.get("primary_isbn13", ""), oclc="",
                    best_rank=b.get("rank", ""), weeks_on_list=b.get("weeks_on_list", "")))
            print(f"   {y}-{m:02d}: cumulative distinct = {len(out)}")
            time.sleep(13)     # NYT allows ~5 req/min
    return list(out.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nyt-key", default=os.environ.get("NYT_BOOKS_API_KEY"))
    ap.add_argument("--skip-nyt", action="store_true",
                    help="skip the 2021-2026 API strata")
    ap.add_argument("--min-year", type=int, default=MIN_YEAR)
    ap.add_argument("--per-stratum", type=int, default=PER_STRATUM)
    args = ap.parse_args()

    rows = post45_rows()
    pools = defaultdict(list)

    for r in rows:
        y = r.get("first_week", "")[:4]
        if not y.isdigit():
            continue
        y = int(y)
        if y < args.min_year or y > 2020:
            continue
        stratum = f"{max(args.min_year, y//10*10)}-{min(y//10*10+9, 2015)}" if y <= 2015 else str(y)
        pools[stratum].append(dict(
            source="post45", post45_title_id=r.get("id", ""), title=r["title"],
            author=r["author"], year=y, first_week=r.get("first_week", ""),
            isbn=r.get("oclc_isbn", ""), oclc=r.get("oclc", ""),
            best_rank=r.get("best_rank", ""), weeks_on_list=""))

    if not args.skip_nyt:
        if not args.nyt_key:
            raise SystemExit("need --nyt-key or NYT_BOOKS_API_KEY (see .env)")
        print("fetching 2021-2026 frame from NYT API...")
        for t in nyt_titles(range(max(2021, args.min_year), 2027), args.nyt_key):
            t["source"] = "nyt_api"
            t["post45_title_id"] = ""
            pools[str(t["year"])].append(t)

    rng = random.Random(SEED)
    os.makedirs(os.path.join(ROOT, "raw_data"), exist_ok=True)
    out = os.path.join(ROOT, "raw_data", "sample.csv")
    n = 0
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        for stratum in sorted(pools):
            pool = pools[stratum]
            take = rng.sample(pool, min(args.per_stratum, len(pool)))
            short = "  <-- SHORT" if len(pool) < args.per_stratum else ""
            print(f"  {stratum:>10}: pool={len(pool):>5} sample={len(take):>3}{short}")
            for row in take:
                n += 1
                # stable across rebuilds: lets crawl.py resume after re-sampling
                key = row.get("post45_title_id") or f"{row['title']}|{row['author']}"
                row["sample_id"] = f"{stratum}:{key}"
                row["stratum"] = stratum
                w.writerow({k: row.get(k, "") for k in FIELDS})
    print(f"\nwrote {n} rows -> {out}")


if __name__ == "__main__":
    main()
