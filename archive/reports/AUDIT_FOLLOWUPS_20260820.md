# Publication audit follow-ups (archived)

Open correctness work identified in the August 2026 publication review. These items are
deliberately recorded here because they can alter evidence or reported uncertainty; they are
not general code-quality cleanup.

## 1. Validate Goodreads resolutions by title

**Status:** complete — audited, corrected, reclassified, and regenerated 2026-08-20.

Before this fix, `booktense/goodreads.py` validated author and publication year after an ISBN
or direct-search resolution, but not the requested title. Bad source ISBNs could therefore
resolve to another book by the same author with high confidence.

Known active cases to audit include:

- *Of Mice and Men* resolved to *The Grapes of Wrath*.
- *The Rainmaker* resolved to *The Client*.
- *The Dead Zone* resolved to *Firestarter*.
- *Scarpetta* resolved to *Trace*.
- *I, Alex Cross* reused the Goodreads work for *Cross*.
- *The Winds of War* and *War and Remembrance* share a Goodreads work/quote set.
- *The Nightingale* appears in both 2015 and 2023 and needs an explicit re-entry policy.

**Acceptance criteria:** ISBN and direct redirects must pass normalized title validation;
all active duplicate Goodreads work IDs must be reviewed; affected books must be refetched,
reclassified if their quote evidence changes, and the report regenerated.

**Resolution:** all 960 active candidates were checked against both the stored Goodreads
book title and cached work-quotes title. Fifteen mismatches were corrected; all 13 corrected
works with quotes received new blind Terra-medium classifications. The two correctly resolved
works with no Goodreads quotes remain unlabelable, and their stale evidence was not retained.
The post-integration audit reports 938 ordinary passes, 8 documented title-alias passes,
0 mismatches, 0 unavailable work pages, and 0 duplicate work-ID assignments. Fourteen
candidates remain unmapped rather than being attached to an unverified work.

## 2. Correct weighted trend centering

**Status:** complete — corrected and regenerated 2026-08-20.

The audited `analysis/build_report.py::trend` used the unweighted mean of represented years
while its denominator was weighted by annual labelled-book counts. The correction uses the
count-weighted mean year in both numerator and denominator.

**Acceptance criteria:** add a regression test with deliberately unequal annual sample sizes,
match a direct weighted calculation, and regenerate `trend.html`, `trend_local.html`, and
`raw_data/report_data.json`.

**Resolution:** the mean year is now weighted by annual labelled-book count in both terms.
The unequal-sample regression test matches a direct weighted calculation. On the corrected
1996–2025 data the slope is +1.11897 percentage points per year (`z = 5.34176`,
`p = 9.20e-08`, `n = 443`); the report displays the rounded +1.1% per year.

## 3. Replace Wald confidence intervals

**Status:** complete — Wilson intervals shipped 2026-08-20.

The audited report calculated `p ± 1.96 × SE`. This collapsed to a zero-width interval at
0% or 100%, including years with only one labelled book. It has been replaced with Wilson
score intervals suitable for small samples.

**Acceptance criteria:** 0/1 and 1/1 produce wide non-degenerate intervals, ordinary annual
rows match a trusted implementation, and the regenerated HTML labels the interval method.

**Resolution:** report periods now carry two-sided 95% Wilson score intervals computed in
Python, and the table labels them `95% Wilson CI`. Regression tests cover 0/1, 1/1, and
10/25; the one-observation extremes are 0–79.3% and 20.7–100%, respectively.
