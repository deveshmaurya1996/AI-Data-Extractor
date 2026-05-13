from __future__ import annotations

import hashlib
import time
from copy import deepcopy
from threading import Lock
from typing import Any

_MAX_ENTRIES = 256
_TTL_SEC = 120.0

_lock = Lock()
_store: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_conv_keys: dict[str, set[str]] = {}


def _cache_key(conversation_id: str | None, sql: str) -> str:
    h = hashlib.sha256()
    h.update((conversation_id or "").encode("utf-8"))
    h.update(b"\x1e")
    h.update(sql.strip().encode("utf-8"))
    return h.hexdigest()


def _evict_one_unlocked() -> None:
    if len(_store) <= _MAX_ENTRIES:
        return
    oldest_k: str | None = None
    oldest_t = float("inf")
    for k, (ts, _) in _store.items():
        if ts < oldest_t:
            oldest_t = ts
            oldest_k = k
    if oldest_k is not None:
        _store.pop(oldest_k, None)
        for keys in _conv_keys.values():
            keys.discard(oldest_k)


def get_cached(
    conversation_id: str | None, sql: str
) -> list[dict[str, Any]] | None:
    k = _cache_key(conversation_id, sql)
    now = time.monotonic()
    with _lock:
        ent = _store.get(k)
        if ent is None:
            return None
        ts, rows = ent
        if now - ts > _TTL_SEC:
            _store.pop(k, None)
            for keys in _conv_keys.values():
                keys.discard(k)
            return None
        return deepcopy(rows)


def set_cached(
    conversation_id: str | None, sql: str, data: list[dict[str, Any]]
) -> None:
    k = _cache_key(conversation_id, sql)
    cid = (conversation_id or "").strip()
    now = time.monotonic()
    with _lock:
        _evict_one_unlocked()
        _store[k] = (now, deepcopy(data))
        _conv_keys.setdefault(cid, set()).add(k)


def invalidate_conversation(conversation_id: str) -> None:
    cid = (conversation_id or "").strip()
    if not cid:
        return
    with _lock:
        for k in _conv_keys.pop(cid, set()):
            _store.pop(k, None)


def clear_all() -> None:
    with _lock:
        _store.clear()
        _conv_keys.clear()
