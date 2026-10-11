"""Build the standalone narrative-person report.

The report is generated exclusively from the reviewed person exports:

    dataset/person_books.csv
    dataset/person_quotes.csv

Rebuild from the repository root with:

    python3 analysis/build_person_report.py

The output, ``person_report.html``, contains its data and JavaScript inline so it can
be opened directly, archived, or published without a server.
"""

from __future__ import annotations

import collections
import csv
import datetime as dt
import html
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BOOKS_CSV = ROOT / "dataset" / "person_books.csv"
QUOTES_CSV = ROOT / "dataset" / "person_quotes.csv"
TENSE_BOOKS_CSV = ROOT / "dataset" / "books.csv"
OUTPUT = ROOT / "person_report.html"
ELIGIBLE_LABELS = ("FIRST", "SECOND", "THIRD", "ALTERNATING")
ABSTENTION_LABELS = ("UNCLEAR", "INSUFFICIENT")
SUBSTANTIVE_TENSE_LABELS = ("PAST", "PRESENT", "DUAL")


def _json_field(value: str, field: str, sample_id: str):
    try:
        return json.loads(value or "[]")
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid {field} JSON for {sample_id}: {exc}") from exc


def load_data(books_path: Path = BOOKS_CSV, quotes_path: Path = QUOTES_CSV):
    """Load and validate the report records, returning compact browser data."""
    with books_path.open(encoding="utf-8", newline="") as handle:
        book_rows = list(csv.DictReader(handle))
    with quotes_path.open(encoding="utf-8", newline="") as handle:
        quote_rows = list(csv.DictReader(handle))

    quotes_by_book: dict[str, list[dict]] = collections.defaultdict(list)
    for row in quote_rows:
        quotes_by_book[row["sample_id"]].append(
            {
                "id": row["quote_id"],
                "bucket": row["bucket"],
                "tense": row["tense"],
                "beat": row["beat_tense"],
                "signal": row["person_signal"],
                "note": row["person_note"],
                "text": row["quote_text"],
            }
        )

    books = []
    for row in book_rows:
        sample_id = row["sample_id"]
        label = row["person_label"]
        if label not in (*ELIGIBLE_LABELS, *ABSTENTION_LABELS, "EXCLUDED"):
            raise ValueError(f"Unexpected person label {label!r} for {sample_id}")
        books.append(
            {
                "id": sample_id,
                "frame": row["frame"],
                "year": int(row["year"]),
                "title": row["title"],
                "author": row["author"],
                "person": label,
                "confidence": row["person_confidence"],
                "person_note": row["person_note"],
                "tense": row["tense_label"],
                "tense_confidence": row["tense_confidence"],
                "n_quotes": int(row["n_quotes"]),
                "signals": {
                    "first": int(row["signal_first"]),
                    "second": int(row["signal_second"]),
                    "third": int(row["signal_third"]),
                    "unmarked": int(row["signal_unmarked"]),
                    "non_base": int(row["signal_non_base"]),
                    "unclear": int(row["signal_unclear"]),
                },
                "web_evidence": _json_field(row["web_evidence_json"], "web_evidence", sample_id),
                "search_log": _json_field(row["search_log_json"], "search_log", sample_id),
                "model": row["model"],
                "reasoning_effort": row["reasoning_effort"],
                "run_id": row["run_id"],
                "quotes": quotes_by_book.get(sample_id, []),
            }
        )

    books.sort(key=lambda row: (row["year"], row["title"], row["id"]))
    known_ids = {book["id"] for book in books}
    orphan_ids = sorted(set(quotes_by_book) - known_ids)
    if orphan_ids:
        raise ValueError(f"Quote rows refer to unknown books: {', '.join(orphan_ids[:5])}")
    for book in books:
        if len(book["quotes"]) != book["n_quotes"]:
            raise ValueError(
                f"Quote count mismatch for {book['id']}: "
                f"book export says {book['n_quotes']}, found {len(book['quotes'])}"
            )

    return books


def load_targets(path: Path = TENSE_BOOKS_CSV):
    """Return the non-abstained tense population that person coverage is targeting."""
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    years = collections.Counter(
        int(row["year"]) for row in rows if row["raw_label"] in SUBSTANTIVE_TENSE_LABELS
    )
    if not years:
        raise ValueError("No substantive tense labels found in dataset/books.csv")
    return {"total": sum(years.values()), "by_year": dict(years)}


def summarize(books, targets=None):
    targets = targets or load_targets()
    eligible = [
        book for book in books
        if book["person"] in ELIGIBLE_LABELS and book["tense"] in SUBSTANTIVE_TENSE_LABELS
    ]
    labels = collections.Counter(book["person"] for book in eligible)
    confidence = collections.Counter(book["confidence"] for book in eligible)
    signals = collections.Counter()
    for book in eligible:
        signals.update(book["signals"])
    return {
        "eligible": len(eligible),
        "reviewed_target": sum(book["tense"] in SUBSTANTIVE_TENSE_LABELS for book in books),
        "abstained_target": sum(
            book["person"] in ABSTENTION_LABELS and book["tense"] in SUBSTANTIVE_TENSE_LABELS
            for book in books
        ),
        "target_total": targets["total"],
        "target_by_year": targets["by_year"],
        "excluded": sum(book["person"] == "EXCLUDED" for book in books),
        "off_target": sum(
            book["person"] in ELIGIBLE_LABELS and book["tense"] not in SUBSTANTIVE_TENSE_LABELS
            for book in books
        ),
        "quotes": sum(book["n_quotes"] for book in eligible),
        "all_quotes": sum(book["n_quotes"] for book in books),
        "labels": dict(labels),
        "confidence": dict(confidence),
        "signals": dict(signals),
        "years": [min(targets["by_year"]), max(targets["by_year"])],
        "generated": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
    }


CSS = r"""
.UNCLEAR,.INSUFFICIENT{color:var(--flag)}
:root{color-scheme:dark;--ink:#e8eaf0;--paper:#0f1216;--surface:#161a20;--surface2:#1b2027;
  --line:#2b323c;--muted:#9ba5b2;--faint:#6f7986;--first:#d8a15e;--second:#c988ce;
  --third:#4fb3b3;--alternating:#8d9bea;--excluded:#717b87;--flag:#df7958;
  --high:#79b98b;--mono:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace;
  --sans:Inter,ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  --serif:Iowan Old Style,Charter,Georgia,serif}
@media(prefers-color-scheme:light){:root{color-scheme:light;--ink:#15191f;--paper:#f6f7f9;
  --surface:#fff;--surface2:#f0f2f5;--line:#dfe3e8;--muted:#59636f;--faint:#87909a;
  --first:#a86e29;--second:#994b9f;--third:#187b7b;--alternating:#5262b8;
  --excluded:#7a838d;--flag:#b44d30;--high:#34794a}}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);
  font-family:var(--sans);line-height:1.58;-webkit-font-smoothing:antialiased}
.wrap{max-width:76rem;margin:auto;padding:3.5rem 1.5rem 6rem;display:flex;flex-direction:column;gap:3.2rem}
.narrow{max-width:61rem}.eyebrow{font:600 .68rem/1.2 var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--faint)}
h1,h2{font-family:var(--serif);font-weight:600;letter-spacing:-.018em;text-wrap:balance}h1{font-size:clamp(2.1rem,5vw,3.15rem);line-height:1.06;margin:.55rem 0 .8rem;max-width:27ch}
h2{font-size:1.55rem;margin:0}h3{font-size:.84rem;letter-spacing:.02em;margin:0}p{margin:0;max-width:68ch}
.lede{font-size:1.08rem;color:var(--muted)}section{display:flex;flex-direction:column;gap:1rem}
.caution{border-left:2px solid var(--flag);padding:.15rem 0 .15rem 1.1rem;color:var(--muted)}
.controls,.chartbox,.card,.tablewrap{background:var(--surface);border:1px solid var(--line);border-radius:3px}
.chartbox{padding:1.25rem 1.25rem 1rem;overflow-x:auto}.charthead{display:flex;align-items:end;justify-content:space-between;gap:1rem;flex-wrap:wrap}
.chartcontrols{display:flex;gap:.45rem;align-items:center;color:var(--muted);font-size:.82rem}
select,input[type=search]{font:inherit;font-size:.82rem;color:var(--ink);background:var(--paper);border:1px solid var(--line);border-radius:2px;padding:.38rem .5rem}
#chart{display:block;min-width:47rem;width:100%;height:auto;margin-top:.8rem}.axis{stroke:var(--line);stroke-width:1}.grid{stroke:var(--line);stroke-width:1;opacity:.72}
.axistext{fill:var(--muted);font:11px var(--mono)}.area{transition:opacity .12s}.chartbox:has(.hoverzone:hover) .area{opacity:.76}.tooltip{position:fixed;pointer-events:none;z-index:20;background:var(--ink);color:var(--paper);padding:.45rem .55rem;border-radius:2px;font:12px/1.4 var(--mono);box-shadow:0 4px 18px #0004;display:none;white-space:pre-line}
.legend{display:flex;flex-wrap:wrap;gap:.6rem 1.2rem;color:var(--muted);font-size:.83rem}.swatch{display:inline-block;width:.72rem;height:.72rem;border-radius:1px;margin-right:.35rem;vertical-align:-1px}
.cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.8rem}.card{padding:1rem 1.05rem}.metric{font:1.55rem/1 var(--mono);margin:.35rem 0}.card p{font-size:.8rem;color:var(--muted)}
.tablewrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:.82rem}th{font:600 .62rem var(--mono);letter-spacing:.09em;text-transform:uppercase;color:var(--muted);text-align:right;padding:.7rem .75rem;border-bottom:1px solid var(--line);white-space:nowrap}th:first-child,th.left,td.left{text-align:left}td{padding:.52rem .75rem;border-bottom:1px solid var(--line);text-align:right;font-family:var(--mono);font-variant-numeric:tabular-nums;white-space:nowrap}tbody tr:last-child td{border-bottom:0}
.definitions{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.8rem}.definitions .card{border-top:3px solid var(--label-color)}.definitions p{font-size:.86rem;color:var(--muted)}
.signalbar{height:1.15rem;display:flex;overflow:hidden;background:var(--surface2);border-radius:2px}.signalbar i{height:100%;display:block}.signallegend{display:grid;grid-template-columns:repeat(3,1fr);gap:.45rem .8rem;font-size:.78rem;color:var(--muted)}
.signallegend strong{font-family:var(--mono);color:var(--ink);font-weight:500}
.controls{display:flex;gap:.55rem;align-items:center;flex-wrap:wrap;padding:.72rem .8rem;position:sticky;top:0;z-index:5}.controls input{flex:1 1 14rem}.count{font:.74rem var(--mono);color:var(--muted);margin-left:auto}.reset,.pagebtn{font:inherit;font-size:.78rem;color:var(--muted);background:var(--paper);border:1px solid var(--line);border-radius:2px;padding:.38rem .6rem;cursor:pointer}.reset:hover,.pagebtn:hover:not(:disabled){color:var(--ink);border-color:var(--muted)}
#books th{cursor:pointer;user-select:none}#books th:hover{color:var(--ink)}tr.book{cursor:pointer}tr.book:hover td,tr.book.open td{background:color-mix(in srgb,var(--third) 8%,transparent)}.title{font-family:var(--sans);font-weight:650}.author{font-family:var(--sans);font-size:.76rem;color:var(--muted)}.caret{display:inline-block;width:.8rem;color:var(--faint);transition:.12s}.book.open .caret{transform:rotate(90deg);color:var(--third)}
.pill{display:inline-block;font:600 .61rem var(--mono);letter-spacing:.055em;border:1px solid currentColor;border-radius:2px;padding:.12rem .35rem}.FIRST{color:var(--first)}.SECOND{color:var(--second)}.THIRD{color:var(--third)}.ALTERNATING{color:var(--alternating)}.EXCLUDED{color:var(--excluded)}.high{color:var(--high)}.med{color:var(--muted)}
.detailrow td{padding:0;background:var(--paper);white-space:normal;text-align:left}.detail{padding:1rem;display:flex;flex-direction:column;gap:1rem}.decision{font-family:var(--sans);color:var(--muted);max-width:95ch}.decision strong{color:var(--ink)}.evidence{display:grid;gap:.55rem}.evidenceitem{border-left:2px solid var(--line);padding-left:.7rem;font-family:var(--sans);font-size:.8rem;color:var(--muted)}.evidenceitem a{color:var(--third);text-decoration:none}.evidenceitem a:hover{text-decoration:underline}.meta{font:600 .62rem var(--mono);letter-spacing:.04em;text-transform:uppercase;color:var(--faint)}
.qlist{display:grid;gap:0}.quote{display:grid;grid-template-columns:7rem 1fr;gap:.8rem;border-top:1px solid var(--line);padding:.65rem .15rem}.qmeta{font:.62rem/1.65 var(--mono);color:var(--faint)}.qtext{font:.92rem/1.52 var(--serif);white-space:pre-wrap}.qnote{font:.75rem/1.45 var(--sans);color:var(--muted);border-left:2px solid var(--line);padding-left:.55rem;margin-top:.35rem}
.pager{display:flex;align-items:center;justify-content:center;gap:1rem}.pagebtn:disabled{opacity:.45;cursor:default}.pagenum{font:.74rem var(--mono);color:var(--muted)}
.methods{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1.5rem}.methods ul{margin:.4rem 0 0;padding-left:1.1rem;color:var(--muted);font-size:.88rem}.methods li{margin:.45rem 0}.methods strong{color:var(--ink)}
footer{border-top:1px solid var(--line);padding-top:1rem;color:var(--faint);font:.72rem/1.7 var(--mono)}
@media(max-width:760px){.wrap{padding:2rem 1rem 4rem;gap:2.5rem}.cards{grid-template-columns:repeat(2,1fr)}.definitions,.methods{grid-template-columns:1fr}.signallegend{grid-template-columns:repeat(2,1fr)}.quote{grid-template-columns:1fr}.hide-mobile{display:none}}
@media(max-width:420px){.cards{grid-template-columns:1fr}}
"""


BODY = r"""
<main class="wrap">
  <header class="narrow">
    <div class="eyebrow">Booktense · narrative-person panel</div>
    <h1>Narrative person in NYT bestsellers, 1931–2025</h1>
    <p class="lede">Person labels for books with substantive past, present, or dual tense classifications, expanding toward the full tense-labelled dataset. Quote-level signals are combined with web research because isolated Goodreads quotes often do not expose who narrates the book.</p>
  </header>

  <section aria-labelledby="trend-title">
    <div class="chartbox">
      <div class="charthead">
        <div><div class="eyebrow">Book-level distribution</div><h2 id="trend-title">Narrative person over time</h2></div>
        <div class="chartcontrols"><label for="window">Group years</label><select id="window"><option value="1">1 year</option><option value="3">3 years</option><option value="5" selected>5 years</option><option value="10">10 years</option></select></div>
      </div>
      <svg id="chart" viewBox="0 0 980 400" role="img" aria-label="Stacked area chart of narrative-person shares over time"></svg>
      <div class="legend" id="legend"></div>
    </div>
    <p class="caution"><strong>Coverage is still in progress.</strong> The historical expansion is being completed sequentially, so compare periods only after checking the labelled/target denominator. The source cohorts themselves are deterministic rather than random samples of all bestsellers.</p>
  </section>

  <section aria-labelledby="snapshot-title">
    <div><div class="eyebrow">Current substantive-tense overlap</div><h2 id="snapshot-title">Classification snapshot</h2></div>
    <div class="cards" id="cards"></div>
    <p>@@REVIEWED@@ target books reviewed; @@ABSTAINED@@ abstentions (unclear or insufficient evidence). Abstentions remain in the evidence browser and are excluded from person-percentage denominators.</p>
    <div class="tablewrap"><table><thead><tr><th class="left">Period</th><th>First</th><th>Second</th><th>Third</th><th>Alternating</th><th>Labelled</th><th>Target</th><th>Coverage</th><th>High conf.</th></tr></thead><tbody id="periods"></tbody></table></div>
  </section>

  <section aria-labelledby="definition-title">
    <div><div class="eyebrow">Output ontology</div><h2 id="definition-title">What the book labels mean</h2></div>
    <div class="definitions">
      <article class="card" style="--label-color:var(--first)"><h3>First person</h3><p>The controlling narrator participates in the story world as “I” or “we.” A character saying “I” in dialogue is not enough.</p></article>
      <article class="card" style="--label-color:var(--third)"><h3>Third person</h3><p>The controlling narrator stands outside the story and narrates characters as “he,” “she,” “they,” or by name. A named character in one quote is not enough.</p></article>
      <article class="card" style="--label-color:var(--second)"><h3>Second person</h3><p>The controlling narration persistently casts the protagonist or narratee as “you.” Generic advice and dialogue address are excluded.</p></article>
      <article class="card" style="--label-color:var(--alternating)"><h3>Alternating</h3><p>First-, second-, or third-person base narration controls distinct sustained sections. Local quotations, documents, or brief frames do not trigger this label.</p></article>
    </div>
    <p>No combined person-and-tense label is emitted. Existing past/present labels remain a separate field and are shown only for comparison in the evidence browser.</p>
  </section>

  <section aria-labelledby="signals-title">
    <div><div class="eyebrow">Quote-level evidence</div><h2 id="signals-title">What the Goodreads passages could establish</h2></div>
    <div class="card"><div class="signalbar" id="signalbar" aria-label="Distribution of quote-level person signals"></div><div class="signallegend" id="signallegend"></div></div>
    <p class="caution">A quote signal is evidence about that passage, not a miniature book label. Dialogue, paratext, gnomic statements, and quoted documents are marked <em>non-base</em>; genuinely narrative but person-neutral fragments are <em>unmarked</em>. This prevents “Maria walked to the store” from being treated as proof that the whole book is third person.</p>
  </section>

  <section aria-labelledby="explorer-title">
    <div><div class="eyebrow">Auditable evidence</div><h2 id="explorer-title">Books, decisions, sources, and quotes</h2></div>
    <div class="controls">
      <input id="search" type="search" placeholder="Search title, author, decision…" aria-label="Search books">
      <select id="year" aria-label="Filter year"><option value="">All years</option></select>
      <select id="person" aria-label="Filter person"><option value="">All person labels</option></select>
      <select id="confidence" aria-label="Filter confidence"><option value="">All confidence</option><option value="high">High</option><option value="med">Medium</option></select>
      <select id="tense" aria-label="Filter tense"><option value="">All tense labels</option></select>
      <button class="reset" id="reset" type="button">Reset</button><span class="count" id="count"></span>
    </div>
    <div class="tablewrap"><table id="books"><thead><tr><th data-sort="year" class="left">Year</th><th data-sort="title" class="left">Book</th><th data-sort="person">Person</th><th data-sort="confidence">Confidence</th><th data-sort="tense">Tense</th><th data-sort="n_quotes">Quotes</th><th data-sort="web">Web sources</th></tr></thead><tbody></tbody></table></div>
    <div class="pager"><button id="prev" class="pagebtn" type="button">Previous</button><span class="pagenum" id="pagenum"></span><button id="next" class="pagebtn" type="button">Next</button></div>
  </section>

  <section aria-labelledby="methods-title">
    <div><div class="eyebrow">Interpretation</div><h2 id="methods-title">Method and limits</h2></div>
    <div class="methods">
      <div><h3>How labels were produced</h3><ul><li><strong>Separate pass:</strong> person classification reused prior quote buckets and tense annotations; it did not reclassify dialogue, paratext, gnomic text, or tense.</li><li><strong>Two evidence streams:</strong> the agent evaluated every available quote, then searched for authorized excerpts and explicit structural descriptions.</li><li><strong>Book-level synthesis:</strong> the final label targets controlling base narration across the book, with a justification, confidence, cited web evidence, and search log.</li><li><strong>Model:</strong> Producing model and reasoning effort are recorded for each book; outputs were schema-validated and reviewed before export.</li></ul></div>
      <div><h3>Limits to keep in view</h3><ul><li><strong>Selection:</strong> coverage began with a deterministic annual panel and is expanding to all books with non-abstained tense labels. Coverage remains uneven until the target is complete; changes may reflect title mix.</li><li><strong>Evidence coverage:</strong> authorized contiguous excerpts were not consistently available, and openings need not represent later sections.</li><li><strong>Alternation:</strong> deciding whether a person shift controls a sustained section involves structural judgment; author concentration can affect that category’s apparent prevalence.</li><li><strong>Second person:</strong> second-person quote signals do not by themselves establish a SECOND book label; dialogue and generic address remain nondiagnostic.</li><li><strong>Exclusion:</strong> <em>Call Us What We Carry</em> is retained in the browser as an audited poetry exclusion; the next eligible 2021 title supplied that year’s fifth prose label.</li></ul></div>
    </div>
  </section>

  <footer>Generated @@BUILT@@ from the tense and person CSV exports. The report contains @@BOOKS@@ reviewed person records; @@ELIGIBLE@@ of @@TARGET@@ substantive-tense books currently have person labels, supported by @@QUOTES@@ in-scope quote annotations. The evidence browser also retains @@OFFTARGET@@ earlier tense-abstained person labels and @@EXCLUDED@@ exclusion. Rebuild with <code>python3 analysis/build_person_report.py</code>.</footer>
</main>
<div class="tooltip" id="tooltip"></div>
"""


JS = r"""
(() => {
  const D=JSON.parse(document.getElementById('data').textContent), books=D.books, S=D.summary;
  const labels=['FIRST','SECOND','THIRD','ALTERNATING'];
  const colors={FIRST:'var(--first)',SECOND:'var(--second)',THIRD:'var(--third)',ALTERNATING:'var(--alternating)',EXCLUDED:'var(--excluded)'};
  const names={FIRST:'First person',SECOND:'Second person',THIRD:'Third person',ALTERNATING:'Alternating',EXCLUDED:'Excluded',UNCLEAR:'Unclear (abstention)',INSUFFICIENT:'Insufficient evidence (abstention)'};
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const pct=(n,d)=>d?`${(100*n/d).toFixed(1)}%`:'—';
  const substantive=['PAST','PRESENT','DUAL'];
  const eligible=books.filter(b=>labels.includes(b.person)&&substantive.includes(b.tense));

  document.getElementById('legend').innerHTML=labels.map(l=>`<span><i class="swatch" style="background:${colors[l]}"></i>${names[l]}</span>`).join('');
  const lc=S.labels, cc=S.confidence;
  document.getElementById('cards').innerHTML=[
    ['Coverage',`${S.eligible}/${S.target_total}`,`${pct(S.eligible,S.target_total)} of substantive-tense books`],
    ['First person',pct(lc.FIRST||0,S.eligible),`${lc.FIRST||0} books`],
    ['Alternating',pct(lc.ALTERNATING||0,S.eligible),`${lc.ALTERNATING||0} books`],
    ['High confidence',pct(cc.high||0,S.eligible),`${cc.high||0} of ${S.eligible} decisions`]
  ].map(x=>`<article class="card"><div class="eyebrow">${x[0]}</div><div class="metric">${x[1]}</div><p>${x[2]}</p></article>`).join('');

  function aggregate(size){
    const out=[];
    const minYear=S.years[0],maxYear=S.years[1];
    for(let start=minYear;start<=maxYear;start+=size){
      const end=Math.min(maxYear,start+size-1), rows=eligible.filter(b=>b.year>=start&&b.year<=end), counts={},target=Object.entries(S.target_by_year).filter(([y])=>+y>=start&&+y<=end).reduce((n,[,v])=>n+v,0);
      labels.forEach(l=>counts[l]=rows.filter(b=>b.person===l).length);
      out.push({start,end,label:start===end?String(start):`${start}–${end}`,rows,counts,n:rows.length,target,high:rows.filter(b=>b.confidence==='high').length});
    }
    return out;
  }
  function drawChart(){
    const groups=aggregate(+document.getElementById('window').value), svg=document.getElementById('chart');
    const W=980,H=400,m={l:52,r:45,t:18,b:52},iw=W-m.l-m.r,ih=H-m.t-m.b;
    groups.forEach(g=>{g.mid=(g.start+g.end+1)/2});
    const x0=groups[0].mid,x1=groups[groups.length-1].mid;
    const x=v=>m.l+iw*(v-x0)/Math.max(1,x1-x0),y=v=>m.t+ih*(1-v);
    const zero=groups.map(()=>0), boundaries=[];let running=zero.slice();
    labels.forEach(l=>{running=groups.map((g,i)=>running[i]+(g.n?g.counts[l]/g.n:0));boundaries.push(running)});
    const band=(lo,hi,l)=>{const up=groups.map((g,i)=>`${x(g.mid)},${y(hi[i])}`).join(' '),dn=groups.map((g,i)=>`${x(g.mid)},${y(lo[i])}`).reverse().join(' ');return `<polygon class="area" points="${up} ${dn}" fill="${colors[l]}" opacity=".88"/>`};
    let parts=[];
    for(let g=0;g<=100;g+=10){const gy=y(g/100);parts.push(`<line class="grid" x1="${m.l}" x2="${W-m.r}" y1="${gy}" y2="${gy}"/><text class="axistext" x="${m.l-9}" y="${gy+4}" text-anchor="end">${g}%</text><text class="axistext" x="${W-m.r+9}" y="${gy+4}" text-anchor="start">${g}%</text>`)}
    labels.forEach((l,i)=>parts.push(band(i?boundaries[i-1]:zero,boundaries[i],l)));
    boundaries.slice(0,-1).forEach((line,i)=>parts.push(`<polyline points="${groups.map((g,j)=>`${x(g.mid)},${y(line[j])}`).join(' ')}" fill="none" stroke="var(--surface)" stroke-width="${i?1.2:1.6}"/>`));
    groups.forEach((g,i)=>{const cx=x(g.mid),show=groups.length<35||g.start%5===0;if(show){parts.push(`<text class="axistext" x="${cx}" y="${H-m.b+18}" text-anchor="middle">${g.label}</text><text class="axistext" x="${cx}" y="${H-m.b+31}" text-anchor="middle" style="fill:var(--faint);font-size:9.5px">n=${g.n}</text>`)}});
    groups.forEach((g,i)=>{const left=i?x((groups[i-1].mid+g.mid)/2):m.l,right=i<groups.length-1?x((g.mid+groups[i+1].mid)/2):W-m.r;parts.push(`<rect class="hoverzone" data-index="${i}" x="${left}" y="${m.t}" width="${Math.max(1,right-left)}" height="${ih}" fill="transparent"/>`)});
    svg.innerHTML=parts.join('');
    const tip=document.getElementById('tooltip');svg.querySelectorAll('.hoverzone').forEach(el=>{el.onmousemove=e=>{const g=groups[+el.dataset.index];tip.style.display='block';tip.style.left=`${e.clientX+12}px`;tip.style.top=`${e.clientY+12}px`;tip.textContent=[`${g.label} · n=${g.n}`,...labels.map(l=>`${names[l]}: ${g.counts[l]} (${pct(g.counts[l],g.n)})`)].join('\n')};el.onmouseleave=()=>tip.style.display='none'});
  }
  document.getElementById('window').onchange=drawChart;window.addEventListener('resize',drawChart);drawChart();

  document.getElementById('periods').innerHTML=aggregate(5).map(g=>`<tr><td class="left">${g.label}</td>${labels.map(l=>`<td>${g.counts[l]} <span style="color:var(--faint)">(${pct(g.counts[l],g.n)})</span></td>`).join('')}<td>${g.n}</td><td>${g.target}</td><td>${pct(g.n,g.target)}</td><td>${pct(g.high,g.n)}</td></tr>`).join('');

  const sigOrder=['first','second','third','unmarked','non_base','unclear'],sigNames={first:'First',second:'Second',third:'Third',unmarked:'Unmarked',non_base:'Non-base',unclear:'Unclear'},sigColors={first:'var(--first)',second:'var(--second)',third:'var(--third)',unmarked:'var(--alternating)',non_base:'var(--excluded)',unclear:'var(--flag)'},sigTotal=Object.values(S.signals).reduce((a,b)=>a+b,0);
  document.getElementById('signalbar').innerHTML=sigOrder.map(k=>`<i style="width:${100*(S.signals[k]||0)/sigTotal}%;background:${sigColors[k]}" title="${sigNames[k]}: ${S.signals[k]||0}"></i>`).join('');
  document.getElementById('signallegend').innerHTML=sigOrder.map(k=>`<span><i class="swatch" style="background:${sigColors[k]}"></i>${sigNames[k]} <strong>${(S.signals[k]||0).toLocaleString()} · ${pct(S.signals[k]||0,sigTotal)}</strong></span>`).join('');

  const els=Object.fromEntries(['search','year','person','confidence','tense','count','prev','next','pagenum','reset'].map(id=>[id,document.getElementById(id)]));
  [...new Set(books.map(b=>b.year))].sort().forEach(v=>els.year.insertAdjacentHTML('beforeend',`<option>${v}</option>`));
  [...labels,'UNCLEAR','INSUFFICIENT','EXCLUDED'].forEach(v=>els.person.insertAdjacentHTML('beforeend',`<option value="${v}">${names[v]}</option>`));
  [...new Set(books.map(b=>b.tense))].sort().forEach(v=>els.tense.insertAdjacentHTML('beforeend',`<option>${esc(v)}</option>`));
  let page=1,sortKey='year',sortDir=1;const pageSize=20;
  function filtered(){
    const q=els.search.value.trim().toLowerCase();
    return books.filter(b=>(!q||`${b.title} ${b.author} ${b.person_note}`.toLowerCase().includes(q))&&(!els.year.value||b.year==els.year.value)&&(!els.person.value||b.person===els.person.value)&&(!els.confidence.value||b.confidence===els.confidence.value)&&(!els.tense.value||b.tense===els.tense.value)).sort((a,b)=>{let av=sortKey==='web'?a.web_evidence.length:a[sortKey],bv=sortKey==='web'?b.web_evidence.length:b[sortKey];return sortDir*(typeof av==='number'?av-bv:String(av).localeCompare(String(bv)))});
  }
  function pill(value){return `<span class="pill ${esc(value)}">${esc(value||'—')}</span>`}
  function details(b){
    const evidence=b.web_evidence.length?b.web_evidence.map(e=>`<div class="evidenceitem"><div class="meta">Tier ${esc(e.tier)} · ${esc(e.scope)} · supports ${esc(e.supports)}</div><a href="${esc(e.url)}" target="_blank" rel="noopener noreferrer">${esc(e.title||e.url)}</a><div>${esc(e.note)}</div></div>`).join(''):'<div class="evidenceitem">No web evidence retained.</div>';
    const qs=b.quotes.map(q=>`<div class="quote"><div class="qmeta">${esc(q.id)}<br>${esc(q.signal)}<br>${esc(q.bucket)}${q.tense?` · ${esc(q.tense)}`:''}${q.beat?`<br>beat: ${esc(q.beat)}`:''}</div><div><div class="qtext">${esc(q.text)}</div>${q.note?`<div class="qnote">${esc(q.note)}</div>`:''}</div></div>`).join('');
    return `<tr class="detailrow"><td colspan="7"><div class="detail"><p class="decision"><strong>Book-level decision.</strong> ${esc(b.person_note)}</p><div><h3>Web evidence (${b.web_evidence.length})</h3><div class="evidence">${evidence}</div></div><details><summary>Search log (${b.search_log.length} steps)</summary><ol>${b.search_log.map(x=>`<li>${esc(x)}</li>`).join('')}</ol></details><div><h3>Quote annotations (${b.quotes.length})</h3><div class="qlist">${qs}</div></div><div class="meta">${esc(b.model)} · ${esc(b.reasoning_effort)} reasoning · ${esc(b.run_id)}</div></div></td></tr>`;
  }
  function render(){
    const rows=filtered(),pages=Math.max(1,Math.ceil(rows.length/pageSize));page=Math.min(page,pages);const shown=rows.slice((page-1)*pageSize,page*pageSize),body=document.querySelector('#books tbody');
    body.innerHTML=shown.map(b=>`<tr class="book" data-id="${esc(b.id)}"><td class="left"><span class="caret">▶</span>${b.year}</td><td class="left"><div class="title">${esc(b.title)}</div><div class="author">${esc(b.author)}</div></td><td>${pill(b.person)}</td><td><span class="${esc(b.confidence)}">${esc(b.confidence||'—')}</span></td><td>${pill(b.tense)}</td><td>${b.n_quotes}</td><td>${b.web_evidence.length}</td></tr>`).join('')||'<tr><td colspan="7" class="left">No matching books.</td></tr>';
    body.querySelectorAll('tr.book').forEach(row=>row.onclick=()=>{const open=row.classList.toggle('open'),next=row.nextElementSibling;if(next&&next.classList.contains('detailrow'))next.remove();else if(open){const b=books.find(x=>x.id===row.dataset.id);row.insertAdjacentHTML('afterend',details(b))}});
    els.count.textContent=`${rows.length} of ${books.length} records`;els.pagenum.textContent=`Page ${page} of ${pages}`;els.prev.disabled=page<=1;els.next.disabled=page>=pages;
  }
  ['search','year','person','confidence','tense'].forEach(id=>els[id].addEventListener(id==='search'?'input':'change',()=>{page=1;render()}));
  els.reset.onclick=()=>{['search','year','person','confidence','tense'].forEach(id=>els[id].value='');page=1;render()};els.prev.onclick=()=>{page--;render();document.getElementById('explorer-title').scrollIntoView()};els.next.onclick=()=>{page++;render();document.getElementById('explorer-title').scrollIntoView()};
  document.querySelectorAll('#books th[data-sort]').forEach(th=>th.onclick=()=>{const k=th.dataset.sort;if(sortKey===k)sortDir*=-1;else{sortKey=k;sortDir=1}page=1;render()});render();
})();
"""


def render(books, targets=None):
    summary = summarize(books, targets)
    built = dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    body = (
        BODY.replace("@@BUILT@@", html.escape(built))
        .replace("@@BOOKS@@", str(len(books)))
        .replace("@@ELIGIBLE@@", str(summary["eligible"]))
        .replace("@@REVIEWED@@", str(summary["reviewed_target"]))
        .replace("@@ABSTAINED@@", str(summary["abstained_target"]))
        .replace("@@TARGET@@", str(summary["target_total"]))
        .replace("@@QUOTES@@", f"{summary['quotes']:,}")
        .replace("@@OFFTARGET@@", str(summary["off_target"]))
        .replace("@@EXCLUDED@@", str(summary["excluded"]))
    )
    payload = json.dumps({"books": books, "summary": summary}, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("</", "<\\/")
    return (
        "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<meta name=\"description\" content=\"Narrative-person classifications for tense-labelled New York Times bestsellers, 1931-2025.\">"
        "<title>Narrative person in NYT bestsellers, 1931–2025</title>"
        f"<style>{CSS}</style></head><body>{body}"
        f'<script id="data" type="application/json">{payload}</script><script>{JS}</script>'
        "</body></html>\n"
    )


def main():
    books = load_data()
    output = render(books)
    OUTPUT.write_text(output, encoding="utf-8")
    summary = summarize(books)
    print(
        f"Wrote {OUTPUT.relative_to(ROOT)}: {len(books)} reviewed records, "
        f"{summary['eligible']} eligible labels, {summary['quotes']:,} quotes"
    )


if __name__ == "__main__":
    main()
