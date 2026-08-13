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

## Budget: ~4.4% of a session per book

Measured 2026-08-10 — **17 books = 74% of one session**.

| Budget | Books |
|---|---|
| quarter session | 5–6 |
| half session | 11–12 |
| full session | 22–23 |

Holds only for **five concurrent agents, one book each**. Degrades sharply otherwise:
six-book batches at eight concurrent tripped the 600s watchdog and killed 6 of 10
agents, and a killed agent burns budget while delivering nothing. Books range 23–48
quotes; a round weighted toward 40+ quote books runs nearer 6% each.

## DONE: beat_tense backfill (completed 2026-08-11)

**All 123 in-frame books backfilled. 1,078 beat judgments. 0 integrity violations.**
Every `dialogue` quote in the corpus now carries `beat_tense`. No methodological split
remains — the whole corpus is on one spec.

```
past=368   present=90   none=620
books with present beats: 27 of 123
zero-yield books (no recoverable beat at all): 9
mixed-profile books (both past and present beats): 4
```

**Mixed profiles are rare and every one is explained by real structure**, not noise:

| book | situation | past | pres | why |
|---|---|---|---|---|
| *American Dirt* | simultaneous | 1 | 2 | present + documented past recollection strand |
| *You Like It Darker* | retrospective | 1 | 1 | **story collection** — multiple narrators |
| `top2020:4688` | simultaneous | 1 | 1 | remembered speech framed in present |
| *Here One Moment* | dual | 1 | 1 | labelled `dual` already |

So the rule is sharper than "beats never mix": **beats mix only where the book already
showed a strand, an anthology, or a dual label.** `beat_tense` detects internal
structure rather than merely echoing the label.

Present-beat share by year (backfilled books, all 123):

| 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|---|---|
| 0% | 7% | 18% | 0% | 24% | 33% | 18% | 38% | 40% | 50% |

Directionally consistent with the trend, but **not independent evidence of it** — a
present-tense novel has present speech tags by construction. Use it as corroboration
and for the abstained books only.

## Backfill mechanics (kept for reference)

`beat_tense` was added to the spec on 2026-08-10 as a required field on every
`dialogue` quote. Books classified **before** that date lack it.

**Dan has confirmed the backfill will happen** — do not treat this as a permitted
methodological split, and do not analyse `beat_tense` as a partial sub-study.
Until the backfill is done, any tense figure must come from `event` quotes only,
exactly as before, so the corpus stays internally consistent.

**Scope:** 131 books, 1,093 dialogue quotes, 8.3 per book, 26% of all quotes.

**Approach:** a focused second pass reading only each book's `dialogue` quotes and
adding `beat_tense` — cheaper than re-classifying, since buckets and event tenses
are already settled. Measure one book before quoting a per-book cost.

**Why the field exists:** narration inside a speech quote (a tag, or an action beat)
is the narrator's own words and is tense evidence; bucketing it `dialogue` threw it
away. The loss is not random — it hits whichever strand happens to be dialogue-heavy.
*Project Hail Mary* read 96% present on event quotes and ~82% once beats counted;
*Wish You Were Here* lost the opposite way. A regex cannot do this job: it missed
narration outside the marks on 49% of mark-bearing dialogue quotes and false-positived
wherever quote marks were unbalanced.

### Backfill mechanics

Queue is `data/backfill/b001.txt`–`b126.txt`, one JSON filename each, sorted
largest-first. Prompt is `data/backfill/PROMPT.md`. Snapshot of the pre-backfill
state is `data/classified_pre_beat/`; `python3 verify_backfill.py` diffs the two and
fails on any change to `bucket`, `tense`, `note`, `narrating_situation` or the quote
set. Run it after every few books — it has reported 0 violations throughout.

Agents must NOT read `data/quotes_topn.csv` (3.2MB); the prompt carries a filtered
extraction command. Two agents stalled before that was added.

**Do not derive progress from a file's existence** — a book counts as backfilled only
when *every* `dialogue` quote carries `beat_tense`. Check that, not the mtime.

### There IS a gold standard, and quote-level agreement is only ~68-84%

`data/gold_b0361.json` is a 25-quote bucket/tense answer key (with blind quote text in
`data/quotes_gold_blind.csv`). It had never been scored. Scored 2026-08-11:

| | bucket | event-tense |
|---|---|---|
| `b0361.json` | 18/25 = 72% | 8/14 |
| `b0361_v2.json` | 21/25 = 84% | 11/14 |
| v1 vs v2 inter-rater | **17/25 = 68%** | — |

**Quote-level bucketing is much noisier than agent self-reports imply.** But three
things bound the damage, and they must be stated together:

1. **Book-level labels survived.** Both runs read `retrospective` and both yield PAST.
   v1 misfiled six event-past quotes as `gnomic`, dropping the event count 14 -> 8 —
   still over the 5 floor. Errors cost confidence, not the verdict. This is empirical
   support for making `narrating_situation` primary.
2. **Every miss was a bucket, never a tense.** No quote was called past-when-present or
   vice versa. Since gnomic quotes are dropped, the errors shrink the sample rather
   than skewing it.
3. **These files predate the current spec** (both dated 2026-08-04). Several misses are
   now impossible — v1 tagged past-tense quotes `gnomic`, but gnomic is now defined
   present-tense-only.

**Treat 68% as the honest floor on quote-level reliability until re-measured against
the current spec.** Do not claim quote-level precision in any writeup without redoing
this. Book-level claims rest on much firmer ground than quote-level ones. Re-scoring is
cheap — the key and the blind text are both already on disk.

### beat_tense has never contradicted narrating_situation

At 62 in-frame books (855 beat judgments by 62 independent agents): **perfect
separation, zero mixed-profile books.** 13 books carry present beats and contain no
past beat; 49 carry past beats and contain no present beat. All 13 present-beat books
are `simultaneous` except *Happy Place*, which is `dual`.

This validates making `narrating_situation` the primary signal — it is reading
something real, not pattern-matching. It does **not** independently confirm the rise:
a present-tense novel has present speech tags by construction, so beats and situation
measure the same fact. Treat it as a consistency check that passed.

**Where beats DO add new information: abstentions.** Books under the 5-event floor
contribute nothing to the trend chart. Of 9 abstained books backfilled, 8 yielded
beats: **6 past, 2 present** (both Rebecca Yarros — *Fourth Wing* 2023, *Onyx Storm*
2025). So abstention bias runs the direction previously guessed but is **weaker than
claimed**: ~25% of abstentions read present vs ~30% of labelled books in the same
period. Excluding abstentions does not meaningfully distort the trend. Do not repeat
the stronger earlier claim that the chart materially understates present tense.

### Three books yield zero beats, for two different reasons

*Identity* (Nora Roberts) 0/13 and `top2016:6678` 0/9 lost their quotation marks to
Goodreads — recoverable in principle from better text. *None of This Is True* (Lisa
Jewell) 0/8 is written as interview/podcast transcript, so there is no narrator to
have beats at all. Keep these causes separate when tallying coverage limits.

### The backfill queue contains 3 out-of-frame pilot books

`b0361.json`, `b0361_v2.json` (the same book stored twice) and `b0521.json` are
leftovers from the original random-sample design. They are **not** in
`data/books_topn.csv`, and `analyze_year.py` filters on the `top<year>` stratum
prefix, so they can never reach a label table. The true frame is **123 books, not
126**. Their quote text lives in `data/archive/quotes.csv`, not `quotes_topn.csv`.

### Quote-mark survival, not narrator style, drives the `none` rate

Measured 2026-08-11 over the first 20 backfilled books (446 dialogue quotes):

| dialogue quotes | past | present | none | n | none rate |
|---|---|---|---|---|---|
| quote marks survive | 154 | 29 | 26 | 209 | **12%** |
| marks stripped | 15 | 1 | 221 | 237 | **93%** |

**221 of 247 `none` calls are markless quotes.** Do not read a high `none` rate as
narrators withholding beats — it is a property of the Goodreads text. Where marks
survive, a beat is recoverable ~88% of the time.

Mark survival is per book and ranges 0–85%: *The Book of Longings* kept 0 of 16,
`top2016:1704` kept 17 of 20. It varies within an author too — *Onyx Storm* 15 of 19,
*Fourth Wing* 5 of 16 — which is why those two books yielded 14 present beats and 1.

**Open confound:** markless quotes are 53% of the dialogue corpus and yield almost
nothing, so beat evidence comes from roughly half the dialogue quotes. Check mark-survival
rate against year and against label before using beat counts in any aggregate claim; a
time trend in mark survival would bias the beat evidence exactly like a coverage bias.

### A slow API looks exactly like a stalled agent

On 2026-08-11 seven consecutive agents failed — three "connection closed
mid-response", four 600s watchdog stalls. It looked like a bad batch of books. It
was not: a single foreground probe on one of the "bad" books **succeeded, but took
38 minutes** against a 70–120s baseline. The API was running ~20x slow and the
watchdog was killing agents that were merely crawling.

Diagnose this before rewriting prompts or blaming particular books: run **one**
foreground agent and look at its duration. If it succeeds slowly, the queue is fine
and the right move is to wait, not to retry at concurrency — every watchdog-killed
agent burns budget and delivers nothing. All seven failures here died before
writing, so nothing was corrupted, but nothing was gained either.
