"""Independent FTS5 and sqlite-vec indices with append-only retrieval experiments."""

import argparse
import hashlib
import json
import math
import re
import sqlite3
import time
from pathlib import Path

import sqlite_vec

from bench import data
from bench.embed import embed
from bench.rrf import rrf

CHUNKS = "data/lab3/chunks.jsonl"
QUERIES = "data/lab3/queries.jsonl"
DB = ".index/lab3.db"


def connect(path, dense_enabled=True):
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    if dense_enabled:
        connection.enable_load_extension(True)
        try:
            sqlite_vec.load(connection)
        finally:
            connection.enable_load_extension(False)
    return connection


def build_index(path, chunks, backend="both", model="bge-m3:latest", embedder=embed):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with connect(path, dense_enabled=backend != "lex") as con:
        con.execute("CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        fingerprint = hashlib.sha256(json.dumps(chunks, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        old = con.execute("SELECT value FROM meta WHERE key='chunks'").fetchone()
        if old and old[0] != fingerprint:
            raise ValueError("corpus changed: use a new index directory")
        con.execute("CREATE TABLE IF NOT EXISTS chunks(id INTEGER PRIMARY KEY, chunk_id TEXT UNIQUE, doc_id TEXT, text TEXT)")
        if not old:
            con.executemany("INSERT INTO chunks VALUES(?,?,?,?)", [(i, c["chunk_id"], c["doc_id"], c["text"])
                                                                  for i, c in enumerate(chunks, 1)])
            con.execute("INSERT INTO meta VALUES('chunks',?)", (fingerprint,))
        if backend in {"lex", "both"}:
            for name, tokenizer in (("ft", "unicode61"), ("tri", "trigram")):
                con.execute(f"DROP TABLE IF EXISTS {name}")
                con.execute(f"CREATE VIRTUAL TABLE {name} USING fts5(text, tokenize='{tokenizer}')")
                con.execute(f"INSERT INTO {name}(rowid,text) SELECT id,text FROM chunks")
        if backend in {"dense", "both"}:
            vectors = []
            for offset in range(0, len(chunks), 12):
                vectors.extend(embedder([c["text"] for c in chunks[offset:offset + 12]], model))
            dimension = len(vectors[0])
            if len(vectors) != len(chunks) or any(len(v) != dimension for v in vectors):
                raise ValueError("embedding dimension mismatch")
            con.execute("DROP TABLE IF EXISTS vectors")
            con.execute(f"CREATE VIRTUAL TABLE vectors USING vec0(emb float[{dimension}] distance_metric=cosine)")
            con.executemany("INSERT INTO vectors(rowid,emb) VALUES(?,?)",
                            [(i, sqlite_vec.serialize_float32(v)) for i, v in enumerate(vectors, 1)])
            for key, value in (("embed_model", model), ("embed_dim", str(dimension))):
                con.execute("INSERT OR REPLACE INTO meta VALUES(?,?)", (key, value))


def lexical(con, query, mode="exact", k=20):
    words = re.findall(r"[\w]+", query.casefold(), flags=re.UNICODE)
    words = [w for w in words if len(w) >= (3 if mode == "trigram" else 2)]
    if not words or k <= 0:
        return []
    clauses = ['"' + w.replace('"', '""') + '"' + ("*" if mode == "prefix" else "") for w in words]
    match = " OR ".join(clauses)
    name = "tri" if mode == "trigram" else "ft"
    return [dict(row) for row in con.execute(
        f"SELECT c.*, bm25({name}) AS score FROM {name} JOIN chunks c ON c.id={name}.rowid "
        f"WHERE {name} MATCH ? ORDER BY bm25({name}),c.chunk_id LIMIT ?", (match, k))]


def dense(con, query, model, k=20, embedder=embed):
    meta = dict(con.execute("SELECT key,value FROM meta"))
    if meta.get("embed_model") != model:
        raise ValueError("embedder differs from indexed model; rebuild")
    vector = embedder([query], model)[0]
    if len(vector) != int(meta["embed_dim"]):
        raise ValueError("query embedding dimension mismatch")
    k = min(k, con.execute("SELECT count(*) FROM chunks").fetchone()[0])
    return [dict(row) for row in con.execute(
        "SELECT c.*,v.distance AS score FROM vectors v JOIN chunks c ON c.id=v.rowid "
        "WHERE v.emb MATCH ? AND k=? ORDER BY v.distance,c.chunk_id",
        (sqlite_vec.serialize_float32(vector), k))]


def retrieve(con, query, backend, config, mode=None, top_k=None, embedder=embed):
    limit = top_k if top_k is not None else config["top_k"]
    lex = lexical(con, query, mode or config["lex_mode"], config["k_lex"]) if backend in {"lex", "both"} else []
    vec = dense(con, query, config["embed_model"], config["k_dense"], embedder) if backend in {"dense", "both"} else []
    if backend == "both":
        lookup = {r["chunk_id"]: r for r in [*lex, *vec]}
        return [{**lookup[key], "score": value} for key, value in rrf(
            [[r["chunk_id"] for r in group] for group in (lex, vec)], config["rrf_k"], limit)]
    return (lex or vec)[:limit]


def metrics(query, retrieved):
    spans = query.get("gold_spans", [])
    ranks = []
    for span in spans:
        ranks.append(next((i for i, chunk in enumerate(retrieved, 1)
                           if chunk["doc_id"] == span["doc_id"] and span["text"] in chunk["text"]), None))
    found = [rank for rank in ranks if rank is not None]
    first = min(found) if found else None
    return dict(hit=bool(found), all_hit=bool(ranks) and len(found) == len(ranks),
                recall=len(found) / len(ranks) if ranks else None,
                mrr=1 / first if first else 0,
                ndcg=(sum(1 / math.log2(rank + 1) for rank in sorted(set(found)) if rank <= 10) /
                      sum(1 / math.log2(i + 2) for i in range(min(len(spans), 10)))) if spans else None)


def config_values():
    from bench.retrieval_config import CONFIG

    return dict(CONFIG)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=["lex", "dense", "both"], default="both")
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument("--db", default=DB)
    parser.add_argument("--fuse", choices=["rrf"])
    parser.add_argument("--split", choices=["dev", "test"], default="test")
    parser.add_argument("--mode", choices=["exact", "prefix", "trigram"])
    parser.add_argument("--k", type=int)
    parser.add_argument("--out")
    args = parser.parse_args()
    if args.fuse and args.backend != "both":
        parser.error("rrf requires both backends")
    if (args.mode is not None or args.k is not None) and args.split != "dev":
        parser.error("mode/k overrides are restricted to dev")
    config = config_values()
    if args.rebuild:
        started = time.perf_counter()
        build_index(args.db, data.read_rows(CHUNKS), args.backend, config["embed_model"])
        print(f"Built {args.backend} in {time.perf_counter() - started:.2f} s", flush=True)
        return
    out = args.out or f"results/lab3/01-{args.backend}-{args.mode or config['lex_mode']}.jsonl"
    previous = data.read_rows(out)
    run = data.utc_now().replace(":", "-") + "_retrieval"
    with connect(args.db, dense_enabled=args.backend != "lex") as con:
        for query in data.read_rows(QUERIES):
            if query["split"] != args.split:
                continue
            start = time.perf_counter()
            result = retrieve(con, query["input"], args.backend, config, args.mode, args.k)
            row = data.new_row(run_id=run, ts=data.utc_now(), git_sha=data.git_sha(),
                dataset_sha256=data.sha256_file(QUERIES), config_sha256=data.sha256_file("src/bench/retrieval_config.py"),
                params=config, id=query["id"], split=query["split"], tags=query["tags"],
                backend=args.backend, fuse=args.fuse, lex_mode=args.mode or config["lex_mode"],
                top_k=args.k or config["top_k"], retrieved=[r["chunk_id"] for r in result],
                latency_ms=round((time.perf_counter() - start) * 1000),
                attempt=1 + sum(r["id"] == query["id"] for r in previous), **metrics(query, result))
            data.append_row(out, row)
    print(out, flush=True)


if __name__ == "__main__":
    main()
