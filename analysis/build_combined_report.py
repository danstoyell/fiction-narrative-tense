"""Build the standalone combined narrative-person and narrative-tense explorer.

Rebuild from the repository root with:

    python3 analysis/build_combined_report.py

The output, ``combined_report.html``, is self-contained and uses the reviewed
person export joined to the tense book export for book-level explanations.
"""

from __future__ import annotations

import collections
import csv
import datetime as dt
import html
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PERSON_BOOKS_CSV = ROOT / "dataset" / "person_books.csv"
PERSON_QUOTES_CSV = ROOT / "dataset" / "person_quotes.csv"
TENSE_BOOKS_CSV = ROOT / "dataset" / "books.csv"
TENSE_QUOTES_CSV = ROOT / "dataset" / "quotes.csv"
OUTPUT = ROOT / "combined_report.html"
PERSON_LABELS = ("FIRST", "SECOND", "THIRD", "ALTERNATING")
TENSE_LABELS = ("PAST", "PRESENT", "DUAL")


def _json_field(value: str, field: str, sample_id: str):
    try:
        return json.loads(value or "[]")
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid {field} JSON for {sample_id}: {exc}") from exc


def load_data(
    person_books_path: Path = PERSON_BOOKS_CSV,
    person_quotes_path: Path = PERSON_QUOTES_CSV,
    tense_books_path: Path = TENSE_BOOKS_CSV,
    tense_quotes_path: Path = TENSE_QUOTES_CSV,
):
    with tense_books_path.open(encoding="utf-8", newline="") as handle:
        tense_rows = {row["sample_id"]: row for row in csv.DictReader(handle)}
    with person_quotes_path.open(encoding="utf-8", newline="") as handle:
        quote_rows = list(csv.DictReader(handle))
    with tense_quotes_path.open(encoding="utf-8", newline="") as handle:
        tense_quote_rows = {
            (row["sample_id"], row["quote_id"]): row for row in csv.DictReader(handle)
        }
    quotes_by_book: dict[str, list[dict]] = collections.defaultdict(list)
    for row in quote_rows:
        tense_quote = tense_quote_rows.get((row["sample_id"], row["quote_id"]))
        if tense_quote is None:
            raise ValueError(
                f"No tense quote record for {row['sample_id']} / {row['quote_id']}"
            )
        quotes_by_book[row["sample_id"]].append(
            {
                "id": row["quote_id"],
                "bucket": row["bucket"],
                "tense": row["tense"],
                "beat": row["beat_tense"],
                "tense_note": tense_quote["note"],
                "person": row["person_signal"],
                "person_note": row["person_note"],
                "text": row["quote_text"],
            }
        )

    with person_books_path.open(encoding="utf-8", newline="") as handle:
        person_rows = list(csv.DictReader(handle))
    books = []
    for row in person_rows:
        sample_id = row["sample_id"]
        tense = tense_rows.get(sample_id, {})
        if not tense:
            raise ValueError(f"No tense record for {sample_id}")
        if row["tense_label"] != tense["raw_label"]:
            raise ValueError(
                f"Tense label mismatch for {sample_id}: "
                f"{row['tense_label']} != {tense['raw_label']}"
            )
        quotes = quotes_by_book.get(sample_id, [])
        if len(quotes) != int(row["n_quotes"]):
            raise ValueError(
                f"Quote count mismatch for {sample_id}: "
                f"{row['n_quotes']} != {len(quotes)}"
            )
        books.append(
            {
                "id": sample_id,
                "frame": row["frame"],
                "year": int(row["year"]),
                "title": row["title"],
                "author": row["author"],
                "person": row["person_label"],
                "person_confidence": row["person_confidence"],
                "person_note": row["person_note"],
                "tense": row["tense_label"],
                "tense_confidence": row["tense_confidence"],
                "tense_note": tense.get("agent_note", "") or tense.get("why", ""),
                "tense_why": tense.get("why", ""),
                "situation": tense.get("narrating_situation", ""),
                "n_quotes": int(row["n_quotes"]),
                "web_evidence": _json_field(
                    row["web_evidence_json"], "web_evidence", sample_id
                ),
                "search_log": _json_field(row["search_log_json"], "search_log", sample_id),
                "model": row["model"],
                "reasoning_effort": row["reasoning_effort"],
                "quotes": quotes,
            }
        )
    books.sort(key=lambda row: (row["year"], row["title"], row["id"]))
    return books


def summarize(books):
    eligible = [
        book
        for book in books
        if book["person"] in PERSON_LABELS and book["tense"] in TENSE_LABELS
    ]
    combinations = collections.Counter(
        f"{book['person']}|{book['tense']}" for book in eligible
    )
    return {
        "eligible": len(eligible),
        "all_records": len(books),
        "quotes": sum(book["n_quotes"] for book in eligible),
        "years": [min(book["year"] for book in eligible), max(book["year"] for book in eligible)],
        "persons": dict(collections.Counter(book["person"] for book in eligible)),
        "tenses": dict(collections.Counter(book["tense"] for book in eligible)),
        "combinations": dict(combinations),
        "generated": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
    }


CSS = r"""
:root{color-scheme:dark;--ink:#e8eaf0;--paper:#0f1216;--surface:#161a20;--surface2:#1b2027;
--line:#2b323c;--muted:#9ba5b2;--faint:#6f7986;--first:#d8a15e;--second:#c988ce;
--third:#4fb3b3;--alternating:#8d9bea;--past:#6f86c7;--present:#d66b63;--dual:#aa83bc;
--fpast:#b98a51;--fpresent:#e17a55;--fdual:#cfaa63;--spast:#a26eac;--spresent:#cb6f9e;
--sdual:#b98acb;--tpast:#397f91;--tpresent:#42a899;--tdual:#64a779;--apast:#6f79b7;
--apresent:#9b70ad;--adual:#8776cf;--flag:#df7958;--high:#79b98b;
--mono:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace;
--sans:Inter,ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
--serif:Iowan Old Style,Charter,Georgia,serif}
@media(prefers-color-scheme:light){:root{color-scheme:light;--ink:#15191f;--paper:#f6f7f9;
--surface:#fff;--surface2:#f0f2f5;--line:#dfe3e8;--muted:#59636f;--faint:#87909a;
--first:#a86e29;--second:#994b9f;--third:#187b7b;--alternating:#5262b8;--past:#526ba9;
--present:#b9534c;--dual:#865f99;--fpast:#9a672c;--fpresent:#bd583e;--fdual:#98762d;
--spast:#805088;--spresent:#a34b7a;--sdual:#8d5fa1;--tpast:#226678;--tpresent:#187f73;
--tdual:#42855a;--apast:#53609d;--apresent:#80538f;--adual:#6654ad;--flag:#b44d30;--high:#34794a}}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);line-height:1.58;-webkit-font-smoothing:antialiased}
.wrap{max-width:80rem;margin:auto;padding:3.5rem 1.5rem 6rem;display:flex;flex-direction:column;gap:3.2rem}.narrow{max-width:66rem}
.eyebrow{font:600 .68rem/1.2 var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--faint)}
h1,h2{font-family:var(--serif);font-weight:600;letter-spacing:-.018em;text-wrap:balance}h1{font-size:clamp(2.1rem,5vw,3.2rem);line-height:1.06;margin:.55rem 0 .8rem;max-width:30ch}h2{font-size:1.55rem;margin:0}h3{font-size:.84rem;margin:0}p{margin:0;max-width:72ch}.lede{font-size:1.08rem;color:var(--muted)}section{display:flex;flex-direction:column;gap:1rem}
.chartbox,.panel,.card,.tablewrap,.explorercontrols{background:var(--surface);border:1px solid var(--line);border-radius:3px}.chartbox{padding:1.25rem;overflow-x:auto}
.charthead{display:flex;align-items:end;justify-content:space-between;gap:1rem;flex-wrap:wrap}.chartcontrols{display:grid;grid-template-columns:repeat(5,minmax(8rem,1fr));gap:.75rem;margin-top:1rem}.control label,.control .label{display:block;font:600 .61rem var(--mono);letter-spacing:.07em;text-transform:uppercase;color:var(--faint);margin-bottom:.28rem}
select,input[type=search]{width:100%;font:inherit;font-size:.82rem;color:var(--ink);background:var(--paper);border:1px solid var(--line);border-radius:2px;padding:.42rem .5rem}.dimensions{display:grid;grid-template-columns:1fr 1fr;gap:.7rem;margin-top:.8rem}.dimension{background:var(--surface2);padding:.65rem .75rem;border-radius:2px}.checks{display:flex;flex-wrap:wrap;gap:.35rem .8rem}.checks label{font-size:.78rem;color:var(--muted);white-space:nowrap}.checks input{accent-color:var(--third)}
.figcaption{margin-top:1.1rem;padding-top:.9rem;border-top:1px solid var(--line)}.figtitle{font:600 1.18rem/1.25 var(--serif);letter-spacing:-.01em;margin:0;text-wrap:balance}.figsub{font-size:.8rem;color:var(--muted);margin-top:.25rem}
#chart{display:block;min-width:47rem;width:100%;height:auto;margin-top:.8rem}.grid{stroke:var(--line);stroke-width:1;opacity:.72}.axistext{fill:var(--muted);font:11px var(--mono)}.area{transition:opacity .12s}.chartbox:has(.hoverzone:hover) .area{opacity:.76}
.legend{display:flex;flex-wrap:wrap;gap:.45rem .65rem;margin-top:.6rem}.legend button{font:600 .68rem var(--mono);color:var(--muted);background:var(--paper);border:1px solid var(--line);border-radius:2px;padding:.3rem .45rem;cursor:pointer}.legend button.off{opacity:.4;text-decoration:line-through}.swatch{display:inline-block;width:.68rem;height:.68rem;border-radius:1px;margin-right:.35rem;vertical-align:-1px}.chartnote{color:var(--muted);font-size:.82rem}.tooltip{position:fixed;pointer-events:none;z-index:20;background:var(--ink);color:var(--paper);padding:.5rem .6rem;border-radius:2px;font:12px/1.45 var(--mono);box-shadow:0 4px 18px #0004;display:none;white-space:pre-line}
.cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.8rem}.card{padding:1rem}.metric{font:1.5rem/1 var(--mono);margin:.35rem 0}.card p{font-size:.79rem;color:var(--muted)}
.tablewrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:.8rem}th{font:600 .61rem var(--mono);letter-spacing:.07em;text-transform:uppercase;color:var(--muted);text-align:right;padding:.68rem .72rem;border-bottom:1px solid var(--line);white-space:nowrap}th.left,td.left{text-align:left}td{padding:.5rem .72rem;border-bottom:1px solid var(--line);text-align:right;font-family:var(--mono);font-variant-numeric:tabular-nums;white-space:nowrap}tbody tr:last-child td{border-bottom:0}
.explorercontrols{display:flex;gap:.55rem;align-items:center;flex-wrap:wrap;padding:.72rem .8rem;position:sticky;top:0;z-index:5}.explorercontrols input{flex:1 1 16rem}.count{font:.72rem var(--mono);color:var(--muted);margin-left:auto}.reset,.pagebtn{font:inherit;font-size:.78rem;color:var(--muted);background:var(--paper);border:1px solid var(--line);border-radius:2px;padding:.4rem .62rem;cursor:pointer}.reset:hover,.pagebtn:hover:not(:disabled){color:var(--ink);border-color:var(--muted)}
tr.book{cursor:pointer}tr.book:hover td,tr.book.open td{background:color-mix(in srgb,var(--third) 8%,transparent)}.title{font-family:var(--sans);font-weight:650}.author{font-family:var(--sans);font-size:.75rem;color:var(--muted)}.caret{display:inline-block;width:.8rem;color:var(--faint);transition:.12s}.book.open .caret{transform:rotate(90deg);color:var(--third)}.pill{display:inline-block;font:600 .61rem var(--mono);border:1px solid currentColor;border-radius:2px;padding:.12rem .34rem}.FIRST{color:var(--first)}.SECOND{color:var(--second)}.THIRD{color:var(--third)}.ALTERNATING{color:var(--alternating)}.PAST{color:var(--past)}.PRESENT{color:var(--present)}.DUAL{color:var(--dual)}
.detailrow td{padding:0;background:var(--paper);white-space:normal;text-align:left}.detail{padding:1rem;display:grid;gap:1rem}.decisions{display:grid;grid-template-columns:1fr 1fr;gap:1rem}.decision{font-family:var(--sans);color:var(--muted)}.decision strong{color:var(--ink)}.evidence{display:grid;gap:.5rem}.evidenceitem{border-left:2px solid var(--line);padding-left:.65rem;font-family:var(--sans);font-size:.8rem;color:var(--muted)}.evidenceitem a{color:var(--third);text-decoration:none}.meta{font:600 .61rem var(--mono);letter-spacing:.04em;text-transform:uppercase;color:var(--faint)}.quote{display:grid;grid-template-columns:8rem 1fr;gap:.75rem;border-top:1px solid var(--line);padding:.62rem .1rem}.qmeta{font:.61rem/1.55 var(--mono);color:var(--faint)}.qtext{font:.9rem/1.5 var(--serif);white-space:pre-wrap}.qnotes{display:grid;grid-template-columns:1fr 1fr;gap:.5rem;margin-top:.35rem}.qnote{font:.73rem/1.4 var(--sans);color:var(--muted);border-left:2px solid var(--line);padding-left:.5rem}.pager{display:flex;justify-content:center;align-items:center;gap:1rem}.pagebtn:disabled{opacity:.45}.pagenum{font:.72rem var(--mono);color:var(--muted)}
.caution{border-left:2px solid var(--flag);padding:.12rem 0 .12rem 1rem;color:var(--muted)}footer{border-top:1px solid var(--line);padding-top:1rem;color:var(--faint);font:.72rem/1.7 var(--mono)}
@media(max-width:850px){.chartcontrols{grid-template-columns:repeat(2,1fr)}.cards{grid-template-columns:repeat(2,1fr)}.decisions{grid-template-columns:1fr}}
@media(max-width:620px){.wrap{padding:2rem 1rem 4rem}.dimensions{grid-template-columns:1fr}.quote,.qnotes{grid-template-columns:1fr}.cards{grid-template-columns:1fr}}
"""


BODY = r"""
<main class="wrap">
  <header class="narrow">
    <div class="eyebrow">Booktense · combined explorer</div>
    <h1>Narrative person and tense, together</h1>
    <p class="lede">Explore how first-, third-, and alternating-person narration intersects with past, present, and dual tense across NYT bestsellers. Switch between joint combinations and either dimension alone without changing the underlying reviewed panel.</p>
  </header>

  <section aria-labelledby="chart-title">
    <div class="chartbox">
      <div class="charthead"><div><div class="eyebrow">Interactive book-level distribution</div><h2 id="chart-title">Person × tense over time</h2></div><button id="resetChart" class="reset" type="button">Reset chart</button></div>
      <div class="chartcontrols">
        <div class="control"><label for="view">Break down by</label><select id="view"><option value="combined">Person × tense</option><option value="person">Person only</option><option value="tense">Tense only</option></select></div>
        <div class="control"><label for="startYear">Start year</label><select id="startYear"></select></div>
        <div class="control"><label for="endYear">End year</label><select id="endYear"></select></div>
        <div class="control"><label for="window">Group years</label><select id="window"><option value="1">1 year</option><option value="3">3 years</option><option value="5" selected>5 years</option><option value="10">10 years</option></select></div>
        <div class="control"><label for="denominator">Percentage of</label><select id="denominator"><option value="all">All eligible books</option><option value="selected">Visible categories</option></select></div>
      </div>
      <div class="dimensions">
        <fieldset class="dimension"><legend class="eyebrow">Include person labels</legend><div class="checks" id="personChecks"></div></fieldset>
        <fieldset class="dimension"><legend class="eyebrow">Include tense labels</legend><div class="checks" id="tenseChecks"></div></fieldset>
      </div>
      <div class="figcaption"><h3 class="figtitle" id="figTitle"></h3><p class="figsub" id="figSub"></p></div>
      <svg id="chart" viewBox="0 0 980 420" role="img" aria-label="Interactive stacked area chart of narrative person and tense over time"></svg>
      <div class="legend" id="legend" aria-label="Click a series to include or exclude it"></div>
      <p class="chartnote" id="chartNote"></p>
    </div>
    <p class="caution">The chart describes this deterministic bestseller panel, not all published fiction. “All eligible books” preserves the original denominator when series are hidden; “Visible categories” renormalizes the displayed bands to 100%.</p>
  </section>

  <section aria-labelledby="summary-title"><div><div class="eyebrow">Current chart selection</div><h2 id="summary-title">Selection summary</h2></div><div class="cards" id="cards"></div><div class="tablewrap"><table><thead id="periodHead"></thead><tbody id="periodBody"></tbody></table></div></section>

  <section aria-labelledby="explorer-title">
    <div><div class="eyebrow">Linked evidence browser</div><h2 id="explorer-title">Books and quote-level annotations</h2></div>
    <div class="explorercontrols"><input id="search" type="search" placeholder="Search title, author, or justification…" aria-label="Search books"><button id="clearSearch" class="reset" type="button">Clear search</button><span class="count" id="count"></span></div>
    <div class="tablewrap"><table id="books"><thead><tr><th class="left">Year</th><th class="left">Book</th><th>Person</th><th>Tense</th><th>Confidence</th><th>Quotes</th></tr></thead><tbody></tbody></table></div>
    <div class="pager"><button id="prev" class="pagebtn" type="button">Previous</button><span id="pagenum" class="pagenum"></span><button id="next" class="pagebtn" type="button">Next</button></div>
  </section>

  <section aria-labelledby="read-title"><div><div class="eyebrow">How to read it</div><h2 id="read-title">What changes—and what does not</h2></div><div class="decisions"><p><strong>Combined view.</strong> Every band is an intersection such as FIRST × PRESENT. Person-only and tense-only views aggregate away the other dimension while its checkboxes remain available as population filters.</p><p><strong>Book labels remain separate.</strong> The report combines existing person and tense outputs for analysis; it does not create a new fused classification or infer either label from the other.</p></div></section>

  <footer>Generated @@BUILT@@ from <code>dataset/person_books.csv</code>, <code>dataset/person_quotes.csv</code>, and <code>dataset/books.csv</code>. The overlap contains @@ELIGIBLE@@ books and @@QUOTES@@ quote annotations from @@START@@–@@END@@. Rebuild with <code>python3 analysis/build_combined_report.py</code>.</footer>
</main><div class="tooltip" id="tooltip"></div>
"""


JS = r"""
(() => {
  const D=JSON.parse(document.getElementById('data').textContent), allBooks=D.books, S=D.summary;
  const PERSONS=['FIRST','SECOND','THIRD','ALTERNATING'].filter(x=>(S.persons[x]||0)>0), TENSES=['PAST','PRESENT','DUAL'].filter(x=>(S.tenses[x]||0)>0);
  const names={FIRST:'First person',SECOND:'Second person',THIRD:'Third person',ALTERNATING:'Alternating',PAST:'Past',PRESENT:'Present',DUAL:'Dual'};
  const short={FIRST:'First',SECOND:'Second',THIRD:'Third',ALTERNATING:'Alternating',PAST:'Past',PRESENT:'Present',DUAL:'Dual'};
  const colors={FIRST:'var(--first)',SECOND:'var(--second)',THIRD:'var(--third)',ALTERNATING:'var(--alternating)',PAST:'var(--past)',PRESENT:'var(--present)',DUAL:'var(--dual)',
    'FIRST|PAST':'var(--fpast)','FIRST|PRESENT':'var(--fpresent)','FIRST|DUAL':'var(--fdual)','SECOND|PAST':'var(--spast)','SECOND|PRESENT':'var(--spresent)','SECOND|DUAL':'var(--sdual)',
    'THIRD|PAST':'var(--tpast)','THIRD|PRESENT':'var(--tpresent)','THIRD|DUAL':'var(--tdual)','ALTERNATING|PAST':'var(--apast)','ALTERNATING|PRESENT':'var(--apresent)','ALTERNATING|DUAL':'var(--adual)'};
  const eligible=allBooks.filter(b=>PERSONS.includes(b.person)&&TENSES.includes(b.tense));
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const pct=(n,d)=>d?`${(100*n/d).toFixed(1)}%`:'—';
  const els=Object.fromEntries(['view','startYear','endYear','window','denominator','personChecks','tenseChecks','legend','chart','chartNote','cards','periodHead','periodBody','search','clearSearch','count','prev','next','pagenum','resetChart','figTitle','figSub'].map(id=>[id,document.getElementById(id)]));
  let hidden=new Set(),page=1;const pageSize=20;
  const years=[...new Set(eligible.map(b=>b.year))].sort((a,b)=>a-b);
  years.forEach(y=>{els.startYear.insertAdjacentHTML('beforeend',`<option>${y}</option>`);els.endYear.insertAdjacentHTML('beforeend',`<option>${y}</option>`)});els.startYear.value=years[0];els.endYear.value=years.at(-1);
  const makeChecks=(where,values,dim)=>{where.innerHTML=values.map(v=>`<label><input type="checkbox" data-dim="${dim}" value="${v}" checked> ${names[v]} <span style="color:var(--faint)">(${dim==='person'?S.persons[v]:S.tenses[v]})</span></label>`).join('')};makeChecks(els.personChecks,PERSONS,'person');makeChecks(els.tenseChecks,TENSES,'tense');
  const checked=dim=>[...document.querySelectorAll(`input[data-dim="${dim}"]:checked`)].map(x=>x.value);
  const adj={FIRST:'first',SECOND:'second',THIRD:'third',ALTERNATING:'alternating',PAST:'past',PRESENT:'present',DUAL:'dual'};
  const orList=a=>a.length<3?a.join(' or '):`${a.slice(0,-1).join(', ')}, or ${a.at(-1)}`;
  const adjList=(labels,dim)=>orList(labels.map((l,i)=>adj[l]+(i<labels.length-1?'-':`-${dim}`)));
  const keyName=k=>k.includes('|')?k.split('|').map(x=>short[x]).join(' × '):names[k];
  function candidateSeries(){const ps=checked('person'),ts=checked('tense');if(els.view.value==='person')return ps;if(els.view.value==='tense')return ts;return ps.flatMap(p=>ts.map(t=>`${p}|${t}`))}
  function matchesSeries(b,key){if(key.includes('|')){const [p,t]=key.split('|');return b.person===p&&b.tense===t}return els.view.value==='person'?b.person===key:b.tense===key}
  function selectedDimensions(b){return checked('person').includes(b.person)&&checked('tense').includes(b.tense)}
  function activeSeries(){return candidateSeries().filter(k=>!hidden.has(k))}
  function aggregate(series){const lo=+els.startYear.value,hi=+els.endYear.value,size=+els.window.value,out=[];for(let start=lo;start<=hi;start+=size){const end=Math.min(hi,start+size-1),base=eligible.filter(b=>b.year>=start&&b.year<=end),counts={};series.forEach(k=>counts[k]=base.filter(b=>selectedDimensions(b)&&matchesSeries(b,k)).length);const selected=series.reduce((n,k)=>n+counts[k],0),denom=els.denominator.value==='all'?base.length:selected;out.push({start,end,mid:(start+end+1)/2,label:start===end?String(start):`${start}–${end}`,base:base.length,selected,denom,counts})}return out}
  function renderLegend(){const candidates=candidateSeries();hidden=new Set([...hidden].filter(k=>candidates.includes(k)));els.legend.innerHTML=candidates.map(k=>`<button type="button" data-key="${k}" class="${hidden.has(k)?'off':''}" aria-pressed="${!hidden.has(k)}"><i class="swatch" style="background:${colors[k]}"></i>${keyName(k)}</button>`).join('');els.legend.querySelectorAll('button').forEach(btn=>btn.onclick=()=>{const k=btn.dataset.key;if(hidden.has(k))hidden.delete(k);else if(activeSeries().length>1)hidden.add(k);renderAll()})}
  function axisLayout(groups,iw){const tick=g=>g.start===g.end?String(g.start):Math.floor(g.start/100)===Math.floor(g.end/100)?`${g.start}–${String(g.end).slice(2)}`:g.label,labels=groups.map(tick),lw=Math.max(...labels.map(s=>s.length))*6.6,size=groups[0].end-groups[0].start+1,span=groups.at(-1).mid-groups[0].mid,step=span?iw*size/span:iw,nice=[1,2,5,10,20,25,50],stride=need=>nice.find(k=>step*k>=need)||nice.at(-1);if(step>=lw+10)return{labels,show:()=>true,rotate:false,b:66};if(size===1){const k=stride(lw+10);return{labels,show:g=>g.start%k===0,rotate:false,b:66}}const k=stride(20);return{labels,show:(g,i)=>i%k===0,rotate:true,b:Math.ceil(24+lw*Math.sin(40*Math.PI/180))}}
  function drawChart(){const series=activeSeries(),groups=aggregate(series),svg=els.chart,W=980,ih=336,m={l:52,r:45,t:18},iw=W-m.l-m.r,axis=axisLayout(groups,iw);m.b=axis.b;const H=m.t+ih+m.b;svg.setAttribute('viewBox',`0 0 ${W} ${H}`);const x0=groups[0].mid,x1=groups.at(-1).mid,x=v=>m.l+iw*(v-x0)/Math.max(1,x1-x0),y=v=>m.t+ih*(1-v);const zero=groups.map(()=>0),bounds=[];let running=zero.slice();series.forEach(k=>{running=groups.map((g,i)=>running[i]+(g.denom?g.counts[k]/g.denom:0));bounds.push(running)});const band=(lo,hi,k)=>{const up=groups.map((g,i)=>`${x(g.mid)},${y(hi[i])}`).join(' '),dn=groups.map((g,i)=>`${x(g.mid)},${y(lo[i])}`).reverse().join(' ');return `<polygon class="area" points="${up} ${dn}" fill="${colors[k]}" opacity=".88"/>`};let parts=[];for(let n=0;n<=100;n+=10){const gy=y(n/100);parts.push(`<line class="grid" x1="${m.l}" x2="${W-m.r}" y1="${gy}" y2="${gy}"/><text class="axistext" x="${m.l-9}" y="${gy+4}" text-anchor="end">${n}%</text><text class="axistext" x="${W-m.r+9}" y="${gy+4}" text-anchor="start">${n}%</text>`)}series.forEach((k,i)=>parts.push(band(i?bounds[i-1]:zero,bounds[i],k)));bounds.slice(0,-1).forEach((line,i)=>parts.push(`<polyline points="${groups.map((g,j)=>`${x(g.mid)},${y(line[j])}`).join(' ')}" fill="none" stroke="var(--surface)" stroke-width="${i?1.2:1.6}"/>`));const y0=m.t+ih;groups.forEach((g,i)=>{if(!axis.show(g,i))return;const cx=x(g.mid),label=axis.labels[i];parts.push(`<line class="grid" x1="${cx}" x2="${cx}" y1="${y0}" y2="${y0+5}"/>`);if(axis.rotate)parts.push(`<text class="axistext" x="${cx}" y="${y0+15}" text-anchor="end" transform="rotate(-40 ${cx} ${y0+15})">${label}</text>`);else parts.push(`<text class="axistext" x="${cx}" y="${y0+18}" text-anchor="middle">${label}</text><text class="axistext" x="${cx}" y="${y0+31}" text-anchor="middle" style="fill:var(--faint);font-size:9.5px">n=${g.denom}</text>`)});groups.forEach((g,i)=>{const left=i?x((groups[i-1].mid+g.mid)/2):m.l,right=i<groups.length-1?x((g.mid+groups[i+1].mid)/2):W-m.r;parts.push(`<rect class="hoverzone" data-i="${i}" x="${left}" y="${m.t}" width="${Math.max(1,right-left)}" height="${ih}" fill="transparent"/>`)});svg.innerHTML=parts.join('');const tip=document.getElementById('tooltip');svg.querySelectorAll('.hoverzone').forEach(z=>{z.onmousemove=e=>{const g=groups[+z.dataset.i];tip.style.display='block';tip.style.left=`${e.clientX+12}px`;tip.style.top=`${e.clientY+12}px`;tip.textContent=[`${g.label} · denominator ${g.denom}`,...series.map(k=>`${keyName(k)}: ${g.counts[k]} (${pct(g.counts[k],g.denom)})`)].join('\n')};z.onmouseleave=()=>tip.style.display='none'});return groups}
  function renderSummary(groups){const series=activeSeries(),lo=+els.startYear.value,hi=+els.endYear.value,range=eligible.filter(b=>b.year>=lo&&b.year<=hi),visible=range.filter(b=>selectedDimensions(b)&&series.some(k=>matchesSeries(b,k)));els.cards.innerHTML=[['Visible books',visible.length,`${pct(visible.length,range.length)} of ${range.length} eligible in range`],['Active bands',series.length,els.view.options[els.view.selectedIndex].text],['Year range',`${lo}–${hi}`,`${hi-lo+1} calendar years`],['Quote evidence',visible.reduce((n,b)=>n+b.n_quotes,0).toLocaleString(),'annotations on visible books']].map(x=>`<article class="card"><div class="eyebrow">${x[0]}</div><div class="metric">${x[1]}</div><p>${x[2]}</p></article>`).join('');els.periodHead.innerHTML=`<tr><th class="left">Period</th>${series.map(k=>`<th>${keyName(k)}</th>`).join('')}<th>Denominator</th></tr>`;els.periodBody.innerHTML=groups.map(g=>`<tr><td class="left">${g.label}</td>${series.map(k=>`<td>${g.counts[k]} <span style="color:var(--faint)">(${pct(g.counts[k],g.denom)})</span></td>`).join('')}<td>${g.denom}</td></tr>`).join('');els.chartNote.textContent=els.denominator.value==='all'?`Bands show shares of every eligible book in each period; hidden or filtered categories remain as blank space above the stack.`:`Bands are renormalized within the ${visible.length} currently visible books across the selected range.`}
  function chartBooks(){const lo=+els.startYear.value,hi=+els.endYear.value,series=activeSeries();return eligible.filter(b=>b.year>=lo&&b.year<=hi&&selectedDimensions(b)&&series.some(k=>matchesSeries(b,k)))}
  function pill(v){return `<span class="pill ${v}">${v}</span>`}
  function details(b){const ev=b.web_evidence.map(e=>`<div class="evidenceitem"><div class="meta">Tier ${esc(e.tier)} · ${esc(e.scope)} · supports ${esc(e.supports)}</div><a href="${esc(e.url)}" target="_blank" rel="noopener noreferrer">${esc(e.title||e.url)}</a><div>${esc(e.note)}</div></div>`).join('')||'<div class="evidenceitem">No retained web evidence.</div>';const qs=b.quotes.map(q=>`<div class="quote"><div class="qmeta">${esc(q.id)}<br>person: ${esc(q.person)}<br>tense: ${esc(q.tense||'—')}${q.beat?`<br>beat: ${esc(q.beat)}`:''}<br>${esc(q.bucket)}</div><div><div class="qtext">${esc(q.text)}</div><div class="qnotes"><div class="qnote"><strong>Person.</strong> ${esc(q.person_note||'No note.')}</div><div class="qnote"><strong>Tense.</strong> ${esc(q.tense_note||'No note.')}</div></div></div></div>`).join('');return `<tr class="detailrow"><td colspan="6"><div class="detail"><div class="decisions"><p class="decision"><strong>Person decision.</strong> ${esc(b.person_note)}</p><p class="decision"><strong>Tense decision.</strong> ${esc(b.tense_note||b.tense_why)}${b.situation?` <span class="meta">${esc(b.situation)}</span>`:''}</p></div><div><h3>Person web evidence (${b.web_evidence.length})</h3><div class="evidence">${ev}</div></div><details><summary>Quote annotations (${b.quotes.length})</summary>${qs}</details><div class="meta">${esc(b.model)} · ${esc(b.reasoning_effort)} reasoning</div></div></td></tr>`}
  function renderExplorer(){const q=els.search.value.trim().toLowerCase(),rows=chartBooks().filter(b=>!q||`${b.title} ${b.author} ${b.person_note} ${b.tense_note} ${b.tense_why}`.toLowerCase().includes(q)),pages=Math.max(1,Math.ceil(rows.length/pageSize));page=Math.min(page,pages);const shown=rows.slice((page-1)*pageSize,page*pageSize),body=document.querySelector('#books tbody');body.innerHTML=shown.map(b=>`<tr class="book" data-id="${esc(b.id)}"><td class="left"><span class="caret">▶</span>${b.year}</td><td class="left"><div class="title">${esc(b.title)}</div><div class="author">${esc(b.author)}</div></td><td>${pill(b.person)}</td><td>${pill(b.tense)}</td><td>${esc(b.person_confidence)}/${esc(b.tense_confidence)}</td><td>${b.n_quotes}</td></tr>`).join('')||'<tr><td colspan="6" class="left">No books match the chart and search filters.</td></tr>';body.querySelectorAll('.book').forEach(row=>row.onclick=()=>{const open=row.classList.toggle('open'),next=row.nextElementSibling;if(next&&next.classList.contains('detailrow'))next.remove();else if(open)row.insertAdjacentHTML('afterend',details(allBooks.find(b=>b.id===row.dataset.id)))});els.count.textContent=`${rows.length} books`;els.pagenum.textContent=`Page ${page} of ${pages}`;els.prev.disabled=page<=1;els.next.disabled=page>=pages}
  function renderTitle(){const series=activeSeries(),view=els.view.value,ps=checked('person'),ts=checked('tense'),lo=+els.startYear.value,hi=+els.endYear.value,size=+els.window.value,sel={person:ps,tense:ts},all={person:PERSONS,tense:TENSES};const qual=Object.fromEntries(['person','tense'].map(d=>[d,sel[d].length<all[d].length?adjList(sel[d],d):'']));let broken,title;if(series.length===1){const fixed=Object.fromEntries(series[0].split('|').map(l=>[PERSONS.includes(l)?'person':'tense',l]));broken=[];title=`Share of ${['person','tense'].map(d=>fixed[d]?`${adj[fixed[d]]}-${d}`:qual[d]).filter(Boolean).join(', ')} NYT bestsellers`}else{broken=view==='combined'?['person','tense'].filter(d=>sel[d].length>1):[view];const subject=broken.length===2?'Narrative person × tense':broken[0]==='person'?'Narrative person':'Narrative tense',q=['person','tense'].filter(d=>!broken.includes(d)&&qual[d]).map(d=>qual[d]).join(', ');title=`${subject} in ${q?`${q} `:''}NYT bestsellers`}title+=`, ${lo===hi?lo:`${lo}–${hi}`}`;const range=eligible.filter(b=>b.year>=lo&&b.year<=hi).length,period=size===1?'each year':`each ${size}-year period`,excluded=broken.flatMap(d=>all[d].filter(l=>!sel[d].includes(l)).map(l=>`${short[l]} ${d}`)),bits=[els.denominator.value==='all'?`Share of all eligible books in ${period}`:`Share of the visible categories in ${period}, stacked to 100%`,`${chartBooks().length.toLocaleString()} of ${range.toLocaleString()} books shown`];if(excluded.length)bits.push(`Excludes ${excluded.join(', ')}`);if(hidden.size)bits.push(`Hidden: ${[...hidden].map(keyName).join(', ')}`);els.figTitle.textContent=title;els.figSub.textContent=bits.join(' · ');els.chart.setAttribute('aria-label',`Stacked area chart: ${title}`)}
  function renderAll(){renderLegend();renderTitle();const groups=drawChart();renderSummary(groups);page=1;renderExplorer()}
  document.querySelectorAll('.checks').forEach(group=>group.onchange=e=>{if(e.target.matches('input')&&!checked(e.target.dataset.dim).length)e.target.checked=true;hidden.clear();renderAll()});['view','window','denominator'].forEach(id=>els[id].onchange=()=>{hidden.clear();renderAll()});els.startYear.onchange=()=>{if(+els.startYear.value>+els.endYear.value)els.endYear.value=els.startYear.value;renderAll()};els.endYear.onchange=()=>{if(+els.endYear.value<+els.startYear.value)els.startYear.value=els.endYear.value;renderAll()};els.resetChart.onclick=()=>{els.view.value='combined';els.startYear.value=years[0];els.endYear.value=years.at(-1);els.window.value='5';els.denominator.value='all';document.querySelectorAll('.checks input').forEach(x=>x.checked=true);hidden.clear();renderAll()};els.search.oninput=()=>{page=1;renderExplorer()};els.clearSearch.onclick=()=>{els.search.value='';page=1;renderExplorer()};els.prev.onclick=()=>{page--;renderExplorer()};els.next.onclick=()=>{page++;renderExplorer()};renderAll();
})();
"""


def render(books):
    summary = summarize(books)
    built = dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    body = (
        BODY.replace("@@BUILT@@", html.escape(built))
        .replace("@@ELIGIBLE@@", str(summary["eligible"]))
        .replace("@@QUOTES@@", f"{summary['quotes']:,}")
        .replace("@@START@@", str(summary["years"][0]))
        .replace("@@END@@", str(summary["years"][1]))
    )
    payload = json.dumps(
        {"books": books, "summary": summary}, ensure_ascii=False, separators=(",", ":")
    ).replace("</", "<\\/")
    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="description" content="Combined narrative-person and narrative-tense explorer for New York Times bestsellers.">'
        '<title>Narrative person and tense, together</title>'
        f"<style>{CSS}</style></head><body>{body}"
        f'<script id="data" type="application/json">{payload}</script><script>{JS}</script>'
        "</body></html>\n"
    )


def main():
    books = load_data()
    page = render(books)
    OUTPUT.write_text(page, encoding="utf-8")
    summary = summarize(books)
    print(
        f"Wrote {OUTPUT.relative_to(ROOT)}: {summary['eligible']} eligible books, "
        f"{len(summary['combinations'])} observed combinations, "
        f"{summary['quotes']:,} quotes"
    )


if __name__ == "__main__":
    main()
