# Person-label run report: 1996–2025

Run completed 2026-08-28 using `gpt-5.6-sol` at high reasoning effort with
mandatory live web search.

## Panel and outputs

- The primary run selected the first five books in consolidated source order
  for every year from 1996 through 2025: 150 reviewed items.
- `CALL US WHAT WE CARRY` (2021) was `EXCLUDED` because it is a poetry
  collection rather than eligible prose narrative.
- The next 2021 book in source order, `CLOUD CUCKOO LAND`, was classified as
  `THIRD`/high so that every year has exactly five substantive person labels.
- Final exports contain 151 reviewed items, 150 substantive labels, and 5,288
  quote annotations.

Outputs:

- `dataset/person_books.csv`
- `dataset/person_quotes.csv`
- `raw_data/person_classified/*.json`

## Book-level results

Among the 150 eligible books:

| Label | Books | Share |
|---|---:|---:|
| `THIRD` | 84 | 56.0% |
| `FIRST` | 40 | 26.7% |
| `ALTERNATING` | 26 | 17.3% |
| `SECOND` | 0 | 0.0% |

Confidence among eligible books was 133 high (88.7%) and 17 medium (11.3%).
There were no `UNCLEAR`, `INSUFFICIENT`, or `CONFLICT` outputs. The separate
poetry exclusion has blank confidence.

## Quote-level results

| Signal | Quotes | Share |
|---|---:|---:|
| `non_base` | 2,652 | 50.2% |
| `first` | 879 | 16.6% |
| `unmarked` | 806 | 15.2% |
| `third` | 775 | 14.7% |
| `unclear` | 171 | 3.2% |
| `second` | 5 | 0.1% |

All five diagnostic second-person quotes came from `AN ANONYMOUS GIRL`, which
was labeled `ALTERNATING` because Jessica's first-person chapters alternate
with Dr. Shields's second-person chapters.

## Conclusions that need caution

1. **The panel is deterministic, not random.** The first five source-order
   records are useful for reproducibility but should not be treated as a
   representative annual sample or used to estimate population prevalence.
2. **`ALTERNATING` is common partly because of panel composition.** Twelve of
   the 26 alternating books are by James Patterson alone or with a coauthor.
   The label also captures structurally sustained exceptions such as a prologue
   or one full chapter (`BIG SUMMER`, `AFTER YOU`). This is consistent with the
   methodology, but it may not match a downstream desire for the dominant or
   modal person of the book.
3. **Eligibility needs a collection rule.** The poetry collection `CALL US WHAT
   WE CARRY` was excluded, while the prose story collection `FORD COUNTY` was
   retained as `ALTERNATING`. Decide explicitly whether prose collections are
   in scope before trend analysis.
4. **High confidence is probably overproduced.** Half of quote rows were
   `non_base`, yet 88.7% of eligible books received high confidence. Some agents
   treated third-party excerpt hosts as Tier A and personal/commercial guides
   as Tier B. The clearest example is `HONEYMOON`, whose high `ALTERNATING`
   decision relies on several personal-review sites classified as Tier B.
   These labels may still be correct, but source tiers and confidence should be
   independently audited.
5. **Zero eligible abstentions reflects this web-rich bestseller panel, not a
   demonstrated general capability.** Mandatory web research resolved every
   eligible book here. That result should not be generalized to obscure books
   or books without searchable excerpts.

## Operational finding

Four concurrent workers did not improve the fixed usage allowance. At one
quota boundary, three interrupted calls consumed 164.8k tokens without usable
output. Switching to one worker reduced the next boundary loss to one 63.9k
call. The harness now dispatches bounded waves, pauses on usage limits without
charging an attempt, passes validator errors into retries, and imposes a
15-minute per-job timeout. One worker is the recommended setting when usage,
not elapsed time, is the bottleneck.
