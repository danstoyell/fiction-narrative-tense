"""Apply METHODOLOGY thresholds to agent classifications -> per-book labels.

Reads data/classified/*.json, joins to data/books_topn.csv, emits a labelled
table plus the abstention accounting. Abstentions are reported, never dropped:
if books that fail the quote threshold differ systematically from those that
pass, the analysis sample is biased even when every individual label is right.
"""
import csv, json, os, glob, argparse, collections

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

MIN_EVENT_PAST = 5          # >=5 event quotes, >=80% past
MIN_EVENT_PRESENT = 8       # >=8 event quotes, >=85% present
PAST_BAR = 0.80
PRESENT_BAR = 0.85
STRAND_BAR = 0.70           # 70-85% present + memory strand -> PRESENT (flagged)


DOMINANT = 0.80             # a "dual" book this one-sided has a base tense + a strand


def label(ev_past, ev_present, situation, verse):
    """Label the BASE NARRATION, using narrating_situation as the primary signal.

    The quote ratio cannot identify base tense on its own. Golden Girl (73%
    present) and Cloud Cuckoo Land (72% present) are a point apart and
    structurally opposite: Golden Girl alternates tense across the main
    narrative, while Cloud Cuckoo Land is present-narrated with a past-tense
    tale embedded inside it. A threshold on the ratio cannot separate those.

    The ratio is also partly an artifact of the source: Goodreads quotes are
    selected for quotability, and an embedded fable is unusually quotable, so
    how much past appears in the sample tracks what readers chose to excerpt.

    `narrating_situation` is the agent's holistic read of the text, recorded
    independently of the counts, and it separates these books cleanly where the
    ratio does not. So: situation sets the base tense, the ratio sets confidence
    and flags disagreement.
    """
    n = ev_past + ev_present
    if verse:
        return "EXCLUDED-verse", "not prose fiction", ""
    if n < MIN_EVENT_PAST:
        return "INSUFFICIENT", f"only {n} event quotes", ""
    p_pres = ev_present / n

    if situation == "retrospective":
        base = "PAST"
    elif situation == "simultaneous":
        base = "PRESENT"
    elif situation == "dual":
        # A genuinely dual book shows a real split. One this lopsided has a base
        # tense and a strand -- Project Hail Mary is 96% present with a past Earth
        # thread, which is a strand, not co-equal duality.
        base = ("PRESENT" if p_pres >= DOMINANT else
                "PAST" if p_pres <= 1 - DOMINANT else "DUAL")
    else:
        return "UNCLEAR", f"situation={situation!r}", ""

    # Confidence: does the quote ratio corroborate the structural read?
    agrees = (base == "PAST" and p_pres <= 0.35) or \
             (base == "PRESENT" and p_pres >= 0.65) or base == "DUAL"
    conf = "high" if (agrees and n >= MIN_EVENT_PRESENT) else \
           "med" if agrees else "CONFLICT"
    why = f"{1-p_pres:.0%} past / {p_pres:.0%} present of {n}, situation={situation}"
    return base, why, conf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stratum", default="top2021")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    books = {r["sample_id"]: r for r in csv.DictReader(
        open(os.path.join(DATA, "books_topn.csv"), encoding="utf-8"))}
    qcount = collections.Counter(
        r["sample_id"] for r in csv.DictReader(
            open(os.path.join(DATA, "quotes_topn.csv"), encoding="utf-8")))

    rows = []
    for p in sorted(glob.glob(os.path.join(DATA, "classified", "*.json"))):
        d = json.load(open(p))
        sid = d.get("sample_id", "")
        if not sid.startswith(a.stratum):
            continue
        qs = d.get("quotes", [])
        bk = collections.Counter(q.get("bucket", "") for q in qs)
        ev = [q for q in qs if q.get("bucket") == "event"]
        ev_past = sum(1 for q in ev if q.get("tense") == "past")
        ev_pres = sum(1 for q in ev if q.get("tense") == "present")
        # A book is verse only if MOST quotes carry the verdict marker. Matching
        # the bare substring "verse" flagged novels whose notes mentioned an
        # embedded Tennyson quotation or an epigraph -- "universe", "reverse" and
        # "quoted verse" all contain it. The judgment is per book, not per note.
        verse_notes = sum(1 for q in qs
                          if "not prose fiction" in (q.get("note") or "").lower())
        verse = bool(qs) and verse_notes > len(qs) / 2
        sit = d.get("narrating_situation", "")
        lab, why, conf = label(ev_past, ev_pres, sit, verse)
        b = books.get(sid, {})
        rows.append(dict(
            sample_id=sid, title=b.get("title", sid.split(":")[-1])[:40],
            author=b.get("author", "")[:24], n_quotes=len(qs),
            event=bk["event"], gnomic=bk["gnomic"], dialogue=bk["dialogue"],
            paratext=bk["paratext"], unclear=bk["unclear"],
            ev_past=ev_past, ev_present=ev_pres,
            pct_present=(ev_pres / (ev_past + ev_pres)) if (ev_past + ev_pres) else "",
            situation=sit, label=lab, confidence=conf, why=why))

    rows.sort(key=lambda r: (r["label"], -r["n_quotes"]))
    out = a.out or os.path.join(DATA, f"labels_{a.stratum}.csv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    print(f"{'label':<16}{'n':>3}  books")
    by = collections.defaultdict(list)
    for r in rows:
        by[r["label"]].append(r)
    for lab in sorted(by):
        print(f"  {lab:<14}{len(by[lab]):>3}  " + ", ".join(x["title"][:22] for x in by[lab][:4])
              + (" ..." if len(by[lab]) > 4 else ""))

    conflicts = [r for r in rows if r["confidence"] == "CONFLICT"]
    if conflicts:
        print("\n  CONFLICT -- structural read disagrees with the quote ratio:")
        for r in conflicts:
            print(f"    {r['title'][:32]:34s} {r['label']:<8} {r['why']}")

    prose = [r for r in rows if r["label"] not in ("EXCLUDED-verse",)]
    labelled = [r for r in prose if r["label"] in ("PAST", "PRESENT", "DUAL")]
    pres = [r for r in labelled if r["label"] == "PRESENT"]
    print(f"\n  classified files      : {len(rows)}")
    print(f"  prose fiction         : {len(prose)}")
    print(f"  yielding a label      : {len(labelled)}")
    dual = [r for r in labelled if r["label"] == "DUAL"]
    determinate = [r for r in labelled if r["label"] in ("PAST", "PRESENT")]
    print(f"  determinate base tense: {len(determinate)}   (dual, no single base: {len(dual)})")
    for name, denom in (("of all labelled  ", labelled), ("of determinate   ", determinate)):
        if denom:
            p = len(pres) / len(denom)
            se = (p * (1 - p) / len(denom)) ** 0.5
            print(f"  PRESENT {name}: {p:>5.1%}  "
                  f"(95% CI {max(0,p-1.96*se):.0%}-{min(1,p+1.96*se):.0%}, n={len(denom)})")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
