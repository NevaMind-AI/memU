from __future__ import annotations

import json
import pathlib
from typing import Any

import numpy as np


class SimpleVectorDB:
    """Simple vector database for storing and querying embeddings."""

    def __init__(self, db_path: str):
        self.db_path = pathlib.Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # In-memory storage: {collection_name: {id: {user_id, agent_id, vector, text}}}
        self.collections: dict[str, dict[str, dict[str, Any]]] = {}
        self._load()

    def _load(self) -> None:
        """Load vectors from disk."""
        if not self.db_path.exists():
            return

        try:
            with self.db_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                # Convert lists back to numpy arrays
                for collection_name, items in data.items():
                    self.collections[collection_name] = {}
                    for item_id, item_data in items.items():
                        self.collections[collection_name][item_id] = {
                            "user_id": item_data["user_id"],
                            "agent_id": item_data["agent_id"],
                            "vector": item_data["vector"],
                            "text": item_data.get("text"),  # Optional text field
                        }
        except json.JSONDecodeError, KeyError:
            self.collections = {}

    def _save(self) -> None:
        """Save vectors to disk."""
        # Convert numpy arrays to lists for JSON serialization
        data: dict[str, dict[str, dict[str, Any]]] = {}
        for collection_name, items in self.collections.items():
            data[collection_name] = {}
            for item_id, item_data in items.items():
                data[collection_name][item_id] = {
                    "user_id": item_data["user_id"],
                    "agent_id": item_data["agent_id"],
                    "vector": item_data["vector"],
                    "text": item_data.get("text"),  # Include text if present
                }

        with self.db_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def upsert(
        self,
        collection: str,
        item_id: str,
        vector: list[float],
        user_id: str,
        agent_id: str,
        text: str | None = None,
    ) -> None:
        """Insert or update a vector with optional text."""
        if collection not in self.collections:
            self.collections[collection] = {}

        self.collections[collection][item_id] = {
            "user_id": user_id,
            "agent_id": agent_id,
            "vector": vector,
            "text": text,
        }
        self._save()

    def get_text(
        self,
        collection: str,
        item_id: str,
        user_id: str,
        agent_id: str,
    ) -> str | None:
        """Get the text associated with a vector by ID."""
        if collection not in self.collections:
            return None

        item = self.collections[collection].get(item_id)
        if not item:
            return None

        if item["user_id"] != user_id or item["agent_id"] != agent_id:
            return None

        return item.get("text")

    def get(
        self,
        collection: str,
        item_id: str,
        user_id: str,
        agent_id: str,
    ) -> list[float] | None:
        """Get a vector by ID."""
        if collection not in self.collections:
            return None

        item = self.collections[collection].get(item_id)
        if not item:
            return None

        if item["user_id"] != user_id or item["agent_id"] != agent_id:
            return None

        vector = item["vector"]
        return vector if isinstance(vector, list) else None

    def delete(
        self,
        collection: str,
        item_id: str,
        user_id: str,
        agent_id: str,
    ) -> None:
        """Delete a vector."""
        if collection not in self.collections:
            return

        item = self.collections[collection].get(item_id)
        if item and item["user_id"] == user_id and item["agent_id"] == agent_id:
            del self.collections[collection][item_id]
            self._save()

    def query(
        self,
        collection: str,
        query_vector: list[float],
        user_id: str,
        agent_id: str,
        top_k: int = 5,
    ) -> list[tuple[str, float]]:
        """Query for similar vectors using cosine similarity."""
        if collection not in self.collections:
            return []

        # Filter by user_id and agent_id
        filtered_items = [
            (item_id, item_data["vector"])
            for item_id, item_data in self.collections[collection].items()
            if item_data["user_id"] == user_id and item_data["agent_id"] == agent_id
        ]

        if not filtered_items:
            return []

        # Compute cosine similarities
        q = np.array(query_vector, dtype=np.float32)
        results: list[tuple[str, float]] = []

        for item_id, vector in filtered_items:
            v = np.array(vector, dtype=np.float32)
            similarity = self._cosine_similarity(q, v)
            results.append((item_id, similarity))

        # Sort by similarity (descending) and return top_k
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def list_all(
        self,
        collection: str,
        user_id: str,
        agent_id: str,
        include_text: bool = False,
    ) -> list[tuple[str, list[float]]] | list[tuple[str, list[float], str | None]]:
        """List all vectors for a user-agent pair, optionally with text."""
        if collection not in self.collections:
            return []

        if include_text:
            return [
                (item_id, item_data["vector"], item_data.get("text"))
                for item_id, item_data in self.collections[collection].items()
                if item_data["user_id"] == user_id and item_data["agent_id"] == agent_id
            ]
        else:
            return [
                (item_id, item_data["vector"])
                for item_id, item_data in self.collections[collection].items()
                if item_data["user_id"] == user_id and item_data["agent_id"] == agent_id
            ]

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-9
        return float(np.dot(a, b) / denom)

    def close(self) -> None:
        """Save and close the database."""
        self._save()
