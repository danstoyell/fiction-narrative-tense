# Tense classification from Goodreads quotes

Method for assigning a narrative-tense label to a book using publicly published quote pages. Every label is backed by retrievable text and a stored source URL, so any label can be re-checked.

**Rule zero: never label from recall.** A label with no quoted passage behind it is not data. This was violated twice in development and produced two wrong labels (*Plainsong*, *Parable of the Sower*), both overturned by evidence.

---

## Procedure

**1. Fetch.** `https://www.goodreads.com/work/quotes/{work_id}` (`?page=N` for more). Needs a browser User-Agent and retries; requests fail intermittently. ~30 quotes/page.

**2. Deduplicate.** Goodreads lists overlapping excerpts of the same passage as separate entries. Normalize (lowercase, strip punctuation, first 90 chars) and drop substring-containment matches. Counting duplicates inflates apparent agreement.

**3. Bucket each quote into three categories — not two.**

| Bucket | Test | Diagnostic? |
|---|---|---|
| **Dialogue** | Character speech. Majority of words inside quotation marks. | No |
| **Gnomic** | **Present-tense** narration that generalizes **beyond the story world**: proverbs, epigraphs, essayistic reflection, second-person universals. Appears in books of any narrative tense. | **No** |
| **Event-narration** | Reports a specific event or state **of a specific character at a specific story-moment**, *or* past-tense exposition and summary about the story world. | **Yes — only these count** |
| **Paratext** | Acknowledgments, author's notes, dedications, epigraph attributions, jacket copy. Not the novel. | **No — discard** |

The gnomic bucket is the critical one. "But books, like people, die" is narration, not dialogue, so a two-bucket filter passes it through and labels the book present. It's the tense of proverbs and appears in past-tense novels constantly. Goodreads quotes are *selected for quotability*, and quotability correlates with aphorism — so this source is adversarially biased toward apparent present tense.

**The test is specificity, not tense.** "My father is dead," "I ache from my wounds," "People are setting fires" are present tense but concern a *specific* character at a *specific* moment — event-narration, not gnomic. Applying a looser "sounds general" test misfiled these in development and flipped *Parable of the Sower*'s label from dual to past.

**Gnomic is a present-tense phenomenon.** The bucket exists to stop timeless present from being read as present narration. Past-tense generalization about the story world is *not* gnomic — "Molenbeek was known as the jihadi capital of Europe" and "security was one of the few growth industries in France" are event-narration/past. Iterative and summary narration ("Such was life in the caliphate, bombs falling upon severed heads") is likewise event-narration: it summarizes the story world rather than generalizing beyond it. A blind agent run applying the specificity test to past-tense prose scored 54% gnomic precision, all errors in this direction — the mirror image of the *Parable* error.

The one past-tense case that stays gnomic is **argument by analogy with no story-world referent** — a narrator reasoning about Switzerland and France to make a rhetorical point, where nothing happens and no character appears. This is genuinely contested; flag it in `note` rather than deciding silently.

**Precedence when rules collide.** Quotation-mark majority wins over the dialogue-tag rule: a long speech carrying one "he shook his head" beat is `dialogue`, not event-narration. Apply the dialogue test first, the tag rule only to quotes that fail it.

A dialogue tag counts as event-narration **only in quotes that fail the dialogue test**: `He hesitated. "You don't deserve it," he said aloud, and turned back to the window.` → past — the narration outweighs the speech. A quote that is mostly speech stays `dialogue` however its tag is tensed; `"Some stories," she says` is 4 spoken words to 2 narrating ones and is therefore **`dialogue`, not event/present**. An earlier version of this file used that string as an event/present example, contradicting the precedence rule directly above it; an agent caught the contradiction mid-run.

**4. Classify tense of each event-narration quote:** past / present.

**5. Apply thresholds — asymmetric by design.**

| Outcome | Requirement |
|---|---|
| **High confidence PAST** | ≥5 event-narration quotes, ≥80% past |
| **High confidence PRESENT** | **≥8** event-narration quotes, **≥85%** present |
| **Dual — diary/epistolary (finding)** | ≥8 quotes, both tenses ≥25%, and the split maps to **recounting vs. writing-moment** |
| **Mixed — strand (finding)** | ≥8 quotes, both tenses ≥25%, and the minority traces to an identifiable **strand, frame, or embedded text** |
| **Present + recollection strand** | ≥8 quotes, 70–85% present, and the past minority traces to **memory/backstory** → counts as PRESENT, strand recorded |
| **Low confidence (flag)** | ≥10 quotes, both tenses ≥25%, no structural explanation for the split |
| **Insufficient** | <5 event-narration quotes → fetch next page, repeat (cap 4 pages, then abstain) |

When a book splits, do not stop at "mixed" — identify *why*. The three causes are structurally different and only one of them is uncertainty.

Present requires a higher bar because the source's bias runs toward false-present. Past-tense evidence is near-unfakeable — no aphorism produces "she went into the air outside the clinic."

**But the asymmetry cuts the other way too, and the first version of this table got it wrong.** Present-tense novels routinely carry a **past recollection strand** — memory, backstory, a dead parent — while past-tense novels contain almost no present event-narration once gnomic is excluded. So quote-purity is not symmetric evidence: 100% past is common and unremarkable, whereas 100% present is rare and 80–85% present is what a clean present-tense novel actually looks like.

*Writers & Lovers* exposed this: 45 event quotes, 84.4% present, past minority entirely memory — and it fell through **every** row of the table, producing no label at all, while a 100%-past book passed on the first row. That is a directional defect, not a conservative one: it abstains selectively on present-tense books and would undercount exactly the trend this study exists to measure. Hence the `Present + recollection strand` row.

The ≥85% bar is now doubly suspect, since the gnomic contamination that justified it is handled at the bucketing step (gnomic is present-tense-only; paratext is discarded). Do not re-tune it on n=2 — but flag every book landing in 80–85% present for audit until there is enough data to set it properly.

**Abstaining is a valid outcome.** Yield varies enormously (*Plainsong*: 8 usable of 18; *Parable*: 7 of 58). Forcing a label on thin evidence is the main way this method fails.

**6. Record per label:** source URL, page count fetched, every quote with its bucket and tense, final counts. Thresholds can then be re-tuned without re-fetching.

---

## Diary, epistolary, and other dual-position forms

A diary or letter novel has **two built-in time positions**: what happened since the last entry (past) and how things stand at the moment of writing (present). "Today I walked to the river" and "my father is dead" sit in the same entry, both are event-narration, and neither is a flaw or a mixture. The form is structurally dual.

"What tense is this book in?" is therefore **malformed** for these novels, and they get their own label rather than being forced into past or present.

**Why this matters beyond bookkeeping.** Naive rules file diary novels as *past*, because event-recounting and dialogue tags dominate the countable verbs — this is what a raw VBD-vs-VBP/VBZ ratio over HathiTrust EF would do, having no way to see the form. If diary, epistolary, blog, or messaging-style forms became more common over the study period, filing them all as past would suppress the exact trend being measured. That is bias in the outcome variable, not noise, and it runs in a known direction.

**Requirement:** record narrating situation (retrospective / simultaneous / dual) as a field independent of tense, so dual-form books can be included or excluded at analysis time instead of being silently absorbed into one class.

## Pipeline

| Step | Tool | Output |
|---|---|---|
| Build stratified sample | `build_sample.py` | `data/sample.csv` |
| Resolve + fetch quotes | `crawl.py` | `data/books.csv`, `data/quotes.csv` |
| **Classify (steps 3–4 above)** | **reading, by hand** | fills `bucket`, `tense` in `data/quotes.csv` |
| Apply thresholds | `label.py` | `data/labels.csv` |

`crawl.py` writes `bucket` and `tense` **blank** on purpose. Bucketing is the step where every error in this project has originated, and it is a reading judgment — no regex substitutes for it. Because quote text and `source_url` are persisted, classification can be revised without re-crawling.

`label.py` never silently resolves a split. It emits `SPLIT_REVIEW` and requires a human to record which of the three causes applies.

## Known limitations

- **One-sided evidence.** Strong for confirming past; weak for confirming present, since present-tense narration is hard to distinguish from gnomic present. The rare class is the one this source serves worst.
- **Non-random sampling.** Quotes are popularity-ranked and interior but not representative. Page 1 is the most aphoristic; deeper pages yield more ordinary narration, so fetching more *improves* sample quality.
- **Not a substitute for whole-book measurement.** Establishes tense of sampled passages, not a proportion over the text.
- Pair with an independent source (e.g. NYT First Chapter archive, `nytimes.com/books/first/{letter}/{slug}.html`) and check agreement where both exist. Openings and interiors failing to agree is itself a signal of a framed or mixed-tense novel.

---

## Validation (2026-08-03)

| Book | Event-narration | Split | Label | Notes |
|---|---|---|---|---|
| *Plainsong* (Haruf, 1999) | 8 of 18 | 8 past / 0 present | HIGH CONF PAST | Overturned an incorrect recalled label |
| *Parable of the Sower* (Butler, 1993) | 20 of 58 | 8 past / 12 present | **DUAL — diary** | See below |
| *Cloud Cuckoo Land* (Doerr, 2021) | 9 of 57 | 1 past / 8 present | HIGH CONF PRESENT | Lone past quote is the embedded Aethon strand — structural, not noise |

n=3. Establishes the buckets and thresholds are workable; does **not** establish accuracy. A real accuracy estimate needs a gold set labeled against independently obtained text.

**Development history of *Parable*, worth preserving as a warning.** It was labeled three times: first "present" from recall (wrong — no evidence); then "HIGH CONF PAST, 7/7" after a first pass at bucketing (wrong — the loose gnomic test swept the diary's deictic present in with the Earthseed aphorisms, leaving only recounting verbs); finally "dual" at 8 past / 12 present once gnomic was redefined as *generalizes beyond the story world*.

Both errors produced **confident** labels. Neither was caught by low agreement — the 7/7 reading looked like the cleanest result in the set. Agreement measures consistency of bucketing, not correctness of it, so a systematic bucketing error yields high agreement on a wrong answer. This is the method's central failure mode and no threshold detects it; only checking bucket assignments against the text does.
