#!/usr/bin/env python3
"""Filter the xd-clues TSV corpus down to a curated word->clues JSON.

Rules:
  * answer must be pure A-Z letters, length 3-5
  * clue's puzzle year must be within the last 4 years
  * clues that reference puzzle-internal context are discarded
  * exact-duplicate clue text for the same word is deduped
  * cap at 8 clues per word, keeping the 8 most recent
  * drop any word left with fewer than 4 clues

Usage: python3 filter_clues_v4.py <input.tsv> <output.json>
"""
import sys
import json
import re
import datetime
from collections import defaultdict

MIN_LEN = 3
MAX_LEN = 5
MAX_CLUES_PER_WORD = 8
MIN_CLUES_PER_WORD = 4
YEARS_BACK = 4
LETTERS_ONLY = re.compile(r'^[A-Z]+$')

# Clues that only make sense with the original grid in front of you.
#
# These rules target self-REFERENCE, not crossword vocabulary. Words like
# "row", "column", "square", "letter" and "answer" are overwhelmingly
# innocent in clue text ("Wall calendar row", "Budget column", "Diez
# squared", "Wrong answer"), so banning them outright would discard
# hundreds of good clues. Likewise a digit must sit beside across/down --
# "Chowed down (on)" and "Dam across the Nile" must survive.
NUM = r'(?:two|three|four|five|six|seven|eight|nine|ten|\d+)'
UNIT = r'(?:answers?|entr(?:y|ies)|clues?)'

PUZZLE_REF = re.compile(
    r'''
    # --- grid cross-references ---
      \b\d+\s*[-/ ]?\s*(?:acrosse?s?|downs?)\b   # 71-Across, 3 Down, 27-Downs
    | \b(?:acrosse?s?|downs?)\s+''' + UNIT + r'''

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
    | \b(?:each|every)\s+(?:of\s+the\s+)?''' + UNIT + r'''
    | \bends?\s+of\s+(?:the\s+)?''' + NUM + r'''\s+''' + UNIT + r'''

    # --- typographic callouts to other squares ---
    | \b(?:circled|shaded|starred|highlighted|capitalized|italicized|boldfaced)\s+
        (?:letters?|squares?|clues?|answers?|entries|entry|boxes)\b
    | \btheme\s+(?:of\s+this|answers?|entr(?:y|ies))\b
    | \bhint\s+to\b
    | \bsee\s+(?:the\s+)?(?:note|notepad|title|instructions)\b
    | \bclued\s+elsewhere\b
    | \bclue\s+(?:number|list)\b
    | \bin\s+the\s+clue\b
    ''',
    re.I | re.X,
)


def current_year():
    return datetime.datetime.now().year


def process(input_path, output_path):
    cutoff_year = current_year() - YEARS_BACK

    entries = defaultdict(list)
    seen_clues = defaultdict(set)

    total_rows = 0
    kept_rows = 0
    dropped_puzzle_ref = 0

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
            if year < cutoff_year:
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

            if clue in seen_clues[answer]:
                continue
            seen_clues[answer].add(clue)

            entries[answer].append((year, clue))
            kept_rows += 1

    result = {}
    dropped_thin = 0
    for word, clue_list in entries.items():
        if len(clue_list) < MIN_CLUES_PER_WORD:
            dropped_thin += 1
            continue
        clue_list.sort(key=lambda yc: yc[0], reverse=True)
        result[word] = [c for _year, c in clue_list[:MAX_CLUES_PER_WORD]]

    with open(output_path, 'w', encoding='utf-8') as out:
        json.dump(result, out, indent=None, separators=(',', ':'), sort_keys=True)

    by_len = defaultdict(int)
    clue_total = 0
    at_cap = 0
    for w, cl in result.items():
        by_len[len(w)] += 1
        clue_total += len(cl)
        if len(cl) == MAX_CLUES_PER_WORD:
            at_cap += 1

    print(f"Total data rows scanned:    {total_rows:,}")
    print(f"Dropped, puzzle-internal:   {dropped_puzzle_ref:,}")
    print(f"Rows kept after filters:    {kept_rows:,}")
    print(f"Words seen:                 {len(entries):,}")
    print(f"Dropped (<{MIN_CLUES_PER_WORD} clues):         {dropped_thin:,}")
    print(f"Unique words in output:     {len(result):,}")
    for L in sorted(by_len):
        print(f"  length {L}: {by_len[L]:,} words")
    print(f"Clues in output:            {clue_total:,}")
    print(f"Words at the {MAX_CLUES_PER_WORD}-clue cap:     {at_cap:,}")
    print(f"Cutoff year: >= {cutoff_year}")
    print(f"Output written to: {output_path}")


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python3 filter_clues_v4.py <input.tsv> <output.json>")
        sys.exit(1)
    process(sys.argv[1], sys.argv[2])
