# curated-word-list

3–5 letter crossword answers with recent clues, filtered from the
[xd crossword corpus](https://xd.saul.pw/).

## Files

| File | Size | Notes |
| --- | --- | --- |
| `clues_filtered.json` | 3.60 MB | word → array of clue strings |
| `clues_filtered.json.gz` | 1.47 MB | gzip -9 of the above, identical contents |
| `filter_clues.py` | — | the script that builds them from `clues.tsv` |

## Format

A single JSON object, keys sorted, mapping an uppercase answer to its clues
(most recent first):

```json
{"GRASP":["Clutch","Fully understand","Hold firmly"]}
```

## Filter rules

Built from 9,981,797 corpus rows; 748,740 survived filtering.

- answer is `A-Z` only — drops numeric and mixed answers from meta-puzzle sources
- answer length is 3, 4, or 5
- clue's puzzle year is within the last 4 years (>= 2022)
- puzzle-internal clues are discarded (see below)
- exact-duplicate clue text per word is deduped
- at most 8 clues per word, keeping the 8 most recent
- words left with fewer than 4 clues are dropped

Result: **16,765 unique words** and 126,016 clues — 2,430 words of length 3,
5,510 of length 4, 8,825 of length 5. 13,797 words (82%) sit at the 8-clue cap.

### Puzzle-internal clues

12,210 clues were discarded for only making sense with the original grid in
front of you:

- cross-references — `71-Across`, `See 12-Down`
- self-reference — "Like this clue", "What the eight longest answers share",
  "hidden in this clue", "This clue number x 2"
- typographic callouts — circled, shaded, starred, capitalized letters and
  squares; "a hint to this puzzle's theme"

The rules target self-*reference*, not crossword vocabulary. Words like `row`,
`column`, `square`, `letter` and `answer` are overwhelmingly innocent in clue
text — "Wall calendar row", "Budget column", "Diez squared", "Wrong answer" —
so banning them outright would discard hundreds of good clues. A digit must sit
beside "across" or "down", which keeps "Chowed down (on)" and "Dam across the
Nile"; "starred" only trips next to letters/squares/clues/answers, which keeps
"Jacobson who starred in 'A League of Their Own'"; and "each" is scoped to
answers and clues, which keeps "One of five in each line of a sonnet".

Filtering happens per source row, before the per-word cap, so a word that loses
a clue backfills with its next-best real one.

## Serving the `.gz`

If you serve the pre-compressed file directly, send both
`Content-Encoding: gzip` and `Content-Type: application/json`, or the browser
will hand your code raw gzip bytes. Most CDNs compress the plain `.json` on the
fly anyway, so the plain file is often the simpler choice.

## Source and licensing

Clue text originates with the individual puzzle publishers and reaches this
repo via the xd corpus, which carries its own terms. No license file has been
chosen for this repository yet — review the upstream terms before reuse.
