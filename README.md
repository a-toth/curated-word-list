# curated-word-list

3–5 letter crossword answers with recent clues, filtered from the
[xd crossword corpus](https://xd.saul.pw/).

## Files

| File | Size | Notes |
| --- | --- | --- |
| `clues_filtered.json` | 4.73 MB | word → array of clue strings |
| `clues_filtered.json.gz` | 1.92 MB | gzip -9 of the above, identical contents |

## Format

A single JSON object, keys sorted, mapping an uppercase answer to its clues
(most recent first):

```json
{"OBOE":["Cousin of the clarinet","Instrument used to tune an orchestra"]}
```

## Filter rules

Built from 9,981,797 corpus rows; 1,476,527 survived filtering.

- answer is `A-Z` only — drops numeric and mixed answers from meta-puzzle sources
- answer length is 3, 4, or 5
- clue's puzzle year is within the last 12 years (>= 2014)
- exact-duplicate clue text per word is deduped
- at most 8 clues per word, keeping the most recent
- words left with fewer than 3 clues are dropped

Result: **21,543 unique words** and 158,193 clues — 2,896 words of length 3,
6,874 of length 4, 11,773 of length 5. 17,380 words (81%) sit at the 8-clue cap.

## Serving the `.gz`

If you serve the pre-compressed file directly, send both
`Content-Encoding: gzip` and `Content-Type: application/json`, or the browser
will hand your code raw gzip bytes. Most CDNs compress the plain `.json` on the
fly anyway, so the plain file is often the simpler choice.

## Source and licensing

Clue text originates with the individual puzzle publishers and reaches this
repo via the xd corpus, which carries its own terms. No license file has been
chosen for this repository yet — review the upstream terms before reuse.
