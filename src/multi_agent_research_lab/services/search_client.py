"""Search clients for the offline corpus and optional providers."""

import json
import re
from pathlib import Path

from multi_agent_research_lab.core.schemas import SourceDocument


class SearchClient:
    """Provider-agnostic search client skeleton."""

    def search(self, query: str, max_results: int = 5) -> list[SourceDocument]:
        """Search for documents relevant to a query.

        Provider-specific implementations should override this method.
        """
        raise NotImplementedError("SearchClient.search must be implemented by a provider")


class OfflineSearchClient(SearchClient):
    """Retrieve embedded documents only; this client never makes network calls."""

    def __init__(self, corpus_root: Path) -> None:
        self.corpus_root = corpus_root

    def search(self, query: str, max_results: int = 5) -> list[SourceDocument]:
        topic_file = self._best_topic(query)
        payload = json.loads(topic_file.read_text(encoding="utf-8"))
        documents = payload["knowledge_base"]["source_documents"]
        query_terms = set(re.findall(r"[a-z0-9]+", query.lower()))

        def score(document: dict[str, object]) -> int:
            text = " ".join(
                str(document.get(key, "")) for key in ("title", "full_text", "key_takeaways")
            ).lower()
            return sum(term in text for term in query_terms)

        selected = sorted(documents, key=score, reverse=True)[:max_results]
        return [
            SourceDocument(
                title=str(document["title"]),
                url=f"offline://{document['document_id']}",
                snippet=str(document["full_text"])[:600],
                metadata={
                    "citation_id": str(document["citation_label"]),
                    "topic": str(payload["topic"]["name"]),
                    "synthetic": bool(document["is_synthetic"]),
                },
            )
            for document in selected
        ]

    def _best_topic(self, query: str) -> Path:
        files = sorted(self.corpus_root.glob("*.json"))
        if not files:
            raise FileNotFoundError(f"Offline corpus has no topic JSON files: {self.corpus_root}")
        terms = set(re.findall(r"[a-z0-9]+", query.lower()))

        def score(path: Path) -> int:
            payload = json.loads(path.read_text(encoding="utf-8"))
            topic = payload["topic"]
            text = " ".join([topic["name"], topic["research_question"], *topic["tags"]]).lower()
            return sum(term in text for term in terms)

        return max(files, key=score)
