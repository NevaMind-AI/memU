"""Backward-compatible re-export of the storage-neutral vector helpers.

The actual cosine/salience math now lives in :mod:`memu.vector` so that neither
the app retrieval layer nor any database backend has to depend on the in-memory
backend's internals. This shim is kept so existing imports
(``memu.database.inmemory.vector``) keep working.
"""

from __future__ import annotations

from memu.vector import _cosine, cosine_topk, cosine_topk_salience, salience_score

__all__ = ["_cosine", "cosine_topk", "cosine_topk_salience", "salience_score"]
