# booktense — narrative tense in fiction over time

**Question:** What tense (past / present / mixed) is fiction written in today, and how has the ratio changed over time?

Last updated: 2026-08-03

**Design (current):** NYT bestsellers as the frame, 1931–2026. Goodreads quotes as the text source. Classification per [METHODOLOGY.md](METHODOLOGY.md). HathiTrust dropped.

---

## 1. Prior art — nobody has answered this

- **Narratology** — Avanessian & Hennig, *Present Tense Narration in Contemporary Fiction* (Palgrave 2016). Argues the surge is real. No counts.
- **Corpus stylistics** — Ikeo, Shigematsu & Nakao (Benjamins 2024). Rigorous, but corpora are *selected by tense*, so structurally cannot yield a ratio.
- **Computational literary studies** — has the tools, no published diachronic tense series.
- **The public debate** — rests on **n = 6**: Hensher's 2010 complaint that 3 of 6 Booker shortlistees were present tense. Gass made the identical claim in the *NYTBR* in **1987**, so "it's surging" is a perennial assertion. That's the reason to get data.

## 2. Frame — settled

**NYT bestsellers, 1931–2026**, from two stitched sources that overlap:

| Source | Coverage | Contents |
|---|---|---|
| **Post45 Data Collective** (CC BY 4.0) | 1931–2020 | `lists.csv` 60,386 weekly appearances · `titles.csv` 7,431 unique titles |
| **NYT Books API** | ~2009–2026 | live lists; key in `.env` |

```bash
B=https://raw.githubusercontent.com/Post45-Data-Collective/data/main/nyt_hardcover_fiction_bestsellers
for f in lists titles hathitrust_metadata; do
  curl -sL -o "data/raw/$f.csv" "$B/nyt_hardcover_fiction_bestsellers-$f.csv"
done
```

NYT API floor is **~2009**, not 1931 as the docs imply (2008-06-08 → 404, 2009-03-01 → 200). Post45 covers everything earlier, so this doesn't bite.

## 3. HathiTrust — dropped

Access **works** (rsync module `features`, EF 2.5, 18.7M vols; path `{libid}/{clean[::3]}/{libid}.{clean}.json.bz2`; POS tags confirmed). Dropped anyway:

- **Bag-of-words can't see form.** EF destroys word order, so a VBD-vs-VBP/VBZ ratio cannot distinguish narration from dialogue, gnomic present from narrative present, or recognize diary form at all. It would file every diary novel as past — directional bias in the outcome variable. See METHODOLOGY.md.
- **Two methods, one seam.** Using POS ratios historically and read-text recently puts a method discontinuity inside the time series. One method across 1931–2026 is worth a lot.
- **HTRC shuts down 2026-09-30** — the dependency has an expiry date.

Post45's `hathitrust_metadata.csv` (4,977 htids) is retained in case this reverses; it would need re-pulling before the shutdown.

## 4. Text source — Goodreads, with a hard operational constraint

**Per-book access works.** Verified quote yields: *Plainsong* 18, *Henderson the Rain King* 30, *Cloud Cuckoo Land* 57, *Parable of the Sower* 58.

**Scraping at scale does not.** After a few dozen requests Goodreads returns **HTTP 202 with an empty body** — a bot challenge. The official API was **retired December 2020**; no new keys.

**Consequence: sample, don't census.** The study never needed all 7,431 titles. A stratified random sample — ~40 books/decade × 10 decades ≈ 400 books — estimates proportions with usable confidence intervals and fits inside a polite crawl rate. At ~4 requests/book and 20s spacing that's roughly 9 hours of unattended, well-behaved crawling. Do not build proxy rotation or evasion.

**Known bias, not yet quantified: coverage tracks fame, not date.** *American Family* (4 ratings) has 0 quotes; *Henderson* (16,339 ratings) has 30. Within any decade, quote availability correlates with popularity → literary status → plausibly with tense itself. This is the main threat to the design.

- **Record ratings count for every sampled book** and report label yield as a function of it.
- **Track abstentions as data.** If books that fail the quote threshold differ systematically from those that pass, the analysis sample is biased even when every individual label is correct.

## 4b. Sample design and pipeline — built

**Strata:** one per decade 1931–2015, then one per **year** 2016–2026. 40 books each.

| Source | Strata | Books |
|---|---|---|
| Post45 | 1931–2015 (9 decades) + 2016–2020 (5 years) | 560 |
| NYT API | 2021–2026 (6 years) | 240 |
| | **Total** | **~800** |

Post45 stops at 2020, so 2021–2026 must come from the API (`build_sample.py` samples ~monthly lists per year and dedupes to distinct titles).

**Code**

| File | Role |
|---|---|
| `booktense/goodreads.py` | Tiered resolution, disk-cached fetch, quote extraction |
| `build_sample.py` | Stratified sampler, seed `20260803` → `data/sample.csv` |
| `crawl.py` | Resumable crawler → `data/books.csv`, `data/quotes.csv` |
| `throttle_probe.py` | Measures the sustainable request rate |

**Resolution ladder** (each result carries method + confidence + notes):

1. **ISBN exact** — Goodreads *redirects* an exact-ISBN search to the book page, so this is **one request**. Viable ~1970+ only (ISBN fill: 11% in the 1930s, 79% by the 1980s).
2. **Title+author** — junk-filtered (`study guide|summary|box set|omnibus|…`), top 3 candidates, ranked by ratings count.
3. **Fail** → `confidence: review`, handled manually.

Validation rejects author-surname mismatch; flags year drift (reissues are common) and low ratings. A bad match is visible in the data rather than silent — this is the fix for the study-guide bug that produced a fabricated coverage finding.

**`data/quotes.csv` schema** — `quote_id, sample_id, gr_work_id, page, idx, source_url, quote_text, bucket, tense, note`. `bucket` and `tense` are written **blank**: the crawler produces auditable text with provenance, and classification is a reading judgment applied afterwards per METHODOLOGY.md. Classification can therefore be revised without re-crawling.

**Throughput — measured, not guessed** (`throttle_probe.py`, 2026-08-03):

| Observation | Value |
|---|---|
| Trip point, rested | ~9 requests |
| Trip point, budget partly spent | 4 requests (at *longer* 30s spacing) |
| Recovery after trip | **6 min** |
| Implied sustainable rate | **~90 requests/hour** |

The limit is a **token bucket on volume**, not an interval limit — spacing alone cannot avoid it, and budget carries across separate runs. Settings follow the measurement: `DELAY=40s` (paces at the refill rate, so it should rarely trip at all) and `cooldown=420s` on a trip.

At ~3 requests/book that's **~30 books/hour**, so ~800 books ≈ **27 hours** of chunked or unattended crawling. `--patient` sleeps through trips with linear backoff; without it the crawler stops cleanly and resumes from cache. **Do not build proxy rotation or evasion.**

**Parked optimization:** Wikidata carries Goodreads work IDs (P8383) and Post45 supplies author QIDs, so one bulk SPARQL query could pre-resolve much of the sample and remove most resolution requests. The query service was in an active outage on 2026-08-03 (hard limit 1 req/min). Retry before the full run.

## 5. Open threats

- **Fame/coverage bias** (§4) — the big one. Quantify before trusting any trend.
- **Genre mix as confound.** If literary vs. genre composition of the list shifts over time, aggregate tense moves without any author changing behavior. Stratify.
- **Dual-form novels.** Diary/epistolary books are structurally dual-tense; naive rules file them as past. If those forms grew, that suppresses the trend. Recorded as a separate label.
- **Weighting.** "What tense are books written in" (per title) ≠ "what tense do people read" (per copy). Bestseller lists are already sales-weighted; report both title-weighted and weeks-on-list-weighted.
- **Bestsellers ≠ fiction.** This measures the commercial mainstream. A random-publication study is a separate, harder project.

## 6. Verification discipline

Three measurement artifacts in one day, each of which would have produced a confident wrong answer:

1. **Hallucinated labels.** Books labeled from recall. *Plainsong* wrong. → Rule zero: never label without retrievable text + stored URL.
2. **Broken resolver.** Took the first Goodreads search hit; got a *study guide* for Bellow (9 ratings, 0 quotes) instead of the novel (16,339 ratings, 30 quotes). Produced a "coverage collapses with age" conclusion that was pure artifact. → Rank candidates by ratings count; filter study guides/box sets/omnibuses.
3. **Silent rate limiting.** HTTP 202 + empty body read as "book has no quotes." Consecutive failures at the tail of a run were the tell. → Assert on HTTP status and body length; never treat an empty response as a zero measurement.

Also: *Parable* was labeled wrong **twice**, and both wrong labels were *high confidence*. Agreement measures bucketing consistency, not correctness. No threshold catches a systematic bucketing error.

**Standing rule: before reporting any number as a finding, verify the measurement isn't an artifact.** Every negative result so far has been one.

## 7. Next steps

1. **Pilot, n≈30**, stratified across decades. Measure: resolution rate, quote yield, event-narration yield, abstention rate, all vs. ratings count. This tests §4's bias directly and is the gate on everything else.
2. **Build the crawler properly** — 20s spacing, HTTP status assertions, resume-on-restart, cached raw HTML so classification can be re-run without re-fetching.
3. **Gold set.** Independently obtained full text for ~50 books, labeled without reference to quotes, to estimate accuracy per class. Present-tense and dual-form classes need deliberate over-sampling — they are rare and where errors concentrate.
4. **Scale to ~400** only if the pilot's abstention rate is acceptable and not correlated with tense.
5. **Analyze**: proportion by decade, stratified by genre, title- and sales-weighted, abstentions reported.

---

## Sources

- [Post45 — NYT Hardcover Fiction Bestsellers](https://data.post45.org/posts/nyt_hardcover_fiction_bestsellers/) · [repo](https://github.com/Post45-Data-Collective/data)
- [NYT Books API](https://github.com/nytimes/public_api_specs/blob/master/books_api/books_api.md) · [Google Books API](https://developers.google.com/books/docs/v1/using) · [Open Library Search](https://openlibrary.org/dev/docs/api/search)
- [HTRC Extracted Features](https://htrc.atlassian.net/wiki/spaces/COM/pages/43290936/Extracted+Features+Dataset+v.1.5) (dropped; shuts down 2026-09-30)
- [Ikeo, Shigematsu & Nakao 2024](https://benjamins.com/catalog/lal.43) · [Avanessian & Hennig 2016](https://link.springer.com/book/10.1057/978-1-137-56213-5)
- [Miller, *Salon* 2010](https://www.salon.com/2010/09/22/present_tense/) · [Chee, *LitHub* 2015](https://lithub.com/in-defense-of-the-present-tense/)
