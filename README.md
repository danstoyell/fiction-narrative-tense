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
| **1. Build annual candidate batches** | `analysis/build_sample.py` or `analysis/build_topn.py` (NYT-ranked candidates) | `raw_data/sample*.csv` |
| **2. Crawl Goodreads quotes** | `crawl.py` / `crawl_step.py`, via `booktense/goodreads.py` | `raw_data/books_*.csv`, `raw_data/quotes_*.csv` — `bucket`/`tense` written blank |
| **3. Classify** | reading judgment per `METHODOLOGY.md`, applied by an agent (`.claude/agents/tense-classifier.md`) or the Terra harness (`terra/terra_pilot.py`, `terra/terra_batch.py`, `terra/terra_early_batch.py`, `terra/terra_rest_step.py`) | `raw_data/classified*/*.json` — per-quote `bucket`, `tense`, `beat_tense`, plus book-level `narrating_situation` |

Downstream of classification, all under **`analysis/`**:

- **`analysis/analyze_year.py`** applies `METHODOLOGY.md`'s pooled-evidence and narrating-situation rules to `classified/*.json` → a PAST/PRESENT/DUAL/INSUFFICIENT label per book, with confidence and abstention accounting.
- **`analysis/build_report.py`** reads every cohort's books/quotes/classified files straight from `raw_data/`, computes every number on the page from source (nothing hand-maintained), and writes `trend.html` (self-contained artifact) and `trend_local.html` + `raw_data/report_data.json` (fetch-based, run `python3 -m http.server` to view locally) — both HTML files land at the repo root, not inside `analysis/`.
- **`analysis/build_dataset.py`** reuses `build_report.py`'s own join to export a consolidated, supplemental view to top-level **`dataset/`** (`books.csv`, `quotes.csv`) — see `dataset/README.md`.
- **`classify_status.py`** (stays at the repo root) reports what's left to classify.

The dataset spans three internal provenance cohorts, not three literal top-N samples. From
1931–1995, NYT-ranked candidates were extended for years below a target of two usable labels;
from 1996–2015, candidates were extended toward ten usable labels per year; from 2016–2025,
all quote-eligible books in a fixed top-30 candidate pool were classified. The internal keys
`pilot`, `hist`, and `modern` are retained in data files only to identify which crawl batches
and source files a row came from. **`raw_data/DATASET.md`** documents the exact mapping and
mirrors `build_report.py`'s `SOURCES` list.

## Methodology

**`METHODOLOGY.md`** is the spec: how a quote is bucketed, when `tense` and `beat_tense` are
recorded, how those signals are pooled, and how `narrating_situation`, dominance, evidence,
and confidence bars produce a book label. It is the one place classification rules live —
`analyze_year.py` and the classifier agent/prompt both point back to it.
`terra/terra_prompt_v2.md` is a tie-breaker addendum used alongside it by the Terra harness.

## Everything else

Finished-job artifacts (batch assignment lists, Terra run manifests, superseded scripts,
one-time verification/eval exercises) live under **`archive/`**, organized by why each
thing is kept rather than deleted — see the tree there for what's in each subfolder.
