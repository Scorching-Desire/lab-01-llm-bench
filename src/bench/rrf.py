"""Reciprocal rank fusion, Cormack et al., SIGIR 2009.

https://cormack.uwaterloo.ca/cormacksigir09-rrf.pdf
Ranks start at one and the paper's pilot constant stays at 60.
"""

from collections import defaultdict

RRF_K = 60


def rrf(rankings, k=RRF_K, top_k=5):
    if k < 0 or top_k < 0:
        raise ValueError("nonnegative k and top_k required")
    scores = defaultdict(float)
    for ranking in rankings:
        if len(set(ranking)) != len(ranking):
            raise ValueError("ranking contains duplicate IDs")
        for rank, doc_id in enumerate(ranking, 1):
            scores[doc_id] += 1 / (k + rank)
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:top_k]
