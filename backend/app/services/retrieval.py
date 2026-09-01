"""Persistent semantic filing retrieval with an explicitly labelled TF-IDF fallback."""
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Literal, Protocol

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.config import get_settings

FILINGS_DIR = Path(__file__).parent.parent / "data" / "filings"
VECTOR_STORE = Path(__file__).parent.parent / "data" / "filing_vectors.json"
RetrievalMode = Literal["semantic", "tfidf_fallback", "unavailable"]


class Encoder(Protocol):
    def encode(self, sentences: list[str], *, normalize_embeddings: bool = True) -> Any: ...


@dataclass(frozen=True)
class RetrievedChunk:
    document: str
    chunk_id: str
    text: str
    score: float
    title: str = "Synthetic regulatory filing passage"

    @property
    def source_id(self) -> str:
        return f"filing:{self.document}:{self.chunk_id}"


class FilingRetriever:
    def __init__(self, filings_dir: Path = FILINGS_DIR, encoder: Encoder | None = None,
                 vector_store: Path = VECTOR_STORE, force_tfidf: bool = False) -> None:
        started = perf_counter()
        self.chunks: list[RetrievedChunk] = []
        self.mode: RetrievalMode = "unavailable"
        self.fallback_reason: str | None = None
        self.vector_store = vector_store
        for path in sorted(filings_dir.glob("*.txt")):
            paragraphs = [part.strip() for part in path.read_text().split("\n\n") if part.strip()]
            for index, text in enumerate(paragraphs):
                self.chunks.append(RetrievedChunk(path.name, f"{path.stem}-chunk-{index}", text, 0.0,
                                                  f"{path.stem.replace('_', ' ')} filing passage"))
        if not self.chunks:
            self.initialization_latency_ms = round((perf_counter() - started) * 1000, 3)
            return
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.matrix = self.vectorizer.fit_transform([chunk.text for chunk in self.chunks])
        self.encoder: Encoder | None = encoder
        self.embeddings: Any = None
        if not force_tfidf and get_settings().semantic_retrieval_enabled:
            try:
                if self.encoder is None:
                    from sentence_transformers import SentenceTransformer
                    self.encoder = SentenceTransformer(get_settings().embedding_model, local_files_only=True)
                self.embeddings = self._load_or_create_embeddings()
                self.mode = "semantic"
            except Exception as exc:
                self.fallback_reason = f"Semantic model unavailable: {type(exc).__name__}"
                self.mode = "tfidf_fallback"
        else:
            self.fallback_reason = "Semantic retrieval disabled or fallback forced"
            self.mode = "tfidf_fallback"
        self.initialization_latency_ms = round((perf_counter() - started) * 1000, 3)

    def _fingerprint(self) -> str:
        content = "\n".join(f"{item.chunk_id}:{item.text}" for item in self.chunks)
        return hashlib.sha256(content.encode()).hexdigest()

    def _load_or_create_embeddings(self) -> list[list[float]]:
        if self.vector_store.exists():
            saved = json.loads(self.vector_store.read_text())
            if saved.get("fingerprint") == self._fingerprint():
                return saved["embeddings"]
        assert self.encoder is not None
        vectors = self.encoder.encode([chunk.text for chunk in self.chunks], normalize_embeddings=True)
        embeddings = vectors.tolist() if hasattr(vectors, "tolist") else [list(row) for row in vectors]
        self.vector_store.parent.mkdir(parents=True, exist_ok=True)
        self.vector_store.write_text(json.dumps({"fingerprint": self._fingerprint(), "embeddings": embeddings}))
        return embeddings

    def retrieve(self, symbol: str, query: str, limit: int = 2) -> list[RetrievedChunk]:
        candidates = [index for index, chunk in enumerate(self.chunks) if chunk.document.startswith(symbol.upper() + "_")]
        if not candidates or self.mode == "unavailable":
            return []
        if self.mode == "semantic":
            assert self.encoder is not None and self.embeddings is not None
            query_vector = self.encoder.encode([query], normalize_embeddings=True)
            scores = cosine_similarity(query_vector, [self.embeddings[index] for index in candidates]).ravel()
        else:
            scores = cosine_similarity(self.vectorizer.transform([query]), self.matrix[candidates]).ravel()
        ranked = sorted(zip(candidates, scores, strict=True), key=lambda item: item[1], reverse=True)
        return [RetrievedChunk(self.chunks[index].document, self.chunks[index].chunk_id,
                               self.chunks[index].text, round(max(0.0, float(score)), 4), self.chunks[index].title)
                for index, score in ranked[:limit] if score > 0]
