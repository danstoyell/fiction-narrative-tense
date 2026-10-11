# Base-narration person classifier

You are producing auditable narrative-person data for one book. Determine the
person of the book's **base narration**, not the grammatical person of whichever
character happens to appear in a quote.

Read `PERSON_METHODOLOGY.md`, `book.json`, and `quotes.csv` completely before
deciding. Then perform the mandatory live internet research described in the
methodology. Use the verified title and author in `book.json`.

## Required reasoning order

1. Classify every quote's person evidence without changing its existing
   `bucket`, `tense`, or `beat_tense`.
2. Search for authorized excerpts and explicit descriptions of point of view,
   narrator, epistolary form, frames, and alternating narration.
3. Open sources before using them. Search snippets and plot-summary grammar are
   not evidence.
4. Reconcile quote and web evidence into one base-narration label.
5. Return exactly one JSON object matching `result_schema.json`.

## Quote signals

- `first`: diagnostically exposes participating base narration as `I`/`we`.
- `second`: diagnostically exposes story-specific base narration as `you`.
- `third`: diagnostically exposes nonparticipating base narration. A proper
  name, `he`, `she`, or `they` alone is not enough.
- `unmarked`: possible base narration that does not identify narrator person.
- `non_base`: speech, gnomic/paratext material, or a demonstrably embedded/local
  voice. A constitutive letter in an epistolary novel is not automatically
  non-base.
- `unclear`: clipping or unresolved local structure prevents a judgment.

Every quote ID must appear exactly once and in input order. Give each a concise
note. Quote signals are evidence annotations; they do not mechanically vote.

## Book labels

Use `FIRST`, `SECOND`, `THIRD`, `ALTERNATING`, `UNCLEAR`, `INSUFFICIENT`, or
`EXCLUDED`. Multiple first-person narrators are still `FIRST`. Use
`ALTERNATING` only for sustained base sections in different persons. Do not
promote an isolated speech, thought, letter, journal passage, or embedded tale
to the book level.

Assign `high`, `med`, or `CONFLICT` only to substantive labels. Leave confidence
empty for `UNCLEAR`, `INSUFFICIENT`, and `EXCLUDED`. High confidence requires
strong web evidence and either corroborating quote evidence or multiple strong
independent web sources.

Record direct source URLs and what each source actually establishes. The final
`person_note` must explain the base narrator, reconcile contrary/local evidence,
and state the main remaining uncertainty. Do not return Markdown or prose
outside the JSON object.
