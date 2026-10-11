# Narrative-person classification from quotes and web evidence

Companion to [`METHODOLOGY.md`](METHODOLOGY.md) for assigning one book-level
narrative-person label. It uses the same Goodreads material plus a mandatory
internet search.

This pass consumes existing `bucket`, `tense`, and `beat_tense` values without
changing them. It does not redo tense, add a second tense-situation field, or
emit a combined person-tense label. Person and tense remain separate columns
that can be joined downstream.

## Execution standard

Use **`gpt-5.6-sol` with high reasoning effort** ("Sol High") for production
classification and adjudication. The 2026-08-25 Terra-medium pilot is an
evaluation artifact, not a production run under this method.

## Target

Assign the book's controlling narrative person:

| Label | Meaning |
|---|---|
| `FIRST` | The controlling narrator participates in the story and narrates as `I` or `we`. Multiple first-person narrators still count as `FIRST`. |
| `SECOND` | Sustained controlling narration casts a story-specific protagonist as `you`. |
| `THIRD` | The controlling narrator does not participate as a character and narrates characters externally. Limited, omniscient, objective, and free-indirect variants all count as `THIRD`. |
| `ALTERNATING` | The book has sustained first-, second-, or third-person sections in more than one person. |
| `UNCLEAR` | Evidence exists but credible sources or passages conflict and the structure cannot be resolved. |
| `INSUFFICIENT` | The combined quote and internet search yields too little diagnostic evidence. |
| `EXCLUDED` | The item is not eligible prose narrative for this study. |

The target is narrator participation, not the grammatical person of every
sentence and not focalization. For example:

> Maria walked to the store.

This identifies Maria as the sentence's subject. It does not reveal whether a
first-person narrator is describing Maria or a nonparticipating narrator is
describing her. Proper names and `he`, `she`, or `they` are compatible with
both first- and third-person books.

## Deliberately lean design

The output contains one person label, confidence, cited evidence, and a short
rationale. It does **not** require a general-purpose narrative-level ontology,
per-quote strand IDs, or a separate book-configuration schema.

One distinction is still unavoidable during judgment: is a passage the book's
controlling narration, or is it local material such as speech, direct thought,
an embedded story, or a quoted document? Record this only when it affects the
decision, in the evidence note. It is a reasoning check, not a required label
on every quote.

## Procedure

### 1. Verify the work and gather Goodreads evidence

Follow `METHODOLOGY.md` for title resolution, deduplication, provenance, and
upstream quote classification. Read all available quotes for the book, not
only those routed as event narration.

Use existing buckets as follows:

- `event`: inspect the narratorial text for person evidence;
- `dialogue`: speech pronouns normally do not identify the narrator, but an
  outside speech beat may do so;
- `gnomic`, `paratext`, and `unclear`: normally nondiagnostic.

Do not reclassify these buckets. If a bucket appears wrong, note it as a
possible upstream issue. An exception in *use*, not in bucket value, is allowed
when research shows that letters, diaries, messages, or transcripts constitute
the book itself. For example, a letter labeled `dialogue` upstream may still
be evidence of the narrator in an epistolary novel. Record why it is
constitutive rather than silently changing the bucket.

### 2. Extract only diagnostic quote evidence

Diagnostic first-person evidence is `I` or `we` used by the narrator outside
character speech, quoted thought, or a subordinate document. Diagnostic
second-person evidence is sustained story-specific narration of a protagonist
as `you`, not direct address or a universal maxim.

Third-person evidence must establish the controlling narrating position across
context. A sentence about a named character is not enough. Stronger patterns
include sustained scene narration of characters as `he`, `she`, or `they`,
especially when no participating narrator frames the passage. Even these are
provisional until reconciled with other quotes and web evidence.

Do not use the old rule that two scattered narratorial `I` quotes automatically
establish `FIRST`. The pilot produced two false first-person labels this way.
The passages must be shown to belong to controlling narration, not merely a
journal excerpt, speech, free-direct thought, or story within the story.

Assign every input quote one compact `person_signal` so the decision remains
auditable:

| Signal | Meaning |
|---|---|
| `first` | The quote diagnostically exposes participating base narration as `I` or `we`. |
| `second` | The quote diagnostically exposes sustained, story-specific base narration as `you`. |
| `third` | The quote diagnostically exposes nonparticipating base narration across enough local context; a bare named or third-person subject is not sufficient. |
| `unmarked` | The quote contains possible base narration but does not identify its person, including “Maria walked to the store.” |
| `non_base` | Speech, gnomic material, paratext, or a demonstrably local/embedded voice that should not identify the base narrator. A constitutive letter in an epistolary novel is not `non_base`. |
| `unclear` | Clipping, lost quotation boundaries, or unresolved local structure prevents a responsible signal. |

Each signal receives a short note. This is an evidence label, not a claim that
the whole book uses the quote's visible pronouns. No strand IDs or general
narrative-level annotations are required.

### 3. Search the internet for person evidence for every book

Internet research is mandatory even when Goodreads looks conclusive. Search
the verified title and author using combinations such as:

- `"title" "author" excerpt`, `first chapter`, or `read an extract`;
- `"title" point of view`, `first person`, `third person`, `narrator`, or
  `narrated by`;
- `"title" epistolary`, `diary`, `frame narrative`, `multiple narrators`, or
  `alternating point of view`; and
- author, publisher, library, Google Books, Open Library/Internet Archive,
  scholarly-repository, and reputable-review searches.

Use the same evidence tiers as `METHODOLOGY.md`:

- **A:** sustained authorized, publisher, author, or library excerpt;
- **B:** scholarly structural analysis or multiple credible explicit sources;
- **C:** one credible explicit description or several short corroborating
  passages; and
- **D:** synopsis, catalog copy, snippet, unattributed assertion, or inaccessible
  preview—useful only for discovery.

An opening proves only how the opening is narrated. Record its limited scope
and look for interior excerpts or a source describing the overall structure.
Likewise, a review written as “we follow Maria” is not evidence of first-person
narration unless it explicitly describes the book's narrator or POV.

For every usable source, record URL, title, evidence tier, scope, supported
label, and a short note. Record the search log even when nothing useful is
found.

### 4. Aggregate the two evidence channels

Do not decide by counting sources or pronouns. Reconcile what each source is
actually capable of showing:

| Evidence pattern | Decision |
|---|---|
| Goodreads narration and credible web evidence agree | Assign the supported label. |
| Goodreads is sparse, but Tier A sustained prose or Tier B structural evidence clearly establishes the controlling person | Assign the web-supported label. |
| Goodreads alone repeatedly exposes an unmistakable controlling narrator and web research finds no contradiction | A label may be assigned at `med`; web silence cannot produce `high`. |
| A single opening is the only useful evidence | Treat it as supporting evidence, not proof of the whole book. Use `med` only when Goodreads corroborates it; otherwise abstain. |
| A local first-person passage conflicts with sustained or structural third-person evidence | Treat the local passage as embedded unless further evidence shows an autonomous first-person section; assign `THIRD` or `ALTERNATING` accordingly. |
| Different persons occur in sustained chapters, timelines, or frame/story sections | Assign `ALTERNATING`. |
| Credible conflict remains after targeted follow-up searches | Assign `UNCLEAR`. |
| Neither channel is diagnostic | Assign `INSUFFICIENT`. |
| The item is not eligible prose narrative for the study | Assign `EXCLUDED`. |

Multiple narrators do not imply `ALTERNATING` if all narrate in first person.
Epistolary form does not need a separate output configuration: if the letters
constitute the novel and the correspondents narrate as `I`, the result is
`FIRST`. A third-person frame plus a sustained first-person story is
`ALTERNATING`. Explain these cases in the rationale.

### 5. Assign confidence

- `high`: Goodreads and Tier A/B evidence independently agree, or several
  strong sources establish the whole-book structure with no credible conflict;
- `med`: one strong route or several weaker routes support the result, but
  coverage or scope is limited;
- `CONFLICT`: a provisional result retains credible unexplained contrary
  evidence and must be reviewed.

`UNCLEAR`, `INSUFFICIENT`, and `EXCLUDED` have no confidence. Medium and conflict cases
require human or independent Sol High adjudication before trend analysis.

## Required output

```json
{on
  "schema_version": 1,
  "sample_id": "top1995:1234",
  "quotes": [
    {"quote_id": "q00001", "person_signal": "first|second|third|unmarked|non_base|unclear", "note": "Why this quote does or does not identify base narration"}
  ],
  "person_label": "FIRST|SECOND|THIRD|ALTERNATING|UNCLEAR|INSUFFICIENT|EXCLUDED",
  "person_confidence": "high|med|CONFLICT|",
  "web_evidence": [
    {
      "url": "https://example.com/excerpt",
      "title": "Source title",
      "tier": "A|B|C|D",
      "scope": "whole_book|named_section|opening|interior|unknown",
      "supports": "FIRST|SECOND|THIRD|ALTERNATING|none",
      "note": "What the source establishes"
    }
  ],
  "search_log": ["queries and material dead ends"],
  "person_note": "How quote and web evidence were reconciled, including any local embedded material"
}
```

`EXCLUDED` is also permitted for an ineligible non-prose item. Every input
quote must appear exactly once and in input order. Derived signal counts need
not be generated by the agent; the export step computes them mechanically.

Keep `bucket`, `tense`, `beat_tense`, and the existing book-level tense label
unchanged. Do not add a `combined_label`, person-specific `tense_situation`,
strand list, or configuration field.

## Quality control and reporting

1. Blindly duplicate a stratified sample with Sol High and adjudicate book-level
   disagreements without showing the second pass the first label.
2. Audit every `med` and `CONFLICT` result. In the 30-book pilot, all nine high
   person labels matched the researched reference, while only four of six
   medium labels matched.
3. Report accuracy and coverage together, including `UNCLEAR` and
   `INSUFFICIENT`. The quote-only pilot classified 15 of 25 resolvable books;
   nine of its ten resolvable abstentions were third person.
4. Report unresolved rates by decade and evidence availability. Web failures
   are not guaranteed to be missing at random.
5. Apply an eligibility check before classification; illustrated puzzle books,
   verse, collections, or other non-prose forms may not belong in the target
   population.

## Known limitations

- Goodreads quotes are popularity-selected and overrepresent dialogue,
  aphorisms, and vivid first-person reflection.
- Web excerpts are legally and commercially uneven. Older and obscure books
  are less likely to have searchable sustained prose.
- A contiguous excerpt improves local attribution but may still be
  unrepresentative, especially when it is only the opening.
- First-person books can contain long passages about other characters without
  an `I`; third-person books can contain highly quotable first-person speech,
  thought, letters, or embedded stories.
- Binary book labels necessarily compress genuinely alternating forms, but the
  `ALTERNATING` label and rationale retain the distinction needed for this
  study without a larger ontology.
