"""Ephemeral PDF/HTML bytes for preview (1-hour TTL)."""

import threading
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class EphemeralArtifacts:
    pdf_bytes: Optional[bytes] = None
    html_str: Optional[str] = None
    docx_bytes: Optional[bytes] = None
    created: float = 0.0


class PreviewStore:
    def __init__(self, ttl_seconds: int = 3600) -> None:
        self._ttl = ttl_seconds
        self._data: dict[str, EphemeralArtifacts] = {}
        self._lock = threading.Lock()

    def set(self, submission_uuid: str, artifacts: EphemeralArtifacts) -> None:
        artifacts.created = time.time()
        with self._lock:
            self._purge_locked()
            self._data[submission_uuid] = artifacts

    def get(self, submission_uuid: str) -> Optional[EphemeralArtifacts]:
        with self._lock:
            self._purge_locked()
            a = self._data.get(submission_uuid)
            if not a:
                return None
            if time.time() - a.created > self._ttl:
                del self._data[submission_uuid]
                return None
            return a

    def _purge_locked(self) -> None:
        now = time.time()
        dead = [k for k, v in self._data.items() if now - v.created > self._ttl]
        for k in dead:
            del self._data[k]


preview_store = PreviewStore()
