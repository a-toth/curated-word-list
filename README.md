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

Built from 9,981,797 corpus rows; 749,051 survived filtering.

- answer is `A-Z` only — drops numeric and mixed answers from meta-puzzle sources
- answer length is 3, 4, or 5
- clue's puzzle year is within the last 4 years (>= 2022)
- puzzle-internal clues are discarded (see below)
- exact-duplicate clue text per word is deduped
- at most 8 clues per word, keeping the 8 most recent
- words left with fewer than 4 clues are dropped

Result: **16,766 unique words** and 126,023 clues — 2,430 words of length 3,
5,511 of length 4, 8,825 of length 5. 13,798 words (82%) sit at the 8-clue cap.

### Puzzle-internal clues

11,866 clues were discarded for only making sense with the original grid in
front of you: cross-references like `71-Across` and `See 12-Down`, "a hint to
this puzzle's theme", circled / shaded / starred letters and squares, and "the
ends of three Down answers".

A digit must sit beside "across" or "down" for the rule to fire. Every clue that
mentions those words without a number is ordinary English — "Chowed down (on)",
"Dam across the Nile" — and is kept. "Starred" likewise only trips next to
letters, squares, clues or answers, so "Jacobson who starred in 'A League of
Their Own'" survives.

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
