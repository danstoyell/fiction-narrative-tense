# Narrative-person pilot: 30 randomly selected books

Run date: 2026-08-25

## Summary

Three `gpt-5.6-terra` subagents at medium reasoning classified ten books each
under [`PERSON_METHODOLOGY.md`](../../PERSON_METHODOLOGY.md). The sample was a
simple random draw from all 793 rows in `dataset/books.csv`, generated with
`random.Random(20260825).sample(books, 30)`. No eligibility filter was applied
before sampling.

The agents used only `dataset/quotes.csv` and the existing `bucket`, `tense`,
and `beat_tense` fields. They were instructed not to read prior book notes,
classification JSON, external sources, or rely on recall. They did not change
any existing bucket or tense label.

All 30 books and all 290 routed event/dialogue-beat observations were returned.
Automated validation found no missing or duplicate books, no missing or extra
quote observations, no invalid labels or signals, and no violations of the
methodology's numeric evidence floors.

## Aggregate results

| Person result | Books | Percent of sample |
|---|---:|---:|
| `FIRST` | 7 | 23.3% |
| `THIRD` | 7 | 23.3% |
| `ALTERNATING` | 1 | 3.3% |
| `UNCLEAR` | 1 | 3.3% |
| `INSUFFICIENT` | 14 | 46.7% |

Fifteen books received a substantive person label. Nine were high confidence
and six medium confidence. Of the 20 sampled books that already had a usable
tense label, 15 (75%) received a substantive person label; the other five were
four `INSUFFICIENT` and one `UNCLEAR`. All ten books already lacking sufficient
tense evidence also lacked sufficient person evidence.

The 290 routed observations produced 88 `first_explicit`, 103 `third_pattern`,
94 `unmarked`, one `second_explicit`, one `unclear`, and three withheld signals
with `bucket_review=true`. These are evidence signals, not estimates of the
amount of text written in each person.

## Per-book results

| # | Year | Book | Result | Confidence | Routed | Audit note |
|---:|---:|---|---|---|---:|---|
| 1 | 1949 | *The Man with the Golden Arm* | `INSUFFICIENT` | — | 12 | Four third-pattern observations, one below the required floor. |
| 2 | 1997 | *The Matarese Countdown* | `INSUFFICIENT` | — | 0 | No usable event or beat narration. |
| 3 | 2020 | *Dear Edward* | `THIRD` | high | 20 | Fourteen coherent third-pattern observations. |
| 4 | 1981 | *Masquerade* | `INSUFFICIENT` | — | 0 | Sole quote is dialogue without a usable beat. |
| 5 | 2001 | *The Last Time They Met* | `FIRST` | med | 5 | Minimum floor; two explicit-first excerpts and one third-pattern excerpt. |
| 6 | 2007 | *A Thousand Splendid Suns* | `THIRD` | high | 11 | Ten coherent third-pattern observations. |
| 7 | 1950 | *The Cardinal* | `INSUFFICIENT` | — | 1 | One unmarked dialogue beat. |
| 8 | 1932 | *Invitation to the Waltz* | `FIRST` | med | 5 | Three first-explicit excerpts, including journal-like material, plus one third-pattern excerpt. |
| 9 | 1984 | *Lincoln* | `THIRD` | high | 21 | Eight third-pattern observations across several focal characters. |
| 10 | 1998 | *A Man in Full* | `THIRD` | high | 17 | Six third-pattern observations; one possible upstream bucket error withheld. |
| 11 | 2021 | *Golden Girl* | `UNCLEAR` | — | 13 | Eight third-pattern observations conflict with one unplaced first-explicit excerpt. |
| 12 | 2001 | *A Painted House* | `FIRST` | high | 21 | Fourteen first-explicit observations; third-person subjects did not form a separate strand. |
| 13 | 1954 | *The Royal Box* | `INSUFFICIENT` | — | 1 | One first-explicit observation. |
| 14 | 1944 | *A Bell for Adano* | `INSUFFICIENT` | — | 2 | Only two third-pattern observations. |
| 15 | 2002 | *From a Buick 8* | `FIRST` | med | 14 | Five first-explicit and three third-pattern observations; strand structure is thin. |
| 16 | 2021 | *The Wish* | `ALTERNATING` | med | 29 | Twelve first-explicit and eight third-pattern observations form recurring apparent strands. |
| 17 | 1992 | *Griffin & Sabine* | `INSUFFICIENT` | — | 1 | One first-explicit observation; other excerpts are dialogue without beats. |
| 18 | 2025 | *Say You'll Remember Me* | `FIRST` | high | 39 | Thirty-five first-explicit observations; one possible bucket error withheld. |
| 19 | 1972 | *The Word* | `INSUFFICIENT` | — | 1 | One unmarked observation. |
| 20 | 2009 | *The Associate* | `INSUFFICIENT` | — | 2 | One first-explicit and one unmarked observation. |
| 21 | 1996 | *The Runaway Jury* | `INSUFFICIENT` | — | 5 | Only two of five observations establish a third-person pattern. |
| 22 | 1978 | *Evergreen* | `INSUFFICIENT` | — | 0 | No usable event or beat narration. |
| 23 | 2025 | *Strangers in Time* | `INSUFFICIENT` | — | 7 | Only two third-pattern observations; clipping and one possible bucket error. |
| 24 | 2020 | *The Boy from the Woods* | `INSUFFICIENT` | — | 6 | Four third-pattern observations, one below the required floor. |
| 25 | 2023 | *I Will Find You* | `FIRST` | med | 7 | Four first signals plus isolated second- and third-person evidence. |
| 26 | 1954 | *Love Is Eternal* | `INSUFFICIENT` | — | 0 | No usable narrative excerpts. |
| 27 | 2008 | *Chasing Harry Winston* | `THIRD` | med | 5 | Meets the third-pattern floor exactly. |
| 28 | 1956 | *The Last Hurrah* | `THIRD` | high | 17 | Seven third-pattern observations with no competing narrator. |
| 29 | 2019 | *The Guardians* | `FIRST` | high | 15 | Nine first-explicit observations; one isolated third-pattern excerpt. |
| 30 | 2016 | *The Wrong Side of Goodbye* | `THIRD` | high | 13 | All thirteen observations support the third-person pattern. |

## Conclusions that deserve suspicion

### Highest-priority structural reviews

1. **`FIRST` for *Invitation to the Waltz* may be the wrong base label.** Three
   excerpts expose first person, but one explicitly presents itself as a
   written record, while another excerpt gives third-person interior access to
   Olivia. The earlier tense annotator independently described the sample as a
   mixture of journal-style first person and third-person narration. The quote
   page does not establish whether the journal material is the base voice or an
   embedded layer. `UNCLEAR` may be safer until a deeper page or independent
   opening resolves the frame.

2. **`FIRST` for *The Last Time They Met* is threshold-sensitive.** It rests on
   the minimum five observations and exactly two explicit-first excerpts. Both
   first-person passages are short, self-contained reflections; the sample also
   contains a third-person focal passage. The fixed upstream `event` labels
   permit the first-person inference, but the excerpts do not securely place
   those reflections in the book's base narrating layer.

3. **`FIRST` for *From a Buick 8* may compress a framed or multi-narrator
   arrangement.** Five first-explicit signals appear across event narration and
   dialogue beats, while three passages establish third-person focalization.
   The agent could not establish whether the different recounting contexts
   belong to one base narrator or several autonomous voices.

4. **`ALTERNATING` for *The Wish* is well supported grammatically but not yet
   structurally proven.** Twelve first-explicit and eight third-pattern excerpts
   recur across the sample. However, Goodreads removes section boundaries, so
   a long first-person account embedded in a third-person frame can look like
   two coequal autonomous strands. The label is plausible, but the distinction
   between alternating narration and an embedded account needs an opening or
   chapter-boundary check.

5. **`FIRST` for *I Will Find You* is a provisional base-person judgment.** The
   sample has four first-person signals but also isolated third- and
   second-person narration. The earlier tense annotation independently noticed
   two narrating positions and recommended fetching a deeper page. `FIRST` is
   reasonable as the exposed base, but it should not be used to claim that the
   book is uniformly first person.

6. **`UNCLEAR` for *Golden Girl* is the correct conservative outcome, but its
   evidence is conspicuously split.** Eight observations form a coherent
   third-person pattern and one is explicit first person. The first-person
   passage cannot be assigned to speech, memory, document, or an autonomous
   narrator from the excerpt alone.

7. **`THIRD` for *Chasing Harry Winston* is fragile.** All five routed excerpts
   support a third-person pattern, but five is exactly the evidence floor and
   the passages span multiple focal characters. A single contrary excerpt on a
   deeper page could change the structural interpretation.

### Stable labels with upstream review flags

- *A Man in Full* has one bare first-person event quote (`q00025`) that looks
  plausibly like stripped speech. It was withheld and sent back for bucket
  review. Six other third-pattern observations make the `THIRD` result stable.
- *Say You'll Remember Me* has one likely speech passage (`q10372`) currently
  bucketed as event. It was withheld. Thirty-five other first-explicit signals
  make the `FIRST` result stable.
- *Strangers in Time* has a similar possible upstream error in `q10496`, plus
  clipped excerpts. Its result is already `INSUFFICIENT`, so the uncertainty
  does not create a false substantive label.

### Threshold-sensitive abstentions

*The Man with the Golden Arm* and *The Boy from the Woods* each contain four
coherent third-pattern observations—one short of the provisional five-pattern
rule. *The Runaway Jury* has five total observations but only two diagnostic
third patterns. These abstentions follow the specification, but they show that
the rule may be conservative for third person. They should be included when
the threshold is validated or sensitivity-tested, not silently converted to
`THIRD`.

## Methodological conclusions

1. **The extension is viable for well-covered books, but raw random-sample
   coverage is low.** Half the sample received a substantive person label.
   Conditional on already having enough evidence for tense, the yield was 75%.
   Deeper Goodreads pages would likely improve person coverage just as they
   improve tense coverage.

2. **The evidentiary burden is asymmetric.** First person can be exposed by a
   small number of narratorial self-references. Third person is usually an
   inference from a recurring focalization pattern and the absence of a visible
   participating narrator. Four likely-third books abstained despite having at
   least five routed observations. Analyses that drop abstentions may therefore
   overrepresent overt first-person narration. This is an inference from the
   pilot and needs validation on a larger sample.

3. **The user's “Maria” concern is empirically important.** Ninety-four routed
   observations were marked `unmarked`: they narrated named or third-person
   subjects without identifying the narrator. Treating those automatically as
   third person would have produced materially more—and less defensible—third
   labels.

4. **Embedded and framed narration is the main structural failure mode.** The
   most questionable substantive outcomes are not caused by recognizing `I`,
   `she`, or verb tense. They arise when Goodreads excerpts omit the section
   boundaries needed to decide whether a voice is base, autonomous, or
   embedded.

5. **This is a single-pass reproducibility pilot, not accuracy validation.**
   Each book was classified by one agent. The prior tense notes were hidden
   during classification and consulted only afterward for suspicious-case
   auditing; they are not an independent gold standard. A blind second pass and
   external opening/preview comparison remain necessary before using these
   labels for trend claims.

## Artifacts

- `selection.csv`: sampled books and batch assignments.
- `batch_1.json`, `batch_2.json`, `batch_3.json`: full book judgments and
  quote-level person signals.
- `results.csv`: consolidated book-level results and signal counts.
