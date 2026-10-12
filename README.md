# curated-word-list

3–5 letter crossword answers with recent clues, filtered from the
[xd crossword corpus](https://xd.saul.pw/).

## Files

| File | Size | Notes |
| --- | --- | --- |
| `clues_filtered.json` | 3.83 MB | word → array of 15 clue strings |
| `clues_filtered.json.gz` | 1.55 MB | gzip -9 of the above, identical contents |
| `filter_clues.py` | — | the script that builds them from `clues.tsv` |

## Format

A single JSON object, keys sorted, mapping an uppercase answer to its clues
(most recent first):

```json
{"GRASP":["Clutch firmly","Comprehend","Grab hold of","Wrap one's head around"]}
```

## Filter rules

Built from 9,981,797 corpus rows; 1,054,602 survived filtering.

- answer is `A-Z` only — drops numeric and mixed answers from meta-puzzle sources
- answer length is 3, 4, or 5
- clue's puzzle year is within the last 7 years (>= 2019)
- puzzle-internal clues are discarded (see below)
- exact-duplicate clue text per word is deduped
- a word needs **at least 30 unique clue texts** to qualify — distinct clues,
  not raw appearances
- the 15 most recent clues are kept

Result: **9,073 unique words** and 136,095 clues — 1,643 words of length 3,
3,465 of length 4, 3,965 of length 5. Every word carries a full 15 clues.

### Why 30

The threshold is a popularity filter, and it does not cut evenly across
lengths: short crosswordese is clued far more often than ordinary 5-letter
words. At a 150-clue minimum only 196 five-letter words survive — too thin to
fill a 5×5 grid without heavy repetition. At 30 the pool is 3,965. Measured
counts at 2019+ with all filters applied:

| min clues | total | len 3 | len 4 | len 5 |
| ---: | ---: | ---: | ---: | ---: |
| 150 | 1,599 | 680 | 723 | 196 |
| 100 | 2,914 | 963 | 1,369 | 582 |
| 60 | 5,213 | 1,287 | 2,343 | 1,583 |
| **30** | **9,073** | **1,643** | **3,465** | **3,965** |
| 15 | 12,705 | 2,007 | 4,388 | 6,310 |
| 10 | 14,517 | 2,181 | 4,890 | 7,446 |

### Puzzle-internal clues

18,954 clues were discarded for only making sense with the original grid in
front of you:

- cross-references — `71-Across`, `See 12-Down`, `27-Downs`
- self-reference — "Like this clue", "What the eight longest answers share",
  "hidden in this clue", "This clue number x 2"
- references to the puzzle around it — `[See title]`, `[Clued elsewhere]`
- typographic callouts — circled, shaded, starred, capitalized letters and
  squares; "a hint to this puzzle's theme"

The rules target self-*reference*, not crossword vocabulary. Words like `row`,
`column`, `square`, `letter` and `answer` are overwhelmingly innocent in clue
text — "Wall calendar row", "Budget column", "Diez squared", "Wrong answer" —
so banning them outright would discard hundreds of good clues. A digit must sit
beside "across" or "down", which keeps "Chowed down (on)", "Dam across the
Nile" and "Tony of 10 Downing St."; "starred" only trips next to
letters/squares/clues/answers, which keeps "Jacobson who starred in 'A League
of Their Own'"; and "each" is scoped to answers and clues, which keeps "One of
five in each line of a sonnet".

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
