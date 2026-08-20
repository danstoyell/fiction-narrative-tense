# Goodreads resolution corrections

## Conclusion

**Complete.** All 15 title mismatches from the 960-candidate audit were replaced with
book- and work-title-verified Goodreads mappings. Thirteen corrected works yielded quotes
and received fresh blind Terra-medium classifications. *White Banners* and *Lady
Chatterley's Lover* resolved correctly but had no Goodreads quotes, so they remain
unlabelable rather than retaining evidence from the wrong work.

The post-integration audit reports 938 ordinary passes, 8 documented title-alias passes,
0 title mismatches, 0 unavailable work pages, and 0 duplicate work-ID assignments. Fourteen
unmapped candidates remain explicitly unresolved.

## Label effects

| Book | Previous result | Corrected result | Corrected quotes |
|---|---:|---:|---:|
| Franny and Zooey | insufficient | Past | 91 |
| War and Remembrance | Past | Past | 24 |
| The Rainmaker | Past | Present | 25 |
| White Banners | unlabelled | no quotes | 0 |
| Of Mice and Men | Past | Past | 26 |
| Lady Chatterley's Lover | insufficient | no quotes | 0 |
| The Dead Zone | Past | Past | 38 |
| Daisy Jones & The Six | unlabelled | Past | 53 |
| The Partner | unlabelled | insufficient | 4 |
| Black House | unlabelled | Present | 36 |
| Scarpetta | Present | Past | 12 |
| I, Alex Cross | insufficient | insufficient | 5 |
| A Memory of Light | unlabelled | Past | 29 |
| S. | unlabelled | Present | 67 |
| Jonathan Strange & Mr. Norrell | insufficient | Past | 110 |

## Classification provenance

- Model: `gpt-5.6-terra`; reasoning effort: `medium`.
- Each agent saw one book's quote text plus `METHODOLOGY.md` and
  `terra_prompt_v2.md`; title, author, year, prior label, and network were withheld.
- Every quote-bearing result passed exact quote-ID/order and field-schema validation before
  integration.
- The first agent initially ran in a read-only child sandbox and produced no accepted file;
  it was resumed with write access limited to its isolated job directory.
- Several agents required schema-only retries. Empty dialogue `beat_tense` values were
  canonicalized to the contract's explicit `none`; no bucket, event tense, narrating
  situation, or note was changed by the harness.
- Every replaced source/classification file is preserved under `integration_backup/`.
