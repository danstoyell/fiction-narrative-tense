"""Advance a Goodreads crawl by at most one uncached HTTP request.

Designed for a scheduler that invokes it at a polite interval. Cached responses
are replayed freely; a book is appended only after its resolver and quotes have
both completed, so an interrupted step is always safe to retry.
"""
import argparse
import csv
import datetime
import hashlib
import os

from booktense import goodreads as gr
from crawl import BOOK_FIELDS, QUOTE_FIELDS, _appender, _load_done


class DeferredRequest(Exception):
    """The scheduled step has spent its one-request budget."""


def _cached_response(url):
    key = hashlib.sha1(url.encode()).hexdigest()[:20]
    path = os.path.join(gr.CACHE, key + ".html")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", required=True)
    parser.add_argument("--books-out", required=True)
    parser.add_argument("--quotes-out", required=True)
    args = parser.parse_args()

    sample = list(csv.DictReader(open(args.sample, encoding="utf-8")))
    done = _load_done(args.books_out)
    todo = [row for row in sample if row["sample_id"] not in done]
    if not todo:
        print("nothing to do", flush=True)
        return

    original_fetch = gr.fetch
    requests_used = 0

    def fetch_once(url, use_cache=True, patient=False, cooldown=75, max_waits=25):
        nonlocal requests_used
        if use_cache:
            cached = _cached_response(url)
            if cached is not None:
                return cached
        if requests_used:
            raise DeferredRequest(url)
        requests_used += 1
        return original_fetch(url, use_cache=use_cache, patient=False,
                              cooldown=cooldown, max_waits=max_waits)

    gr.fetch = fetch_once
    books_fh, books_writer = _appender(args.books_out, BOOK_FIELDS)
    quotes_fh, quotes_writer = _appender(args.quotes_out, QUOTE_FIELDS)
    quote_count = len(_load_done(args.quotes_out, "quote_id"))
    now = datetime.datetime.now().isoformat(timespec="seconds")
    try:
        for row in todo:
            try:
                result = gr.resolve(row["title"], row["author"], row.get("year"),
                                    row.get("isbn"), patient=False)
                quotes, raw_count = (gr.quotes(result["work_id"], patient=False,
                                                expected_title=row["title"])
                                     if result["work_id"] else ([], 0))
            except DeferredRequest as error:
                print(f"deferred after one request: {row['sample_id']} ({error})", flush=True)
                return
            except gr.RateLimited as error:
                print(f"rate limited: {row['sample_id']} ({error})", flush=True)
                return
            except gr.TitleMismatch as error:
                result["confidence"] = "review"
                result["notes"] = ";".join(
                    x for x in (result.get("notes"), str(error)) if x)
                quotes, raw_count = [], 0
                print(f"title mismatch: {row['sample_id']} ({error})", flush=True)

            for page, index, url, quote_text in quotes:
                quote_count += 1
                quotes_writer.writerow(dict(
                    quote_id=f"q{quote_count:05d}", sample_id=row["sample_id"],
                    gr_work_id=result["work_id"], page=page, idx=index, source_url=url,
                    quote_text=quote_text, bucket="", tense="", note=""))
            books_writer.writerow(dict(
                sample_id=row["sample_id"], stratum=row["stratum"], title=row["title"],
                author=row["author"], year=row["year"], isbn=row.get("isbn", ""),
                gr_book_id=result["book_id"], gr_work_id=result["work_id"],
                gr_title=result["gr_title"], gr_author=result["gr_author"],
                gr_year=result["gr_year"] or "", gr_ratings=result["ratings"],
                resolve_method=result["method"], resolve_confidence=result["confidence"],
                resolve_notes=result["notes"],
                pages_fetched=max([page for page, *_ in quotes], default=0),
                quotes_raw=raw_count, quotes_dedup=len(quotes), fetched_at=now))
            books_fh.flush()
            quotes_fh.flush()
            print(f"completed cached book: {row['sample_id']} quotes={len(quotes)}", flush=True)
    finally:
        gr.fetch = original_fetch
        books_fh.close()
        quotes_fh.close()


if __name__ == "__main__":
    main()
