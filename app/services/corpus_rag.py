"""RAG index over our own seeded learning corpus (mock/rag_learning_corpus_flat.csv),
used to generate quiz questions grounded in our course material -- as opposed to
rag_service.py, which indexes an uploaded PDF instead.

The index is built lazily on first use and cached in-process. It's cheap enough
(a few hundred rows) to rebuild on a cold start, and doing it lazily (not at
import time) matters on serverless platforms like Vercel."""
from typing import List, Dict, Any, Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.adapters.mock_dataset_loader import load_rag_corpus
from app.services.rag_service import DOMAIN_RETRIEVAL_QUERIES

_vectorizer: Optional[TfidfVectorizer] = None
_rows: List[Dict[str, Any]] = []
_embeddings: Optional[np.ndarray] = None


def _ensure_index() -> None:
    global _vectorizer, _rows, _embeddings
    if _vectorizer is not None:
        return
    _rows = load_rag_corpus()
    if not _rows:
        return
    texts = [f"{r['module_title']}. {r['study_material']}" for r in _rows]
    _vectorizer = TfidfVectorizer(stop_words="english", max_features=4096)
    _embeddings = _vectorizer.fit_transform(texts).toarray()


def corpus_index_available() -> bool:
    _ensure_index()
    return _vectorizer is not None


def retrieve(domain: str, extra_query: str = "", k: int = 4) -> List[Dict[str, Any]]:
    """Top-k course modules for a domain, ranked by relevance to that domain's
    seed query plus any extra context (e.g. the learner's current gap)."""
    _ensure_index()
    if _vectorizer is None or _embeddings is None:
        return []

    domain_indices = [i for i, r in enumerate(_rows) if r["domain"] == domain]
    if not domain_indices:
        return []

    query = DOMAIN_RETRIEVAL_QUERIES.get(domain, domain)
    if extra_query:
        query = f"{query}. {extra_query}"
    query_embedding = _vectorizer.transform([query]).toarray()

    sub_embeddings = _embeddings[domain_indices]
    similarities = cosine_similarity(query_embedding, sub_embeddings)[0]
    top_k = min(k, len(domain_indices))
    top_local = np.argsort(similarities)[::-1][:top_k]

    results = []
    for local_idx in top_local:
        row = _rows[domain_indices[local_idx]]
        results.append({
            "text": f"{row['module_title']}: {row['study_material']}",
            "citation": f"{row['course_title']} — Module {row['module_no']}: {row['module_title']}",
        })
    return results