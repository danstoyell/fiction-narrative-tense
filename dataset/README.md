# Consolidated dataset

Two flat CSVs covering every classified book across all three annual-selection cohorts
(`pilot` 1931–1995, `hist` 1996–2015, `modern` 2016–2025). **Generated, not authoritative** — regenerate with
`python3 analysis/build_dataset.py` from the repo root. Never hand-edit these files; the
source of truth is the per-cohort fragment CSVs and `classified_*/` directories documented in
[`../raw_data/DATASET.md`](../raw_data/DATASET.md), which `analysis/build_report.py` reads
directly. This pair exists because that fragmentation isn't a convenient shape to consume the
dataset in — these are a derived, presentable view of the same data, kept in sync by reusing
`analysis/build_report.py`'s own `load()` function rather than re-implementing the join.

For what the classification judgments mean, see [`../METHODOLOGY.md`](../METHODOLOGY.md).

## `books.csv` — one row per book

| Column | Meaning |
|---|---|
| `sample_id` | Unique book ID, e.g. `top2021:PROJECT HAIL MARY` |
| `frame` | Internal provenance key: `pilot` (historical candidates extended toward ≥2 labels/year) · `hist` (extended toward ≥10 labels/year) · `modern` (all eligible books from a fixed top-30 candidate pool). It does not mean every cohort is a literal top-N sample. |
| `year`, `title`, `author` | |
| `label` | Display class: `PAST`, `PRESENT`, `OTHER` (dual-narration or excluded-verse), or `ABSTAIN` |
| `raw_label` | Finer-grained: `PAST`, `PRESENT`, `DUAL`, `EXCLUDED-verse`, `INSUFFICIENT`, or `UNCLEAR` |
| `confidence` | `high`, `med`, `CONFLICT` (structural read disagrees with the quote ratio), or `manual` (a manual override applied) |
| `narrating_situation` | The classifying agent's holistic read: `retrospective`, `simultaneous`, `dual`, or `unclear` — the primary signal `raw_label` is derived from |
| `agent_note` | Free-text note from the classifying agent |
| `why` | One-line explanation of the label (ratio + situation) |
| `n_quotes` | Total quotes fetched for this book (all buckets) |
| `event_past`, `event_present` | Tense counts on `event`-bucket quotes only |
| `beat_past`, `beat_present` | `beat_tense` counts on `dialogue`-bucket quotes (narrator's tag/action-beat tense, pooled with event counts to produce the label per `METHODOLOGY.md` §4b) |
| `bucket_event`, `bucket_dialogue`, `bucket_gnomic`, `bucket_paratext`, `bucket_unclear` | Quote counts by bucket |

## `quotes.csv` — one row per quote

| Column | Meaning |
|---|---|
| `sample_id`, `frame`, `year`, `title` | Joins back to `books.csv` |
| `quote_id` | Unique within a book |
| `bucket` | `event`, `dialogue`, `gnomic`, `paratext`, or `unclear` |
| `tense` | `past`/`present`, set only when `bucket == event` |
| `beat_tense` | `past`/`present`/`none`, set only when `bucket == dialogue` |
| `note` | Classifying agent's per-quote note |
| `quote_text` | The excerpt itself, verbatim |

`quote_text` is an in-copyright excerpt from the source novel, included here because most of
the existing per-cohort quote CSVs in `raw_data/` already commit quote text the same way.
