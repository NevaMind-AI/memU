from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from memu.database.models import RecallFileSegment
from memu.database.postgres.repositories.base import PostgresRepoBase
from memu.database.postgres.session import SessionManager
from memu.database.repositories.recall_file_segment import RecallFileSegmentRepo
from memu.database.state import DatabaseState


class PostgresRecallFileSegmentRepo(PostgresRepoBase, RecallFileSegmentRepo):
    def __init__(
        self,
        *,
        state: DatabaseState,
        recall_file_segment_model: type[RecallFileSegment],
        sqla_models: Any,
        sessions: SessionManager,
        scope_fields: list[str],
        use_vector: bool = True,
    ) -> None:
        super().__init__(
            state=state,
            sqla_models=sqla_models,
            sessions=sessions,
            scope_fields=scope_fields,
            use_vector=use_vector,
        )
        self._recall_file_segment_model = recall_file_segment_model
        self.segments: list[RecallFileSegment] = self._state.segments

    def _row_to_record(self, row: Any) -> RecallFileSegment:
        return RecallFileSegment(
            id=row.id,
            recall_file_id=row.recall_file_id,
            track=row.track,
            text=row.text,
            embedding=self._normalize_embedding(row.embedding),
            created_at=row.created_at,
            updated_at=row.updated_at,
            **self._scope_kwargs_from(row),
        )

    def _cache_segment(self, row: Any) -> RecallFileSegment:
        seg = self._row_to_record(row)
        if not any(s.id == seg.id for s in self.segments):
            self.segments.append(seg)
        return seg

    def list_segments(self, where: Mapping[str, Any] | None = None) -> list[RecallFileSegment]:
        from sqlmodel import select

        filters = self._build_filters(self._sqla_models.RecallFileSegment, where)
        with self._sessions.session() as session:
            rows = session.scalars(select(self._sqla_models.RecallFileSegment).where(*filters)).all()
            return [self._cache_segment(row) for row in rows]

    def list_segments_for_file(self, recall_file_id: str) -> list[RecallFileSegment]:
        return self.list_segments({"recall_file_id": recall_file_id})

    def vector_search_segments(
        self,
        query_vec: list[float],
        top_k: int,
        where: Mapping[str, Any] | None = None,
        *,
        query_text: str | None = None,
    ) -> list[tuple[RecallFileSegment, float]]:
        """Rank segments with pgvector, inside the database.

        Cosine-only: Postgres orders and truncates, so only ``top_k`` rows cross
        the wire. Hybrid: take ``candidate_k`` cosine hits from the index, BM25
        over scoped texts, RRF-fuse the two lists, then cut to ``top_k``.

        A deployment that asked for a non-pgvector index (``vector_index.provider``)
        gets the inherited scan instead, even though the column type is ``VECTOR``
        either way.
        """
        if top_k <= 0:
            return []
        if not self._use_vector:
            return super().vector_search_segments(query_vec, top_k, where, query_text=query_text)

        from sqlmodel import select

        from memu.hybrid import hybrid_candidate_k, maybe_hybrid_topk

        hybrid = bool(query_text and query_text.strip())
        cosine_k = hybrid_candidate_k(top_k) if hybrid else top_k
        model = self._sqla_models.RecallFileSegment
        # ``<=>`` yields cosine *distance*; the contract is similarity, hence
        # ``1 - distance`` below. Rows without an embedding are filtered out
        # rather than left to sort to whichever end NULLs land on.
        distance = model.embedding.cosine_distance(query_vec)
        filters = [*self._build_filters(model, where), model.embedding.is_not(None)]
        with self._sessions.session() as session:
            rows = session.exec(
                select(model, distance.label("distance")).where(*filters).order_by(distance).limit(cosine_k)
            ).all()
            cosine_pairs = [(self._cache_segment(row), 1.0 - float(dist)) for row, dist in rows]
        if not hybrid:
            return cosine_pairs

        pool = self.list_segments(where)
        by_id = {seg.id: seg for seg in pool}
        for seg, _ in cosine_pairs:
            by_id.setdefault(seg.id, seg)
        fused = maybe_hybrid_topk(
            query_text=query_text,
            cosine_hits=[(seg.id, score) for seg, score in cosine_pairs],
            texts={seg.id: seg.text for seg in by_id.values()},
            top_k=top_k,
            bm25_limit=cosine_k,
        )
        return [(by_id[seg_id], score) for seg_id, score in fused if seg_id in by_id]

    def create_segment(
        self,
        *,
        recall_file_id: str,
        text: str,
        embedding: list[float] | None,
        user_data: dict[str, Any],
        track: str = "memory",
    ) -> RecallFileSegment:
        now = self._now()
        row = self._recall_file_segment_model(
            recall_file_id=recall_file_id,
            track=track,
            text=text,
            embedding=self._prepare_embedding(embedding),
            created_at=now,
            updated_at=now,
            **user_data,
        )
        with self._sessions.session() as session:
            session.add(row)
            session.commit()
            session.refresh(row)
            return self._cache_segment(row)

    def delete_segment(self, segment_id: str) -> None:
        from sqlmodel import delete

        with self._sessions.session() as session:
            session.exec(
                delete(self._sqla_models.RecallFileSegment).where(self._sqla_models.RecallFileSegment.id == segment_id)
            )
            session.commit()
        self.segments[:] = [seg for seg in self.segments if seg.id != segment_id]

    def delete_segments_for_file(self, recall_file_id: str) -> list[RecallFileSegment]:
        from sqlmodel import delete, select

        with self._sessions.session() as session:
            rows = session.scalars(
                select(self._sqla_models.RecallFileSegment).where(
                    self._sqla_models.RecallFileSegment.recall_file_id == recall_file_id
                )
            ).all()
            removed = [self._row_to_record(row) for row in rows]
            if removed:
                session.exec(
                    delete(self._sqla_models.RecallFileSegment).where(
                        self._sqla_models.RecallFileSegment.recall_file_id == recall_file_id
                    )
                )
                session.commit()
        self.segments[:] = [seg for seg in self.segments if seg.recall_file_id != recall_file_id]
        return removed

    def clear_segments(self, where: Mapping[str, Any] | None = None) -> list[RecallFileSegment]:
        from sqlmodel import delete, select

        filters = self._build_filters(self._sqla_models.RecallFileSegment, where)
        with self._sessions.session() as session:
            rows = session.scalars(select(self._sqla_models.RecallFileSegment).where(*filters)).all()
            removed = [self._row_to_record(row) for row in rows]
            if removed:
                session.exec(delete(self._sqla_models.RecallFileSegment).where(*filters))
                session.commit()
        removed_ids = {seg.id for seg in removed}
        self.segments[:] = [seg for seg in self.segments if seg.id not in removed_ids]
        return removed

    def load_existing(self) -> None:
        from sqlmodel import select

        with self._sessions.session() as session:
            rows = session.scalars(select(self._sqla_models.RecallFileSegment)).all()
            for row in rows:
                self._cache_segment(row)


__all__ = ["PostgresRecallFileSegmentRepo"]
