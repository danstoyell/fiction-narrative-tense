# Recall-based priors, 2021 stratum — LOCKED BEFORE SEEING ANY AGENT OUTPUT

Written 2026-08-08, before reading any file in `data/classified/` for these books.

**These are guesses from memory, not measurements.** Recall is the very first way this
project produced a wrong answer (*Plainsong*, labelled present from memory, was wrong).
They exist only as an independent signal: where a prior and a text-derived label
disagree, that book is worth auditing. A disagreement does NOT mean the agent is wrong —
the prior is the less trustworthy of the two.

`conf` = how much I'd stake on the prior: H = confident, M = moderate, L = little/none.

| # | Book | Prior | conf | Reasoning |
|---|---|---|---|---|
| 1 | Apples Never Fall | past | M | Moriarty writes retrospective domestic thriller w/ dual timeline |
| 2 | Project Hail Mary | past | H | First-person retrospective + amnesia flashback structure |
| 3 | Harlem Shuffle | past | H | Literary historical, third-person past |
| 4 | Cloud Cuckoo Land | **mixed** | M | Multi-strand; I believe some strands are present tense |
| 5 | Malibu Rising | **present** | M | I recall a present-tense frame across one day, w/ past backstory |
| 6 | Beautiful World, Where Are You | **present** | H | Rooney's third-person sections are present tense; letters interleaved |
| 7 | Wish You Were Here | **present** | M | Picoult pandemic novel, I think present first-person |
| 8 | Klara and the Sun | past | H | Klara narrates retrospectively |
| 9 | The Lincoln Highway | **mixed** | L | Towles rotates POV; uncertain on tense |
| 10 | The Maidens | past | M | Commercial thriller convention |
| 11 | The Last Thing He Told Me | **present** | M | I recall present-tense first person |
| 12 | The Wish | past | M | Sparks, dual timeline, likely past |
| 13 | The Paper Palace | **mixed** | M | Present-day single day + past strand |
| 14 | Billy Summers | past | H | King writes past third-person |
| 15 | Call Us What We Carry | **n/a** | H | **POETRY — should not be in a fiction study** |
| 16 | A Court of Silver Flames | past | M | Maas writes past third-person |
| 17 | The Four Winds | past | H | Hannah historical, past third |
| 18 | Go Tell the Bees That I Am Gone | past | M | Gabaldon, first-person past |
| 19 | The Lost Apothecary | **mixed** | M | Dual timeline; present-day strand may be present tense |
| 20 | The Judge's List | past | H | Grisham, past third |
| 21 | The Stranger in the Lifeboat | past | L | Albom uses framing devices; unsure |
| 22 | The Cellist | past | H | Silva, past third (matches hand-labelled *Black Widow*) |
| 23 | Golden Girl | **mixed** | L | I recall a dead narrator watching from above — may be present |
| 24 | State of Terror | past | M | Political thriller convention |
| 25 | Win | **present** | L | Coben's Win novels may be present first-person |
| 26 | The Hill We Climb | **n/a** | H | **POETRY — single inaugural poem, not fiction** |

## Predictions to check against results

1. **Roughly 6–8 of 24 (25–33%) present or mixed.** If the run returns near 0% or above
   60%, suspect the method before believing the number.
2. **Items 15 and 26 are poetry, not fiction.** Amanda Gorman appears twice. The NYT
   hardcover *fiction* list should not contain these; if it does, the frame has a
   genre-contamination problem that also affects other years. Flag regardless of label.
3. **#22 The Cellist** is a Silva novel, same series as the hand-labelled *Black Widow*
   (100% past, 11/11). If it comes back anything but clean past, suspect the classifier.
4. Books where I said **mixed** (4, 9, 13, 19, 23) are where the dual/strand rules get
   exercised — the least reliable part of METHODOLOGY.
