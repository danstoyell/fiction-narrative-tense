# Base-narration person harness

Separate Sol Medium pipeline for `FIRST` / `SECOND` / `THIRD` / `ALTERNATING`
base-narration labels. It does not modify the finished tense classifications,
their harnesses, or `METHODOLOGY.md`.

The agent definition is [`PROMPT.md`](PROMPT.md), the output contract is
[`result_schema.json`](result_schema.json), and the governing rules are
[`../PERSON_METHODOLOGY.md`](../PERSON_METHODOLOGY.md).

## Outputs

- `raw_data/person_runs/<run-id>/`: immutable staged inputs, results, logs, and
  manifest. Gitignored because it duplicates quote text.
- `raw_data/person_classified/<safe-sample-id>.json`: promoted source-of-truth
  result per book.
- `dataset/person_books.csv`: flat book labels, justifications, evidence, and
  signal counts.
- `dataset/person_quotes.csv`: every source quote joined to its person signal.
- `person_report.html`: standalone interactive report generated from both CSVs by
  `python3 analysis/build_person_report.py`.

Each book JSON contains every quote ID exactly once, a quote-level
`person_signal`, the book's base-person label and confidence, web evidence,
search log, and final reconciliation note.

## Bulk workflow

For the normal one-command path:

```bash
python3 person/person_harness.py batch \
  --run-id person_batch_001 \
  --sample-file ids.csv \
  --workers 1
```

This stages the books, runs and validates Sol Medium jobs, promotes only if every
job validates, and regenerates both person CSVs. It never overwrites an existing
book result. Use the staged commands below when you want to inspect inputs or
the exact model command before spending calls.

From the repository root, stage either specific sample IDs, a text/CSV list, or
every book without an existing person result:

For a deterministic annual panel, select the first `N` books in source order
for every year in an inclusive range:

```bash
python3 person/person_harness.py prepare \
  --run-id person_1996_2025_5peryear \
  --per-year 5 --year-from 1996 --year-to 2025
```

```bash
python3 person/person_harness.py prepare \
  --run-id person_batch_001 \
  --sample-file ids.csv
```

```bash
python3 person/person_harness.py prepare \
  --run-id person_batch_001 \
  --all --limit 30
```

Inspect the exact Codex commands without spending model calls:

```bash
python3 person/person_harness.py run \
  --run-id person_batch_001 --workers 1 --dry-run
```

Run all staged books. `--workers` controls concurrent Sol calls;
`--max-attempts` controls schema-validation retries, and `--job-timeout`
prevents a transport stall from holding a worker indefinitely:

```bash
python3 person/person_harness.py run \
  --run-id person_batch_001 --workers 1 --max-attempts 2 --job-timeout 900
```

Use one worker when Codex usage allowance, rather than elapsed wall time, is the
bottleneck. Jobs are dispatched in waves no larger than `--workers`. If Codex
reports a usage limit, the wave finishes and the run pauses without charging
those capacity rejections against `--max-attempts`; rerun the same command after
the reported reset. A rejected schema/evidence result does consume an attempt,
and the next attempt receives the validator's exact failure as correction
feedback.

Validate, promote without overwriting any prior result, then rebuild flat CSVs:

```bash
python3 person/person_harness.py status --run-id person_batch_001
python3 person/person_harness.py promote --run-id person_batch_001
python3 person/person_harness.py export
```

`prepare` defaults to `dataset/books.csv` and `dataset/quotes.csv`. Use
`--books-csv` and `--quotes-csv` for another compatible dataset. A CSV sample
file needs a `sample_id` column; a text file uses one sample ID per line.

## Execution guarantees

- Model is pinned to `gpt-5.6-sol` with medium reasoning effort (updated 2026-09-06). Earlier results retain their recorded Sol High or Astra Medium provenance; resumed batches record the producing model per book. This execution setting supersedes the older model requirement in `PERSON_METHODOLOGY.md`.
- Live hosted search is explicitly enabled with `web_search="live"`.
- Each job receives only its book metadata, quote rows, methodology, prompt,
  task, and JSON schema.
- Codex runs in a read-only local sandbox. The CLI captures its structured final
  response into `results.json`.
- Promotion validates the schema, quote completeness/order, confidence rules,
  URLs, search log, and minimum label support before writing production files.
- Existing promoted results are never overwritten.

The invocation follows OpenAI's documented `codex exec` automation mode and
top-level live-search configuration:

- https://learn.chatgpt.com/docs/non-interactive-mode
- https://learn.chatgpt.com/docs/config-file/config-reference

## Quote signals

`first`, `second`, and `third` mean the quote diagnostically supports that base
narrating position. `unmarked` means narration is present but the local sentence
does not expose the narrator—such as “Maria walked to the store.” `non_base`
covers speech, paratext, gnomic material, and demonstrably embedded voices;
`unclear` preserves genuinely clipped or unresolved cases.

These signals are evidence annotations, not majority votes. The book label is
the agent's cited reconciliation of all quote and web evidence.
