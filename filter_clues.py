#!/usr/bin/env python3
"""Filter the xd-clues TSV corpus down to a curated word->clues JSON.

Two windows do two different jobs:

  ELIGIBILITY (last 10 years) decides which words make the list and
  supplies their settled clues. A word qualifies if at least one clue
  text accounts for >= 5% of its appearances in the window; EVERY clue
  clearing 5% is kept, so a word may contribute several.

  CONTENT (last 1 year) tops each word up with what is current: the 8
  most recent distinct clues, skipping any already kept above.

Rules:
  * answer must be pure A-Z letters, length 3-5
  * clues that reference puzzle-internal context are discarded
  * >= MIN_APPEARANCES appearances within the eligibility window
  * at least one clue text at >= 5% of those appearances
  * output = the 5 most-used staple clues, then up to 8 recent
    distinct clues (13 per word at most)

A shorter --years window is the dial for clue freshness: a 10-year window
drags in dated and abstract clues, and narrowing it to 4 costs almost no words
provided --min-appearances drops to match (a 4-year window simply holds fewer
appearances per word).

The staple rule is a SECOND popularity filter on top of MIN_APPEARANCES: it
asks that a word own a settled, often-repeated clue. That measures how
established a word is in crossword grids, not whether a solver knows it, and
it costs 12,363 qualifying words down to 8,423. When the downstream gate is
general English frequency (see curate.py), set --min-staple-uses 1 to switch
it off and let frequency do the judging instead.

Usage: python3 filter_clues.py <input.tsv> <output.json> [min_appearances]
       python3 filter_clues.py clues.tsv clues_wide.json --min-appearances 10 \
                               --min-staple-uses 1 --max-staples 20
"""
import argparse
import sys
import json
import re
import datetime
from collections import defaultdict, Counter

MIN_LEN = 3
MAX_LEN = 5
ELIGIBILITY_YEARS = 10
CONTENT_YEARS = 1
MIN_APPEARANCES = 30
MIN_STAPLE_USES = 10   # a clue is a "staple" once used this many times in the window
MAX_STAPLES = 5        # keep only the most-used staples; the rest add no familiarity
MAX_FRESH_CLUES = 8
LETTERS_ONLY = re.compile(r'^[A-Z]+$')

# Clues that only make sense with the original grid in front of you.
#
# These rules target self-REFERENCE, not crossword vocabulary. Words like
# "row", "column", "square", "letter", "title" and "answer" are
# overwhelmingly innocent in clue text ("Wall calendar row", "Budget
# column", "Diez squared", "'New Girl' title character"), so banning them
# outright would discard hundreds of good clues.
NUM = r'(?:two|three|four|five|six|seven|eight|nine|ten|\d+)'
UNIT = r'(?:answers?|entr(?:y|ies)|clues?)'

PUZZLE_REF = re.compile(
    r'''
    # --- grid cross-references ---
    # A digit must sit beside across/down, so "Chowed down (on)" and "Dam
    # across the Nile" survive. Inflections matter: "Nasty 27-Downs",
    # "Was 18-Acrossed". "Tony of 10 Downing St." is untouched.
      \b\d+\s*[-/ ]?\s*(?:acrosse?[sd]?|downe?[sd]?)\b
    | \b(?:acrosse?[sd]?|downe?[sd]?)\s+''' + UNIT + r'''

    # --- pointing at itself or its neighbours ---
    | \bthis\s+(?:clue|answer|entry|puzzle|grid)\b
    | \bthese\s+clues\b
    | \bthis\s+list\s+of\s+clues\b
    | \bpuzzle'?s\b
    | \btoday'?s\s+(?:puzzle|theme)\b

    # --- "the four longest answers" and friends ---
    | \b''' + NUM + r'''\s+(?:longest|shortest)\s+''' + UNIT + r'''
    | \bthe\s+(?:other|remaining|preceding|following)\s+''' + UNIT + r'''
    | \bthe\s+answers?\s+to\s+the\b
    | \b(?:the|these)\s+clues\b
    # "each" is scoped to answers/clues, so "One of five in each line of
    # a sonnet" survives.
    | \b(?:each|every)\s+(?:of\s+the\s+)?''' + UNIT + r'''
    | \bends?\s+of\s+(?:the\s+)?''' + NUM + r'''\s+''' + UNIT + r'''

    # --- pointing outside the clue entirely ---
    | \bsee\s+(?:the\s+)?(?:note|notepad|title|instructions)\b
    | \bclued\s+elsewhere\b

    # --- typographic callouts to other squares ---
    # "starred" only trips beside letters/squares/clues/answers, so
    # "Jacobson who starred in 'A League of Their Own'" survives.
    | \b(?:circled|shaded|starred|highlighted|capitalized|italicized|boldfaced)\s+
        (?:letters?|squares?|clues?|answers?|entries|entry|boxes)\b
    | \btheme\s+(?:of\s+this|answers?|entr(?:y|ies))\b
    | \bhint\s+to\b
    | \bclue\s+(?:number|list)\b
    | \bin\s+the\s+clue\b
    ''',
    re.I | re.X,
)


def current_year():
    return datetime.datetime.now().year


def process(input_path, output_path, min_appearances=MIN_APPEARANCES,
            min_staple_uses=MIN_STAPLE_USES, max_staples=MAX_STAPLES,
            max_fresh=MAX_FRESH_CLUES, eligibility_years=ELIGIBILITY_YEARS):
    year_now = current_year()
    eligibility_from = year_now - eligibility_years
    content_from = year_now - CONTENT_YEARS

    counts = defaultdict(Counter)   # word -> clue -> appearances in window
    recent = defaultdict(dict)      # word -> clue -> most recent year

    total_rows = 0
    dropped_puzzle_ref = 0
    in_window = 0

    with open(input_path, 'r', encoding='utf-8', errors='replace') as f:
        f.readline()  # skip header row

        for line in f:
            total_rows += 1
            line = line.rstrip('\n')
            if not line:
                continue

            parts = line.split('\t', 3)
            if len(parts) < 4:
                continue

            _pubid, year_str, answer, clue = parts

            try:
                year = int(year_str.strip())
            except ValueError:
                continue
            if year < eligibility_from:
                continue

            answer = answer.strip().upper()
            if not (MIN_LEN <= len(answer) <= MAX_LEN):
                continue
            if not LETTERS_ONLY.match(answer):
                continue

            clue = clue.strip()
            if not clue:
                continue

            if PUZZLE_REF.search(clue):
                dropped_puzzle_ref += 1
                continue

            in_window += 1
            counts[answer][clue] += 1
            if year >= content_from and year > recent[answer].get(clue, -1):
                recent[answer][clue] = year

    result = {}
    dropped_thin = 0
    dropped_flat = 0
    staple_total = 0
    fresh_total = 0
    no_fresh = 0

    for word, clue_counts in counts.items():
        appearances = sum(clue_counts.values())
        if appearances < min_appearances:
            dropped_thin += 1
            continue

        # Every clue holding at least MIN_SHARE of the window, most used
        # first; clue text breaks ties so the output is deterministic.
        staples = [c for c, n in sorted(
            clue_counts.items(), key=lambda cn: (-cn[1], cn[0]),
        ) if n >= min_staple_uses][:max_staples]

        if not staples:
            dropped_flat += 1
            continue

        seen = set(staples)
        # Most recent first; clue text breaks ties inside a year.
        fresh = [c for c, _y in sorted(
            ((c, y) for c, y in recent[word].items() if c not in seen),
            key=lambda cy: (-cy[1], cy[0]),
        )][:max_fresh]

        staple_total += len(staples)
        fresh_total += len(fresh)
        if not fresh:
            no_fresh += 1
        result[word] = staples + fresh

    with open(output_path, 'w', encoding='utf-8') as out:
        json.dump(result, out, indent=None, separators=(',', ':'), sort_keys=True)

    by_len = defaultdict(int)
    for w in result:
        by_len[len(w)] += 1

    print(f"Total data rows scanned:      {total_rows:,}")
    print(f"Dropped, puzzle-internal:     {dropped_puzzle_ref:,}")
    print(f"Rows inside {eligibility_years}-year window:  {in_window:,}")
    print(f"Words seen:                   {len(counts):,}")
    print(f"Dropped (<{min_appearances} appearances):   {dropped_thin:,}")
    print(f"Dropped (no staple clue):     {dropped_flat:,}")
    print(f"Unique words in output:       {len(result):,}")
    for L in sorted(by_len):
        print(f"  length {L}: {by_len[L]:,} words")
    print(f"Clues in output:              {staple_total + fresh_total:,}")
    print(f"  staples (>= {min_staple_uses} uses):           {staple_total:,}")
    print(f"  fresh (last {CONTENT_YEARS} yr, max {max_fresh}):  {fresh_total:,}")
    print(f"Words with no fresh clue:     {no_fresh:,}")
    print(f"Eligibility window: >= {eligibility_from}   Content window: >= {content_from}")
    print(f"Output written to: {output_path}")


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('input', help='the xd clues.tsv corpus')
    p.add_argument('output', help='word -> clues JSON to write')
    p.add_argument('min_appearances_pos', nargs='?', type=int,
                   help=argparse.SUPPRESS)   # backwards-compatible 3rd argument
    p.add_argument('--min-appearances', type=int, default=MIN_APPEARANCES)
    p.add_argument('--min-staple-uses', type=int, default=MIN_STAPLE_USES,
                   help='uses before a clue counts as settled; 1 switches the '
                        f'staple rule off (default: {MIN_STAPLE_USES})')
    p.add_argument('--max-staples', type=int, default=MAX_STAPLES)
    p.add_argument('--max-fresh', type=int, default=MAX_FRESH_CLUES)
    p.add_argument('--years', type=int, default=ELIGIBILITY_YEARS,
                   help='clue window in years; clues older than this are not '
                        'collected at all, and a word with nothing inside it '
                        f'drops out (default: {ELIGIBILITY_YEARS})')
    a = p.parse_args()
    process(a.input, a.output,
            a.min_appearances_pos if a.min_appearances_pos is not None
            else a.min_appearances,
            a.min_staple_uses, a.max_staples, a.max_fresh, a.years)
