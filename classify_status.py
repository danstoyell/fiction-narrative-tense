#!/usr/bin/env python3
"""What still needs classifying. Survives any session; reads only disk state.

Run:  python3 classify_status.py            # summary by year
      python3 classify_status.py top2019    # pending sample_ids for one year
"""
import csv, os, glob, json, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
MIN_QUOTES = 15


def state():
    """Done = every quote in the CSV is labelled. Partial files do NOT count.

    Agents write large books in chunks so a kill mid-run still persists progress.
    A file with 25 of 38 quotes is real work worth keeping, but it is not a
    finished book -- counting it as done would silently analyse a truncated
    sample.
    """
    books = [r for r in csv.DictReader(open(os.path.join(DATA, "books_topn.csv"), encoding="utf-8"))
             if r["stratum"] >= "top2016" and int(r["quotes_raw"]) >= MIN_QUOTES]
    want = collections.Counter()
    for r in csv.DictReader(open(os.path.join(DATA, "quotes_topn.csv"), encoding="utf-8")):
        want[r["sample_id"]] += 1
    done, partial = set(), {}
    for p in glob.glob(os.path.join(DATA, "classified", "*.json")):
        try:
            d = json.load(open(p))
        except Exception:
            continue
        sid, n = d.get("sample_id", ""), len(d.get("quotes") or [])
        if not sid or not n:
            continue
        if sid not in want:
            continue                      # validation books from another CSV
        if n >= want[sid]:
            done.add(sid)
        else:
            partial[sid] = (n, want[sid])
    return books, done, partial


def main():
    books, done, partial = state()
    if len(sys.argv) > 1:
        want = sys.argv[1]
        pend = [b for b in books if b["stratum"] == want and b["sample_id"] not in done]
        for b in pend:
            print(b["sample_id"])
        print(f"\n# {len(pend)} pending in {want}", file=sys.stderr)
        return
    by = collections.defaultdict(lambda: [0, 0])
    for b in books:
        by[b["stratum"]][0] += 1
        if b["sample_id"] in done:
            by[b["stratum"]][1] += 1
    tot = pend = 0
    print(f"{'year':>9} {'labelable':>10} {'done':>6} {'pending':>8}")
    for s in sorted(by):
        n, d = by[s]
        tot += n; pend += n - d
        flag = "  <-- complete" if d == n else ""
        print(f"{s:>9} {n:>10} {d:>6} {n-d:>8}{flag}")
    print(f"\n  {tot} labelable books, {tot-pend} classified, {pend} pending")
    if partial:
        print(f"  {len(partial)} PARTIAL (chunked write interrupted -- will be re-done):")
        for sid, (got, exp) in sorted(partial.items()):
            print(f"    {sid[:56]:58s} {got}/{exp} quotes")


if __name__ == "__main__":
    main()
