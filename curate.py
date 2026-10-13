#!/usr/bin/env python3
"""Curate clues_filtered.json down to words casual solvers actually know.

The daily Mini is too hard because of the word data, not the generator.
"Appears often in crosswords" mostly means a word has friendly, vowel-heavy
letters, not that anyone knows it: OGEE, ASTI, EDUCE and ANDSO all clear the
appearance threshold in clues_filtered.json. This script applies the gates
that appearance counts cannot.

Two gates, in that order, because they measure different things:

  LEGITIMACY  Spread the Wordlist scores an entry up to 55, where 50 means
              "clean" - a real entry, not necessarily an exciting or
              familiar one. ESSEN, GENOA and PADUA all score 50. So a 50
              floor is necessary but nowhere near sufficient.

  FAMILIARITY General English frequency (wordfreq's Zipf scale) is what
              actually separates CAKE from ALIA. This is the gate that
              makes the puzzles easy; the Zipf floor is the main dial.

Everything here happens offline. The browser receives a pool that is already
approved, so no frequency data ships to players and solving stays fast.

Output is frozen and versioned - clues_clean_v1.json, clues_clean_v2.json -
because the puzzle is a pure function of (day, word pool). Overwriting a
published version would change days people have already played.

The schema is unchanged from clues_filtered.json ({"WORD": ["clue", ...]}),
so the page only needs its WORD_DATA_URL swapped.

Usage:
  python3 curate.py --zipf 3.5 --clues 3 --out clues_clean_v1.json
"""
import argparse
import json
import random
import re
import sys
import unicodedata
from collections import defaultdict

MIN_LEN = 3
MAX_LEN = 5
LETTERS_ONLY = re.compile(r'^[A-Z]+$')
SAMPLE_SIZE = 25          # cut words shown per step in the report
NEAR_BAND = 0.25          # Zipf distance either side of the floor to review


# ---------------------------------------------------------------------------
# Input loading
# ---------------------------------------------------------------------------

def load_scored_list(path):
    """Read a Spread the Wordlist .dict/.txt: one "ENTRY;score" per line.

    Returns {raw_entry: score}. Raw entries are kept exactly as written,
    because the surface-forms edition carries the casing, spaces and periods
    that tell a proper noun or an abbreviation from an ordinary word.
    """
    entries = {}
    with open(path, 'r', encoding='utf-8-sig', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            entry, _, score = line.partition(';')
            entry = entry.strip()
            if not entry:
                continue
            try:
                value = int(score.strip()) if score.strip() else 50
            except ValueError:
                continue
            # Keep the best score if an entry is listed more than once.
            if value > entries.get(entry, -1):
                entries[entry] = value
    return entries


def normalize(entry):
    """Fold a surface form to the A-Z uppercase key the clue list uses."""
    stripped = unicodedata.normalize('NFKD', entry)
    stripped = ''.join(c for c in stripped if not unicodedata.combining(c))
    return re.sub(r'[^A-Za-z]', '', stripped).upper()


def load_manual_list(path):
    """Read allowlist.txt / blocklist.txt: one word per line, # comments."""
    if not path:
        return set()
    words = set()
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.split('#', 1)[0].strip().upper()
                if line:
                    words.add(line)
    except FileNotFoundError:
        return set()
    return words


def load_frequencies(path):
    """Read a fallback frequency table: "word<TAB>zipf" per line."""
    freqs = {}
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            parts = line.split()
            if len(parts) < 2:
                continue
            try:
                freqs[parts[0].strip().upper()] = float(parts[1])
            except ValueError:
                continue
    return freqs


def frequency_lookup(freq_file):
    """Return zipf(word) -> float, from wordfreq or a supplied table."""
    if freq_file:
        table = load_frequencies(freq_file)
        return lambda w: table.get(w, 0.0)
    try:
        from wordfreq import zipf_frequency
    except ImportError:
        sys.exit(
            "wordfreq is not installed, and no --freq-file was given.\n"
            "  pip install wordfreq\n"
            "or supply a table of 'word<TAB>zipf' lines with --freq-file."
        )
    return lambda w: zipf_frequency(w.lower(), 'en')


# ---------------------------------------------------------------------------
# Step 4: what the surface forms and clue text say about a word
# ---------------------------------------------------------------------------

# Clues that will not age well, or that arrived broken.
#
# A narrow --years window keeps clue text current, but "current" is exactly
# what goes stale: a clue pegged to someone's age, to "this year", or to a
# running season is wrong by the next one. The puzzle is generated years
# ahead of the day it is played, so these have to go.
TIME_BOUND = re.compile(
    r'''
      \b(?:will\s+(?:turn|be)|turns|turned)\s+\d+
    | \b(?:this|last|next)\s+(?:year|season|month|week|summer|winter)\b
    | \b(?:currently|recently|nowadays|these\s+days|to\s+date|so\s+far)\b
    | \b(?:current|latest|newest|upcoming|recent)\s+
        (?:season|series|film|movie|album|book|show|host|champion|winner)\b
    | \bas\s+of\s+(?:20\d\d|today)\b
    | \bsince\s+20[12]\d\b
    ''',
    re.I | re.X,
)

# "****" and friends: censored or placeholder text from the source corpus.
CENSORED = re.compile(r'^[\W_]+$')

ABBR_IN_CLUE = re.compile(
    r'\b(?:abbr|abbrev|acronym|initialism|init)\b\.?|'
    r'\bfor\s+short\b|\bin\s+brief\b|\bbriefly\b|\bon\s+a\s+(?:form|label)\b',
    re.I,
)


def classify(word, surfaces):
    """Why `word` is not an ordinary English word, or None if it is.

    Judged from the surface forms Spread the Wordlist lists for it. A word
    is cleared as soon as ONE surface form looks ordinary, so DELTA survives
    on the lowercase "delta" even though "Delta" is also listed.
    """
    if not surfaces:
        return None

    reasons = set()
    for surface in surfaces:
        body = surface.strip()
        if not body:
            continue
        if ' ' in body or '-' in body:
            # AGAME, TEEUP, INAPP: a partial phrase jammed into one entry.
            reasons.add('multiword')
            continue
        if '.' in body:
            reasons.add('abbreviation')
            continue
        letters = [c for c in body if c.isalpha()]
        if len(letters) > 1 and all(c.isupper() for c in letters):
            # USPS, ATVS. Plurals of acronyms land here too, via "ATVs".
            reasons.add('abbreviation')
            continue
        if body[:1].isupper() and body[1:].lower() == body[1:]:
            reasons.add('proper noun')
            continue
        return None          # an ordinary lowercase surface form: cleared

    if not reasons:
        return None
    for reason in ('multiword', 'abbreviation', 'proper noun'):
        if reason in reasons:
            return reason
    return None


def looks_abbreviated(word, clues):
    """True when most of a word's clues flag it as an abbreviation."""
    if not clues:
        return False
    hits = sum(1 for c in clues if ABBR_IN_CLUE.search(c))
    return hits * 2 > len(clues)


# ---------------------------------------------------------------------------
# Step 6: clue cleanup
# ---------------------------------------------------------------------------

# Capitalized words that carry no trivia burden: a solver does not need to
# "know" a nationality, a weekday or a brand-free place adjective.
COMMON_CAPS = {
    'I', 'A', 'AN', 'THE', 'GOD', 'ENGLISH', 'FRENCH', 'SPANISH', 'ITALIAN',
    'GERMAN', 'GREEK', 'LATIN', 'IRISH', 'DUTCH', 'ROMAN', 'CHINESE',
    'JAPANESE', 'RUSSIAN', 'AMERICAN', 'BRITISH', 'MEXICAN', 'CANADIAN',
    'INDIAN', 'AFRICAN', 'EUROPEAN', 'ASIAN', 'SCOTTISH', 'SWEDISH',
    'HAWAIIAN', 'MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY',
    'SATURDAY', 'SUNDAY', 'JANUARY', 'FEBRUARY', 'MARCH', 'APRIL', 'MAY',
    'JUNE', 'JULY', 'AUGUST', 'SEPTEMBER', 'OCTOBER', 'NOVEMBER', 'DECEMBER',
    'EARTH', 'MR', 'MRS', 'MS', 'DR', 'ST', 'US', 'USA', 'UK', 'TV', 'OK',
    'EAST', 'WEST', 'NORTH', 'SOUTH', 'NEW', 'OLD',
}

WORD_TOKEN = re.compile(r"[A-Za-z][A-Za-z'’]*")
OPENS_QUOTED = re.compile(r'^\s*["“]')
BLANK = re.compile(r'_{2,}')
SUFFIXES = ('S', 'ES', 'D', 'ED', 'ING', 'ER', 'ERS', 'LY', 'IER', 'IEST')


def contains_answer(word, clue):
    """True if the clue gives away the answer, in any obvious form."""
    for token in WORD_TOKEN.findall(clue):
        bare = re.sub(r"[^A-Za-z]", '', token).upper()
        if bare == word:
            return True
        if bare.startswith(word) and bare[len(word):] in SUFFIXES:
            return True
        if word.startswith(bare) and len(bare) >= 3 and word[len(bare):] in SUFFIXES:
            return True
    return False


def proper_names(clue):
    """Capitalized tokens a solver must recognise.

    The first word of a clue is skipped: clues are sentence-capitalized, so
    its case says nothing. A clue that OPENS on a quotation mark is the
    exception - there the first word sits inside a title or a line of
    dialogue ('"Stay" singer Lisa'), and its capital is real.
    """
    tokens = WORD_TOKEN.findall(clue)
    start = 0 if OPENS_QUOTED.match(clue) else 1
    names = []
    for token in tokens[start:]:
        bare = re.sub(r"[^A-Za-z]", '', token)
        if bare[:1].isupper() and bare.upper() not in COMMON_CAPS:
            names.append(bare)
    return names


def clue_verdict(word, clue, strict=False):
    """(drop_reason, penalty) for one clue.

    `strict` raises the bar to "no proper names at all". It is used for words
    re-admitted by --proper-zipf, which earn their place only on a clue that
    stands without a second name to recognise: EARTH on "Our planet", IOWA on
    "Corn Belt state", PETER on "Fizzle (out)". RYAN and TIM have no such
    clue and drop out entirely, which is the right answer for both.

    drop_reason is None when the clue survives. penalty orders survivors:
    0 is a plain definition, 1 carries a name the solver has to know. It
    keeps trivia out of clues[0] without discarding a word that has nothing
    plainer available.
    """
    if CENSORED.match(clue):
        return 'censored or placeholder', 0
    if TIME_BOUND.search(clue):
        return 'time-bound', 0
    if contains_answer(word, clue):
        return 'gives away the answer', 0
    if '?' in clue:
        # Wordplay. Unfair in a mini with few crossings.
        return 'wordplay (?)', 0
    names = proper_names(clue)
    if names and strict:
        return 'trivia (name needed)', 0
    if len(names) >= 2:
        # "Stay" singer Lisa. Two names is a trivia question, not a definition.
        return 'trivia (proper names)', 0
    if BLANK.search(clue):
        # Fill-in-the-blank. Easy in a mini even when it carries one name
        # ("___ Jones"), because the phrase does the work, not recall.
        return None, 0
    return None, (1 if names else 0)


def clean_clues(word, clues, keep, strict=False):
    """Surviving clues, plainest first, capped at `keep`.

    Ordering is (penalty, original index, length). The original index is
    already most-used-first in clues_filtered.json - staple clues come first,
    ordered by how often they were used - so this honours "most used first"
    while keeping a name-bearing clue out of slot 0.
    """
    kept, dropped = [], []
    for index, clue in enumerate(clues):
        reason, penalty = clue_verdict(word, clue, strict)
        if reason:
            dropped.append((clue, reason))
        else:
            kept.append((penalty, index, len(clue), clue))
    kept.sort()
    return [k[3] for k in (kept if keep <= 0 else kept[:keep])], dropped


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def curate(args):
    report = []

    def say(line=''):
        print(line)
        report.append(line)

    def sample(words):
        words = sorted(words)
        if len(words) <= SAMPLE_SIZE:
            return ', '.join(words)
        picked = random.Random(0).sample(words, SAMPLE_SIZE)
        return ', '.join(sorted(picked)) + f", ... (+{len(words) - SAMPLE_SIZE:,} more)"

    def by_length(words):
        counts = defaultdict(int)
        for w in words:
            counts[len(w)] += 1
        return '  '.join(f"len {L}: {counts[L]:,}" for L in sorted(counts))

    with open(args.source, 'r', encoding='utf-8') as f:
        raw = json.load(f)

    say("=" * 72)
    say("Mini word-list curation")
    say("=" * 72)
    say(f"Source:          {args.source}  ({len(raw):,} words)")
    say(f"Zipf floor:      {args.zipf}")
    say(f"Score floor:     {args.min_score}")
    say(f"Clues per word:  {args.clues_per_word}")
    say()

    # --- 1. Normalize -------------------------------------------------------
    pool = {}
    cut_shape = []
    for word, clues in raw.items():
        key = word.strip().upper()
        if not (MIN_LEN <= len(key) <= MAX_LEN) or not LETTERS_ONLY.match(key):
            cut_shape.append(word)
            continue
        texts = [c.strip() for c in clues if c and c.strip()]
        if not texts:
            cut_shape.append(word)
            continue
        pool[key] = texts
    say(f"1. Normalize (A-Z, {MIN_LEN}-{MAX_LEN} letters, >=1 clue)")
    say(f"   kept {len(pool):,}   cut {len(cut_shape):,}")
    say(f"   {by_length(pool)}")
    if cut_shape:
        say(f"   cut: {sample(cut_shape)}")
    say()

    # --- 2. Legitimacy gate -------------------------------------------------
    scored = load_scored_list(args.wordlist)
    best_score = {}
    for entry, value in scored.items():
        key = normalize(entry)
        if key and value > best_score.get(key, -1):
            best_score[key] = value

    allow = load_manual_list(args.allowlist)
    block = load_manual_list(args.blocklist)

    cut_score, cut_unlisted = [], []
    after_score = {}
    for word, clues in pool.items():
        if word in allow:
            after_score[word] = clues
            continue
        score = best_score.get(word)
        if score is None:
            cut_unlisted.append(word)
        elif score < args.min_score:
            cut_score.append(word)
        else:
            after_score[word] = clues
    say(f"2. Legitimacy gate (Spread the Wordlist score >= {args.min_score})")
    say(f"   wordlist entries: {len(scored):,}  ->  {len(best_score):,} A-Z keys")
    say(f"   kept {len(after_score):,}   cut {len(cut_score) + len(cut_unlisted):,} "
        f"({len(cut_score):,} scored low, {len(cut_unlisted):,} not listed)")
    say(f"   {by_length(after_score)}")
    if cut_score:
        say(f"   cut, low score: {sample(cut_score)}")
    if cut_unlisted:
        say(f"   cut, not listed: {sample(cut_unlisted)}")
    say()

    # --- 3. Familiarity gate ------------------------------------------------
    zipf = frequency_lookup(args.freq_file)
    freqs = {w: zipf(w) for w in after_score}

    cut_rare = []
    after_freq = {}
    for word, clues in after_score.items():
        if word in allow or freqs[word] >= args.zipf:
            after_freq[word] = clues
        else:
            cut_rare.append(word)
    say(f"3. Familiarity gate (Zipf >= {args.zipf})")
    say(f"   kept {len(after_freq):,}   cut {len(cut_rare):,}")
    say(f"   {by_length(after_freq)}")
    if cut_rare:
        say(f"   cut: {sample(cut_rare)}")
    say()

    # --- 4. Drop non-words --------------------------------------------------
    surfaces = defaultdict(list)
    if args.surface:
        for entry in load_scored_list(args.surface):
            key = normalize(entry)
            if key:
                surfaces[key].append(entry)

    cuts_by_reason = defaultdict(list)
    kept_proper = []
    after_shape = {}
    for word, clues in after_freq.items():
        if word in allow:
            after_shape[word] = clues
            continue
        reason = classify(word, surfaces.get(word, []))
        if reason == 'proper noun' and freqs[word] >= args.proper_zipf:
            # EARTH, APRIL, INDIA, PARIS, OHIO. A proper noun this common in
            # ordinary English is easier than most of the word list; dropping
            # it on grammar alone costs real words for nothing.
            kept_proper.append(word)
            reason = None
        if reason is None and looks_abbreviated(word, clues):
            reason = 'abbreviation'
        if reason:
            cuts_by_reason[reason].append(word)
        else:
            after_shape[word] = clues
    dropped_here = sum(len(v) for v in cuts_by_reason.values())
    say("4. Drop non-words (proper nouns, abbreviations, multi-word partials)")
    if not args.surface:
        say("   no --surface file given: judged from clue text only")
    say(f"   kept {len(after_shape):,}   cut {dropped_here:,}")
    say(f"   {by_length(after_shape)}")
    for reason in sorted(cuts_by_reason):
        words = cuts_by_reason[reason]
        say(f"   cut, {reason} ({len(words):,}): {sample(words)}")
    if kept_proper:
        say(f"   kept, proper noun above Zipf {args.proper_zipf} "
            f"({len(kept_proper):,}): {sample(kept_proper)}")
    say()

    # --- 5. Manual lists ----------------------------------------------------
    forced_in = sorted(w for w in allow if w in pool and w not in after_shape)
    for word in forced_in:
        after_shape[word] = pool[word]
    forced_out = sorted(w for w in after_shape if w in block)
    for word in forced_out:
        del after_shape[word]
    missing = sorted(w for w in allow if w not in pool)
    say("5. Manual lists")
    say(f"   allowlist {len(allow):,}   blocklist {len(block):,}")
    say(f"   forced in {len(forced_in):,}: {sample(forced_in) if forced_in else '-'}")
    say(f"   forced out {len(forced_out):,}: {sample(forced_out) if forced_out else '-'}")
    if missing:
        say(f"   allowlisted but absent from source ({len(missing):,}): {sample(missing)}")
    say(f"   kept {len(after_shape):,}")
    say()

    # --- 6. Clue cleanup ----------------------------------------------------
    final = {}
    cut_no_clue = []
    clue_cuts = defaultdict(int)
    kept_clues = 0
    strict_words = set(kept_proper)
    for word, clues in after_shape.items():
        keep, dropped = clean_clues(word, clues, args.clues_per_word,
                                    strict=word in strict_words)
        for _text, reason in dropped:
            clue_cuts[reason] += 1
        if not keep:
            cut_no_clue.append(word)
            continue
        final[word] = keep
        kept_clues += len(keep)
    cap = 'no cap' if args.clues_per_word <= 0 else f"keep {args.clues_per_word}"
    say(f"6. Clue cleanup ({cap} plainest per word)")
    say(f"   kept {len(final):,} words, {kept_clues:,} clues   "
        f"cut {len(cut_no_clue):,} words with no clue left")
    for reason in sorted(clue_cuts, key=lambda r: -clue_cuts[r]):
        say(f"   clues dropped, {reason}: {clue_cuts[reason]:,}")
    dropped_proper = sorted(w for w in cut_no_clue if w in strict_words)
    if dropped_proper:
        say(f"   of those, proper nouns with no name-free clue "
            f"({len(dropped_proper):,}): {sample(dropped_proper)}")
    if cut_no_clue:
        say(f"   cut, no usable clue: {sample(cut_no_clue)}")
    say()

    # --- 7. Write -----------------------------------------------------------
    with open(args.out, 'w', encoding='utf-8') as out:
        json.dump(final, out, indent=None, separators=(',', ':'), sort_keys=True)

    if args.scores_out:
        tiers = {w: round(freqs.get(w, 0.0), 2) for w in final}
        with open(args.scores_out, 'w', encoding='utf-8') as out:
            json.dump(tiers, out, indent=None, separators=(',', ':'), sort_keys=True)

    say("=" * 72)
    say("Result")
    say("=" * 72)
    say(f"   {len(raw):,} words in  ->  {len(final):,} words out "
        f"({len(final) / max(len(raw), 1):.0%})")
    say(f"   {by_length(final)}")
    say(f"   {kept_clues:,} clues, {kept_clues / max(len(final), 1):.1f} per word")
    say()

    # Enough words to fill? The solver gives up after 4,000 nodes per attempt.
    counts = defaultdict(int)
    for w in final:
        counts[len(w)] += 1
    for L in (4, 5):
        if counts[L] < 1000:
            say(f"   WARNING: only {counts[L]:,} words of length {L}. "
                f"The 5x5 fill needs thousands, not hundreds.")
    say()

    rng = random.Random(1)
    for L in (3, 4, 5):
        words = sorted(w for w in final if len(w) == L)
        if not words:
            continue
        say(f"Survivors, random sample of {L}-letter words")
        for word in sorted(rng.sample(words, min(15, len(words)))):
            say(f"   {word}  {freqs.get(word, 0.0):.2f}  {final[word][0]}")
        say()

    near = sorted(
        ((freqs[w], w) for w in after_score
         if abs(freqs[w] - args.zipf) <= NEAR_BAND),
        reverse=True,
    )
    say(f"At the threshold (Zipf {args.zipf - NEAR_BAND:.2f}-{args.zipf + NEAR_BAND:.2f}) "
        f"- review these to tune --zipf")
    say(f"   kept:    {', '.join(w for z, w in near if w in final)[:900]}")
    say(f"   dropped: {', '.join(w for z, w in near if w not in final)[:900]}")
    say()
    say(f"Wrote {args.out}")
    if args.scores_out:
        say(f"Wrote {args.scores_out}")

    if args.report:
        with open(args.report, 'w', encoding='utf-8') as out:
            out.write('\n'.join(report) + '\n')
        print(f"Wrote {args.report}")


def main():
    p = argparse.ArgumentParser(
        description="Curate the crossword clue list down to words casual "
                    "solvers know.")
    p.add_argument('--source', default='clues_full.json',
                   help='the full pool to curate (default: clues_full.json). '
                        'NOT clues_filtered.json - that is the served copy of '
                        'this script\'s own output.')
    p.add_argument('--wordlist', default='spreadthewordlist.dict',
                   help='Spread the Wordlist scored list, "ENTRY;score" lines')
    p.add_argument('--surface', default='spreadthewordlist_forms.dict',
                   help='Spread the Wordlist surface-forms edition')
    p.add_argument('--zipf', type=float, default=3.5,
                   help='Zipf frequency floor (default: 3.5)')
    p.add_argument('--min-score', type=int, default=50,
                   help='Spread the Wordlist score floor (default: 50)')
    p.add_argument('--clues', dest='clues_per_word', type=int, default=12,
                   help='clues kept per word, 0 for no cap (default: 12). '
                        'Clues are ordered plainest-first either way, so a '
                        'generator can take clues[0] or pick at random.')
    p.add_argument('--proper-zipf', type=float, default=99.0,
                   help='keep proper nouns at or above this Zipf, instead of '
                        'dropping them all (default: 99, i.e. drop them all)')
    p.add_argument('--allowlist', default='allowlist.txt')
    p.add_argument('--blocklist', default='blocklist.txt')
    p.add_argument('--freq-file',
                   help='fallback "word<TAB>zipf" table instead of wordfreq')
    p.add_argument('--out', default='clues_clean_v1.json')
    p.add_argument('--report', help='report path (default: <out>.report.txt)')
    p.add_argument('--scores-out',
                   help='also write {"WORD": zipf} for generator weighting')
    args = p.parse_args()
    if not args.report:
        args.report = args.out.rsplit('.json', 1)[0] + '.report.txt'
    curate(args)


if __name__ == '__main__':
    main()
