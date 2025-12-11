"""Lightweight RAG orchestrator that can leverage DSPy when installed."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional


@dataclass
class RAGResponse:
    query: str
    answer: str
    sources: List[str]


class RAGPipeline:
    def __init__(self, retriever, llm=None) -> None:
        self.retriever = retriever
        self.llm = llm

    def _generate_with_dspy(self, query: str, context: str) -> str:
        try:
            import dspy  # type: ignore
        except ImportError:
            return f"[fallback] {context[:200]}"
        except Exception as exc:
            return f"[unexpected error invoking dspy: {exc}]"
        try:
            prompt = dspy.Prompt(f"Context: {context}\n\nQuestion: {query}\nAnswer:")
            return str(prompt)
        except Exception as exc:
            return f"[fallback] {context[:200]} ({exc})"

    def _generate_with_langgraph(self, query: str, context: str) -> str:
        try:
            from langgraph.graph import Graph  # type: ignore
        except ImportError:
            return self._generate_with_dspy(query, context)
        except Exception:
            return self._generate_with_dspy(query, context)

        def node(inputs):  # pragma: no cover - simple wiring
            return {"answer": f"{inputs['context']} => {inputs['query']}"}

        graph = Graph()
        graph.add_node("answer", node)
        graph.set_entry_point("answer")
        result = graph.invoke({"context": context, "query": query})
        return result.get("answer", "")

    def answer(self, query: str) -> RAGResponse:
        docs = list(self.retriever.retrieve(query)) if hasattr(self.retriever, "retrieve") else []
        context = "\n".join(docs)
        generated = self._generate_with_langgraph(query, context)
        return RAGResponse(query=query, answer=generated, sources=docs)


class InMemoryRetriever:
    def __init__(self, documents: Iterable[str]):
        self.documents = list(documents)

    def retrieve(self, query: str) -> Iterable[str]:
        query_lower = query.lower()
        return [doc for doc in self.documents if query_lower in doc.lower()]
