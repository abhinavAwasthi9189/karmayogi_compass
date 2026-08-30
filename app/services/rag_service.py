"""RAG pipeline for quiz generation: extracts text from an uploaded PDF, chunks
it with page-level citation metadata, embeds it into an in-memory vector store,
and retrieves the passages most relevant to a competency domain.

Retrieval is a plain numpy cosine-similarity search over TF-IDF vectors — there's
only ever one small, ephemeral, single-request collection here, so a full vector
database is unnecessary overhead. This also keeps the dependency footprint small
and avoids packages that lag behind on new Python version support."""
import io
from typing import List, Dict, Any

import numpy as np
from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

CHUNK_SIZE_WORDS = 180
CHUNK_OVERLAP_WORDS = 30

# Retrieval seed queries per competency domain — used to pull the most
# relevant chunks for that domain's scenario questions.
DOMAIN_RETRIEVAL_QUERIES = {
    "statistical": "statistical methodology, survey design, sampling, data compilation, estimation",
    "technical": "technical tools, data processing, software, analytics, systems used for the work",
    "digital_gov": "digital governance, e-governance platforms, data security, online systems, compliance",
    "managerial": "management, leadership, team coordination, decision making, administration, planning",
}


def extract_pages(pdf_bytes: bytes) -> List[Dict[str, Any]]:
    """Returns [{"page": int, "text": str}, ...] for non-empty pages."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append({"page": i, "text": text})
    return pages


def chunk_pages(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Splits page text into overlapping word-window chunks, each tagged with its source page."""
    chunks = []
    for page in pages:
        words = page["text"].split()
        if not words:
            continue
        start = 0
        while start < len(words):
            end = start + CHUNK_SIZE_WORDS
            chunk_text = " ".join(words[start:end])
            chunks.append({"text": chunk_text, "page": page["page"]})
            if end >= len(words):
                break
            start = end - CHUNK_OVERLAP_WORDS
    return chunks


class RAGSession:
    """One ephemeral, in-memory vector index scoped to a single quiz-generation request.

    Embeddings are produced locally with a TF-IDF vectorizer fit on the document's own chunks,
    and similarity search is plain cosine similarity over the resulting matrix. This keeps quiz
    generation fully self-contained and network-independent (no embedding model download), and
    avoids pulling in a full vector-database dependency for what is, per request, a small,
    single-use, in-memory search over a few dozen chunks."""

    def __init__(self):
        self._vectorizer: TfidfVectorizer | None = None
        self._chunk_texts: List[str] = []
        self._chunk_pages: List[int] = []
        self._embeddings: np.ndarray | None = None

    def ingest(self, pdf_bytes: bytes) -> int:
        pages = extract_pages(pdf_bytes)
        if not pages:
            raise ValueError("No extractable text found in the uploaded PDF.")
        chunks = chunk_pages(pages)

        self._chunk_texts = [c["text"] for c in chunks]
        self._chunk_pages = [c["page"] for c in chunks]

        self._vectorizer = TfidfVectorizer(stop_words="english", max_features=2048)
        self._embeddings = self._vectorizer.fit_transform(self._chunk_texts).toarray()

        return len(chunks)

    def retrieve(self, domain: str, k: int = 4) -> List[Dict[str, Any]]:
        if self._vectorizer is None or self._embeddings is None:
            raise RuntimeError("ingest() must be called before retrieve()")
        query = DOMAIN_RETRIEVAL_QUERIES.get(domain, domain)
        query_embedding = self._vectorizer.transform([query]).toarray()

        similarities = cosine_similarity(query_embedding, self._embeddings)[0]
        top_k = min(k, len(self._chunk_texts))
        top_indices = np.argsort(similarities)[::-1][:top_k]

        return [
            {"text": self._chunk_texts[i], "page": self._chunk_pages[i]}
            for i in top_indices
        ]
