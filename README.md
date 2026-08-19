# booktense — narrative tense in fiction over time

**Question:** what tense (past / present / mixed) is fiction written in, and how has that
changed over time? Measured against NYT hardcover fiction bestsellers, using Goodreads
pull-quotes as the text source. Full design rationale, prior art, and why HathiTrust was
dropped: `archive/design-history/PLAN.md`.

## Pipeline

Three stages, each independently re-runnable because every stage persists its output with
provenance (source URL, page fetched) rather than just a verdict.

| Stage | Tool | Output |
|---|---|---|
| **1. Fetch the frame** | `build_sample.py` (stratified sample) or `build_topn.py` (top-N/year census) | `data/sample*.csv` |
| **2. Crawl Goodreads quotes** | `crawl.py` / `crawl_step.py`, via `booktense/goodreads.py` | `data/books_*.csv`, `data/quotes_*.csv` — `bucket`/`tense` written blank |
| **3. Classify** | reading judgment per `METHODOLOGY.md`, applied by an agent (`.claude/agents/tense-classifier.md`) or the Terra harness (`terra_pilot.py`, `terra_batch.py`, `terra_early_batch.py`, `terra_rest_step.py`) | `data/classified*/*.json` — per-quote `bucket`, `tense`, `beat_tense`, plus book-level `narrating_situation` |

Downstream of classification:

- **`analyze_year.py`** applies `METHODOLOGY.md`'s thresholds to `classified/*.json` → a PAST/PRESENT/DUAL/INSUFFICIENT label per book, with confidence and abstention accounting.
- **`build_report.py`** reads every frame's books/quotes/classified files straight from `data/`, computes every number on the page from source (nothing hand-maintained), and writes `trend.html` (self-contained artifact) and `trend_local.html` + `data/report_data.json` (fetch-based, run `python3 -m http.server` to view locally).
- **`classify_status.py`** reports what's left to classify.

The dataset spans three frames — `modern` (2016–2025, top 30/year), `hist` (1996–2015, top
~10/year), `pilot` (1931–1995, top 3/year) — fragmented across one CSV/directory per crawl
or classify batch. **`data/DATASET.md`** documents exactly which files belong to which
frame; it mirrors `build_report.py`'s `SOURCES` list.

## Methodology

**`METHODOLOGY.md`** is the spec: how a quote is bucketed (dialogue / gnomic / event /
paratext), when `tense` and `beat_tense` are recorded, and the thresholds that turn quote
counts into a book label. It is the one place classification rules live — `analyze_year.py`
and the classifier agent/prompt both point back to it, so it does not drift from the code.
`terra_prompt_v2.md` is a tie-breaker addendum used alongside it by the Terra harness.

## Everything else

Finished-job artifacts (batch assignment lists, Terra run manifests, superseded scripts,
one-time verification/eval exercises) live under **`archive/`**, organized by why each
thing is kept rather than deleted — see the tree there for what's in each subfolder.
