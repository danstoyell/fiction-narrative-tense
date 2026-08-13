# Terra production classification pilot

Read `METHODOLOGY.md` and `terra_prompt_v2.md`, then classify every quote in
`quotes.csv`. This workspace contains exactly one book.

Use only the files in this workspace. Do not use the network, parent directories,
or knowledge of the title. Write `results.json` with the production-compatible
shape below. Do not calculate an overall book label.

```json
{
  "sample_id": "top2023:YELLOWFACE|R.F. Kuang",
  "quotes": [
    {"quote_id": "q00001", "bucket": "dialogue|gnomic|event|paratext|unclear", "tense": "past|present|", "beat_tense": "past|present|none (dialogue only)", "note": ""}
  ],
  "narrating_situation": "retrospective|simultaneous|dual|unclear",
  "agent_note": ""
}
```

Every input quote must appear exactly once and in input order. `tense` is required
only for `event` and must otherwise be empty. `beat_tense` is required only for
`dialogue` and must not be included for other buckets. Before responding, validate
the JSON against those conditions.
