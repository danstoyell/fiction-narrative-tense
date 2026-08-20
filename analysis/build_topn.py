"""Alternative frame: top-N bestsellers per year by weeks on list.

A census of a defined subpopulation ("the biggest bestsellers of year Y")
rather than a random sample suffering differential availability.
Ranking: total weeks on the NYT hardcover fiction list, tie-broken by peak rank.
"""
import csv, os, collections, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "raw_data", "raw")

def _nyt_week(ds, api_key, cache_dir):
    """One weekly list, cached to disk so re-runs cost no requests."""
    import json, os, time, urllib.request
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, f"{ds}.json")
    if os.path.exists(path):
        return json.load(open(path))
    url = (f"https://api.nytimes.com/svc/books/v3/lists/{ds}/"
           f"hardcover-fiction.json?api-key={api_key}")
    try:
        d = json.load(urllib.request.urlopen(url, timeout=40))
    except Exception as e:
        print(f"    {ds}: {type(e).__name__}"); time.sleep(13); return None
    json.dump(d, open(path, "w"))
    time.sleep(13)
    return d


def nyt_index(years, api_key, cache_dir):
    """Index every title seen across `years` of WEEKLY lists.

    Returns title-key -> first sighting, weeks-at-first-sighting, max weeks, best rank.

    Two things this must get right, both of which a naive version got wrong:

    * WEEKLY, not monthly. Monthly snapshots miss short-run titles and catch
      5-15 week books once, early, so weeks_on_list is undercounted exactly
      where the rank-30 cutoff sits -- distorting the ranking that defines
      the sample.
    * ONE year per book. Post45 assigns a title to the year it FIRST charted.
      Assigning it to every year it appears in put The Midnight Library in
      2021, 2022 AND 2023, over-weighting long-runners on one side of the
      2020/2021 boundary and making the seam look like a trend.
    """
    import datetime
    seen = {}
    for year in years:
        d, end = datetime.date(year, 1, 1), datetime.date(year, 12, 31)
        dates = []
        while d <= end:
            dates.append(d.isoformat()); d += datetime.timedelta(days=7)
        got = 0
        for ds in dates:
            data = _nyt_week(ds, api_key, cache_dir)
            if not data:
                continue
            got += 1
            pub = data.get("results", {}).get("published_date", ds)
            for b in data.get("results", {}).get("books", []):
                k = (b["title"].strip().upper(), b["author"].strip())
                w = int(b.get("weeks_on_list") or 0)
                r = int(b.get("rank") or 99)
                if k not in seen:
                    seen[k] = dict(title=b["title"].strip(), author=b["author"].strip(),
                                   isbn=b.get("primary_isbn13", ""), first_seen=pub,
                                   weeks_at_first=w, max_weeks=w, best_rank=r)
                else:
                    e = seen[k]
                    e["max_weeks"] = max(e["max_weeks"], w)
                    e["best_rank"] = min(e["best_rank"], r)
        print(f"  {year}: {got} weekly lists fetched")
    return seen


def nyt_topn(year, top, index):
    """Top-N for `year`, where a book belongs to the year it FIRST charted.

    weeks_on_list at first sighting back-dates the true start: a title first
    seen in Jan 2021 already carrying 10 weeks began in late 2020 and belongs
    to 2020, not 2021.
    """
    import datetime
    rows = []
    for e in index.values():
        try:
            fs = datetime.date.fromisoformat(e["first_seen"])
        except ValueError:
            continue
        start = fs - datetime.timedelta(days=7 * max(0, e["weeks_at_first"] - 1))
        if start.year != year:
            continue
        rows.append(e)
    rows.sort(key=lambda x: (-x["max_weeks"], x["best_rank"]))
    sel = rows[:top]
    print(f"  {year}: {len(rows)} first charted -> top {len(sel)}"
          + (f"  <-- SHORT" if len(rows) < top else ""))
    return [dict(sample_id=f"top{year}:{r['title'][:40]}|{r['author'][:30]}",
                 stratum=f"top{year}", source="nyt_topn", post45_title_id="",
                 title=r["title"], author=r["author"], year=year,
                 first_week=r["first_seen"], isbn=r["isbn"], oclc="",
                 best_rank=r["best_rank"], weeks_on_list=r["max_weeks"]) for r in sel]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=40)
    ap.add_argument("--years", default="1990-2020",
                    help="comma list and/or ranges, e.g. 1990-2020,2021")
    ap.add_argument("--nyt-key", default=os.environ.get("NYT_BOOKS_API_KEY"))
    ap.add_argument("--out", default=os.path.join(ROOT, "raw_data", "sample_topn.csv"))
    a = ap.parse_args()

    lists = list(csv.DictReader(open(os.path.join(RAW, "lists.csv"), encoding="utf-8", errors="replace")))
    titles = {r["id"]: r for r in csv.DictReader(open(os.path.join(RAW, "titles.csv"), encoding="utf-8", errors="replace"))}
    weeks, best = collections.Counter(), collections.defaultdict(lambda: 99)
    for r in lists:
        weeks[r["title_id"]] += 1
        try: best[r["title_id"]] = min(best[r["title_id"]], int(r["rank"]))
        except ValueError: pass

    nyt_ix = None
    years = []
    for part in a.years.split(","):
        if "-" in part:
            lo, hi = part.split("-"); years += list(range(int(lo), int(hi) + 1))
        else:
            years.append(int(part))
    rows = []
    for y in years:
        if y > 2020:
            if nyt_ix is None:
                # index the whole span once so "first charted" is span-wide,
                # then pull one extra prior year so 2021 back-dating is correct
                span = [x for x in range(min(y for y in years if y > 2020) - 1, max(years) + 1)]
                nyt_ix = nyt_index(span, a.nyt_key,
                                   os.path.join(ROOT, "raw_data", "cache_nyt"))
            rows += nyt_topn(y, a.top, nyt_ix); continue
        pool = [t for t in titles.values() if t.get("first_week", "")[:4] == str(y)]
        pool.sort(key=lambda t: (-weeks[t["id"]], best[t["id"]]))
        for rank, t in enumerate(pool[:a.top], 1):
            rows.append(dict(sample_id=f"top{y}:{t['id']}", stratum=f"top{y}",
                             source="post45_topn", post45_title_id=t["id"],
                             title=t["title"], author=t["author"], year=y,
                             first_week=t.get("first_week", ""), isbn=t.get("oclc_isbn", ""),
                             oclc=t.get("oclc", ""), best_rank=best[t["id"]],
                             weeks_on_list=weeks[t["id"]]))
        print(f"  {y}: pool={len(pool)} -> top {min(a.top,len(pool))}, "
              f"weeks {weeks[pool[0]['id']]}..{weeks[pool[min(a.top,len(pool))-1]['id']]}")
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(f"\nwrote {len(rows)} -> {a.out}")

if __name__ == "__main__":
    main()
