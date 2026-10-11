# Ground-truth narration-person audit

Date: 2026-08-25  
Sample: 30 books randomly selected with seed `20260825`  
Inputs: Goodreads-derived quote classifications in `batch_1.json`–`batch_3.json`  
Machine-readable adjudication: `gold_batch_1.json`–`gold_batch_3.json` and `gold_results.csv`

## Executive conclusion

The quote-only method is useful as a **high-precision, limited-coverage classifier**, but it is not a reliable estimator of the sample's first-/third-person distribution.

- 25 of 30 books received a defensible web-verified reference label; 5 remain unresolved.
- On the 25 resolved books, the pilot emitted a substantive label for 15 (60% coverage).
- Of those 15 labels, 13 matched (86.7% selective accuracy).
- All 9 `high`-confidence pilot labels matched. Only 4 of 6 `med` labels matched.
- Counting abstentions as failures to classify, the pilot exactly classified 13 of 25 resolved books (52%).
- The two errors were both `FIRST` → `THIRD`: *The Last Time They Met* and *Invitation to the Waltz*.
- Of the 10 pilot abstentions that research resolved, 9 were `THIRD` and 1 was `FIRST`. Dropping abstentions would therefore produce severe class-selection bias.

The central methodological problem is not tense. It is **narrative level**: isolated first-person language may be speech, thought, a journal, a letter, or an embedded storyteller rather than the book's controlling narrator. Conversely, a sentence about Maria in a first-person novel says nothing decisive about the narrator because grammatical subject and narrator participation are different variables. Narratology expressly warns that grammatical person does not map one-to-one to narrative person ([García Landa](https://personal.unizar.es/garciala/publicaciones/structuralnarratology/4.Narration/4.4.Person.html)); embedded narrators also occupy distinct narrative levels ([Living Handbook of Narratology](https://www-archiv.fdm.uni-hamburg.de/lhn/node/32.html)).

## What “gold” means here

These labels are web-verified reference labels, not infallible truth. Research was performed blind to the pilot result until an initial label was fixed. Evidence was ranked as follows:

- **A:** sustained official, publisher, author, library, or authorized excerpt directly demonstrates the narrative structure.
- **B:** two or more credible independent descriptions explicitly identify the narration, or one strong scholarly/structural account is corroborated.
- **C:** one explicit credible description plus weaker supporting excerpt/search evidence.
- **D:** no convincing lawful sustained excerpt or explicit structural source was located; label remains `UNRESOLVED`.

`FIRST` means the controlling narrator participates in the story world, even where a novel has several first-person narrators. `THIRD` means the controlling narrator does not participate as a character. `ALTERNATING` requires sustained autonomous sections in different grammatical-person configurations, rather than brief embedded speech, thought, or documents.

## Results for all 30 books

| # | Book | Pilot | Gold | Tier | Result | Principal evidence |
|---:|---|---|---|:---:|---|---|
| 1 | *The Man with the Golden Arm* | Insufficient | **Third** (med) | C | Abstain | An English professor explicitly describes its third-person narration, supported by Google Books indexing ([review](https://johnpauljaramillo.com/2013/08/21/the-man-with-the-golden-arm/)). |
| 2 | *The Matarese Countdown* | Insufficient | **Unresolved** | D | Unscorable | Catalog and snippet searches did not expose sustained narrative prose or a credible explicit POV statement ([Google Books record](https://books.google.com/books/about/The_Matarese_Countdown.html?id=51eUukT50dYC)). |
| 3 | *Dear Edward* | Third (high) | **Third** (high) | B | Match | Independent review describes the alternating time lines and Edward-centered third-person narrative ([WLRN/NPR review](https://www.wlrn.org/npr-breaking-news/2020-01-16/kingdomtide-and-dear-edward-2-new-novels-take-on-a-singular-situation)). |
| 4 | *Masquerade* | Insufficient | **Third** (med) | C | Abstain | Narrative descriptions and the puzzle-book's framing consistently use an external third-person account ([Independent overview](https://www.the-independent.com/news/uk/home-news/golden-hare-kit-williams-masquerade-auction-b2872047.html)). This illustrated puzzle book may be outside the intended prose-novel population. |
| 5 | *The Last Time They Met* | First (med) | **Third** (high) | A | **Mismatch** | A long authorized excerpt sustains third-person narration centered on Linda ([ReadingGroupGuides excerpt](https://www.readinggroupguides.com/reviews/the-last-time-they-met-a-novel/excerpt)). |
| 6 | *A Thousand Splendid Suns* | Third (high) | **Third** (high) | B | Match | Scholarly analysis identifies the novel's third-person narration and changing focalization ([article](https://www.ilkogretim-online.org/index.php/pub/article/view/4887)). |
| 7 | *The Cardinal* | Insufficient | **Third** (high) | A | Abstain | A sustained digitized excerpt consistently narrates Stephen Fermoyle externally ([excerpt](https://www.basicincome.com/bp/thecardinal.htm)). |
| 8 | *Invitation to the Waltz* | First (med) | **Third** (med) | B | **Mismatch** | Scholarship explicitly calls it third person with occasional shifts into first, with Olivia controlling focalization ([King's College London thesis](https://kclpure.kcl.ac.uk/portal/files/2930814/DX215343.pdf)); an independent review also describes third-person shifts between the sisters ([Shelf Love](https://shelflove.wordpress.com/2011/03/05/invitation-to-the-waltz-review/)). |
| 9 | *Lincoln* | Third (high) | **Third** (high) | B | Match | Contemporary review discusses Vidal's external, multi-character historical narration ([Washington Post](https://www.washingtonpost.com/archive/entertainment/books/1984/06/10/gore-vidals-lincoln-log/afc1f337-4215-4400-904d-6f050adea69a/)). |
| 10 | *A Man in Full* | Third (high) | **Third** (high) | B | Match | Critical analysis describes Wolfe's naturalistic third-person method across several characters ([article](https://www.researchgate.net/publication/303336467_The_Last_of_the_Naturalist_Writers_A_Discussion_on_the_Naturalistic_nature_of_Tom_Wolfe%27s_A_Man_In_Full_and_Back_to_Blood)). |
| 11 | *Golden Girl* | Unclear | **Third** (high) | B | Abstain | Structural summaries identify a third-person voice moving among Vivi and other focal characters ([SuperSummary](https://www.supersummary.com/golden-girl/chapters-1-10-summary/)). |
| 12 | *A Painted House* | First (high) | **First** (high) | A | Match | Publisher material and excerpt establish Luke's participating first-person narration ([Hachette](https://www.hachette.com.au/john-grisham/a-painted-house)). |
| 13 | *The Royal Box* | Insufficient | **Unresolved** | D | Unscorable | Reviews describe plot but not narrator, and no sustained preview was located ([Kirkus](https://www.kirkusreviews.com/book-reviews/a/frances-parkinson-keyes-2/the-royal-box/)). |
| 14 | *A Bell for Adano* | Insufficient | **Third** (high) | A | Abstain | A contemporaneous serialized excerpt supplies sustained third-person prose ([Historic Oregon Newspapers PDF](https://oregonnews.uoregon.edu/lccn/2025240345/1945-03-22/ed-1/seq-2.pdf)). |
| 15 | *From a Buick 8* | First (med) | **First** (high) | B | Match | The authorized opening is first person, and structural sources describe multiple first-person voices ([BookBrowse excerpt](https://www.bookbrowse.com/excerpts/index.cfm/book_number/1081/from-a-buick-8); [publisher page](https://www.hachette.co.uk/titles/stephen-king-3/from-a-buick-8/9781444708110/)). Multiple narrators are not, by themselves, mixed grammatical person. |
| 16 | *The Wish* | Alternating (med) | **Alternating** (high) | A | Match | The official excerpt demonstrates a third-person present-day frame and Maggie's sustained first-person past account ([official PDF](https://nicholassparks.com/wp-content/uploads/2022/09/excerpt-23.2021.09-the-wish.pdf)). |
| 17 | *Griffin & Sabine* | Insufficient | **First** (high) | B | Abstain | The work is an epistolary exchange between two participating correspondents, both using first person ([critical study](https://www.researchgate.net/publication/327600795_An_Open_Letter_to_Nick_Bantock_OR_Letters_andas_Ephemeral_Desire_Transposition_and_Transpoetic_Possibility_within_Epistolary_Form_A_Critical_Approach_to_Contemporary_Letter_Narratives_in_Anglophone_Fi)). The pilot skipped most usable evidence because the letters were upstream-labeled `dialogue`. |
| 18 | *Say You'll Remember Me* | First (high) | **First** (med) | C | Match | The publisher-authorized extract sustains participating first-person narration ([Yours With Love extract](https://www.yourswithlove.co.uk/blog/article/read-an-extract-from-say-you-ll-remember-me-by-abby-jimenez)). |
| 19 | *The Word* | Insufficient | **Unresolved** | D | Unscorable | Available scholarship and catalog material describe its gospel-thriller plot but did not settle narration ([USC Scalar](https://scalar.usc.edu/works/gospel-thrillers/media/1972-the-word)). |
| 20 | *The Associate* | Insufficient | **Third** (high) | A | Abstain | A publisher-hosted excerpt sustains external third-person narration of Kyle ([Booktopia/Hachette PDF](https://static.booktopia.com.au/pdf/9781846050923-1.pdf)). |
| 21 | *The Runaway Jury* | Insufficient | **Third** (high) | B | Abstain | Independent study sources explicitly identify omniscient third person with access to several characters ([SuperSummary](https://www.supersummary.com/the-runaway-jury/important-quotes/)). |
| 22 | *Evergreen* | Insufficient | **Unresolved** | D | Unscorable | Catalog access and searchable snippets were insufficient to establish narrative structure ([Open Library](https://openlibrary.org/books/OL7517575M/Evergreen)). |
| 23 | *Strangers in Time* | Insufficient | **Third** (high) | A | Abstain | The author's official excerpt sustains third-person narration across the principal characters ([David Baldacci](https://www.davidbaldacci.com/articles/strangers-in-time-excerpt/)). |
| 24 | *The Boy from the Woods* | Insufficient | **Third** (high) | A | Abstain | A publisher excerpt sustains third-person narration centered on Wilde and other characters ([Penguin](https://www.penguin.com.au/books/the-boy-from-the-woods-9781787462977/extracts/2223-the-boy-from-the-woods)). |
| 25 | *I Will Find You* | First (med) | **First** (high) | A | Match | A publisher excerpt directly establishes David's participating first-person narration ([Penguin](https://www.penguin.com.au/books/i-will-find-you-9781804965412/extracts/2916-i-will-find-you)). |
| 26 | *Love Is Eternal* | Insufficient | **Unresolved** | D | Unscorable | Bibliographic records and snippets did not expose enough prose or an explicit reliable POV description ([Google Books](https://books.google.com/books/about/Love_is_Eternal.html?id=aVEOAAAAIAAJ)). |
| 27 | *Chasing Harry Winston* | Third (med) | **Third** (high) | A | Match | The author's official first chapter sustains third-person narration while shifting focal character ([Lauren Weisberger](https://www.laurenweisberger.com/books/chasing-harry-winston/1st-chapter/)). |
| 28 | *The Last Hurrah* | Third (high) | **Third** (high) | B | Match | Reference material and digitized academic discussion consistently characterize the external third-person account ([EBSCO Research Starters](https://www.ebsco.com/research-starters/history/last-hurrah-edwin-oconnor)). |
| 29 | *The Guardians* | First (high) | **First** (high) | B | Match | Structural reference explicitly identifies first-person narration by Cullen Post ([BookRags](https://www.bookrags.com/studyguide-the-guardians-a-novel/styles.html)). |
| 30 | *The Wrong Side of Goodbye* | Third (high) | **Third** (high) | A | Match | The author's official excerpt sustains third-person Bosch narration ([Michael Connelly](https://www.michaelconnelly.com/writing/the-wrong-side-of-goodbye/the-wrong-side-of-goodbye-excerpt/)). |

## Aggregate comparison

### Gold-label distribution

Among the 25 resolved books:

| Gold label | Books | Share |
|---|---:|---:|
| Third | 18 | 72% |
| First | 6 | 24% |
| Alternating | 1 | 4% |

The pilot's 15 substantive outputs were 7 third, 7 first, and 1 alternating. If abstentions were silently discarded, the apparent first-person share would be 46.7% rather than the reference set's 24%. This is not a minor calibration issue: it is a strongly directional missing-data problem.

### Confusion and coverage

| Gold label | Pilot same | Pilot wrong | Pilot abstained |
|---|---:|---:|---:|
| Third (18) | 7 | 2 first | 9 |
| First (6) | 5 | 0 | 1 |
| Alternating (1) | 1 | 0 | 0 |

- Selective accuracy: `13 / 15 = 86.7%`
- Coverage on resolvable books: `15 / 25 = 60%`
- Exact classification over all resolvable books: `13 / 25 = 52%`
- High-confidence precision: `9 / 9 = 100%`
- Medium-confidence precision: `4 / 6 = 66.7%`

This sample is too small for a population performance claim, but it is adequate to expose failure modes and to reject an analysis that treats classified books as representative of all books.

### Are the five gold-set abstentions class-biased?

There is no evidence that these five unresolved reference cases have the same
first-/third-person bias as the quote-only pilot's abstentions. The pilot bias
is observed directly because later research resolved nine of ten abstentions
as third person. The remaining five labels are unknown, so claiming a person
direction would be circular.

They are, however, strongly patterned by evidence availability and age: 4 of
9 sampled books published before 1980 remain unresolved (44.4%), compared with
1 of 21 published from 1980 onward (4.8%). Four of the five are from 1954–1978;
the fifth is from 1997. This small sample does not establish a stable rate, but
it is enough to reject missing-completely-at-random across publication era.

Operationally, keep these records in the denominator and report unresolved
coverage by decade. Do not impute them as third person, and do not claim that
their exclusion biases the person distribution unless later evidence reveals
that pattern. Their clear current risk is era/rights-availability bias, with
possible downstream person bias only if narrative person is correlated with
those variables.

## Suspicious conclusions and error analysis

### 1. Two isolated first-person quotes can produce a false base-narrator label

For *The Last Time They Met*, two event quotes with `I` drove a medium-confidence `FIRST` label, while another quote showed third-person access to Linda. The long authorized opening is consistently third person. The first-person fragments are therefore local voice—speech, direct thought, or another embedded utterance—not evidence of the controlling narrator.

For *Invitation to the Waltz*, an `I` quote explicitly announces keeping a record, while other evidence follows Olivia externally. Scholarship resolves the structure as primarily third person with occasional first-person shifts. A local journal/document voice was promoted to book-level narration.

**Implication:** quote count cannot substitute for identifying who is speaking and at what narrative level. The current rule requiring two explicit first-person event quotes is not safe unless both are demonstrably primary-level narration from contiguous prose.

### 2. The abstentions are not class-neutral

Nine of ten resolvable abstentions were third-person books. Third-person narration is often expressed through ordinary named-character sentences or zero-person description, neither of which is as diagnostically salient as `I`. In this pilot, 94 routed observations were `unmarked`. Goodreads' preference for memorable speech, aphorism, and interior monologue compounds the asymmetry.

**Implication:** reporting accuracy only on classified books makes the method look substantially better and makes the corpus look substantially more first-person than it is.

### 3. The upstream tense-oriented buckets lose legitimate person evidence

In *Griffin & Sabine*, three of four available excerpts were letters classified upstream as `dialogue`, so the person pass skipped the work's actual autonomous narrative medium. Those labels may be appropriate for a tense analysis, but `dialogue` is too coarse for person inference: a quoted exchange embedded in a scene and a novel composed of letters are structurally different.

**Implication:** existing upstream labels should remain immutable, as requested.
The person stage must still ask whether a passage is controlling narration or
local/embedded material, but this can be recorded only in the evidence note
when it affects the decision. A full narrative-level schema is not required.

### 4. Some resolved labels still conceal important structures

- *From a Buick 8* has multiple participating first-person voices. That is `FIRST`, not necessarily `ALTERNATING`.
- *The Wish* really does alternate sustained first- and third-person narrative configurations.
- *Invitation to the Waltz* is primary third person with localized first-person material.
- *Griffin & Sabine* is first-person epistolary narration by two correspondents.
- *Golden Girl* shifts focal characters inside third-person narration.

A single label is usable for the narrow task if the rationale explains any
material exception. A separate configuration output is not required.

## Recommended methodology changes

1. **Define the target as narrator participation, not visible pronouns.** Use `FIRST` for a homodiegetic/participating controlling narrator and `THIRD` for a heterodiegetic/nonparticipating controlling narrator. Treat pronouns as evidence, not the target.

2. **Keep person independent of tense.** Continue consuming existing quote-level past/present labels. Do not introduce a new “tense situation” decision and do not emit a combined person-tense class. Person aggregation should be its own output layer.

3. **Keep contextual structure as a judgment, not an ontology.** When a passage
   could be speech, thought, a letter, or an embedded story, explain its role in
   the evidence note. Do not overwrite upstream buckets or annotate every quote
   with a narrative level.

4. **Remove `third_pattern` as a production field.** A named character's action,
   perception, or interior access is supporting context, not proof of
   third-person narration. “Maria walked to the store” is compatible with a
   first-person narrator describing Maria.

5. **Require evidence about controlling narration before assigning `FIRST`.**
   Two scattered `I` quotes are insufficient. Establish their role through
   surrounding text, recurring Goodreads evidence, or a credible structural
   source.

6. **Make internet research mandatory, not merely validation.** Search for
   authorized excerpts and explicit descriptions of POV or narrative structure,
   then reconcile those sources with Goodreads. Store URLs and evidence scope.

7. **Treat contiguous excerpts as useful but neither mandatory nor globally
   representative.** When available, record whether an excerpt is an opening,
   interior passage, or named section. A lone opening cannot settle the whole
   book when the other evidence conflicts.

8. **Return one book label and a rationale.** Multiple first-person narrators
   remain `FIRST`; sustained sections in different persons are `ALTERNATING`;
   epistolary or framed details belong in the note. Do not add a separate
   configuration schema.

9. **Use Sol High and audit all medium-confidence outputs.** The high-confidence
   threshold performed well in this small test; medium confidence contained
   both errors.

10. **Keep abstentions in every reported denominator.** Report coverage,
    selective accuracy, and class-specific abstention rates together. Do not
    estimate class prevalence from only substantive outputs unless missingness
    is corrected.

11. **Add an eligibility check.** Determine whether the item is a conventional
    prose narrative before person classification. *Masquerade* is an
    illustrated puzzle book, so including it may violate the population
    definition.

12. **Validate on a larger, independent set.** Use blind double annotation,
    adjudicate disagreements with all available evidence, and stratify by
    publication era, preliminary class, quote coverage, unusual narrative
    forms, and source availability.

## Fundamental gaps that methodology alone cannot close

- **Scattered quotations omit hierarchy.** They usually lack chapter boundaries, adjacent prose, and reliable speaker attribution, so primary narration cannot always be distinguished from embedded narration.
- **Quote selection is endogenous.** Readers disproportionately save dialogue, aphorisms, emotional first-person language, and polished interior statements rather than representative narration.
- **Evidence is asymmetric.** `I` can be strong local evidence but is easy to misattribute; named-character third-person prose is common but may describe a non-narrator character inside a first-person book.
- **Preview availability is historically uneven.** The five unresolved books are all older or have limited lawful searchable access. A web-grounded dataset will inherit publication-era and rights-availability bias.
- **Binary labels compress real narrative systems.** Framed tales, epistolary
  books, multiple same-person narrators, and genuinely mixed-person novels need
  explanation in the rationale even when no auxiliary schema is used.
- **The existing buckets were designed for tense.** They can remain immutable,
  but the person decision must sometimes use a letter or document that the
  upstream tense pass legitimately called `dialogue`.

## Recommended operational decision

Use a hybrid Sol High classification pass:

1. Classify the Goodreads evidence and perform internet research for every book.
2. Assign high confidence only when independent evidence routes agree; review
   medium, unclear, conflict, and insufficient cases.
3. Preserve unresolved books and all abstentions in analysis.
4. Do not use the current substantive-only outputs to estimate first-/third-person prevalence.

That design preserves the encouraging precision of strong quote evidence while
using external evidence to address missing context and third-person
undercoverage.
