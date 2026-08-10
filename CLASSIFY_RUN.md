# Classification run — all 10 years (2016–2025)

**Everything persists to disk. Nothing depends on a session staying alive.**

| Path | Contents |
|---|---|
| `data/classified/<sample_id>.json` | one file per book — per-quote buckets, tenses, notes |
| `data/batches/<year>_<n>.txt` | 43 batch assignments, 6 books each |
| `data/classified_v1_2021/` | archived first-pass 2021 labels, for comparison |
| `data/labels_<stratum>.csv` | thresholded output from `analyze_year.py` |

## Resume after any interruption

```bash
python3 classify_status.py              # done vs pending, by year
python3 classify_status.py top2019      # pending sample_ids for one year
```

A batch is safe to re-run: agents overwrite their own per-book file and never
touch a CSV, so a partially finished batch loses nothing.

## Agent prompt template

> You are the tense-classifier agent. Working dir: this repo.
> Read `.claude/agents/tense-classifier.md` and `METHODOLOGY.md` first.
> Quotes CSV: `data/quotes_topn.csv`. Your assignment: the sample_ids in
> `data/batches/<NAME>.txt`. Write one JSON per book to `data/classified/`.
> Classify only from quote text — never from prior knowledge of the novel.
> Report bucket counts, past/present split, `narrating_situation`, verse verdict,
> and any quote that would flip a label.

## Then

```bash
for y in 2016 2017 2018 2019 2020 2021 2022 2023 2024 2025; do
  python3 analyze_year.py --stratum top$y
done
```

## Known issues carried into this run

- METHODOLOGY's `"Some stories," she says` contradiction is **fixed**; the v1 2021
  pass ran under the contradictory text, which is why 2021 is being redone.
- `narrating_situation` drives the base-tense label; the quote ratio only sets
  confidence and flags disagreement. A ratio alone cannot tell a present-base
  novel with an embedded past tale (Cloud Cuckoo Land) from one that genuinely
  alternates (Golden Girl).
- Goodreads wraps quotes in curly quotes indistinguishable from dialogue marks,
  so ~87% of quotes give the dialogue test nothing to work with. Agents fall back
  on vocatives, register and speech markers.


---

## Session checkpoint — 2026-08-09

**76 of 239 classified.** Queue rebuilt from disk truth; 85 batches of 2 remain,
now ordered **quote-richest first** (earlier batches ran smallest-first to beat a
watchdog, which front-loaded the thin, abstention-prone books).

| year | labelable | done | pending |
|---|---|---|---|
| 2016 | 23 | 18 | 5 |
| 2017 | 23 | 14 | 9 |
| 2018 | 23 | 4 | 19 |
| 2019 | 23 | 2 | 21 |
| 2020 | 25 | 16 | 9 |
| 2021 | 26 | 2 | 24 |
| 2022 | 23 | 6 | 17 |
| 2023 | 22 | 14 | 8 |
| 2024 | 24 | 0 | 24 |
| 2025 | 27 | 0 | 27 |

`narrating_situation` so far: retrospective 56, simultaneous 13, dual 7, unclear 1.

### Operational lessons (do not relearn these)

* **Three concurrent agents, two books each.** Eight concurrent tripped a 600s
  no-output watchdog and killed six agents. Three concurrent has not failed once.
* **Agents must write each book's JSON before starting the next.** Two agents died
  holding results in memory and lost everything they had classified.
* **Never rewrite `data/batches/*.txt` while agents are reading them.** Done once by
  mistake; an agent noticed mid-run. Rebuild the queue only when nothing is in flight.
* Spend-limit terminations are indistinguishable from stalls at the caller and hit
  regardless of batch size. Retry is always safe — recovery reads disk, not context.

### Open issues found during this run, not yet acted on

1. **Fragment rule misfiles truncated past narration as `gnomic`.** Tense counts are
   unaffected (fragments carry no tense) but gnomic share is inflated in past-tense
   books — so it cannot be cited as an aphorism-contamination measure without
   correcting for this first.
2. **Epigraph ambiguity**: the bucket table lists epigraphs under `gnomic` but
   "epigraph attributions" under `paratext`. Both non-diagnostic; needs a tiebreak.
3. **Four distinct abstention causes** now observed, with different bias
   implications — report them separately, never as one rate:
   quote-poor · event-poor (aphorism-dominated) · dialogue-dominated ·
   paratext-dominated (one 2020 book was 14/25 author's note, 0 event quotes).
4. **Genre contamination beyond verse**: at least one title reads as a multi-story
   volume rather than a novel ("what tense is this book in" is malformed for it).
   Two categories found so far — verse and collections — both detectable only by
   reading quotes, not titles.
5. **2021 re-run is incomplete** (2 of 26). Its v1 labels are in
   `data/classified_v1_2021/`; `report_2021.html` still reflects v1 and must be
   regenerated once the re-run finishes.

### Partial-file sweeps are DESTRUCTIVE — never run one while agents are live

`classify_status.py` reports partial files (chunk written, agent then killed).
Deleting them so they re-run clean is correct **only when nothing is in flight**.

Run mid-flight, the sweep deletes a live agent's chunk-1 output. That happened to
`top2019:3349`: the agent wrote 25/42, the sweep removed it, and the agent
reported its file had vanished and hypothesised the chunked-write strategy was
silently losing data. It was not — the sweep ate it. The agent recovered by
rewriting all 42 in one pass and verifying on disk.

A partial file is indistinguishable from a live agent's in-progress chunk. Check
that no agents are running before sweeping, or just leave partials alone: a
re-run overwrites them anyway.
