"""Lightweight in-memory vector store for PCID matching.

This module intentionally avoids heavyweight dependencies so it can operate in
unit tests and constrained environments. It offers:

- Hash-based text embeddings for name/company/currency fields.
- Cosine similarity search with configurable thresholds.
- JSONL persistence helpers so offline-built indices can be loaded at runtime.

It is not a production-grade ANN implementation, but provides a functional
backend for local PCID matching and replay scenarios until a dedicated service
is wired in.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
import time
from typing import Any, Dict, Iterable, List, Mapping, Optional, Protocol, Sequence, Tuple

import requests

from src.common.logging_utils import get_logger

log = get_logger(__name__)


def _normalize(vec: Sequence[float]) -> List[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:
        return list(vec)
    return [v / norm for v in vec]


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))


def _text_to_vector(text: str, dims: int = 48) -> List[float]:
    vec = [0.0] * dims
    for token in text.lower().split():
        vec[hash(token) % dims] += 1.0
    return vec


def _record_embedding(record: Mapping[str, str], dims: int = 48) -> List[float]:
    name = (record.get("name") or "").strip()
    company = (record.get("company") or "").strip()
    currency = (record.get("currency") or "").strip()
    raw_vec = [
        *_text_to_vector(name, dims=dims),
        *_text_to_vector(company, dims=dims),
        *_text_to_vector(currency, dims=dims // 2),
    ]
    return _normalize(raw_vec)


class BasePCIDVectorBackend(Protocol):
    """Minimal interface for PCID vector backends."""

    dims: int

    def query(
        self, vector: Sequence[float], top_k: int = 3, threshold: float = 0.75
    ) -> Sequence[Mapping[str, Any]]:
        """Return the top matching PCIDs for the supplied embedding."""
        ...


def embed_pcid_record(record: Mapping[str, str], dims: int = 48) -> List[float]:
    """Helper to build a deterministic embedding for a PCID record."""

    return _record_embedding(record, dims=dims)


class PCIDVectorStore:
    """In-memory vector store to support PCID similarity lookups."""

    def __init__(self, dims: int = 48):
        self.dims = dims
        self._entries: List[Tuple[str, List[float], Dict]] = []

    def add(self, pcid: str, vector: Sequence[float], metadata: Optional[Dict] = None) -> None:
        self._entries.append((pcid, _normalize(vector), metadata or {}))

    def embed_record(self, record: Mapping[str, str]) -> List[float]:
        return embed_pcid_record(record, dims=self.dims)

    def query(
        self, vector: Sequence[float], top_k: int = 3, threshold: float = 0.75
    ) -> Sequence[Mapping[str, Any]]:
        vector = _normalize(vector)
        scored = [
            {"pcid": pcid, "score": _cosine(vector, candidate_vec), "metadata": meta}
            for pcid, candidate_vec, meta in self._entries
        ]
        above_threshold = [row for row in scored if row["score"] >= threshold]
        if not above_threshold and scored and threshold <= 0.1:
            best = max(scored, key=lambda row: row["score"])
            above_threshold = [best]
        above_threshold.sort(key=lambda row: row["score"], reverse=True)
        return above_threshold[:top_k]

    @classmethod
    def from_jsonl(cls, path: Path, dims: int = 48) -> "PCIDVectorStore":
        store = cls(dims=dims)
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            store.add(entry["pcid"], entry["vector"], entry.get("metadata") or {})
        return store

    def to_jsonl(self, path: Path) -> None:
        lines = []
        for pcid, vector, metadata in self._entries:
            lines.append(json.dumps({"pcid": pcid, "vector": vector, "metadata": metadata}))
        path.write_text("\n".join(lines), encoding="utf-8")

    def populate_from_records(self, records: Iterable[Mapping[str, str]]) -> None:
        for record in records:
            if hasattr(record, "model_dump"):
                record = record.model_dump()
            elif not isinstance(record, Mapping):
                record = dict(record)

            pcid = record.get("pcid")
            if not pcid:
                continue
            vector = self.embed_record(record)
            self.add(pcid, vector, metadata={"source": record.get("source")})


class HashVectorBackend(BasePCIDVectorBackend):
    """Hash-based in-memory backend (current toy behavior)."""

    def __init__(self, store: PCIDVectorStore):
        self.store = store
        self.dims = store.dims

    @classmethod
    def from_records(
        cls, records: Iterable[Mapping[str, str]], dims: int = 48
    ) -> "HashVectorBackend":
        store = PCIDVectorStore(dims=dims)
        store.populate_from_records(records)
        return cls(store)

    @classmethod
    def from_jsonl(cls, path: Path, dims: int = 48) -> "HashVectorBackend":
        return cls(PCIDVectorStore.from_jsonl(path, dims=dims))

    def query(
        self, vector: Sequence[float], top_k: int = 3, threshold: float = 0.75
    ) -> Sequence[Mapping[str, Any]]:
        return self.store.query(vector, top_k=top_k, threshold=threshold)


class InMemoryVectorStore:
    def _embed(self, text: str) -> List[float]:
        """
        Embedding function used for similarity search.

        NOTE: This implementation is a placeholder and should NOT be used in
        production for semantic search. Replace with a real embedding model
        (e.g., sentence-transformers) and keep this as a fallback.
        """
        return self._hash_embedding(text)

    def _hash_embedding(self, text: str) -> List[float]:
        h = hash(text)
        return [(h % 1_000_000) / 1_000_000.0]


class RemotePCIDVectorBackend(BasePCIDVectorBackend):
    """HTTP client for an external PCID vector store service."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 5.0,
        api_key: Optional[str] = None,
        max_retries: int = 3,
        backoff_base: float = 0.5,
        dims: int = 48,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.api_key = api_key
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.dims = dims

    def _post(self, path: str, payload: Mapping) -> Mapping[str, Any]:
        headers: Dict[str, str] = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        last_exc: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                kwargs = {"json": payload, "timeout": self.timeout}
                if headers:
                    kwargs["headers"] = headers

                response = requests.post(f"{self.base_url}{path}", **kwargs)
                status_code = getattr(response, "status_code", None)
                if status_code is not None and 500 <= status_code < 600:
                    raise requests.HTTPError(
                        f"Remote vector backend 5xx: {response.status_code}",
                        response=response,
                    )
                response.raise_for_status()
                return response.json()
            except requests.HTTPError as exc:
                status_code = getattr(exc.response, "status_code", None)
                if status_code is None or not (500 <= status_code < 600):
                    raise
                last_exc = exc
            except (requests.Timeout, requests.ConnectionError) as exc:
                last_exc = exc
            except Exception:
                # Preserve unexpected exceptions to avoid masking bugs.
                raise

            log.warning(
                "RemotePCIDVectorBackend POST failed",
                extra={
                    "attempt": attempt,
                    "max_retries": self.max_retries,
                    "status_code": getattr(getattr(last_exc, "response", None), "status_code", None),
                },
            )
            if attempt >= self.max_retries:
                break
            sleep_for = self.backoff_base * (2 ** (attempt - 1))
            time.sleep(sleep_for)

        log.error(
            "RemotePCIDVectorBackend POST failed after retries",
            extra={"max_retries": self.max_retries, "error": str(last_exc)},
        )
        return {}

    def query(
        self, vector: Sequence[float], top_k: int = 3, threshold: float = 0.75
    ) -> Sequence[Mapping[str, Any]]:
        payload = {"vector": list(vector), "top_k": top_k, "threshold": threshold}
        data = self._post("/query", payload)
        matches = data.get("matches") if isinstance(data, Mapping) else None
        if matches is None:
            # Fallback to raw response if the service returns a bare list
            matches = data
        return [match for match in (matches or []) if isinstance(match, Mapping)]

    def query_record(
        self, record: Mapping[str, str], top_k: int = 3, threshold: float = 0.75
    ) -> List[Mapping[str, object]]:
        """Send a similarity query to the remote backend using a raw record."""

        payload = {"record": dict(record), "top_k": top_k, "threshold": threshold}
        data = self._post("/query", payload)
        matches = data.get("matches") if isinstance(data, Mapping) else None
        if matches is None:
            # Fallback to raw response if the service returns a bare list
            matches = data
        return [match for match in (matches or []) if isinstance(match, Mapping)]


def connect_vector_store_backend() -> Optional[RemotePCIDVectorBackend]:
    """Instantiate a remote backend if configured via env vars."""

    url = os.getenv("PCID_VECTOR_STORE_URL")
    if not url:
        return None
    return RemotePCIDVectorBackend(url)


def get_pcid_backend(
    settings: Optional[Mapping[str, Any]],
    *,
    vector_store: Optional[PCIDVectorStore] = None,
) -> Optional[BasePCIDVectorBackend]:
    """Instantiate a PCID backend based on configuration."""

    pcid_cfg = settings.get("pcid", {}) if isinstance(settings, Mapping) else {}
    backend_name = str(pcid_cfg.get("backend") or "hash").lower()

    if backend_name == "remote":
        remote_cfg = pcid_cfg.get("remote", {}) if isinstance(pcid_cfg, Mapping) else {}
        base_url = remote_cfg.get("base_url") or os.getenv("PCID_VECTOR_STORE_URL")
        if not base_url:
            log.warning("PCID remote backend requested but no base_url provided")
        else:
            return RemotePCIDVectorBackend(
                base_url,
                timeout=float(remote_cfg.get("timeout", 5.0)),
                api_key=remote_cfg.get("api_key"),
                max_retries=int(remote_cfg.get("max_retries", 3)),
                backoff_base=float(remote_cfg.get("backoff_base", 0.5)),
                dims=int(remote_cfg.get("dims", 48)),
            )

    if backend_name in {"hash", ""}:
        hash_cfg = pcid_cfg.get("hash", {}) if isinstance(pcid_cfg, Mapping) else {}
        dims = int(hash_cfg.get("dims", 48))
        store = vector_store or PCIDVectorStore(dims=dims)

        index_path = hash_cfg.get("index_path")
        if index_path and vector_store is None:
            index_file = Path(index_path)
            if index_file.exists():
                store = PCIDVectorStore.from_jsonl(index_file, dims=dims)
            else:
                log.warning("Configured PCID hash index not found", extra={"path": str(index_file)})

        if getattr(store, "dims", dims) != dims:
            log.warning("PCID vector store dims mismatch; expected %s", dims)

        return HashVectorBackend(store)

    log.warning("Unsupported PCID backend configured", extra={"backend": backend_name})
    return None
