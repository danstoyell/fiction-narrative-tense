# 1931–1995 Terra classification tranche

Read `METHODOLOGY.md` and `terra_prompt_v2.md`, then classify every quote in
`quotes.csv`. This workspace contains exactly one book. Use only these workspace
files: do not access parent directories, the network, or prior knowledge.

Write `results.json` with exactly this production-compatible shape:

```json
{
  "sample_id": "top1980:3621",
  "quotes": [
    {"quote_id": "q00001", "bucket": "dialogue|gnomic|event|paratext|unclear", "tense": "past|present|", "beat_tense": "past|present|none (dialogue only)", "note": ""}
  ],
  "narrating_situation": "retrospective|simultaneous|dual|unclear",
  "agent_note": ""
}
```

Every input quote must appear exactly once and in input order. Every quote object
must include `tense`: use `past` or `present` only for `event`, otherwise `""`.
Only `dialogue` has `beat_tense`; use `past`, `present`, or `none`. Do not compute
an overall book label. Validate the file before responding.
