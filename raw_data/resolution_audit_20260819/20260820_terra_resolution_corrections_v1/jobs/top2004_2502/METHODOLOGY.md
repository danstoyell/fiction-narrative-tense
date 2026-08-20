# Tense classification from Goodreads quotes

Method for assigning a narrative-tense label to a book using publicly published quote pages. Every label is backed by retrievable text and a stored source URL, so any label can be re-checked.

**Rule zero: never label from recall.** A label with no quoted passage behind it is not data. This was violated twice in development and produced two wrong labels (*Plainsong*, *Parable of the Sower*), both overturned by evidence.

---

## Procedure

**1. Resolve and verify the title before fetching.** An ISBN is a lookup hint, not proof: source
metadata can attach another book's ISBN, especially another title by the same author. Compare
the requested NYT title with both the Goodreads book-page title and the title printed on
`https://www.goodreads.com/work/quotes/{work_id}`. Accept punctuation, leading-article,
subtitle, and documented translation-title variants; reject a different title, a sequel,
prologue, omnibus, collection, or partial volume. Duplicate Goodreads work IDs assigned to
different requested titles require review. Never attach old classifications to newly resolved
quote text.

Then fetch `https://www.goodreads.com/work/quotes/{work_id}` (`?page=N` for more). Requests
need a browser User-Agent and retries and fail intermittently. Expect about 30 quotes/page.

**2. Deduplicate.** Goodreads lists overlapping excerpts of the same passage as separate entries. Normalize (lowercase, strip punctuation, first 90 chars) and drop substring-containment matches. Counting duplicates inflates apparent agreement.

**3. Bucket each quote into five categories — not two.**

| Bucket | Test | Diagnostic? |
|---|---|---|
| **Dialogue** | Character speech. Majority of words inside quotation marks. | **Yes, when a narratorial beat is present** |
| **Gnomic** | **Present-tense** narration that generalizes **beyond the story world**: proverbs, epigraphs, essayistic reflection, second-person universals. Appears in books of any narrative tense. | **No** |
| **Event-narration** | Reports a specific event or state **of a specific character at a specific story-moment**, *or* past-tense exposition and summary about the story world. | **Yes** |
| **Paratext** | Acknowledgments, author's notes, dedications, epigraph attributions, jacket copy. Not the novel. | **No — discard** |
| **Unclear** | The excerpt is too clipped or ambiguous to classify responsibly. | **No** |

The gnomic bucket is the critical one. "But books, like people, die" is narration, not dialogue, so a two-bucket filter passes it through and labels the book present. It's the tense of proverbs and appears in past-tense novels constantly. Goodreads quotes are *selected for quotability*, and quotability correlates with aphorism — so this source is adversarially biased toward apparent present tense.

**The test is specificity, not tense.** "My father is dead," "I ache from my wounds," "People are setting fires" are present tense but concern a *specific* character at a *specific* moment — event-narration, not gnomic. Applying a looser "sounds general" test misfiled these in development and flipped *Parable of the Sower*'s label from dual to past.

**Gnomic is a present-tense phenomenon.** The bucket exists to stop timeless present from being read as present narration. Past-tense generalization about the story world is *not* gnomic — "Molenbeek was known as the jihadi capital of Europe" and "security was one of the few growth industries in France" are event-narration/past. Iterative and summary narration ("Such was life in the caliphate, bombs falling upon severed heads") is likewise event-narration: it summarizes the story world rather than generalizing beyond it. A blind agent run applying the specificity test to past-tense prose scored 54% gnomic precision, all errors in this direction — the mirror image of the *Parable* error.

The one past-tense case that stays gnomic is **argument by analogy with no story-world referent** — a narrator reasoning about Switzerland and France to make a rhetorical point, where nothing happens and no character appears. This is genuinely contested; flag it in `note` rather than deciding silently.

**Precedence when rules collide.** Quotation-mark majority wins over the dialogue-tag rule: a long speech carrying one "he shook his head" beat is `dialogue`, not event-narration. Apply the dialogue test first, the tag rule only to quotes that fail it.

**Near 50%, prefer `event`.** The split decides whether a quote yields a tense-bearing
`event` or only a `beat_tense`, so it is load-bearing. One observed quote came out 52/48
speech. When the margin is within ~10 points, treat the quote as `event` — narration that
substantial is evidence, and the tie-break should not silently discard it. Goodreads also
clips quotes mid-pair, leaving a closing mark with no opener; a lone unmatched mark is not
a quoted span for counting purposes.

A dialogue tag counts as event-narration **only in quotes that fail the dialogue test**: `He hesitated. "You don't deserve it," he said aloud, and turned back to the window.` → past — the narration outweighs the speech. A quote that is mostly speech stays `dialogue` however its tag is tensed; `"Some stories," she says` is 4 spoken words to 2 narrating ones and is therefore **`dialogue`, not event/present**. An earlier version of this file used that string as an event/present example, contradicting the precedence rule directly above it; an agent caught the contradiction mid-run.

**4. Classify tense of each event-narration quote:** past / present.

**4b. Record `beat_tense` on every dialogue quote.** A quote bucketed `dialogue` still
usually contains narration *the narrator speaks* -- a tag or an action beat. That narration
is diagnostic and was previously discarded along with the speech.

This matters because the loss is not random: it hits whichever strand happens to be
dialogue-heavy. *Project Hail Mary*'s past Earth strand is conversational, so the book read
96% present on event quotes and ~82% once beats were counted. *Wish You Were Here* lost the
opposite way -- all nine of its dialogue quotes carried present tags, none counted.

Beats must be judged by a reader, not extracted by pattern. The tag-verb class in fiction is
open (`opined`, `drawled`, `ventured`), many beats are not speech verbs at all, and a tag can
sit *inside* a character's speech, where it is that character narrating and must not count.
A ten-verb regex over the corpus missed narration outside the quotation marks on **49%** of
mark-bearing dialogue quotes, and produced false positives wherever marks were unbalanced.

**How `beat_tense` is consumed.** Event tense and dialogue-beat tense are pooled into one
tense-bearing tally. This is the production standard. A backfill supplied `beat_tense` for
books classified before the field was introduced; subsequent Terra classifications recorded
it directly under the same rule. Event and beat counts remain separate in the stored data so
the effect of pooling can be audited without reclassification.

Pooling matters because dialogue-heavy strands otherwise disappear. *Project Hail Mary*'s
past Earth strand is conversational, so the book read 96% present on event quotes and about
82% once beats were counted. *Wish You Were Here* loses evidence in the opposite direction if
its present-tense dialogue beats are discarded.

**5. Derive the book label from the pooled tally and narrating situation.**

The target is the tense of the book's **base narration**, not the majority tense among sampled
quotes. Goodreads quotation frequency is not a representative measure of page share, and an
embedded tale or unusually quotable strand can dominate it. The independently recorded
`narrating_situation` therefore supplies the structural label; the pooled tally gates thin
evidence, resolves strongly one-sided dual readings, and sets confidence.

| Decision | Production rule |
|---|---|
| **Verse / not prose fiction** | `EXCLUDED-verse`, before the evidence gate |
| **Evidence gate** | Fewer than 5 pooled event + dialogue-beat tense observations → `INSUFFICIENT` |
| **Retrospective situation** | `PAST` |
| **Simultaneous situation** | `PRESENT` |
| **Dual situation** | `PRESENT` at ≥80% present; `PAST` at ≥80% past; otherwise `DUAL` |
| **Unclear situation** | `UNCLEAR` |

The old 80%-past and 85%-present event-only bars are development history, not production
label gates. In the current method, the only dominance bar that changes a base label is the
80% rule for a structurally `dual` book: a split that one-sided is treated as a base tense
with a minority strand rather than co-equal dual narration.

**Confidence uses separate corroboration bars.** For a `PAST` label, a pooled tally with at
least 65% past corroborates the structural read; for `PRESENT`, at least 65% present does so;
`DUAL` corroborates itself. Corroborated labels are `high` confidence with at least 8 pooled
observations and `med` confidence with 5–7. A structurally past or present label whose pooled
tally falls on the other side of those bars is retained but marked `CONFLICT` for review.
`CONFLICT` is a review flag, not an automatic abstention.

**Abstaining is a valid outcome.** Yield varies enormously (*Plainsong*: 8 usable of 18; *Parable*: 7 of 58). Forcing a label on thin evidence is the main way this method fails.

**6. Record per label:** source URL, page count fetched, every quote with its bucket, event
tense or dialogue-beat tense, narrating situation, pooled and separate counts, final label,
and confidence. Bars can then be audited or re-tuned without re-fetching.

---

## Diary, epistolary, and other dual-position forms

A diary or letter novel has **two built-in time positions**: what happened since the last entry (past) and how things stand at the moment of writing (present). "Today I walked to the river" and "my father is dead" sit in the same entry, both are event-narration, and neither is a flaw or a mixture. The form is structurally dual.

"What tense is this book in?" is therefore **malformed** for these novels, and they get their own label rather than being forced into past or present.

**Why this matters beyond bookkeeping.** Naive rules file diary novels as *past*, because event-recounting and dialogue tags dominate the countable verbs — this is what a raw VBD-vs-VBP/VBZ ratio over HathiTrust EF would do, having no way to see the form. If diary, epistolary, blog, or messaging-style forms became more common over the study period, filing them all as past would suppress the exact trend being measured. That is bias in the outcome variable, not noise, and it runs in a known direction.

**Requirement:** record narrating situation (retrospective / simultaneous / dual) as a field independent of tense, so dual-form books can be included or excluded at analysis time instead of being silently absorbed into one class.

## Pipeline

| Step | Tool | Output |
|---|---|---|
| Build annual NYT candidate batches | `analysis/build_sample.py`, `analysis/build_topn.py` | `raw_data/sample*.csv` |
| Resolve + fetch quotes | `crawl.py`, `crawl_step.py` | `raw_data/books_*.csv`, `raw_data/quotes_*.csv` |
| **Classify quotes and narrating situation** | classifier agent or Terra harness | `raw_data/classified*/*.json` |
| Derive labels and report | `analysis/analyze_year.py`, `analysis/build_report.py` | label tables and `trend.html` |

`crawl.py` writes classification fields blank on purpose. Bucketing is the step where every
error in this project has originated, and it is a reading judgment — no regex substitutes
for it. Because quote text and `source_url` are persisted, classification can be revised
without re-crawling. The classifier records `narrating_situation` independently so a split can
be interpreted structurally rather than reduced to a raw quote majority.

## Known limitations

- **One-sided evidence.** Strong for confirming past; weak for confirming present, since present-tense narration is hard to distinguish from gnomic present. The rare class is the one this source serves worst.
- **Non-random sampling.** Quotes are popularity-ranked and interior but not representative. Page 1 is the most aphoristic; deeper pages yield more ordinary narration, so fetching more *improves* sample quality.
- **Not a substitute for whole-book measurement.** Establishes tense of sampled passages, not a proportion over the text.
- Pair with an independent source (e.g. NYT First Chapter archive, `nytimes.com/books/first/{letter}/{slug}.html`) and check agreement where both exist. Openings and interiors failing to agree is itself a signal of a framed or mixed-tense novel.

---

## Early bucket validation (2026-08-03; historical)

| Book | Event-narration | Split | Label | Notes |
|---|---|---|---|---|
| *Plainsong* (Haruf, 1999) | 8 of 18 | 8 past / 0 present | HIGH CONF PAST | Overturned an incorrect recalled label |
| *Parable of the Sower* (Butler, 1993) | 20 of 58 | 8 past / 12 present | **DUAL — diary** | See below |
| *Cloud Cuckoo Land* (Doerr, 2021) | 9 of 57 | 1 past / 8 present | HIGH CONF PRESENT | Lone past quote is the embedded Aethon strand — structural, not noise |

n=3. This exercise helped establish the specificity and diary-form distinctions. It predates
the pooled-beat, narrating-situation-first production label rule and does **not** validate the
current end-to-end method or establish accuracy.

**Development history of *Parable*, worth preserving as a warning.** It was labeled three times: first "present" from recall (wrong — no evidence); then "HIGH CONF PAST, 7/7" after a first pass at bucketing (wrong — the loose gnomic test swept the diary's deictic present in with the Earthseed aphorisms, leaving only recounting verbs); finally "dual" at 8 past / 12 present once gnomic was redefined as *generalizes beyond the story world*.

Both errors produced **confident** labels. Neither was caught by low agreement — the 7/7 reading looked like the cleanest result in the set. Agreement measures consistency of bucketing, not correctness of it, so a systematic bucketing error yields high agreement on a wrong answer. This is the method's central failure mode and no bar detects it; only checking bucket assignments against the text does.

## Blind reproducibility check (2026-08-11)

Across 30 blindly reclassified books, Terra and the earlier Sonnet pass agreed on 83.9% of
quote buckets, 99.1% of event tense where both selected `event`, 98.2% of dialogue-beat tense
where both selected `dialogue`, and 86.7% of narrating situations and derived book labels.
This measures reproducibility between two model passes, not accuracy against an external gold
standard. Full artifacts live in `archive/eval/evals/terra_sonnet_blind_20260811/`.
