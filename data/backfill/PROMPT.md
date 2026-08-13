# beat_tense backfill — one book

You are adding ONE field to an existing classification. You are **not** re-classifying.

Read `METHODOLOGY.md` §4b ("Record `beat_tense` on every dialogue quote") before starting.

## What to do

0. **If every dialogue quote in the file already has `beat_tense`, stop.** Report that it
   was already complete and write nothing. A book can already be done — an agent killed by
   the watchdog may have written its file before dying.
1. Your assignment file names a JSON in `data/classified/`. Read it.
2. Pull that book's quote text with the command below. **Do not read the CSV directly** --
   it is 3.2 MB and reading it wastes most of your budget before you start:

   ```bash
   python3 -c "
   import csv,sys,json
   sid=json.load(open(sys.argv[1]))['sample_id']
   rs=[r for r in csv.DictReader(open('data/quotes_topn.csv')) if r['sample_id']==sid]
   print(json.dumps([{'id':r['quote_id'],'t':r['quote_text']} for r in rs],indent=1))
   " data/classified/<YOUR_FILE>.json
   ```
3. For **every quote whose `bucket` is `dialogue`**, add `"beat_tense"`.
4. Write the file back.

## PRESERVE EVERYTHING ELSE EXACTLY

Do not change any `bucket`, `tense`, `note`, `quote_id`, `narrating_situation`, or
`agent_note`. Do not add, drop, or reorder quotes. Do not re-judge buckets even if you
disagree — a later pass depends on these labels being stable. The ONLY permitted change
is adding `beat_tense` to dialogue quotes.

## The judgment

`beat_tense` is `past`, `present`, or `none`.

A speech quote usually carries narration the **narrator** speaks — a tag (`he said`,
`she opined`, `Wilson thinks`) or an action beat (`He patted the stock of Reel's rifle`,
`she pushed back her chair`). Record that narration's tense.

* Only narration **the narrator** speaks counts. A tag inside a character's own speech
  ("A wise woman once told me that…") is that character reporting — `none`.
* The speech CONTENT never counts. A character saying "I am hungry" in a past-tense novel
  is not present evidence.
* Habitual `would` is past narration ("his father **would say**" = used to say).
  Conditional/subjunctive `would` is not.
* A truncated or dangling attribution (bare name, no verb) is `none`.
* Use quotation marks when the quote has them; mark survival varies sharply by book.
  Fall back on who is speaking only when marks are absent.
* Pure oratory with no narrator words at all is `none`. Most markless quotes are this.

## Report

ONE line: `<n> dialogue quotes: X past / Y present / Z none`, plus any quote id where the
call was genuinely close.
