"""Goodreads resolution + quote extraction for the booktense study.

Resolution is tiered and every result carries the method and a confidence flag,
because taking the first search hit silently returns study guides and box sets
(this produced a completely wrong coverage result during development).

Fetching is cached to disk: classification can be re-run without re-crawling,
and a rate-limit interruption never loses work.
"""
import re, os, time, html, hashlib, unicodedata, urllib.request, urllib.error, urllib.parse

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
CACHE = os.path.join(os.path.dirname(__file__), "..", "raw_data", "cache")
DELAY = 40.0          # measured: bucket ~9 requests, refills ~6min => ~90 req/hr.
                      # Pacing at the refill rate avoids tripping at all.
_last = [0.0]

# Goodreads returns these instead of the novel if you trust the first hit.
# Deliberately narrow. Broad words like "volume", "collection" and "book club"
# appear in real novel titles -- they rejected "Dragons of a Lost Star: The War
# of Souls Volume Two" and "The Southern Book Club's Guide to Slaying Vampires".
JUNK = re.compile(r'study guide|sparknotes|cliffs?notes|conversation starters|'
                  r'quicklet|\btrivia\b|summary (and|&|of)|'
                  r'\ba? ?(study|reading) guide\b|box(ed) set|omnibus', re.I)


class RateLimited(Exception):
    """Goodreads served a bot challenge (HTTP 202 / empty body)."""


class TitleMismatch(Exception):
    """A resolved book or quote-work page does not match the requested title."""


def _pause(seconds, reason):
    """Sleep in observable increments so unattended crawls remain monitorable."""
    remaining = seconds
    while remaining > 0:
        nap = min(remaining, 10)
        time.sleep(nap)
        remaining -= nap
        if remaining > 0:
            print(f"      {reason} -- {remaining:.0f}s remaining", flush=True)


def _get(url, retries=3):
    """GET with retry on transient network faults.

    A bare read-timeout killed a 28-book pilot at book 17; long unattended runs
    must survive one flaky socket.
    """
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            resp = urllib.request.urlopen(req, timeout=45)
            return resp.status, resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, ""
        except Exception as e:                      # timeout, reset, DNS blip
            last = e
            time.sleep(10 * (attempt + 1))
    raise last


def fetch(url, use_cache=True, patient=False, cooldown=75, max_waits=25):
    """GET with disk cache and polite spacing.

    The Goodreads limit is on request VOLUME over a long window, not on interval:
    a run tripped after 9 requests at 20s spacing and after 4 at 30s spacing,
    because the budget carried over from a previous run. Spacing alone cannot
    avoid it, so long runs must wait the budget out.

    patient=True sleeps `cooldown` and retries (up to max_waits) instead of
    raising, so an unattended crawl survives throttling. patient=False raises
    RateLimited immediately -- correct for interactive/short runs.
    """
    key = hashlib.sha1(url.encode()).hexdigest()[:20]
    path = os.path.join(CACHE, key + ".html")
    if use_cache and os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return fh.read()

    for attempt in range(max_waits + 1):
        wait = DELAY - (time.time() - _last[0])
        if wait > 0:
            _pause(wait, "pacing Goodreads request")
        status, body = _get(url)
        _last[0] = time.time()

        # A 202 with an empty body is the bot challenge. Treating it as "no data"
        # silently converts throttling into fake zero-measurements -- never do that.
        if status == 202 or len(body) < 5000:
            if not patient or attempt == max_waits:
                raise RateLimited(f"HTTP {status}, {len(body)} bytes: {url}")
            # Probe-based recovery, not blind backoff. A 7-min linear backoff
            # slept through windows in which the service had already recovered:
            # one pilot did 1 book in 41 minutes while ad-hoc requests to the
            # same host returned 200 immediately. Short naps + frequent cheap
            # retries track the token bucket instead of guessing at it.
            nap = min(cooldown * (1.4 ** attempt), 600)
            print(f"      throttled -- retry in {nap:.0f}s "
                  f"(attempt {attempt+1}/{max_waits})", flush=True)
            _pause(nap, "throttle recovery")
            continue

        os.makedirs(CACHE, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(body)
        return body
    raise RateLimited(f"exhausted {max_waits} waits: {url}")


# ---------------------------------------------------------------- page parsing

def _ratings(page):
    m = re.search(r'([\d,]+)\s*ratings', page)
    return int(m.group(1).replace(",", "")) if m else 0


def _page_title(page):
    m = re.search(r'(?is)<h1[^>]*>(.*?)</h1>', page)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", m.group(1)))).strip() if m else ""


def _work_page_title(page):
    """Title named by a Goodreads work-quotes page."""
    title = _page_title(page)
    return re.sub(r"\s+Quotes\s*$", "", title, flags=re.I).strip()


def _page_author(page):
    m = re.search(r'(?is)<span[^>]*class="ContributorLink__name"[^>]*>(.*?)</span>', page)
    if not m:
        m = re.search(r'(?is)class="authorName"[^>]*>\s*<span[^>]*>(.*?)</span>', page)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", m.group(1)))).strip() if m else ""


def _pub_year(page):
    yrs = [int(y) for y in re.findall(r'(?:First published|Published)[^<]{0,40}?(1[89]\d\d|20\d\d)', page)]
    return min(yrs) if yrs else None


def _work_id(page):
    m = re.search(r'/work/quotes/(\d+)', page)
    return m.group(1) if m else None


# ------------------------------------------------------------------ resolution

def _txt(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", s))).strip()


def _candidates(search_html, limit=6):
    """Parse search-result rows -> [{id,title,author,ratings}].

    Search results are <tr itemtype="schema.org/Book"> rows carrying title,
    author and ratings count inline, so candidates can be ranked WITHOUT
    fetching each book page.

    The previous version regexed loosely over /book/show/ links and matched the
    cover-image anchor rather than the title, so it returned whatever ranked
    first -- for "Cannery Row" that is a "Summary & Study Guide", whose author
    parses as "BookRags". That silently produced author_mismatch, ratings=0 and
    a false zero-quote result. Parse the row, not the page.
    """
    out = []
    for row in re.findall(r'(?is)<tr[^>]*itemtype="http://schema\.org/Book".*?</tr>', search_html):
        m = re.search(r'(?is)<a class="bookTitle"[^>]*href="/book/show/(\d+)[^"]*".*?'
                      r"<span[^>]*itemprop='name'[^>]*>(.*?)</span>", row)
        if not m:
            continue
        bid, title = m.group(1), _txt(m.group(2))
        am = re.search(r"(?is)<span itemprop='author'.*?<span itemprop='name'[^>]*>(.*?)</span>", row)
        if not am:
            am = re.search(r'(?is)class="authorName"[^>]*>\s*<span[^>]*>(.*?)</span>', row)
        author = _txt(am.group(1)) if am else ""
        rm = re.search(r'([\d,]+)\s*ratings?', row)
        ratings = int(rm.group(1).replace(",", "")) if rm else 0
        out.append(dict(id=bid, title=title, author=author, ratings=ratings))
        if len(out) >= limit:
            break
    return out


def _title_key(t):
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode()
    t = t.replace("&", " and ")
    t = re.sub(r"\s*\([^)]*\)\s*$", "", t)                 # drop "(Series, #2)"
    t = re.sub(r"^(the|a|an)\s+", "", t.strip().lower())
    return " ".join(re.sub(r"[^a-z0-9 ]", "", t).split())


_COLLECTION = re.compile(r'\b(?:box(?:ed)? set|omnibus|collection|anthology|\d+ books?)\b', re.I)
_EDITION_TAIL = re.compile(
    r'^(?::|-)?\s*(?:a novel\b|the novel\b|by\b|paperback\b|hardback\b|hardcover\b|'
    r'mass market\b|reissue\b|\d+(?:st|nd|rd|th)? edition\b)', re.I)


def title_match(want_title, got_title, want_author=None):
    """Return (matches, normalized score, reason) for a resolved Goodreads title.

    Matching is intentionally conservative. Punctuation, leading articles, subtitles, and
    seller-style edition tails are accepted. Collections and merely related same-author books
    are rejected even when they contain the requested title.
    """
    want = _title_key(want_title)
    got = _title_key(got_title)
    if not want or not got:
        return False, 0.0, "missing_title"
    if want == got:
        return True, 1.0, "exact"
    if _COLLECTION.search(got_title or ""):
        return False, 0.0, "collection_or_multiwork"
    if got.startswith(want):
        tail = got[len(want):].strip()
        if not tail or _EDITION_TAIL.match(tail):
            return True, len(want) / len(got), "subtitle_or_edition"
        raw_want = re.sub(r"^(?:the|a|an)\s+", "", (want_title or "").strip(), flags=re.I)
        raw_got = re.sub(r"^(?:the|a|an)\s+", "", (got_title or "").strip(), flags=re.I)
        # Normalization erases the punctuation that marks a genuine subtitle.
        if re.match(rf'(?i)^{re.escape(raw_want)}\s*:', raw_got):
            return True, len(want) / len(got), "subtitle"
        # Search sometimes returns bookseller-style edition titles. Accept only when the
        # appended material names the requested author; this keeps "Title / Other Title"
        # omnibuses from passing merely because the first work matches.
        surnames = _surnames(want_author)
        if surnames and any(surname in _norm_name(tail) for surname in surnames):
            return True, len(want) / len(got), "seller_listing"
    return False, 0.0, f"title_mismatch({got_title!r})"


def _rank(cands, want_title, want_author):
    """Order candidates by a BLEND of title match and popularity.

    Neither signal can be allowed to dominate outright:

    * Ratings alone picks the wrong book -- for "Cannery Row" the Steinbeck
      omnibuses all match the author and carry real rating counts.
    * Title alone also picks the wrong book -- Vonnegut's "Slapstick" is really
      "Slapstick, or Lonesome No More!" (45,837 ratings), which only scores as a
      prefix match, so a stray edition titled exactly "Slapstick" with ONE
      rating beat it and produced a false zero.

    So: score = 3*title_score + log10(ratings), which lets a well-known
    subtitled edition outrank an obscure exact-title match, while an exact match
    still beats a merely-related title at comparable popularity.
    """
    import math
    surs = _surnames(want_author)
    want = _title_key(want_title)
    scored = []
    for c in cands:
        if JUNK.search(c["title"]):
            continue
        if surs and not any(s in _norm_name(c["author"]) for s in surs):
            continue
        k = _title_key(c["title"])
        if k == want:
            tscore = 2
        elif len(want) >= 4 and (k.startswith(want) or want.startswith(k)):
            tscore = 1
        elif len(want) >= 4 and want in k:
            tscore = 0
        else:
            continue                                       # unrelated title
        scored.append((3 * tscore + math.log10(c["ratings"] + 1), c))
    scored.sort(key=lambda x: -x[0])
    return [c for _, c in scored]


def _norm_name(s):
    """Fold punctuation so O'Hara/OHara and Le Carre/le Carre compare equal."""
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


_SUFFIX = re.compile(r'^(jr|sr|ii|iii|iv|v|vi|phd|md)$', re.I)


def _surnames(author):
    """All plausible surnames in an author field.

    Post45 author fields are often compound ("Margaret Weis and Tracy Hickman",
    9.1% of the sample) and sometimes suffixed. Taking the last token yields
    "iv" for "W.E.B. Griffin and William E. Butterworth IV", which matches
    nothing and fails the book outright. Return every conjunct's surname and
    accept a candidate if ANY of them matches.
    """
    out = set()
    for part in re.split(r'\s+(?:and|with|&)\s+|,', author or ""):
        toks = [t for t in re.sub(r"[^A-Za-z' .-]", "", part).split()
                if len(t) > 1 and not _SUFFIX.match(t.strip("."))]
        if toks:
            out.add(_norm_name(toks[-1]))
    return {s for s in out if s}


def _surname(author):
    """Primary surname (first-listed author) -- kept for the search query."""
    ss = _surnames(author)
    return sorted(ss)[0] if ss else ""


def _score(book_page, want_title, want_author, want_year):
    """Validation checks -> (ok, notes). Cheap, but catches the real failure modes."""
    notes = []
    ok = True
    title_ok, _, title_note = title_match(want_title, _page_title(book_page), want_author)
    if not title_ok:
        ok = False
        notes.append(title_note)
    surs = _surnames(want_author)
    got = _norm_name(_page_author(book_page))
    if surs and not any(s in got for s in surs):
        ok = False
        notes.append(f"author_mismatch({_page_author(book_page)!r})")
    py = _pub_year(book_page)
    if want_year and py and abs(py - int(want_year)) > 3:
        notes.append(f"year_off({py}vs{want_year})")   # reissues are common; warn only
    if _ratings(book_page) < 20:
        notes.append("low_ratings")
    return ok, ";".join(notes)


MAX_CANDIDATES = 3      # request budget matters far more than exhaustive search


def _record(page, book_id, method, want_title, want_author, want_year):
    ok, notes = _score(page, want_title, want_author, want_year)
    return dict(book_id=book_id, work_id=_work_id(page), ratings=_ratings(page),
                gr_title=_page_title(page), gr_author=_page_author(page),
                gr_year=_pub_year(page), method=method, notes=notes,
                confidence="high" if ok and not notes else ("medium" if ok else "review"))


def _validate_work_record(record, want_title, patient):
    """Confirm the resolved work-quotes page names the requested work."""
    if not record.get("work_id") or record.get("confidence") == "review":
        return record
    page = fetch(f"https://www.goodreads.com/work/quotes/{record['work_id']}", patient=patient)
    work_title = _work_page_title(page)
    ok, _, note = title_match(want_title, work_title)
    if not ok:
        record["confidence"] = "review"
        record["notes"] = ";".join(
            item for item in (record.get("notes"), f"work_{note}") if item)
    return record


def resolve(title, author, year=None, isbn=None, patient=False):
    """Return dict with book_id, work_id, method, confidence and validation notes.

    Tier 1: ISBN exact -- Goodreads REDIRECTS an exact-ISBN search straight to the
            book page, so this costs a single request. Only useful ~1970+; ISBN
            fill in the Post45 frame is 11% for the 1930s, 79% by the 1980s.
    Tier 2: title+author search, junk-filtered, top MAX_CANDIDATES by ratings.
    Tier 3: give up -> confidence 'review', handle manually.
    """
    if isbn:
        clean = re.sub(r"[^0-9Xx]", "", str(isbn))
        if len(clean) in (10, 13):
            page = fetch("https://www.goodreads.com/search?q=" + clean, patient=patient)
            if "/work/quotes/" in page:                    # redirected to the book page
                m = re.search(r'/book/show/(\d+)', page)
                rec = _record(page, m.group(1) if m else None, "isbn", title, author, year)
                rec = _validate_work_record(rec, title, patient)
                if rec["work_id"] and rec["confidence"] != "review":
                    return rec

    page = fetch("https://www.goodreads.com/search?q=" + urllib.parse.quote(f"{title} {author}"),
                 patient=patient)
    if "/work/quotes/" in page:                            # single-hit redirect here too
        m = re.search(r'/book/show/(\d+)', page)
        rec = _record(page, m.group(1) if m else None, "title_author_direct",
                      title, author, year)
        rec = _validate_work_record(rec, title, patient)
        if rec["work_id"] and rec["confidence"] != "review":
            return rec

    ranked = _rank(_candidates(page, 30), title, author)
    if not ranked or ranked[0]["ratings"] < 50:
        # Compound author strings make poor queries: searching
        # "Dragons of a Lost Star Margaret Weis and Tracy Hickman" returns one
        # weak hit. Retry with the first-listed author only. Kept as a FALLBACK
        # so the primary query's cache keys stay valid.
        first = re.split(r'\s+(?:and|with|&)\s+', author or "")[0].strip()
        if first and first != (author or "").strip():
            alt = fetch("https://www.goodreads.com/search?q=" +
                        urllib.parse.quote(f"{title} {first}"), patient=patient)
            alt_ranked = _rank(_candidates(alt, 30), title, author)
            if alt_ranked and (not ranked or alt_ranked[0]["ratings"] > ranked[0]["ratings"]):
                ranked = alt_ranked

    # Rank candidates from the search page itself, then fetch ONE book page for
    # the winner (the work_id lives only there). Costs 2 requests, not 1+N.
    #
    # Scan the WHOLE result list. Goodreads ranks study guides and omnibuses
    # above the novel: for "Cannery Row John Steinbeck" the actual book is
    # result #7 (160,450 ratings) behind five study guides. A 6-candidate
    # window missed it entirely and recorded a false zero.
    for c in ranked[:MAX_CANDIDATES]:
        rec = _record(fetch(f"https://www.goodreads.com/book/show/{c['id']}", patient=patient),
                      c["id"], "title_author", title, author, year)
        rec = _validate_work_record(rec, title, patient)
        if rec["work_id"] and rec["confidence"] != "review":
            if not rec["ratings"]:
                rec["ratings"] = c["ratings"]     # book-page parse can miss it
            return rec
    return dict(book_id=None, work_id=None, ratings=0, gr_title="", gr_author="",
                gr_year=None, method="failed", notes="no_candidate", confidence="review")


# --------------------------------------------------------------------- quotes

def _norm(s):
    return re.sub(r"[^a-z0-9 ]", "", s.lower())


# Goodreads work pages aggregate quotes across ALL editions, including
# translations -- a Portuguese passage turned up in an English thriller during
# the pilot. Tense classification on translated text is meaningless here.
_EN = set("the a an and or but of to in that it is was were be been has have had "
          "he she they i you his her their not with as for on at by from this "
          "would could said says are am we me him them there what when who".split())


def is_english(text, min_ratio=0.18):
    # Script check FIRST. The stopword ratio only sees [a-zA-Z] words, so pure
    # Cyrillic/Greek/CJK text yields zero words, hits the "too short to judge"
    # escape hatch and was returning True -- letting translated editions through
    # the very filter meant to stop them.
    letters = re.findall(r"[^\W\d_]", text, re.UNICODE)
    if letters:
        latin = sum(1 for c in letters if c.isascii())
        if latin / len(letters) < 0.6:
            return False
    w = re.findall(r"[a-zA-Z']+", text.lower())
    if len(w) < 6:
        return True                      # too short to judge; fragment filter handles it
    return sum(1 for x in w if x in _EN) / len(w) >= min_ratio


def _shingles(text, k=6):
    w = _norm(text).split()
    return {tuple(w[i:i + k]) for i in range(max(1, len(w) - k + 1))} if len(w) >= k else set()


def _is_dup(text, seen_shingles, thresh=0.45):
    """Overlap-based dedupe.

    Prefix containment is not enough: Goodreads lists a long quote and an inner
    fragment of it as separate entries, and the shared text is often mid-string.
    The pilot missed exactly that case, which would inflate agreement counts.
    """
    sh = _shingles(text)
    if not sh:
        return False
    for prev in seen_shingles:
        if not prev:
            continue
        if len(sh & prev) / min(len(sh), len(prev)) >= thresh:
            return True
    return False


def quotes(work_id, max_pages=4, patient=False, expected_title=None):
    """Fetch and dedupe quotes. Returns (deduplicated quotes, raw count).

    When expected_title is supplied, page 1 must name that work. This catches bad Goodreads
    work links even when the edition/book page itself had the right title.
    """
    seen, out, raw_count = [], [], 0
    for p in range(1, max_pages + 1):
        url = f"https://www.goodreads.com/work/quotes/{work_id}"
        if p > 1:
            url += f"?page={p}"
        page = fetch(url, patient=patient)
        if p == 1 and expected_title:
            work_title = _work_page_title(page)
            title_ok, _, title_note = title_match(expected_title, work_title)
            if not title_ok:
                raise TitleMismatch(
                    f"requested {expected_title!r}, work {work_id} is {work_title!r}: {title_note}")
        found = 0
        for i, blk in enumerate(re.findall(r'(?is)<div class="quoteText">(.*?)</div>', page)):
            blk = re.split(r'(?is)<br\s*/?>\s*<span class="authorOrTitle"', blk)[0]
            t = re.sub(r"\s+", " ", html.unescape(re.sub(r"(?is)<[^>]+>", "", blk))).strip()
            t = re.sub(r"\s*―.*$", "", t).strip()
            # Goodreads wraps every pull-quote in ONE pair of curly quotes. Strip
            # that pair only -- str.strip('“”"') removed EVERY leading/trailing
            # mark, which ate the opening quote of any excerpt beginning with
            # dialogue ("You wired the kid," Truemann said -> You wired the kid,"
            # Truemann said). Unmarked dialogue then fails the quotation-majority
            # test and is promoted to event-narration, contaminating the tense
            # count with character speech.
            m = re.match(r'^[“"](.*)[”"]$', t, re.S)
            if m:
                t = m.group(1)
            t = t.strip()
            if len(t.split()) < 6:
                continue
            found += 1
            raw_count += 1
            if not is_english(t):                     # translated editions leak in
                continue
            if _is_dup(t, seen):                      # overlapping excerpts of one passage
                continue
            seen.append(_shingles(t))
            out.append((p, i, url, t))
        if found < 30:      # page not full -> no more pages exist
            break
    return out, raw_count
