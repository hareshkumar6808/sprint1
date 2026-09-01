"""Small local TF-IDF filing retrieval index."""
from dataclasses import dataclass
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

FILINGS_DIR = Path(__file__).parent.parent / "data" / "filings"


@dataclass(frozen=True)
class RetrievedChunk:
    document: str
    chunk_id: str
    text: str
    score: float


class FilingRetriever:
    def __init__(self, filings_dir: Path = FILINGS_DIR) -> None:
        self.chunks: list[RetrievedChunk] = []
        for path in sorted(filings_dir.glob("*.txt")):
            paragraphs = [part.strip() for part in path.read_text().split("\n\n") if part.strip()]
            for index, text in enumerate(paragraphs):
                self.chunks.append(RetrievedChunk(path.name, f"{path.stem}-chunk-{index}", text, 0.0))
        if not self.chunks:
            raise ValueError("No filing documents found")
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.matrix = self.vectorizer.fit_transform([chunk.text for chunk in self.chunks])

    def retrieve(self, symbol: str, query: str, limit: int = 2) -> list[RetrievedChunk]:
        candidates = [index for index, chunk in enumerate(self.chunks) if chunk.document.startswith(symbol.upper() + "_")]
        if not candidates:
            return []
        scores = cosine_similarity(self.vectorizer.transform([query]), self.matrix[candidates]).ravel()
        ranked = sorted(zip(candidates, scores, strict=True), key=lambda item: item[1], reverse=True)
        return [RetrievedChunk(self.chunks[index].document, self.chunks[index].chunk_id,
                               self.chunks[index].text, round(float(score), 4))
                for index, score in ranked[:limit] if score > 0]
