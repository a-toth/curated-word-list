#!/usr/bin/env python3
"""Split the clue corpus into batches for model judging, then apply the
model's deletion lists to build the pruned corpus.

Each batch is written twice: batch_NNN.json (used by apply) and
batch_NNN.txt (numbered clues, sent to the model so it never has to count
positions). The model judges the .txt with solvability_prompt.txt, and its
reply is saved as deletions/batch_NNN.txt, one line per changed word:
  WORD i j k   delete clues at 0-based positions i, j, k
  WORD -       drop the whole word

Usage:
  python3 prune_clues.py split <input.json> <work_dir> [batch_size]
  python3 prune_clues.py check <work_dir>
  python3 prune_clues.py apply <work_dir> <output.json>
"""
import gzip
import json
import os
import re
import sys

DEFAULT_BATCH_SIZE = 100
LINE = re.compile(r'^([A-Z]+)\s+(-|\d+(?:\s+\d+)*)$')


def numbered(batch):
    return '\n\n'.join(
        word + '\n' + '\n'.join(f'[{i}] {c}' for i, c in enumerate(clues))
        for word, clues in batch.items()
    ) + '\n'


def split(input_path, work_dir, batch_size):
    with open(input_path, encoding='utf-8') as f:
        data = json.load(f)
    batch_dir = os.path.join(work_dir, 'batches')
    os.makedirs(batch_dir, exist_ok=True)
    os.makedirs(os.path.join(work_dir, 'deletions'), exist_ok=True)

    words = list(data.items())
    count = 0
    for n, start in enumerate(range(0, len(words), batch_size)):
        batch = dict(words[start:start + batch_size])
        path = os.path.join(batch_dir, f'batch_{n:03d}.json')
        with open(path, 'w', encoding='utf-8') as out:
            json.dump(batch, out, ensure_ascii=False, separators=(',', ':'))
        with open(path[:-5] + '.txt', 'w', encoding='utf-8') as out:
            out.write(numbered(batch))
        count += 1
    print(f'{len(words):,} words -> {count} batches of up to {batch_size} in {batch_dir}')


def parse_deletions(text, batch):
    """Return ({word: set_of_indexes or None for drop}, [errors])."""
    result = {}
    errors = []
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip().strip('`')
        if not line:
            continue
        m = LINE.match(line)
        if not m:
            errors.append(f'line {lineno}: bad format: {raw!r}')
            continue
        word, rest = m.groups()
        if word not in batch:
            errors.append(f'line {lineno}: {word} is not in this batch')
            continue
        if word in result:
            errors.append(f'line {lineno}: {word} listed twice')
            continue
        if rest == '-':
            result[word] = None
            continue
        idx = [int(x) for x in rest.split()]
        bad = [i for i in idx if i >= len(batch[word])]
        if bad:
            errors.append(f'line {lineno}: {word} has {len(batch[word])} clues, got index {bad}')
            continue
        if len(set(idx)) != len(idx):
            errors.append(f'line {lineno}: {word} repeats an index')
            continue
        result[word] = set(idx)
    return result, errors


def load_batches(work_dir):
    batch_dir = os.path.join(work_dir, 'batches')
    del_dir = os.path.join(work_dir, 'deletions')
    for name in sorted(os.listdir(batch_dir)):
        if not name.endswith('.json'):
            continue
        with open(os.path.join(batch_dir, name), encoding='utf-8') as f:
            batch = json.load(f)
        del_path = os.path.join(del_dir, name[:-5] + '.txt')
        text = None
        if os.path.exists(del_path):
            with open(del_path, encoding='utf-8') as f:
                text = f.read()
        yield name[:-5], batch, text


def check(work_dir):
    done = missing = failed = 0
    for name, batch, text in load_batches(work_dir):
        if text is None:
            missing += 1
            continue
        _, errors = parse_deletions(text, batch)
        if errors:
            failed += 1
            print(f'{name}: {len(errors)} error(s)')
            for e in errors:
                print(f'  {e}')
        else:
            done += 1
    print(f'valid: {done}  invalid: {failed}  not yet judged: {missing}')
    return failed == 0 and missing == 0


def apply(work_dir, output_path):
    if not check(work_dir):
        print('Fix or re-judge the batches above before applying.')
        sys.exit(1)

    result = {}
    words_in = clues_in = dropped_words = dropped_clues = 0
    for _name, batch, text in load_batches(work_dir):
        deletions, _ = parse_deletions(text, batch)
        for word, clues in batch.items():
            words_in += 1
            clues_in += len(clues)
            remove = deletions.get(word, set())
            if remove is None:
                dropped_words += 1
                dropped_clues += len(clues)
                continue
            kept = [c for i, c in enumerate(clues) if i not in remove]
            dropped_clues += len(clues) - len(kept)
            if not kept:
                dropped_words += 1
                continue
            result[word] = kept

    with open(output_path, 'w', encoding='utf-8') as out:
        json.dump(result, out, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
    with open(output_path, 'rb') as src, gzip.open(output_path + '.gz', 'wb', compresslevel=9) as gz:
        gz.write(src.read())

    print(f'Words in:      {words_in:,}')
    print(f'Words dropped: {dropped_words:,}')
    print(f'Words out:     {len(result):,}')
    print(f'Clues in:      {clues_in:,}')
    print(f'Clues dropped: {dropped_clues:,}')
    print(f'Clues out:     {clues_in - dropped_clues:,}')
    print(f'Output written to: {output_path} (+ .gz)')


if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) in (3, 4) and args[0] == 'split':
        size = int(args[3]) if len(args) == 4 else DEFAULT_BATCH_SIZE
        split(args[1], args[2], size)
    elif len(args) == 2 and args[0] == 'check':
        sys.exit(0 if check(args[1]) else 1)
    elif len(args) == 3 and args[0] == 'apply':
        apply(args[1], args[2])
    else:
        print(__doc__)
        sys.exit(1)
