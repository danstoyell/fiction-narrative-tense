"""Apply METHODOLOGY.md thresholds to classified quotes -> data/labels.csv

Reads data/quotes.csv AFTER bucket/tense have been filled in by reading.
Thresholds are asymmetric: present-tense evidence is contaminated by gnomic
present, so it needs a higher bar than past.

A split result is NOT automatically 'low confidence'. Splits have three causes
and only one is uncertainty, so this script emits SPLIT_REVIEW and expects a
human to record which -- dual (diary/epistolary: recounting vs writing-moment),
mixed (strand/frame/embedded text), or genuinely low confidence.
"""
import csv, os, argparse
from collections import defaultdict

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

MIN_PAST, PCT_PAST = 5, 0.80
MIN_PRESENT, PCT_PRESENT = 8, 0.85
MIN_SPLIT, PCT_MINORITY = 8, 0.25
MIN_LOWCONF = 10

FIELDS = ["sample_id", "stratum", "title", "author", "year", "gr_ratings",
          "resolve_confidence", "n_quotes", "n_dialogue", "n_gnomic", "n_event",
          "n_past", "n_present", "pct_present", "label", "needs_review"]


def classify(n_event, n_past, n_present):
    if n_event < MIN_PAST:
        return "INSUFFICIENT", "fetch more pages, or abstain"
    pp = n_present / n_event if n_event else 0
    if n_event >= MIN_PAST and (n_past / n_event) >= PCT_PAST:
        return "PAST", ""
    if n_event >= MIN_PRESENT and pp >= PCT_PRESENT:
        return "PRESENT", ""
    if n_event >= MIN_SPLIT and min(pp, 1 - pp) >= PCT_MINORITY:
        return "SPLIT_REVIEW", "classify as dual (diary) / mixed (strand) / low-confidence"
    if n_event >= MIN_LOWCONF:
        return "LOW_CONFIDENCE", ""
    return "INSUFFICIENT", "below thresholds; fetch more"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quotes", default=os.path.join(DATA, "quotes.csv"))
    ap.add_argument("--books", default=os.path.join(DATA, "books.csv"))
    ap.add_argument("--out", default=os.path.join(DATA, "labels.csv"))
    args = ap.parse_args()

    books = {r["sample_id"]: r for r in csv.DictReader(open(args.books, encoding="utf-8"))}
    agg = defaultdict(lambda: defaultdict(int))
    unclassified = 0
    for q in csv.DictReader(open(args.quotes, encoding="utf-8")):
        a = agg[q["sample_id"]]
        a["n_quotes"] += 1
        b = (q.get("bucket") or "").strip().lower()
        if not b:
            unclassified += 1
            continue
        a["n_" + b] = a["n_" + b] + 1
        if b == "event":
            t = (q.get("tense") or "").strip().lower()
            if t in ("past", "present"):
                a["n_" + t] += 1

    rows = []
    for sid, b in books.items():
        a = agg.get(sid, {})
        n_event = a.get("n_event", 0)
        n_past, n_present = a.get("n_past", 0), a.get("n_present", 0)
        lab, note = classify(n_event, n_past, n_present)
        rows.append(dict(
            sample_id=sid, stratum=b["stratum"], title=b["title"], author=b["author"],
            year=b.get("year", ""), gr_ratings=b.get("gr_ratings", ""),
            resolve_confidence=b.get("resolve_confidence", ""),
            n_quotes=a.get("n_quotes", 0), n_dialogue=a.get("n_dialogue", 0),
            n_gnomic=a.get("n_gnomic", 0), n_event=n_event, n_past=n_past,
            n_present=n_present,
            pct_present=round(n_present / n_event, 3) if n_event else "",
            label=lab, needs_review=note))

    rows.sort(key=lambda r: (r["stratum"], r["sample_id"]))
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    tally = defaultdict(int)
    for r in rows:
        tally[r["label"]] += 1
    print(f"wrote {len(rows)} rows -> {args.out}")
    if unclassified:
        print(f"NOTE: {unclassified} quotes still have an empty bucket (unclassified)")
    print("\nlabel distribution:")
    for k in sorted(tally, key=lambda x: -tally[x]):
        print(f"  {k:16s} {tally[k]:>4}")
    lab = [r for r in rows if r["label"] in ("PAST", "PRESENT")]
    if lab:
        print(f"\nabstention rate: {1 - len(lab)/len(rows):.1%} "
              f"({len(rows)-len(lab)} of {len(rows)} unlabelled)")
        print("NOTE: abstentions are data. If they correlate with stratum or "
              "ratings, the analysis sample is biased even when every label is right.")


if __name__ == "__main__":
    main()
