# curated-word-list

Word and puzzle data for word-game generators.

- **Crossword clues** — 3–5 letter answers with recent clues, filtered from the
  [xd crossword corpus](https://xd.saul.pw/).
- **Strands** — 730 daily word-search puzzles and a 59,551-word dictionary.

Every `.json` has a matching `.json.gz` (gzip -9, identical contents).

---

# Crossword clues

## Files

| File | Size | Notes |
| --- | --- | --- |
**`clues_filtered.json` is the file the game fetches.** It currently holds the
curated Mini pool, byte-identical to `clues_clean_v1.json`.

| File | Size | Notes |
| --- | --- | --- |
| `clues_filtered.json` | 204 KB | **what the game serves** — a copy of the current `clues_clean_vN.json` |
| `clues_filtered.json.gz` | 84 KB | gzip -9 of the above, identical contents |
| `clues_clean_v2.json` | 0.96 MB | **current version** — 5,595 words, ~9 clues each |
| `clues_clean_v2.json.gz` | 385 KB | gzip -9 of the above, identical contents |
| `scores_v2.json` | — | word -> Zipf frequency, for weighting the fill |
| `clues_clean_v1.json` | 204 KB | frozen: 3,578 words, 3 clues each |
| `curate.py` | — | the script that builds `clues_clean_vN.json` |
| `clues_recent.json` | 3.6 MB | the two-bucket pool — `curate.py`'s input since v2 |
| `clues_recent.json.gz` | 1.4 MB | gzip -9 of that pool |
| `clues_full.json` | 2.08 MB | the pool `curate.py` used for v1 |
| `filter_clues.py` | — | the script that builds both pools from `clues.tsv` |
| `clues_legacy.json` | 3.33 MB | an older generation, kept to fall back to |
| `clues_legacy.json.gz` | 1.33 MB | gzip -9 of the legacy list |
| `filter_clues_legacy.py` | — | the script that built the legacy list |

### The generations

`clues_legacy.json` -> `clues_full.json` -> `clues_recent.json` ->
`clues_clean_vN.json`. Each is kept rather than replaced, because the Mini is a
pure function of (day, word pool) and going back has to stay possible.

### Switching what is served

Copy the version you want over `clues_filtered.json` (and its `.gz`) and push.
The game needs no edit — its `WORD_DATA_URL` points at that filename. To go
back to the full pool:

```sh
cp clues_clean_v1.json clues_filtered.json
cp clues_clean_v1.json.gz clues_filtered.json.gz
```

Swapping the served file changes the puzzle for every day, including days
already played. That is the cost of pinning by filename instead of by version;
point the page at `clues_clean_vN.json` directly if that ever matters more than
the convenience.

## The full pool: `clues_full.json`

`curate.py`'s input, and what the game served until the curated list replaced
it. Built to favour entries a solver will recognise, on the theory that a word
is easy when its clue is one they have met many times before.

- 10-year eligibility window (>= 2016)
- answer is `A-Z` only, length 3-5
- word must appear at least 30 times in the window
- every clue used at least 10 times in the window is a "staple"; a word
  needs at least one, and the 5 most-used are kept
- up to 8 more distinct clues from the last year (>= 2025)
- puzzle-internal clues are discarded throughout (see below)

**8,423 words, 86,883 clues** — 1,567 of length 3, 3,336 of length 4,
3,520 of length 5. Staples come first and are ordered most-used first, so
`clues[0]` is the single most familiar clue for that word; everything
after the staples is recent flavour.

```
ERA  ->  Historical period (185x) | Historic period | Historic time |
         Notable time | Pitching stat | "I'm in my villain ___!" | ...
```

### Why absolute use count, not a percentage

An earlier cut required one clue to hold some percentage of a word's
appearances. That selects against easy words: ERA is clued 4,528 times, so
"Historical period" is only 4.1% of them despite 185 uses, while an
obscure word clued 9 times out of 88 clears 10%. The percentage rule threw
out ERA, AREA, ORE, ALE, ATE, ERR, ETA, ERIE and kept RENU, EHOW, SKORT.
Counting actual uses measures what a solver has seen.

## Curated list for the Mini

`clues_filtered.json` selects for words that appear often in crosswords, which
is not the same as words people know. OGEE, ASTI, EDUCE, SNEE and ANDSO all
clear its appearance threshold; across a year of generated puzzles the most
repeated entries were ESSE, SSNS, EENIE, STDS and SNEE. `curate.py` applies the
two gates an appearance count cannot.

**Legitimacy** — [Spread the Wordlist](https://www.spreadthewordlist.com/)
scores an entry up to 55, where 50 means "clean": a real entry, not necessarily
a familiar one. ESSEN, GENOA and PADUA all score 50, so this gate is necessary
and nowhere near sufficient.

**Familiarity** — general English frequency, via `wordfreq`'s Zipf scale. This
is the gate that does the work, and `--zipf` is the main dial.

### Two upstream constraints, and what they cost

v1 curated `clues_full.json`, which caps out at 8,423 words. Lowering `--zipf`
to widen the pool trades quality for size and runs out of road around 4,600.
Both real constraints were upstream, in `filter_clues.py`.

**The staple rule.** A word had to own one clue used 10 or more times. That is
a second popularity filter on top of the appearance threshold, and it measures
how established a word is in crossword grids, not whether a solver knows it.
It cost 12,363 qualifying words down to 8,423, cutting ordinary words that
simply never settled on a stock clue. `--min-staple-uses 1` switches it off and
lets frequency judge instead, which gives more words at a **higher** quality
bar:

| Zipf | staple rule on | staple rule off |
| ---: | ---: | ---: |
| 3.0 | 3,710 | 5,138 |
| **2.8** | 4,140 | **5,766** |
| 2.5 | 4,663 | 6,637 |

**Which clues each word keeps.** The pool is built from two buckets: the **5
most-used clues over 10 years**, then the **5 most recent from the past year**,
so every word carries its heavy hitters plus what is current. Earlier builds
took 20 of each, which dragged in clues used only once — 31% of the total, and
the source of every rambling 160-character clue. Capping each bucket at 5 is
what keeps the clue list from outweighing the words.

### Clue count and staleness

The page picks a clue at random, so the number a word keeps controls how often
a repeated word repeats its clue. v1 kept 3 and showed the same clue on
**33.5%** of repeat pairs. v2 keeps up to 10, and that falls to **12.4%**
— REST appears 39 times over two years with 10 different clues.

This is also why the page should keep choosing at random rather than switching
to `clues[0]`: every clue has passed the quality gate, so a random pick is safe
and the variety is free.

Two clue rules guard against ageing. **Time-bound** clues go ("Bob who will
turn 85 in May", "this season", "as of 2024") because puzzles are generated
years before they are played — that rule alone removed DYLAN, whose every clue
was pegged to something. **Censored or placeholder** text from the source
corpus goes too; BUTCH arrived with `****` as its most-used clue.

### Building a version

```sh
# the pool: 5 most-used clues over 10 years, plus 5 most recent from the
# last year, for every word appearing at least 10 times
python3 filter_clues.py clues.tsv clues_recent.json \
        --years 10 --min-appearances 10 --min-staple-uses 1 \
        --max-staples 5 --max-fresh 5

# then curate it
python3 curate.py --source clues_recent.json --zipf 2.8 --clues 0 \
                  --proper-zipf 4.0 --out clues_clean_v2.json \
                  --scores-out scores_v2.json
```

Needs `wordfreq` (`pip install wordfreq`) and both Spread the Wordlist
downloads — `spreadthewordlist.dict` and `spreadthewordlist_forms.dict`. They
are gitignored, not vendored; see Licensing below. `--freq-file` takes a plain
`word<TAB>zipf` table instead of `wordfreq`.

Every run prints a report and writes it beside the output
(`clues_clean_v1.report.txt`): counts and cut samples per step, survivor
samples with their frequencies, and the words sitting either side of the
threshold, which is what you read to pick the next `--zipf`.

**Output files are frozen.** The puzzle is a pure function of (day, word
pool), so overwriting a published version silently rewrites days people have
already played. Build `clues_clean_v2.json` instead and repoint the page.

### The pipeline

1. **Normalize** — uppercase, `A-Z`, 3-5 letters, at least one clue. 3-letter
   words are kept even though the current grids only use 4s and 5s.
2. **Legitimacy** — Spread the Wordlist score >= 50.
3. **Familiarity** — Zipf >= `--zipf`.
4. **Drop non-words** — judged from the surface-forms edition, which keeps the
   original casing, spaces and periods. A word is cleared as soon as one
   surface form looks ordinary, so DELTA survives on "delta" despite "Delta".
   This is what catches proper nouns (`Genoa`, `Maine`), abbreviations and
   their plurals (`USPS`, `ATVs`) and multi-word partials (`a game`, `tee up`,
   `in app`). Clue text is a second source: a word whose clues mostly say
   "Abbr." or "for short" goes too.
5. **Manual lists** — `allowlist.txt` forces a word in past every gate,
   `blocklist.txt` forces it out and beats the allowlist. The shipped
   blocklist holds the entries that clear both gates on a technicality:
   foreign words (HOLA, TORO, UNA), affixes (TELE, UNI) and misspellings
   (NITE, TWAS).
6. **Clue cleanup** — drop clues that give away the answer, use `?` wordplay,
   or carry two or more proper names. Fill-in-the-blank clues are kept: they
   are easy in a mini even with a name in them, because the phrase does the
   work. Survivors are ordered plainest first, then capped at `--clues`.
   Since `clues_filtered.json` is already most-used-first, `clues[0]` is the
   single most familiar clue for that word.
7. **Write** the JSON, the optional scores file, and the report.

### Results

**5,595 words, 48,125 clues** — 715 of length 3, 1,940 of length 4, 2,940 of
length 5, 8.6 clues per word.

Checked against the game's own generator, lifted out of the page and run
headless over two years of puzzles:

| | v1 | v2 |
| --- | ---: | ---: |
| words | 3,578 | **5,595** |
| clues | 10,726 | **48,125** |
| clues per word | 3 | **8.6** |
| 5-letter words | 1,469 | **2,940** |
| Zipf floor | 3.0 | **2.8** |
| days filled, of 730 | 730 | **730** |
| distinct words used | 1,843 | **2,593** |
| repeats with the same clue | 33.5% | **12.4%** |

The most repeated entries are REST, TEST, NEST and ARENA, against ESSE, SSNS
and EENIE for the uncurated list.

### Using it in the game

`clues_filtered.json` is a copy of the current `clues_clean_vN.json`, and the
schema is unchanged, so the page needed no edit at all. Two optional follow-ups
in the page:

- Leave clue choice random. Clues are ordered plainest-first, so `clues[0]` is
  available, but every clue has passed the quality gate and random choice is
  what keeps a repeated word from repeating its clue.
- Weight the candidate pool by `scores_v1.json` instead of shuffling
  uniformly, with seeded randomness inside a tier. Determinism survives
  because the ordering is fixed by the file.

## Legacy list

`clues_legacy.json` is the list this replaced: **9,023 words, 124,084
clues**, built on a 7-year window with a 30-unique-clue floor and then
pruned for standalone solvability. Kept verbatim so it can be restored or
compared. Its builder is `filter_clues_legacy.py`; the solvability pass is
`prune_clues.py` with `solvability_prompt.txt`.

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

Result before pruning: 9,073 unique words and 136,095 clues — 1,643 words of
length 3, 3,465 of length 4, 3,965 of length 5. Every word carries a full 15
clues. See [Solvability pruning](#solvability-pruning) for the shipped corpus.

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

## Solvability pruning

The clues are meant for a standalone game with no grid and no crossing letters,
so the filtered corpus was pruned a second time. An LLM (Claude Sonnet, low
reasoning) judged every clue with `solvability_prompt.txt` against a typical
Monday–Wednesday NYT solver, deleting clues that need niche or regional
knowledge, deep pop-culture cuts, time-bound references, or wordplay that is
unfair without crossings. Whole words were dropped when the answer itself is
obscure crosswordese or an abbreviation (ANI, SAO, ERTE, ESTD).

Result: **9,023 unique words** and **124,084 clues** — 1,627 words of length 3,
3,442 of length 4, 3,954 of length 5. 50 words and 12,011 clues (8.8%) were
removed. Clue counts now vary: 3,726 words keep all 15, and 14 words have 5 or
fewer.

The model only outputs deletion lists (`WORD 2 7` or `WORD -`); the script
applies them, so clue text is never rewritten:

```sh
python3 prune_clues.py split clues_filtered.json work      # 100-word batches
# judge each work/batches/batch_NNN.txt, save to work/deletions/batch_NNN.txt
python3 prune_clues.py check work
python3 prune_clues.py apply work clues_filtered.json
```

Re-running `filter_clues.py` overwrites `clues_full.json` with the unpruned
corpus.

## Serving the `.gz`

If you serve the pre-compressed file directly, send both
`Content-Encoding: gzip` and `Content-Type: application/json`, or the browser
will hand your code raw gzip bytes. Most CDNs compress the plain `.json` on the
fly anyway, so the plain file is often the simpler choice.

## Source and licensing

Clue text originates with the individual puzzle publishers and reaches this
repo via the xd corpus, which carries its own terms. No license file has been
chosen for this repository yet — review the upstream terms before reuse.

Spread the Wordlist is licensed **CC BY-NC-SA 4.0**. It is used here only as an
input filter and is not redistributed — the `.dict` files are gitignored, and
`clues_clean_vN.json` contains no wordlist data, only which of our own words
survived. Anything shipped that was built with it needs attribution, and the
non-commercial term applies.

---

# Strands

| File | Size | gzipped |
| --- | --- | --- |
| `strands-puzzles.json` | 441 KB | 100 KB |
| `strands-words.json` | 627 KB | 163 KB |

## `strands-puzzles.json`

730 daily puzzles, one per day from **2026-10-12 to 2028-10-10**, drawn from 337
distinct themes. Grids are 8 rows × 6 columns.

```json
{
  "game": "Strands", "start": "2026-10-12", "end": "2028-10-10",
  "rows": 8, "cols": 6, "themes": 338, "days": 730,
  "puzzles": [
    {
      "date": "2026-10-12",
      "clue": "Stormy weather",
      "spangram": "STORMFRONT",
      "grid": "SEAGELTOLGUETRFONDYPMRTTTHPMETNOOESEARNOCNDOCYLO",
      "words": [{"word": "STORMFRONT", "cells": [0, 6, 7, 13, 20, ...], "spangram": true}]
    }
  ]
}
```

`grid` is 48 characters in row-major order, so cell `n` sits at row `n / 6`,
column `n % 6`. Each `cells` array lists the path spelling that word. Puzzles
carry 6 to 9 words each.

### Validation

All 730 puzzles were checked and pass:

- every `cells` path spells its `word` against the grid — 0 mismatches
- every step in a path is adjacent, diagonals included — 0 breaks
- each puzzle's words cover all 48 cells exactly once — 0 gaps, 0 overlaps

## `strands-words.json`

A flat sorted array of 59,551 unique uppercase words, 4 to 12 letters, for
validating player guesses.

```json
["AARDVARK", "AARDVARKS", "AARGH"]
```

### Note on theme words

332 theme answers used by the puzzles are **not** in this dictionary, because
they are proper nouns — ACADIA, AKRON, ALGERIA, AMUNDSEN, ATHENS, BALI,
BELFAST. The dictionary holds common nouns only. If a game validates guesses
against this file alone, those theme words will be rejected; validate theme
words against the puzzle's own `words` array first.
