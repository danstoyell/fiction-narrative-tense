# Goodreads resolution correction classification

Read `METHODOLOGY.md` and `terra_prompt_v2.md`, then classify every quote in
`quotes.csv`. This workspace contains exactly one unidentified book.

Use only the files in this workspace. Do not use the network, parent directories,
the book title, or any prior classification. Write `results.json` with exactly:

```json
{
  "sample_id": "top2001:710",
  "quotes": [
    {"quote_id": "q00001", "bucket": "dialogue|gnomic|event|paratext|unclear", "tense": "past|present|", "beat_tense": "past|present|none (dialogue only)", "note": ""}
  ],
  "narrating_situation": "retrospective|simultaneous|dual|unclear",
  "agent_note": ""
}
```

Every input quote must appear exactly once and in input order. `tense` is required
only for `event` and must otherwise be empty. `beat_tense` is required only for
`dialogue` and must be omitted for other buckets. Do not compute an overall book
label. Validate the complete JSON before responding.
