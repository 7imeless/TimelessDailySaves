"""Build a small, reproducible English library from a local ECDICT CSV."""
import argparse
import csv
import hashlib
import heapq
import json
from pathlib import Path
import re
import sqlite3


def build(source, output, limit, required_tag=None, name="英语高频基础词库"):
    def candidates():
        with source.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                word = row["word"].strip()
                if not word or not row["translation"].strip():
                    continue
                if not required_tag and not re.fullmatch(r"[a-z]+(?:[-'][a-z]+)*", word):
                    continue
                if required_tag and required_tag not in row.get("tag", "").split():
                    continue
                rank = int(row.get("frq") or 0) or int(row.get("bnc") or 0)
                if rank <= 0 and not required_tag:
                    continue
                yield rank, word, row
    selected = heapq.nsmallest(limit, candidates(), key=lambda x: (x[0] if x[0] > 0 else float('inf'), x[1]))
    words = []
    seen = set()
    for rank, word, row in selected:
        if word.casefold() in seen:
            continue
        seen.add(word.casefold())
        words.append({"word": word, "phonetic": row["phonetic"],
                      "translation": row["translation"].replace("\\n", "\n"),
                      "definition": row["definition"].replace("\\n", "\n"),
                      "tags": row["tag"].split(), "frequency_rank": rank or None,
                      "frequency_source": ("frq" if int(row.get("frq") or 0) else "bnc") if rank else None,
                      "exchange": row["exchange"], "source": "ECDICT"})
    payload = {"schema_version": 1, "name": name,
               "source_url": "https://github.com/skywind3000/ECDICT",
               "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
               "selection": "Exact ECDICT tag filter with nonempty translations (including proper nouns and unranked entries)." if required_tag else "Lowercase English entries with translations; frq rank, falling back to bnc. Not CEFR levels or word families.",
               "required_tag": required_tag,
               "license": "MIT (upstream repository declaration)", "count": len(words), "words": words}
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def import_sqlite(payload, database):
    # This database contains dictionary data only, never user learning records.
    with sqlite3.connect(database) as db:
        db.execute("CREATE TABLE IF NOT EXISTS words (word TEXT PRIMARY KEY COLLATE NOCASE, phonetic TEXT, translation TEXT, definition TEXT, tags TEXT, frequency_rank INTEGER, frequency_source TEXT, exchange TEXT, source TEXT)")
        db.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT)")
        db.execute("DELETE FROM words")
        db.executemany("INSERT INTO words VALUES (?,?,?,?,?,?,?,?,?)", [
            (w['word'], w['phonetic'], w['translation'], w['definition'],
             json.dumps(w['tags']), w['frequency_rank'], w['frequency_source'], w['exchange'], w['source'])
            for w in payload['words']])
        db.execute("CREATE INDEX IF NOT EXISTS words_frequency ON words(frequency_rank)")
        db.execute("INSERT OR REPLACE INTO metadata VALUES ('manifest', ?)",
                   (json.dumps({k: v for k, v in payload.items() if k != 'words'}, ensure_ascii=False),))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', type=Path)
    parser.add_argument('--json', type=Path, default=Path('data/english-core.json'))
    parser.add_argument('--database', type=Path, default=Path('words.db'))
    parser.add_argument('--limit', type=int, default=2000)
    parser.add_argument('--tag', help='Require an exact ECDICT tag, for example cet6')
    parser.add_argument('--name', default='英语高频基础词库')
    args = parser.parse_args()
    if args.limit < 1:
        parser.error('--limit must be positive')
    payload = build(args.csv, args.json, args.limit, args.tag, args.name) if args.csv else json.loads(args.json.read_text(encoding='utf-8'))
    import_sqlite(payload, args.database)
    print(f"Imported {payload['count']} words into {args.database}")
