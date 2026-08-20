"""Build the Booktense report: trend chart, method, limits, and the full quote explorer.

One page, two builds, both written to the repo root:

  trend.html        data inlined -- no server, publishable as an artifact
  trend_local.html  fetches ./raw_data/report_data.json -- always current

The local page needs an origin so `fetch` is not CORS-blocked:

    python3 -m http.server 8000      # then localhost:8000/trend_local.html

Every number on the page -- year counts, era shares, p-values, coverage, abstentions --
is computed here from raw_data/, and labels come from analyze_year rather than a copy of
its rules. Nothing on the page is hand-maintained, so it cannot drift. Rebuild with:

    python3 analysis/build_report.py
"""
import csv, json, glob, os, math, collections, datetime
from analyze_year import tally, label

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "raw_data")
MANUAL_LABEL_OVERRIDES = os.path.join(DATA, "manual_label_overrides.json")
YEARS = list(range(2016, 2026))
ERA_SPLIT = 2020          # first year of the later era

# Internal source cohorts preserve crawl provenance. They are not all literal top-N samples:
# historical years were extended toward annual usable-label targets, while 2016--2025 uses
# a fixed top-30 candidate pool and classifies every quote-eligible title.
SOURCES = [
    dict(key="pilot", books=["books_top3_1931_1995.csv", "books_top3_1931_1995_zero_label_more.csv",
                              "books_top3_1931_1995_zero_label_final.csv",
                              "books_top3_1931_1995_under_two_more.csv",
                              "books_top3_1931_1995_zero_label_round2.csv",
                              "books_top3_1931_1995_zero_label_round3.csv"],
         quotes=["quotes_top3_1931_1995.csv", "quotes_top3_1931_1995_zero_label_more.csv",
                 "quotes_top3_1931_1995_zero_label_final.csv",
                 "quotes_top3_1931_1995_under_two_more.csv",
                 "quotes_top3_1931_1995_zero_label_round2.csv",
                 "quotes_top3_1931_1995_zero_label_round3.csv"],
         dirs=["classified_top3_1931_1995_first31", "classified_top3_1931_1995_rest",
               "classified_top3_1931_1995_zero_label_more", "classified_top3_1931_1995_zero_label_final",
               "classified_top3_1931_1995_zero_label_final_rest",
               "classified_top3_1931_1995_under_two_more",
               "classified_top3_1931_1995_resolution_corrections",
               "classified_top3_1931_1995_zero_label_round*"],
         lo=1931, hi=1995),
    dict(key="modern", books=["books_topn.csv"], quotes=["quotes_topn.csv"],
         dirs=["classified"], lo=2016, hi=2025),
    # Directories are globbed, not listed: batches land in new folders as labelling
    # proceeds, and an earlier version of this file silently dropped two of them.
    dict(key="hist",
         books=["books_topn5_1996_2016.csv", "books_topn5_more_1996_2015.csv",
                "books_topn5_1996_2015_to10.csv", "books_topn5_1996_2015_to10_more.csv",
                "books_topn5_1996_2015_to10_final.csv",
                "books_topn5_1996_2015_to10_round3.csv",
                "books_topn5_1996_2015_to10_round4.csv",
                "books_topn5_1996_2015_to10_round5.csv",
                "books_topn5_1996_2015_to10_round6.csv",
                "books_topn5_1996_2015_to10_round7.csv"],
         quotes=["quotes_topn5_1996_2016.csv", "quotes_topn5_more_1996_2015.csv",
                 "quotes_topn5_1996_2015_to10.csv", "quotes_topn5_1996_2015_to10_more.csv",
                 "quotes_topn5_1996_2015_to10_final.csv",
                 "quotes_topn5_1996_2015_to10_round3.csv",
                 "quotes_topn5_1996_2015_to10_round4.csv",
                 "quotes_topn5_1996_2015_to10_round5.csv",
                 "quotes_topn5_1996_2015_to10_round6.csv",
                 "quotes_topn5_1996_2015_to10_round7.csv"],
         dirs=["classified_topn5_*"], lo=1996, hi=2015),
]
def group(lab):
    """Three display classes plus abstention. DUAL and verse both read as OTHER."""
    if lab in ("PAST", "PRESENT"):
        return lab
    if lab in ("DUAL", "EXCLUDED-verse"):
        return "OTHER"
    return "ABSTAIN"


# ---------------------------------------------------------------- data

def load():
    """Every classified book, tagged with its internal source cohort."""
    rows, missing = [], 0
    manual_overrides = json.load(open(MANUAL_LABEL_OVERRIDES, encoding="utf-8")) \
        if os.path.exists(MANUAL_LABEL_OVERRIDES) else {}
    frame_n = collections.Counter()
    skipped = collections.Counter()
    for src in SOURCES:
        books = {}
        for f in src["books"]:
            for r in csv.DictReader(open(os.path.join(DATA, f), encoding="utf-8")):
                books[r["sample_id"]] = r
        # Keyed by (sample_id, quote_id): crawl.py numbers quote_id sequentially
        # *within a single batch CSV*, restarting at q00001 per file. A frame
        # assembled from several batch files (pilot, hist) reuses the same ids
        # across unrelated books, so quote_id alone collides and silently
        # overwrites another book's text with last-file-loaded-wins.
        qtext = {}
        for f in src["quotes"]:
            for r in csv.DictReader(open(os.path.join(DATA, f), encoding="utf-8")):
                qtext[(r["sample_id"], r["quote_id"])] = r["quote_text"]
        for sid in books:
            y = sid[3:7]
            if y.isdigit() and src["lo"] <= int(y) <= src["hi"]:
                frame_n[src["key"]] += 1
        seen = set()
        paths = []
        for sub in src["dirs"]:
            paths += sorted(glob.glob(os.path.join(DATA, sub, "*.json")))
        for p in sorted(set(paths)):
            if True:
                d = json.load(open(p, encoding="utf-8"))
                sid = d.get("sample_id", "")
                bk = books.get(sid)
                if sid in seen:
                    skipped[src["key"] + ":duplicate"] += 1
                    continue
                if not bk:
                    skipped[src["key"] + ":no-book-row"] += 1
                    continue
                seen.add(sid)
                year = int(sid[3:7])
                if not (src["lo"] <= year <= src["hi"]):
                    skipped[src["key"] + ":out-of-range"] += 1
                    continue
                qs = d.get("quotes", [])
                e_past, e_pres, b_past, b_pres = tally(qs, "include")
                verse_notes = sum(1 for q in qs
                                  if "not prose fiction" in (q.get("note") or "").lower())
                verse = bool(qs) and verse_notes > len(qs) / 2
                lab, why, conf = label(e_past + b_past, e_pres + b_pres,
                                       d.get("narrating_situation", ""), verse)
                if override := manual_overrides.get(sid):
                    lab = override["label"]
                    why = override["note"]
                    conf = "manual"
                bkt = collections.Counter(q.get("bucket", "") for q in qs)
                quotes = []
                for q in qs:
                    qid = q.get("quote_id", "")
                    txt = qtext.get((sid, qid), "")
                    if not txt:
                        missing += 1
                    quotes.append({"id": qid, "b": q.get("bucket", ""),
                                   "t": q.get("tense", "") or "",
                                   "bt": q.get("beat_tense", "") or "",
                                   "n": q.get("note", "") or "", "x": txt})
                rows.append({
                    "sid": sid, "year": year, "frame": src["key"],
                    "period": str(year),
                    "title": bk.get("title", ""), "author": bk.get("author", ""),
                    "label": group(lab), "raw": lab, "conf": conf,
                    "sit": d.get("narrating_situation", ""),
                    "why": why, "note": d.get("agent_note", "") or "",
                    "n": len(qs), "ev": [e_past, e_pres], "bt": [b_past, b_pres],
                    "bk": [bkt["event"], bkt["dialogue"], bkt["gnomic"],
                           bkt["paratext"], bkt["unclear"]],
                    "q": quotes,
                })
    rows.sort(key=lambda r: (r["year"], r["title"]))
    # Never drop a classified book without saying so.
    for k, v in sorted(skipped.items()):
        if not k.endswith(":no-book-row") or v:
            print(f"  NOTE: skipped {v} classified file(s) [{k}]")
    return rows, missing, dict(frame_n), dict(skipped)


def wilson_interval(successes, n, z=1.959963984540054):
    """Wilson score interval for a binomial proportion."""
    if n <= 0:
        return None
    proportion = successes / n
    denominator = 1 + z ** 2 / n
    center = (proportion + z ** 2 / (2 * n)) / denominator
    half_width = z * math.sqrt(
        proportion * (1 - proportion) / n + z ** 2 / (4 * n ** 2)
    ) / denominator
    return max(0, center - half_width), min(1, center + half_width)


def periods(rows, span=1, lo=1996, hi=2025):
    """Chart/table rows grouped into evenly sized periods for an inclusive range."""
    if span not in (1, 3, 5, 10):
        raise ValueError(f"unsupported period span: {span}")
    by_year = collections.defaultdict(collections.Counter)
    for r in rows:
        by_year[r["year"]][r["label"]] += 1
        by_year[r["year"]]["cls"] += 1
    out = []
    for start in range(lo, hi + 1, span):
        end = min(hi, start + span - 1)
        c = collections.Counter()
        for year in range(start, end + 1):
            c.update(by_year[year])
        key = str(start) if start == end else f"{start}\u2013{end}"
        short = f"'{str(start)[2:]}" if start == end else f"{str(start)[2:]}\u2013{str(end)[2:]}"
        frame = "pilot" if end <= 1995 else "hist" if end <= 2015 else "modern" if start >= 2016 else "mixed"
        n = c["PAST"] + c["PRESENT"] + c["OTHER"]
        interval = wilson_interval(c["PRESENT"], n)
        out.append({"y": key, "short": short, "lo": start, "hi": end,
                    "mid": (start + end) / 2, "span": end - start + 1, "frame": frame,
                    "past": c["PAST"], "other": c["OTHER"], "pres": c["PRESENT"],
                    "ab": c["ABSTAIN"], "cls": c["cls"], "n": n,
                    "ci_lo": interval[0] if interval else None,
                    "ci_hi": interval[1] if interval else None})
    return out


def trend(rows, frame=None):
    """Weighted linear trend in present-share against year, optionally by source cohort."""
    sel = [r for r in rows if r["label"] in ("PAST", "PRESENT", "OTHER")
           and (frame is None or r["frame"] == frame)]
    if not sel:
        return None
    by = collections.defaultdict(collections.Counter)
    for r in sel:
        by[r["year"]]["n"] += 1
        by[r["year"]]["p"] += (r["label"] == "PRESENT")
    ys = sorted(by)
    tp = sum(by[y]["p"] for y in ys)
    tn = sum(by[y]["n"] for y in ys)
    pbar = tp / tn
    xbar = sum(y * by[y]["n"] for y in ys) / tn
    num = sum((y - xbar) * (by[y]["p"] - by[y]["n"] * pbar) for y in ys)
    den = sum(by[y]["n"] * (y - xbar) ** 2 for y in ys)
    if den == 0 or pbar in (0, 1):
        return None
    z = num / math.sqrt(pbar * (1 - pbar) * den)
    return dict(z=z, p=math.erfc(abs(z) / math.sqrt(2)), slope=num / den,
                n=tn, pres=tp, share=pbar)


def era(rows):
    """Later vs earlier within the fixed top-30 candidate cohort."""
    sel = [r for r in rows if r["frame"] == "modern"
           and r["label"] in ("PAST", "PRESENT", "OTHER")]
    def tot(g):
        n = len(g); return sum(1 for r in g if r["label"] == "PRESENT"), n
    p1, n1 = tot([r for r in sel if r["year"] < ERA_SPLIT])
    p2, n2 = tot([r for r in sel if r["year"] >= ERA_SPLIT])
    P1, P2 = p1 / n1, p2 / n2
    pp = (p1 + p2) / (n1 + n2)
    z = (P2 - P1) / math.sqrt(pp * (1 - pp) * (1 / n1 + 1 / n2))
    return dict(p1=p1, n1=n1, P1=P1, p2=p2, n2=n2, P2=P2,
                z=z, p=math.erfc(abs(z) / math.sqrt(2)), labelled=n1 + n2)


def nonmonotonic(per):
    """A pre-2020 point that outranks later ones -- the page's own honesty check."""
    pct = lambda r: (r["pres"] / r["n"]) if r["n"] else 0
    early = [r for r in per if r["frame"] == "modern" and float(r["mid"]) < ERA_SPLIT]
    late = [r for r in per if r["frame"] == "modern" and float(r["mid"]) >= ERA_SPLIT]
    if not early or not late:
        return None, [], pct
    hi = max(early, key=pct)
    below = sorted([r for r in late if pct(r) <= pct(hi)], key=lambda r: r["mid"])
    return hi, below, pct


def mark_survival():
    """Share of quotes that kept their quotation marks across source cohorts."""
    import re as _re
    lo, hi = 100.0, 0.0
    for src in SOURCES:
        by = collections.defaultdict(lambda: [0, 0])
        for f in src["quotes"]:
            for r in csv.DictReader(open(os.path.join(DATA, f), encoding="utf-8")):
                y = r["sample_id"][3:7]
                if not y.isdigit() or not (src["lo"] <= int(y) <= src["hi"]):
                    continue
                by[y][1] += 1
                if _re.search(r'[\u201c\u201d"]', r["quote_text"]):
                    by[y][0] += 1
        for m, t in by.values():
            if t:
                lo = min(lo, 100 * m / t); hi = max(hi, 100 * m / t)
    return lo, hi


def gnomic_share(rows):
    g = sum(r["bk"][2] for r in rows)
    n = sum(r["n"] for r in rows)
    return 100 * g / n if n else 0


def quote_summary(rows):
    """Top-level quote buckets, with the dialogue-only beat subdivision."""
    buckets = collections.Counter()
    dialogue_beats = collections.Counter()
    for row in rows:
        for quote in row["q"]:
            buckets[quote["b"]] += 1
            if quote["b"] == "dialogue":
                dialogue_beats[quote["bt"] or "none"] += 1
    return {
        "total": sum(buckets.values()),
        "buckets": {bucket: buckets[bucket] for bucket in
                    ("event", "dialogue", "gnomic", "paratext", "unclear")},
        "dialogueBeats": {beat: dialogue_beats[beat] for beat in
                          ("past", "present", "none")},
    }


# ---------------------------------------------------------------- page

CSS = """
  :root{
    --ink:#12161C; --paper:#F6F7F9; --surface:#FFFFFF; --line:#DFE3E8;
    --muted:#59626E; --faint:#858E9A;
    --past:#A8763C; --present:#1F7A7A; --dual:#98A0AA; --flag:#B44A2C;
    --quote-event:#7EC1BD; --quote-gnomic:#D7B177; --quote-paratext:#B6BEC8; --quote-unclear:#E2A08B;
    --dialogue-none:#D4D9E0; --dialogue-past:#AAA0D0; --dialogue-present:#9CB8EA;
    --serif:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;
    --sans:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
    --mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
  }
  @media (prefers-color-scheme:dark){
    :root{--ink:#E6E8EC;--paper:#0F1216;--surface:#161A20;--line:#282E37;
          --muted:#98A1AD;--faint:#6B7480;--past:#D9A163;--present:#4FB3B3;
          --dual:#737B86;--flag:#DE7A56;--quote-event:#4FA29C;--quote-gnomic:#C79757;--quote-paratext:#77818E;--quote-unclear:#C96E55;
          --dialogue-none:#77818E;--dialogue-past:#A99AE0;--dialogue-present:#84A9F6;}
  }
  :root[data-theme="dark"]{--ink:#E6E8EC;--paper:#0F1216;--surface:#161A20;--line:#282E37;
    --muted:#98A1AD;--faint:#6B7480;--past:#D9A163;--present:#4FB3B3;--dual:#737B86;--flag:#DE7A56;
    --quote-event:#4FA29C;--quote-gnomic:#C79757;--quote-paratext:#77818E;--quote-unclear:#C96E55;
    --dialogue-none:#77818E;--dialogue-past:#A99AE0;--dialogue-present:#84A9F6;}
  :root[data-theme="light"]{--ink:#12161C;--paper:#F6F7F9;--surface:#FFFFFF;--line:#DFE3E8;
    --muted:#59626E;--faint:#858E9A;--past:#A8763C;--present:#1F7A7A;--dual:#98A0AA;--flag:#B44A2C;
    --quote-event:#7EC1BD;--quote-gnomic:#D7B177;--quote-paratext:#B6BEC8;--quote-unclear:#E2A08B;
    --dialogue-none:#D4D9E0;--dialogue-past:#AAA0D0;--dialogue-present:#9CB8EA;}

  body{background:var(--paper);color:var(--ink);font-family:var(--sans);line-height:1.6;
       -webkit-font-smoothing:antialiased;}
  .wrap{max-width:58rem;margin:0 auto;padding:3.5rem 1.5rem 6rem;
        display:flex;flex-direction:column;gap:3.25rem;}
  .wide{max-width:76rem;}
  .eyebrow{font-family:var(--mono);font-size:.68rem;letter-spacing:.14em;
           text-transform:uppercase;color:var(--faint);}
  h1{font-family:var(--serif);font-size:clamp(2rem,5vw,2.9rem);line-height:1.08;
     font-weight:600;text-wrap:balance;margin:.5rem 0 0;letter-spacing:-.015em;
     max-width:30ch;}
  h2{font-family:var(--serif);font-size:1.45rem;font-weight:600;margin:0;text-wrap:balance;}
  h3{font-family:var(--sans);font-size:.82rem;font-weight:650;margin:0;
     letter-spacing:.02em;color:var(--ink);}
  p{margin:0;max-width:64ch;}
  section{display:flex;flex-direction:column;gap:1rem;}
  .lede{font-size:1.08rem;color:var(--muted);max-width:66ch;}
  strong{font-weight:650;}

  .chartbox{background:var(--surface);border:1px solid var(--line);border-radius:2px;
            padding:1.5rem 1.3rem 1.1rem;overflow-x:auto;}
  .chart-controls{display:flex;align-items:center;justify-content:flex-end;gap:.45rem;
                  margin-bottom:.7rem;font-size:.92rem;color:var(--muted);}
  .chart-title{margin:0 0 .45rem;font-size:1.35rem;}
  #chart{display:block;min-width:44rem;width:100%;height:auto;}
  .legend{display:flex;flex-wrap:wrap;gap:1.3rem;margin-top:.35rem;font-size:.9rem;color:var(--muted);}
  .legend i{display:inline-block;width:.8rem;height:.8rem;border-radius:1px;
            margin-right:.42rem;vertical-align:-1px;}
  .quote-chart{background:var(--surface);border:1px solid var(--line);border-radius:2px;
               padding:1.05rem 1.1rem .85rem;}
  .quote-chart p{font-size:.84rem;color:var(--muted);max-width:68ch;}
  #quote-chart{display:block;width:100%;height:auto;margin:.35rem 0 .2rem;}
  .quote-legend{display:flex;flex-wrap:wrap;gap:.45rem 1rem;margin-top:.25rem;
                font-size:.76rem;color:var(--muted);}
  .quote-legend span{white-space:nowrap;}
  .quote-legend i{display:inline-block;width:.65rem;height:.65rem;border-radius:1px;
                  margin-right:.32rem;vertical-align:-1px;}

  .tw{overflow-x:auto;border:1px solid var(--line);border-radius:2px;background:var(--surface);}
  table{border-collapse:collapse;width:100%;font-size:.81rem;}
  th{font-family:var(--mono);font-size:.62rem;letter-spacing:.1em;text-transform:uppercase;
     color:var(--muted);text-align:right;font-weight:600;padding:.7rem .8rem;
     border-bottom:1px solid var(--line);white-space:nowrap;background:var(--surface);}
  th:first-child,th.l{text-align:left;}
  td{padding:.52rem .8rem;border-bottom:1px solid var(--line);text-align:right;
     font-family:var(--mono);font-variant-numeric:tabular-nums;white-space:nowrap;
     vertical-align:top;}
  td:first-child,td.l{text-align:left;font-family:var(--sans);}
  td.l{white-space:normal;}
  tbody tr:last-child td{border-bottom:none;}

  .split{display:grid;grid-template-columns:repeat(auto-fit,minmax(15rem,1fr));gap:1rem;}
  .card{background:var(--surface);border:1px solid var(--line);border-radius:2px;
        padding:1.1rem 1.2rem;display:flex;flex-direction:column;gap:.45rem;}
  .big{font-family:var(--mono);font-size:1.65rem;font-variant-numeric:tabular-nums;
       letter-spacing:-.02em;line-height:1;}
  .card p{font-size:.85rem;color:var(--muted);}

  td.def{text-align:left;font-family:var(--sans);white-space:normal;color:var(--muted);
         line-height:1.5;min-width:22rem;}
  td.yes{font-size:.7rem;letter-spacing:.05em;text-transform:uppercase;color:var(--present);}
  td.no{color:var(--faint);}
  .ladder{margin:0;padding-left:1.35rem;display:flex;flex-direction:column;gap:.7rem;
          max-width:64ch;color:var(--muted);font-size:.92rem;}
  .ladder li::marker{font-family:var(--mono);font-size:.8em;color:var(--faint);}
  .ladder strong{color:var(--ink);}

  .caution{border-left:2px solid var(--flag);padding:.2rem 0 .2rem 1.15rem;
           display:flex;flex-direction:column;gap:.75rem;}
  .caution p{color:var(--muted);font-size:.95rem;max-width:62ch;}
  .caution strong{color:var(--ink);}
  ul{margin:0;padding-left:1.15rem;display:flex;flex-direction:column;gap:.65rem;
     max-width:64ch;color:var(--muted);font-size:.92rem;}
  li strong{color:var(--ink);}

  /* ---- explorer ---- */
  .controls{display:flex;flex-wrap:wrap;gap:.55rem;align-items:center;
            background:var(--surface);border:1px solid var(--line);border-radius:2px;
            padding:.75rem .85rem;position:sticky;top:0;z-index:6;}
  select,input[type=search]{font-family:var(--sans);font-size:.82rem;color:var(--ink);
    background:var(--paper);border:1px solid var(--line);border-radius:2px;
    padding:.36rem .45rem;}
  input[type=search]{flex:1 1 15rem;min-width:9rem;}
  .count{font-family:var(--mono);font-size:.73rem;color:var(--muted);margin-left:auto;
         white-space:nowrap;}
  button.reset{font-family:var(--sans);font-size:.78rem;color:var(--muted);background:none;
    border:1px solid var(--line);border-radius:2px;padding:.36rem .6rem;cursor:pointer;}
  button.reset:hover{color:var(--ink);border-color:var(--muted);}
  #xtable th{cursor:pointer;user-select:none;font-size:.61rem;}
  #xtable th:hover{color:var(--ink);}
  #xtable th .ar{color:var(--present);font-size:.85em;}
  #xtable td{padding:.45rem .7rem;font-size:.82rem;}
  tr.book{cursor:pointer;}
  tr.book:hover>td{background:color-mix(in srgb,var(--present) 6%,transparent);}
  tr.book.open>td{background:color-mix(in srgb,var(--present) 10%,transparent);}
  .ttl{font-weight:600;}
  .au{color:var(--muted);font-size:.92em;}
  .caret{display:inline-block;width:.75em;color:var(--faint);transition:transform .12s ease;}
  tr.book.open .caret{transform:rotate(90deg);color:var(--present);}
  .pill{display:inline-block;font-family:var(--mono);font-size:.63rem;letter-spacing:.06em;
        text-transform:uppercase;padding:.12rem .4rem;border-radius:2px;
        border:1px solid currentColor;line-height:1.4;}
  .l-PAST{color:var(--past);} .l-PRESENT{color:var(--present);}
  .l-DUAL{color:var(--dual);}
  .l-INSUFFICIENT,.l-UNCLEAR,.l-EXCLUDED-verse{color:var(--faint);}
  .c-CONFLICT{color:var(--flag);font-weight:600;}
  .c-high,.c-med,.c-none{color:var(--faint);}
  tr.detail-row>td{background:var(--paper);padding:0;}
  .detail{padding:.1rem 0 1.1rem;}
  .anote{font-size:.83rem;color:var(--muted);max-width:82ch;padding:.8rem .9rem .2rem;
         white-space:normal;font-family:var(--sans);text-align:left;line-height:1.6;}
  .anote strong{color:var(--ink);}
  .qlist{display:flex;flex-direction:column;padding:.45rem .6rem 0;}
  .q{display:grid;grid-template-columns:6rem 1fr;gap:.8rem;padding:.55rem .35rem;
     border-top:1px solid var(--line);text-align:left;white-space:normal;}
  .qmeta{display:flex;flex-direction:column;gap:.25rem;align-items:flex-start;}
  .qid{font-family:var(--mono);font-size:.61rem;color:var(--faint);}
  .qtx{font-family:var(--serif);font-size:.93rem;line-height:1.55;color:var(--ink);
       white-space:pre-wrap;}
  .qnote{font-family:var(--sans);font-size:.76rem;color:var(--muted);margin-top:.4rem;
         padding-left:.7rem;border-left:2px solid var(--line);}
  .b-event{color:var(--present);} .b-dialogue{color:var(--ink);}
  .b-gnomic{color:var(--past);} .b-paratext,.b-unclear{color:var(--faint);}
  .t{font-family:var(--mono);font-size:.61rem;letter-spacing:.04em;color:var(--muted);}
  .empty,.loading{padding:2.5rem 1rem;text-align:center;color:var(--faint);font-size:.9rem;}
  .pager{display:flex;align-items:center;justify-content:center;gap:1rem;padding:.2rem 0;}
  .pg{font-family:var(--sans);font-size:.8rem;color:var(--ink);background:var(--surface);
      border:1px solid var(--line);border-radius:2px;padding:.4rem .8rem;cursor:pointer;}
  .pg:hover:not(:disabled){border-color:var(--present);color:var(--present);}
  .pg:disabled{color:var(--faint);cursor:default;opacity:.5;}
  .pgnum{font-family:var(--mono);font-size:.74rem;color:var(--muted);
         font-variant-numeric:tabular-nums;}
  ul ul{margin-top:.4rem;padding-left:1.05rem;gap:.4rem;font-size:.9rem;}

  footer{border-top:1px solid var(--line);padding-top:1.2rem;font-size:.73rem;
         color:var(--faint);font-family:var(--mono);line-height:1.8;}
  :focus-visible{outline:2px solid var(--present);outline-offset:2px;}
"""


era_p = 0.0


def body(rows, per, pilot, modern, early, recent, p_trend, hist, frame_n, nq, missing, built):
    hi, below, pct = nonmonotonic(per)
    lo_mark, hi_mark = mark_survival()
    cls = len(rows)
    ns = [r["n"] for r in per if r["n"]]
    total_frame = sum(frame_n.values())
    labelled = sum(r["label"] in ("PAST", "PRESENT", "OTHER") for r in rows)
    classified_abstentions = cls - labelled
    not_classified = total_frame - cls
    below_txt = ", ".join(f"{r['y']} ({pct(r):.0%})" for r in below) or "no later point"
    swing = 0
    modern_periods = [r for r in per if r["frame"] == "modern"]
    for i in range(1, len(modern_periods)):
        if modern_periods[i]["n"] and modern_periods[i - 1]["n"]:
            swing = max(swing, abs(pct(modern_periods[i]) - pct(modern_periods[i - 1])))
    gn = gnomic_share(rows)
    hist_txt = (f"{hist['share']:.0%} present across {hist['n']} books"
                if hist else "not enough labelled books")
    n5 = frame_n.get("hist", 0)
    n30 = frame_n.get("modern", 0)
    npilot = frame_n.get("pilot", 0)
    pilot_lbl = "target ≥2 labels/year"
    hist_lbl = "target ≥10 labels/year"
    mod_lbl = "eligible books from top 30/year"

    return f"""
<div class="wrap wide">

<header>
  <div class="eyebrow">Booktense &middot; {cls} books classified &middot; {nq:,} quotes &middot; built {built}</div>
  <h1>Present-tense narration in NYT bestsellers, 1931&ndash;2025</h1>
  <p class="lede">Share of labelled books by the tense of their <em>base narration</em>.
  Choose one-, three-, five-, or ten-year periods across the whole series. Earlier years were
  extended toward annual usable-label targets; 2016 onward uses all quote-eligible books in a
  fixed top-30 candidate pool. Every quote behind every label is in the explorer at the bottom.</p>
</header>

<section>
  <div class="chartbox">
    <div class="chart-controls">
      <label for="range-view">Time range</label>
      <select id="range-view">
        <option value="all">All classified years</option>
        <option value="pilot">1931&ndash;1995 historical sample</option>
        <option value="main">1996&ndash;2025 main study</option>
      </select>
      <label for="period-view">Bucket size</label>
      <select id="period-view">
        <option value="1">1 year</option>
        <option value="3">3 years</option>
        <option value="5">5 years</option>
        <option value="10" selected>10 years</option>
      </select>
    </div>
    <h2 class="chart-title" id="chart-title">Narrative Tense in NYT Bestsellers, 1931&ndash;2025</h2>
    <svg id="chart" viewBox="0 0 980 400" role="img"
         aria-label="Stacked area chart of present, other and past tense share over time, with the present band rising from the baseline"></svg>
    <div class="legend">
      <span><i style="background:var(--present)"></i>Present</span>
      <span><i style="background:var(--dual)"></i>Other &mdash; dual-tense or not prose fiction</span>
      <span><i style="background:var(--past)"></i>Past</span>
    </div>
  </div>
</section>

<section>
  <div class="split">
    <div class="card">
      <h3>1931&ndash;1995</h3>
      <div class="big" style="color:var(--present)">{pilot['share']:.0%}</div>
      <p>present, across {pilot['n']} labelled books</p>
    </div>
    <div class="card">
      <h3>1996&ndash;2019</h3>
      <div class="big" style="color:var(--present)">{early['share']:.0%}</div>
      <p>present, across {early['n']} labelled books</p>
    </div>
    <div class="card">
      <h3>2020&ndash;2025</h3>
      <div class="big" style="color:var(--present)">{recent['share']:.0%}</div>
      <p>present, across {recent['n']} labelled books</p>
    </div>
    <div class="card">
      <h3>Trend within 1996&ndash;2025</h3>
      <div class="big" style="color:var(--present)">{p_trend['slope']:+.1%} a year</div>
      <p>p = {p_trend['p']:.3f}</p>
    </div>
  </div>
</section>

<section>
  <h2>The numbers behind it</h2>
  <div class="tw">
    <table>
      <thead><tr>
        <th class="l">Period</th><th class="l">Selection plan</th><th>Past</th><th>Other</th>
        <th>Present</th><th>n labelled</th><th>% present</th><th>95% Wilson CI</th>
        <th>abstained</th><th>classified</th>
      </tr></thead>
      <tbody id="tbody"></tbody>
    </table>
  </div>
  <p id="point-note" style="font-size:.79rem;color:var(--faint)">Each point rests on {min(ns)}&ndash;{max(ns)}
  labelled books. <strong>Other</strong> covers books with no single base tense and books that
  turned out not to be prose fiction &mdash; Amanda Gorman&rsquo;s verse collections reached
  the hardcover fiction list and sit here rather than being dropped.</p>
</section>

<section>
  <h2>Methodology</h2>
  <p>Each quote is sorted into one bucket. Only two of them carry evidence about the
  narrator&rsquo;s tense &mdash; the other three exist to keep those two clean.</p>

  <div class="tw">
    <table>
      <thead><tr><th class="l">Bucket</th><th class="l">What it is</th><th class="l">Yields</th></tr></thead>
      <tbody>
        <tr><td>event</td>
          <td class="def">A specific character at a specific story-moment, or past-tense
              exposition about the story world</td><td class="yes">tense</td></tr>
        <tr><td>dialogue</td>
          <td class="def">Character speech &mdash; but the narrator&rsquo;s own tag or action
              beat around it still counts</td><td class="yes">beat&nbsp;tense</td></tr>
        <tr><td>gnomic</td>
          <td class="def"><em>Present-tense</em> generalization reaching beyond the story
              world: proverbs, epigraphs, essayistic asides</td><td class="no">&mdash;</td></tr>
        <tr><td>paratext</td>
          <td class="def">Acknowledgments, dedications, jacket copy &mdash; not the novel</td>
          <td class="no">&mdash;</td></tr>
        <tr><td>unclear</td>
          <td class="def">Undecidable from the excerpt alone</td><td class="no">&mdash;</td></tr>
      </tbody>
    </table>
  </div>

  <p>&ldquo;My father is dead&rdquo; is present tense but concerns one person at
  one moment, so it counts. &ldquo;Books, like people, die&rdquo; does not.</p>

  <div class="quote-chart">
    <h3>Quote labels across all classified excerpts</h3>
    <p><strong>Dialogue is one top-level bucket</strong>, outlined below. Within it, gray means
    no narratorial beat; purple and blue mean a past- or present-tense narrator beat.</p>
    <svg id="quote-chart" viewBox="0 0 920 140" role="img"
         aria-label="Stacked bar showing all classified quotes by bucket, with dialogue subdivided by beat tense"></svg>
    <div class="quote-legend" id="quote-legend"></div>
  </div>

  <p>Those two evidence-bearing buckets pool into a single tally, and the book&rsquo;s label
  follows in three steps:</p>

  <ol class="ladder">
    <li><strong>Gate.</strong> Fewer than five tense-bearing quotes and the book abstains
    rather than guessing.</li>
    <li><strong>Base tense.</strong> A holistic read of the narrating situation &mdash;
    recorded independently of the counts &mdash; sets it: <em>retrospective</em> gives past,
    <em>simultaneous</em> gives present, <em>dual</em> gives other unless the tally runs 80%
    one way, which marks a base tense with a strand rather than true duality.</li>
    <li><strong>Confidence.</strong> The tally then either corroborates that read or
    contradicts it, flagging the book for review.</li>
  </ol>

  <p>The counts do not set the label because they cannot. <em>Golden Girl</em> and
  <em>Cloud Cuckoo Land</em> sit one percentage point apart and are structurally opposite
  &mdash; one alternates tense across its main narrative, the other is present-narrated with a
  past tale embedded inside it. No threshold separates those two; reading the narrating
  situation does.</p>
</section>

<section>
  <h2>Raw Data</h2>
  <p>All {cls} classified books and all {nq:,} quotes behind them &mdash; nothing truncated,
  no bucket hidden. Click a row for its quotes, buckets, and the classifier&rsquo;s reasoning.
  Search reaches into quote text and notes, not just titles.</p>

  <div class="controls">
    <select id="fyear"><option value="">All periods</option></select>
    <select id="flabel"><option value="">All labels</option></select>
    <select id="fconf"><option value="">Any confidence</option></select>
    <select id="fsit"><option value="">Any situation</option></select>
    <select id="fbucket"><option value="">Any bucket present</option></select>
    <input type="search" id="fq" placeholder="Search titles, authors, quote text, notes…">
    <button class="reset" id="reset">Reset</button>
    <span class="count" id="count"></span>
  </div>

  <div class="tw">
    <table id="xtable">
      <thead><tr>
        <th class="l" data-k="year">Year <span class="ar"></span></th>
        <th class="l" data-k="title">Book <span class="ar"></span></th>
        <th class="l" data-k="label">Label <span class="ar"></span></th>
        <th class="l" data-k="conf">Conf <span class="ar"></span></th>
        <th class="l" data-k="sit">Situation <span class="ar"></span></th>
        <th data-k="pct">% pres <span class="ar"></span></th>
        <th data-k="ev">Event <span class="ar"></span></th>
        <th data-k="bt">Beats <span class="ar"></span></th>
        <th data-k="n">Quotes <span class="ar"></span></th>
      </tr></thead>
      <tbody id="rows"></tbody>
    </table>
    <div class="loading" id="status">Loading…</div>
  </div>
  <div class="pager" id="pager" hidden>
    <button class="pg" id="prev">&larr; Previous</button>
    <span class="pgnum" id="pgnum"></span>
    <button class="pg" id="next">Next &rarr;</button>
  </div>
</section>

<section>
  <h2>Notes</h2>
  <div class="caution">
    <p><strong>Across 1996&ndash;2025 the rise is statistically detectable</strong> &mdash; a
    linear trend across those years gives p&nbsp;=&nbsp;{p_trend['p']:.3f} on {p_trend['n']} books.
    The two-era split reads p&nbsp;=&nbsp;{era_p:.3f}, but its {ERA_SPLIT - 1}/{ERA_SPLIT}
    boundary was drawn after seeing the data, so lead with the trend.</p>
    <p><strong>Selection depth changes over time.</strong> The 1996&ndash;2015 batches extend
    NYT-ranked candidates toward ten usable labels per year; from 2016 on, all quote-eligible
    books in a fixed top-30 candidate pool are classified. The same label method is applied
    throughout, but the represented depth of the list and annual precision vary.</p>
    <p><strong>Detectable is not monotonic.</strong> Adjacent years swing by as much as
    {swing:.0%}, and {hi['y']} ({pct(hi):.0%}) sits at or above {below_txt}. What the recent
    data supports is a level shift, not a steady year-on-year climb.</p>
  </div>
  <ul>
    <li><strong>Goodreads pull-quotes are a biased source, and the bias runs toward apparent
    present tense.</strong> Everything below is a symptom of reading books through the
    passages readers chose to excerpt:
      <ul style="margin-top:.55rem">
        <li>Quotes are selected for quotability, and quotability loves aphorism &mdash;
        {gn:.0f}% of all quotes are gnomic, timeless-present generalization that says nothing
        about a book&rsquo;s narration. The bucket scheme exists to strip exactly this.</li>
        <li>Quotation marks survive only {lo_mark:.0f}&ndash;{hi_mark:.0f}% of the time, so
        speech and narration often cannot be told apart from the text alone.</li>
        <li>Excerpts arrive clipped mid-sentence, stripping the attribution that would settle
        who is speaking.</li>
        <li>How many quotes a book has tracks its fame, not its prose. Across all annual
        candidate batches, {total_frame - labelled} of {total_frame} selected candidates do
        not yield a usable label, either because they never reach classification or because
        the available evidence requires abstention.</li>
        <li>Nothing marks where in a book a quote came from, so a framed prologue or an
        embedded tale reads the same as the main narration.</li>
      </ul>
    </li>
    <li><strong>Quote-level labels are noisier than tense judgments.</strong> In the latest
    blind reproducibility check over 30 books, Terra and the earlier Sonnet pass agreed on
    83.9% of quote buckets, 99.1% of event tense where both chose event, 98.2% of dialogue-beat
    tense where both chose dialogue, and 86.7% of narrating situations and derived book labels.
    Sonnet is a comparator, not an external accuracy gold standard.</li>
  </ul>
</section>

<footer>
  Selection: NYT Hardcover Fiction &middot; {pilot_lbl} in 1931&ndash;1995 ({npilot} candidates),
  {hist_lbl} in 1996&ndash;2015 ({n5} candidates), fixed top-30 candidate pool in
  2016&ndash;2025 ({n30} candidates)<br>
  Text: Goodreads pull-quotes &middot; Labels: base narration from narrating_situation; event
  quotes and dialogue beats pooled for ratio and confidence<br>
  {total_frame} selected candidates &middot; {cls} classified &middot; {labelled} usable labels
  &middot; {classified_abstentions} classified abstentions &middot; {not_classified} not classified{'' if not missing else f' &middot; {missing} quotes with no text on file'}
</footer>
</div>
"""


APP = r"""
const esc = s => String(s).replace(/[&<>"]/g, c =>
  ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const BUCKETS = ["event","dialogue","gnomic","paratext","unclear"];

function drawChart(A){
  const PILOTLBL=window.__PILOTLBL||"pilot", HISTLBL=window.__HISTLBL||"early", MODLBL=window.__MODLBL||"recent";
  const W=980,H=400,L=52,R=45,T=18,B=52, iw=W-L-R, ih=H-T-B;
  // Points sit at the midpoint of the span each period covers on a real time axis.
  A.forEach(d=>{ d.mid=(d.lo + d.hi + 1)/2;
                 d.pPres=d.n?d.pres/d.n:0; d.pOther=d.n?d.other/d.n:0; });
  const X0=A[0].mid, X1=A[A.length-1].mid;
  const x=v=>L+iw*(v-X0)/(X1-X0), y=v=>T+ih*(1-v);

  const b1=A.map(d=>d.pPres), b2=A.map(d=>d.pPres+d.pOther);
  const zero=A.map(()=>0), one=A.map(()=>1);
  const band=(lo,hi,tok)=>{
    const up=A.map((d,i)=>`${x(d.mid)},${y(hi[i])}`).join(" ");
    const dn=A.map((d,i)=>`${x(d.mid)},${y(lo[i])}`).reverse().join(" ");
    return `<polygon points="${up} ${dn}" fill="var(--${tok})" opacity="0.88"/>`;
  };
  let s="";
  for(let g=0;g<=100;g+=10){
    s+=`<line x1="${L}" x2="${W-R}" y1="${y(g/100)}" y2="${y(g/100)}" stroke="var(--line)" stroke-width="1"/>`;
    s+=`<text x="${L-9}" y="${y(g/100)+4}" text-anchor="end" font-family="var(--mono)" font-size="12" fill="var(--faint)">${g}%</text>`;
    s+=`<text x="${W-R+9}" y="${y(g/100)+4}" text-anchor="start" font-family="var(--mono)" font-size="12" fill="var(--faint)">${g}%</text>`;
  }
  s+=band(zero,b1,"present")+band(b1,b2,"dual")+band(b2,one,"past");
  s+=`<polyline points="${A.map((d,i)=>`${x(d.mid)},${y(b1[i])}`).join(" ")}" fill="none" stroke="var(--surface)" stroke-width="1.6"/>`;
  s+=`<polyline points="${A.map((d,i)=>`${x(d.mid)},${y(b2[i])}`).join(" ")}" fill="none" stroke="var(--surface)" stroke-width="1.2"/>`;

  A.forEach((d,i)=>{
    const cx=x(d.mid);
    // A multi-year bucket spans its full interval on the x-axis.
    if(d.span>1){
      const a=x(d.lo), b=x(d.hi+1);
      s+=`<line x1="${Math.max(a,L)}" x2="${Math.min(b,W-R)}" y1="${H-B+4}" y2="${H-B+4}"
           stroke="var(--faint)" stroke-width="1" opacity="0.5"/>`;
    }
    const xLabel=d.span===10 ? `${d.lo}–${d.hi}` : d.short;
    s+=`<text x="${cx}" y="${H-B+18}" text-anchor="middle" font-family="var(--mono)"
         font-size="11.5" fill="var(--muted)">${xLabel}</text>`;
    s+=`<text x="${cx}" y="${H-B+30}" text-anchor="middle" font-family="var(--mono)"
         font-size="9.5" fill="var(--faint)">n=${d.n}</text>`;
  });
  document.getElementById("chart").innerHTML=s;

  document.getElementById("tbody").innerHTML=A.map(d=>`
    <tr><td>${d.y}</td>
    <td style="color:var(--faint)">${d.frame==="pilot"?PILOTLBL:d.frame==="hist"?HISTLBL:d.frame==="modern"?MODLBL:"mixed cohorts"}</td>
    <td>${d.past}</td><td>${d.other}</td><td>${d.pres}</td>
    <td>${d.n}</td><td>${d.n?Math.round(d.pPres*100)+"%":"—"}</td>
    <td>${d.n?`${Math.round(d.ci_lo*100)}–${Math.round(d.ci_hi*100)}%`:"—"}</td>
    <td>${d.ab}</td><td style="color:var(--faint)">${d.cls}</td></tr>`).join("");
  const counts=A.filter(d=>d.n).map(d=>d.n);
  document.getElementById("point-note").firstChild.textContent=
    `Each point rests on ${Math.min(...counts)}–${Math.max(...counts)} labelled books. `;
}

function drawQuoteChart(summary){
  const {total,buckets,dialogueBeats}=summary;
  const W=920,L=14,R=14,Y=45,H=42,iw=W-L-R;
  const color={event:"var(--quote-event)",gnomic:"var(--quote-gnomic)",paratext:"var(--quote-paratext)",unclear:"var(--quote-unclear)"};
  const x={}; let cursor=L;
  const width=n=>iw*n/total;
  const rect=(left,w,fill)=>`<rect x="${left}" y="${Y}" width="${w}" height="${H}" fill="${fill}"/>`;
  let svg="";

  for(const bucket of ["event","dialogue","gnomic","paratext","unclear"]){
    const w=width(buckets[bucket]); x[bucket]=[cursor,w];
    if(bucket!=="dialogue") svg+=rect(cursor,w,color[bucket]);
    cursor+=w;
  }
  let dialogueX=x.dialogue[0];
  const dialogueColors={none:"var(--dialogue-none)",past:"var(--dialogue-past)",present:"var(--dialogue-present)"};
  const beatLabels={none:"no beat",past:"past beat"};
  for(const beat of ["none","past","present"]){
    const w=width(dialogueBeats[beat]);
    svg+=rect(dialogueX,w,dialogueColors[beat]);
    if(beatLabels[beat] && w>55) svg+=`<text x="${dialogueX+w/2}" y="${Y+25}" text-anchor="middle" font-family="var(--mono)" font-size="10" font-weight="600" fill="var(--ink)">${beatLabels[beat]}</text>`;
    if(beat!=="present") svg+=`<line x1="${dialogueX+w}" x2="${dialogueX+w}" y1="${Y}" y2="${Y+H}" stroke="var(--surface)" stroke-width="1.25"/>`;
    dialogueX+=w;
  }
  svg+=`<rect x="${x.dialogue[0]+.5}" y="${Y+.5}" width="${x.dialogue[1]-1}" height="${H-1}" fill="none" stroke="var(--ink)" stroke-width="1.5"/>`;
  svg+=`<path d="M ${x.dialogue[0]} 35 v-6 H ${x.dialogue[0]+x.dialogue[1]} v6" fill="none" stroke="var(--ink)" stroke-width="1.25"/>`;
  svg+=`<text x="${x.dialogue[0]+x.dialogue[1]/2}" y="18" text-anchor="middle" font-family="var(--mono)" font-size="11" font-weight="600" fill="var(--ink)">DIALOGUE · ${buckets.dialogue.toLocaleString()}</text>`;
  const presentX=x.dialogue[0]+x.dialogue[1];
  svg+=`<path d="M ${presentX-7} ${Y+H+1} v9 h-13" fill="none" stroke="var(--dialogue-present)" stroke-width="1.5"/>`;
  svg+=`<text x="${presentX-24}" y="${Y+H+22}" text-anchor="end" font-family="var(--mono)" font-size="10" font-weight="600" fill="var(--ink)">present beat · ${dialogueBeats.present.toLocaleString()}</text>`;

  const labels={event:"EVENT",gnomic:"GNOMIC"};
  for(const bucket of Object.keys(labels)){
    const [left,w]=x[bucket];
    if(w>120) svg+=`<text x="${left+w/2}" y="${Y+18}" text-anchor="middle" font-family="var(--mono)" font-size="11" font-weight="600" fill="var(--ink)">${labels[bucket]}</text><text x="${left+w/2}" y="${Y+31}" text-anchor="middle" font-family="var(--mono)" font-size="10" fill="var(--ink)">${buckets[bucket].toLocaleString()}</text>`;
  }
  svg+=`<line x1="${L}" x2="${W-R}" y1="${Y+H+10}" y2="${Y+H+10}" stroke="var(--line)"/>`;
  document.getElementById("quote-chart").innerHTML=svg;

  const item=(fill,text)=>`<span><i style="background:${fill}"></i>${text}</span>`;
  document.getElementById("quote-legend").innerHTML=[
    item(color.event,`Event ${buckets.event.toLocaleString()}`),
    item("var(--dialogue-none)",`Dialogue — no narratorial beat ${dialogueBeats.none.toLocaleString()}`),
    item("var(--dialogue-past)",`Dialogue — past-tense beat ${dialogueBeats.past.toLocaleString()}`),
    item("var(--dialogue-present)",`Dialogue — present-tense beat ${dialogueBeats.present.toLocaleString()}`),
    item(color.gnomic,`Gnomic ${buckets.gnomic.toLocaleString()}`),
    item(color.paratext,`Paratext ${buckets.paratext.toLocaleString()}`),
    item(color.unclear,`Unclear ${buckets.unclear.toLocaleString()}`),
  ].join("");
}

function initExplorer(BOOKS){
  const rowsEl=document.getElementById("rows");
  const statusEl=document.getElementById("status");
  const countEl=document.getElementById("count");

  BOOKS.forEach(b=>{
    const t=b.ev[0]+b.ev[1];
    b.pct=t?b.ev[1]/t:-1; b.evn=t; b.btn=b.bt[0]+b.bt[1];
    b._hay=(b.title+" "+b.author+" "+b.note+" "+
            b.q.map(q=>q.x+" "+q.n).join(" ")).toLowerCase();
  });

  const fill=(id,vals)=>{const s=document.getElementById(id);
    vals.forEach(v=>{const o=document.createElement("option");
      o.value=v; o.textContent=v; s.appendChild(o);});};
  fill("fyear",[...new Set(BOOKS.map(b=>String(b.year)))].sort());
  fill("flabel",[...new Set(BOOKS.map(b=>b.label))].sort());
  fill("fconf",[...new Set(BOOKS.map(b=>b.conf).filter(Boolean))].sort());
  fill("fsit",[...new Set(BOOKS.map(b=>b.sit).filter(Boolean))].sort());
  fill("fbucket",BUCKETS);

  let sortKey="year", sortDir=1, page=0;
  const PAGE=20;
  const open=new Set();
  const val=id=>document.getElementById(id).value;

  const current=()=>{
    const q=val("fq").trim().toLowerCase();
    const bIdx=BUCKETS.indexOf(val("fbucket"));
    return BOOKS.filter(b=>
      (!val("fyear")||String(b.year)===val("fyear")) &&
      (!val("flabel")||b.label===val("flabel")) &&
      (!val("fconf")||b.conf===val("fconf")) &&
      (!val("fsit")||b.sit===val("fsit")) &&
      (bIdx<0||b.bk[bIdx]>0) &&
      (!q||b._hay.includes(q)));
  };

  function detailHTML(b){
    const rows=b.q.map(q=>{
      const bits=[`<span class="pill b-${esc(q.b)}">${esc(q.b)}</span>`];
      if(q.t)  bits.push(`<span class="t">tense · ${esc(q.t)}</span>`);
      if(q.bt) bits.push(`<span class="t">beat · ${esc(q.bt)}</span>`);
      return `<div class="q">
        <div class="qmeta"><span class="qid">${esc(q.id)}</span>${bits.join("")}</div>
        <div><div class="qtx">${q.x?esc(q.x):"<span style='color:var(--faint)'>[no text on file]</span>"}</div>
        ${q.n?`<div class="qnote">${esc(q.n)}</div>`:""}</div></div>`;
    }).join("");
    const bk=BUCKETS.map((nm,i)=>b.bk[i]?`${b.bk[i]} ${nm}`:null).filter(Boolean).join(" · ");
    return `<td class="l" colspan="9"><div class="detail">
      <div class="anote"><strong>${esc(b.why||"no tense evidence")}</strong><br>${esc(bk)}
      ${b.note?`<br><br>${esc(b.note)}`:""}</div>
      <div class="qlist">${rows}</div></div></td>`;
  }

  function render(){
    const all=current();
    all.sort((a,z)=>{
      let A=a[sortKey], Z=z[sortKey];
      if(sortKey==="ev"){A=a.evn;Z=z.evn;}
      if(sortKey==="bt"){A=a.btn;Z=z.btn;}
      if(typeof A==="string") return sortDir*A.localeCompare(Z);
      return sortDir*(A-Z);
    });
    const pages=Math.max(1,Math.ceil(all.length/PAGE));
    if(page>=pages) page=pages-1;
    if(page<0) page=0;
    const list=all.slice(page*PAGE,(page+1)*PAGE);
    const frag=document.createDocumentFragment();
    list.forEach(b=>{
      const tr=document.createElement("tr");
      tr.className="book"+(open.has(b.sid)?" open":"");
      tr.dataset.sid=b.sid;
      tr.innerHTML=
        `<td class="l">${b.year}</td>
         <td class="l"><span class="caret">&#9656;</span> <span class="ttl">${esc(b.title)}</span>
             <span class="au">— ${esc(b.author)}</span></td>
         <td class="l"><span class="pill l-${esc(b.label)}">${esc(b.label)}</span></td>
         <td class="l"><span class="c-${esc(b.conf||"none")}">${esc(b.conf||"—")}</span></td>
         <td class="l">${esc(b.sit||"—")}</td>
         <td>${b.pct<0?"—":Math.round(b.pct*100)+"%"}</td>
         <td>${b.ev[0]}/${b.ev[1]}</td>
         <td>${b.bt[0]}/${b.bt[1]}</td>
         <td>${b.n}</td>`;
      frag.appendChild(tr);
      if(open.has(b.sid)){
        const d=document.createElement("tr");
        d.className="detail-row"; d.innerHTML=detailHTML(b);
        frag.appendChild(d);
      }
    });
    rowsEl.replaceChildren(frag);
    const from=all.length?page*PAGE+1:0, to=Math.min(all.length,(page+1)*PAGE);
    countEl.textContent=all.length===BOOKS.length
      ? `${from}–${to} of ${all.length} books`
      : `${from}–${to} of ${all.length} matching · ${BOOKS.length} total`;
    statusEl.hidden=all.length>0;
    statusEl.textContent="No books match those filters.";
    statusEl.className="empty";
    document.getElementById("pager").hidden=all.length<=PAGE;
    document.getElementById("pgnum").textContent=`Page ${page+1} of ${pages}`;
    document.getElementById("prev").disabled=page===0;
    document.getElementById("next").disabled=page>=pages-1;
  }

  const go=d=>{ page+=d; open.clear(); render();
    document.getElementById("xtable").scrollIntoView({block:"start",behavior:"smooth"}); };
  document.getElementById("prev").addEventListener("click",()=>go(-1));
  document.getElementById("next").addEventListener("click",()=>go(1));

  /* detail rows build on demand -- all quotes never hit the DOM at once */
  rowsEl.addEventListener("click",e=>{
    const tr=e.target.closest("tr.book");
    if(!tr) return;
    const sid=tr.dataset.sid;
    if(open.has(sid)){
      open.delete(sid); tr.classList.remove("open");
      const nx=tr.nextElementSibling;
      if(nx&&nx.classList.contains("detail-row")) nx.remove();
    }else{
      open.add(sid); tr.classList.add("open");
      const d=document.createElement("tr");
      d.className="detail-row";
      d.innerHTML=detailHTML(BOOKS.find(x=>x.sid===sid));
      tr.after(d);
    }
  });

  document.querySelectorAll("#xtable th[data-k]").forEach(th=>{
    th.addEventListener("click",()=>{
      const k=th.dataset.k;
      sortDir=(sortKey===k)?-sortDir:1; sortKey=k;
      document.querySelectorAll("#xtable th .ar").forEach(a=>a.textContent="");
      th.querySelector(".ar").textContent=sortDir>0?"▲":"▼";
      page=0; render();
    });
  });
  const refilter=()=>{ page=0; render(); };
  ["fyear","flabel","fconf","fsit","fbucket"].forEach(id=>
    document.getElementById(id).addEventListener("change",refilter));
  document.getElementById("fq").addEventListener("input",refilter);
  document.getElementById("reset").addEventListener("click",()=>{
    ["fyear","flabel","fconf","fsit","fbucket"].forEach(id=>
      document.getElementById(id).value="");
    document.getElementById("fq").value="";
    open.clear(); page=0; render();
  });
  render();
}

function init(payload){
  window.__PILOTLBL=payload.pilotLbl; window.__HISTLBL=payload.histLbl; window.__MODLBL=payload.modLbl;
  const periodView=document.getElementById("period-view");
  const rangeView=document.getElementById("range-view");
  const rangeLabels={all:"1931–2025",pilot:"1931–1995",main:"1996–2025"};
  const renderPeriods=()=>{
    document.getElementById("chart-title").textContent=
      `Narrative Tense in NYT Bestsellers, ${rangeLabels[rangeView.value]}`;
    drawChart(payload.periods[rangeView.value][periodView.value].filter(d=>d.cls));
  };
  periodView.addEventListener("change",renderPeriods);
  rangeView.addEventListener("change",renderPeriods);
  renderPeriods();
  drawQuoteChart(payload.quoteSummary);
  initExplorer(payload.books);
}
"""

EMBEDDED_BOOT = """
init(JSON.parse(document.getElementById("data").textContent));
"""

FETCH_BOOT = """
fetch("raw_data/report_data.json")
  .then(r => { if(!r.ok) throw new Error(r.status+" "+r.statusText); return r.json(); })
  .then(init)
  .catch(err => {
    const s=document.getElementById("status");
    s.className="empty";
    s.innerHTML="Could not load <code>data/report_data.json</code> — "+esc(err.message)+
      ".<br><br>This page must be served over http, not opened from the filesystem.<br>"+
      "Run <code>python3 -m http.server 8000</code> in the project directory, "+
      "then open <code>localhost:8000/trend_local.html</code>.";
  });
"""


def main():
    rows, missing, frame_n, skipped = load()
    per = periods(rows, lo=1996, hi=2025)
    pilot = trend(rows, "pilot")
    modern = trend(rows, "modern")
    early = trend([row for row in rows if 1996 <= row["year"] <= 2019])
    recent = trend([row for row in rows if row["frame"] == "modern" and row["year"] >= 2020])
    p_trend = trend([row for row in rows if 1996 <= row["year"] <= 2025])
    hist = trend(rows, "hist")
    e = era(rows)
    nq = sum(len(r["q"]) for r in rows)
    quote_buckets = quote_summary(rows)
    built = datetime.date.today().strftime("%d %b %Y")

    global era_p
    era_p = e["p"]
    html_body = body(rows, per, pilot, modern, early, recent, p_trend, hist, frame_n, nq, missing, built)
    ranges = {"all": (min(r["year"] for r in rows), 2025), "pilot": (1931, 1995),
              "main": (1996, 2025)}
    payload = {"periods": {name: {str(span): periods(rows, span, lo, hi)
                                   for span in (1, 3, 5, 10)}
                           for name, (lo, hi) in ranges.items()},
               "books": rows,
               "quoteSummary": quote_buckets,
               "pilotLbl": "target ≥2 labels/year",
               "histLbl": "target ≥10 labels/year",
               "modLbl": "eligible of top 30/year"}
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    def page(title, boot, data_script=""):
        return (f"<title>{title}</title>\n<style>{CSS}</style>\n{html_body}\n"
                f"{data_script}<script>{APP}\n{boot}</script>\n")

    safe = (blob.replace("<", "\\u003c")
                .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))
    full = page("Narrative tense in NYT bestsellers, 1996-2025", EMBEDDED_BOOT,
                f'<script id="data" type="application/json">{safe}</script>\n')
    open(os.path.join(ROOT, "trend.html"), "w", encoding="utf-8").write(full)

    open(os.path.join(DATA, "report_data.json"), "w", encoding="utf-8").write(blob)
    local = page("Narrative tense in NYT bestsellers (local)", FETCH_BOOT)
    open(os.path.join(ROOT, "trend_local.html"), "w", encoding="utf-8").write(local)

    print(f"{len(rows)} books, {nq} quotes"
          + (f", {missing} quotes missing text" if missing else ""))
    print(f"  eligible top30 2016-2025 : {modern['pres']}/{modern['n']} = {modern['share']:.1%} present")
    print(f"  trend 1996-2025 : p={p_trend['p']:.4f}")
    if hist:
        print(f"  target10 1996-2015 : {hist['pres']}/{hist['n']} = {hist['share']:.1%} present"
              f"  trend z={hist['z']:.2f} p={hist['p']:.4f}")
    print(f"  era {2016}-{ERA_SPLIT-1} {e['P1']:.1%} vs {ERA_SPLIT}-2025 {e['P2']:.1%}"
          f"  z={e['z']:.2f} p={e['p']:.4f}")
    print(f"  trend.html        {len(full)/1e6:.2f} MB  (self-contained)")
    print(f"  trend_local.html  {len(local)/1e3:.1f} KB  + raw_data/report_data.json "
          f"{len(blob)/1e6:.2f} MB")


if __name__ == "__main__":
    main()
