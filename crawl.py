"""Resolve sampled books on Goodreads and log every pull-quote.

Writes two CSVs:
  raw_data/books.csv   one row per book: resolution result + validation + yield counts
  raw_data/quotes.csv  one row per quote, with EMPTY bucket/tense columns

The bucket/tense columns are deliberately left blank. Classification is a
reading judgment made per METHODOLOGY.md, not a regex -- the crawler's job is
to produce an auditable pile of text with provenance, nothing more.

Resumable: re-running skips books already in books.csv, and all HTTP responses
are cached, so a rate-limit stop costs nothing. Run in chunks.
"""
import csv, os, sys, argparse, datetime
from booktense import goodreads as gr

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "raw_data")

BOOK_FIELDS = ["sample_id", "stratum", "title", "author", "year", "isbn",
               "gr_book_id", "gr_work_id", "gr_title", "gr_author", "gr_year",
               "gr_ratings", "resolve_method", "resolve_confidence", "resolve_notes",
               "pages_fetched", "quotes_raw", "quotes_dedup", "fetched_at"]

QUOTE_FIELDS = ["quote_id", "sample_id", "gr_work_id", "page", "idx", "source_url",
                "quote_text",
                # filled in by reading, per METHODOLOGY.md:
                "bucket",      # dialogue | gnomic | event
                "tense",       # past | present | (blank if bucket != event)
                "note"]


def _load_done(path, key="sample_id"):
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8") as fh:
        return {r[key] for r in csv.DictReader(fh) if r.get(key) and r[key] != key}


def _appender(path, fields):
    new = not os.path.exists(path) or os.path.getsize(path) == 0
    fh = open(path, "a", newline="", encoding="utf-8")
    w = csv.DictWriter(fh, fieldnames=fields)
    if new:
        w.writeheader()
    return fh, w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=25, help="books this run (chunking)")
    ap.add_argument("--stratum", help="restrict to one stratum")
    ap.add_argument("--per-stratum", type=int,
                    help="take N from EACH stratum (stratified pilot)")
    ap.add_argument("--max-pages", type=int, default=4)
    ap.add_argument("--sample", default=None, help="alternate sample csv")
    ap.add_argument("--books-out", default=None)
    ap.add_argument("--quotes-out", default=None)
    ap.add_argument("--patient", action="store_true",
                    help="sleep through rate limits instead of stopping (unattended runs)")
    args = ap.parse_args()

    sample = list(csv.DictReader(open(args.sample or os.path.join(DATA, "sample.csv"), encoding="utf-8")))
    books_p = args.books_out or os.path.join(DATA, "books.csv")
    quotes_p = args.quotes_out or os.path.join(DATA, "quotes.csv")
    done = _load_done(books_p)

    avail = [r for r in sample if r["sample_id"] not in done
             and (not args.stratum or r["stratum"] == args.stratum)]
    if args.per_stratum:
        from collections import defaultdict
        buckets = defaultdict(list)
        for r in avail:
            buckets[r["stratum"]].append(r)
        todo = [r for s_ in sorted(buckets) for r in buckets[s_][:args.per_stratum]]
    else:
        todo = avail[:args.limit]
    if not todo:
        print("nothing to do")
        return

    bfh, bw = _appender(books_p, BOOK_FIELDS)
    qfh, qw = _appender(quotes_p, QUOTE_FIELDS)
    now = datetime.datetime.now().isoformat(timespec="seconds")
    nq = len(_load_done(quotes_p, "quote_id")) if os.path.exists(quotes_p) else 0

    try:
        for i, r in enumerate(todo, 1):
            try:
                print(f"  [{i}/{len(todo)}] fetching {r['title'][:34]}", flush=True)
                res = gr.resolve(r["title"], r["author"], r.get("year"), r.get("isbn"),
                                 patient=args.patient)
                qs, raw_count = (gr.quotes(res["work_id"], args.max_pages,
                                           patient=args.patient)
                                 if res["work_id"] else ([], 0))
            except gr.RateLimited as e:
                print(f"\nRATE LIMITED: {e}\nStopping cleanly. Wait ~15min and re-run; "
                      f"cache preserved, {i-1} books done this run.")
                break

            for page, idx, url, text in qs:
                nq += 1
                qw.writerow(dict(quote_id=f"q{nq:05d}", sample_id=r["sample_id"],
                                 gr_work_id=res["work_id"], page=page, idx=idx,
                                 source_url=url, quote_text=text,
                                 bucket="", tense="", note=""))
            bw.writerow(dict(
                sample_id=r["sample_id"], stratum=r["stratum"], title=r["title"],
                author=r["author"], year=r.get("year", ""), isbn=r.get("isbn", ""),
                gr_book_id=res["book_id"], gr_work_id=res["work_id"],
                gr_title=res["gr_title"], gr_author=res["gr_author"],
                gr_year=res["gr_year"] or "", gr_ratings=res["ratings"],
                resolve_method=res["method"], resolve_confidence=res["confidence"],
                resolve_notes=res["notes"],
                pages_fetched=max([p for p, *_ in qs], default=0),
                quotes_raw=raw_count, quotes_dedup=len(qs), fetched_at=now))
            bfh.flush(); qfh.flush()
            print(f"  [{i}/{len(todo)}] {r['title'][:34]:36s} "
                  f"{res['method']:>12} {res['confidence']:>6} "
                  f"ratings={res['ratings']:>6} quotes={len(qs):>3}")
    finally:
        bfh.close(); qfh.close()
    print(f"\nbooks -> {books_p}\nquotes -> {quotes_p}")


if __name__ == "__main__":
    main()
