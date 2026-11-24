"""Retrieval candidate values. Freeze after the dev grid, before decision-test runs."""

CONFIG = {
    "chunk_chars": 1100,
    "chunk_overlap": 180,
    "embed_model": "bge-m3:latest",
    "embed_dim": 1024,
    "truncate": False,
    "lex_mode": "prefix",
    "k_lex": 20,
    "k_dense": 20,
    "rrf_k": 60,
    "top_k": 5,
    "single_best": "lex",
}
