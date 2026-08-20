"""Audit every active NYT candidate -> Goodreads book/work title mapping.

This is deliberately separate from classification. It writes a complete audit table and a
sample CSV containing only mismatches that should be re-resolved and refetched. Corrected
quotes must remain staged until they receive new classifications.
"""
import argparse
import collections
import csv
import datetime
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "raw_data")
sys.path.insert(0, ROOT)

from build_report import SOURCES
from booktense import goodreads as gr

AUDIT_FIELDS = [
    "sample_id", "cohort", "year", "title", "author", "source_books_file",
    "gr_book_id", "gr_work_id", "gr_title", "work_page_title",
    "book_title_status", "work_title_status", "duplicate_work_id",
    "verdict", "reason",
]

# Goodreads sometimes names the same work by a translation/original-market title or a
# shortened canonical title. These were manually reviewed against the requested title,
# author, and stored Goodreads book-page title. Keep exceptions narrow and documented.
WORK_TITLE_ALIASES = {
    "top1949:5038": "The Egyptian is published under the translated title Sinuhe/سینوهه.",
    "top1953:5125": "Wanita is a translated title for The Female by Paul I. Wellman.",
    "top1979:6507": "The Goodreads work omits the subtitle August 1985.",
    "top1998:2118": "Sorcerer's Stone and Philosopher's Stone are market titles for one work.",
    "top2005:1045": "Out of Egypt is the shortened work title for Christ the Lord: Out of Egypt.",
    "top2005:3787": "The work title Star Wars is shortened; the book page names Revenge of the Sith.",
    "top2018:4451": "Target is the shortened market title for Target: Alex Cross.",
    "top2022:THE 6:20 MAN|David Baldacci": "Goodreads truncates the work heading to The 6; the book page is exact.",
}


def active_books():
    """Yield the same active candidate rows and source precedence as build_report.load()."""
    for source in SOURCES:
        books = {}
        for filename in source["books"]:
            path = os.path.join(DATA, filename)
            for row in csv.DictReader(open(path, encoding="utf-8")):
                books[row["sample_id"]] = (filename, row)
        for sample_id, (filename, row) in books.items():
            year_text = sample_id[3:7]
            if year_text.isdigit() and source["lo"] <= int(year_text) <= source["hi"]:
                yield source["key"], filename, row


def cached_work_title(work_id):
    if not work_id:
        return "", False
    url = f"https://www.goodreads.com/work/quotes/{work_id}"
    key = hashlib.sha1(url.encode()).hexdigest()[:20]
    path = os.path.join(gr.CACHE, key + ".html")
    if not os.path.exists(path):
        return "", False
    with open(path, encoding="utf-8") as handle:
        return gr._work_page_title(handle.read()), True


def status(ok, note):
    return "pass" if ok else note


def audit_rows():
    active = list(active_books())
    by_work = collections.defaultdict(list)
    for cohort, filename, row in active:
        if row.get("gr_work_id"):
            by_work[row["gr_work_id"]].append(row)

    audited = []
    for cohort, filename, row in active:
        sample_id = row["sample_id"]
        work_id = row.get("gr_work_id", "")
        work_title, work_cached = cached_work_title(work_id)
        book_ok, _, book_note = gr.title_match(
            row["title"], row.get("gr_title", ""), row["author"])
        work_ok, _, work_note = gr.title_match(row["title"], work_title, row["author"])
        alias_note = WORK_TITLE_ALIASES.get(sample_id)
        if alias_note and work_cached:
            book_ok, book_note = True, "documented_alias"
            work_ok, work_note = True, "documented_alias"

        duplicate_titles = sorted({item["title"] for item in by_work.get(work_id, [])})
        duplicate = " | ".join(duplicate_titles) if len(duplicate_titles) > 1 else ""

        reasons = []
        if not work_id:
            verdict = "unmapped"
            reasons.append("no Goodreads work ID")
        elif not work_cached:
            verdict = "review"
            reasons.append("work quote page is not cached")
        elif not book_ok or not work_ok:
            verdict = "mismatch"
            if not book_ok:
                reasons.append("book page: " + book_note)
            if not work_ok:
                reasons.append("work page: " + work_note)
        else:
            verdict = "pass_alias" if alias_note else "pass"
            if alias_note:
                reasons.append(alias_note)
        if duplicate:
            reasons.append("work ID also assigned to: " + duplicate)

        audited.append({
            "sample_id": sample_id,
            "cohort": cohort,
            "year": row.get("year", ""),
            "title": row["title"],
            "author": row["author"],
            "source_books_file": filename,
            "gr_book_id": row.get("gr_book_id", ""),
            "gr_work_id": work_id,
            "gr_title": row.get("gr_title", ""),
            "work_page_title": work_title,
            "book_title_status": status(book_ok, book_note),
            "work_title_status": status(work_ok, work_note),
            "duplicate_work_id": duplicate,
            "verdict": verdict,
            "reason": "; ".join(reasons),
            "_source": row,
        })
    return audited


def write_csv(path, fields, rows):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=os.path.join(DATA, "resolution_audit_20260819"))
    args = parser.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    rows = audit_rows()
    mismatches = [row for row in rows if row["verdict"] == "mismatch"]
    counts = collections.Counter(row["verdict"] for row in rows)

    audit_path = os.path.join(args.out_dir, "audit.csv")
    write_csv(audit_path, AUDIT_FIELDS, rows)

    sample_fields = ["sample_id", "stratum", "title", "author", "year", "isbn"]
    sample_rows = []
    for row in mismatches:
        source = row["_source"]
        sample_rows.append({field: source.get(field, "") for field in sample_fields})
    sample_path = os.path.join(args.out_dir, "refetch_sample.csv")
    write_csv(sample_path, sample_fields, sample_rows)

    report_path = os.path.join(args.out_dir, "REPORT.md")
    with open(report_path, "w", encoding="utf-8") as handle:
        handle.write("# Goodreads resolution audit\n\n")
        handle.write(f"Generated {datetime.date.today().isoformat()}. Every active candidate "
                     "mapping was checked against its stored Goodreads book title and the "
                     "title on its cached work-quotes page.\n\n")
        handle.write(f"- Candidates audited: {len(rows)}\n")
        handle.write(f"- Mapped and passed: {counts['pass']}\n")
        handle.write(f"- Passed with documented title alias: {counts['pass_alias']}\n")
        handle.write(f"- Mismatches staged for refetch: {counts['mismatch']}\n")
        handle.write(f"- Unmapped candidates: {counts['unmapped']}\n")
        handle.write(f"- Needs review because work page was unavailable: {counts['review']}\n\n")
        handle.write("Corrected quote files are staged here and must not replace production "
                     "quote rows until the affected books are reclassified.\n\n")
        handle.write("## Mismatches\n\n")
        for row in mismatches:
            handle.write(f"- **{row['title']}** ({row['year']}, {row['author']}): "
                         f"book `{row['gr_title']}`; work `{row['work_page_title']}`. "
                         f"{row['reason']}\n")

    print(f"audited {len(rows)} candidates: " + ", ".join(
        f"{key}={counts[key]}" for key in ("pass", "pass_alias", "mismatch", "unmapped", "review")))
    print(f"audit -> {audit_path}")
    print(f"refetch sample ({len(mismatches)}) -> {sample_path}")
    print(f"report -> {report_path}")


if __name__ == "__main__":
    main()
