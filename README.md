# curated-word-list

3–5 letter crossword answers with recent clues, filtered from the
[xd crossword corpus](https://xd.saul.pw/).

## Files

| File | Size | Notes |
| --- | --- | --- |
| `clues_filtered.json` | 4.94 MB | word → array of clue strings |
| `clues_filtered.json.gz` | 2.04 MB | gzip -9 of the above, identical contents |

## Format

A single JSON object, keys sorted, mapping an uppercase answer to its clues
(most recent first):

```json
{"OBOE":["Cousin of the clarinet","Instrument used to tune an orchestra"]}
```

## Filter rules

Built from 9,981,797 corpus rows; 2,383,709 survived filtering.

- answer is `A-Z` only — drops numeric and mixed answers from meta-puzzle sources
- answer length is 3, 4, or 5
- clue's puzzle year is within the last 30 years (>= 1996)
- exact-duplicate clue text per word is deduped
- at most 6 clues per word, keeping the most recent

Result: **36,220 unique words** — 4,501 of length 3, 11,379 of length 4,
20,340 of length 5.

## Serving the `.gz`

If you serve the pre-compressed file directly, send both
`Content-Encoding: gzip` and `Content-Type: application/json`, or the browser
will hand your code raw gzip bytes. Most CDNs compress the plain `.json` on the
fly anyway (Brotli lands around 1.54 MB), so the plain file is often the simpler
choice.

## Source and licensing

Clue text originates with the individual puzzle publishers and reaches this
repo via the xd corpus, which carries its own terms. No license file has been
chosen for this repository yet — review the upstream terms before reuse.
