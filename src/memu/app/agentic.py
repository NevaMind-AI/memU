from __future__ import annotations

import base64
import binascii
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

if TYPE_CHECKING:
    from memu.app.settings import ProgressiveRetrieveConfig
    from memu.database.interfaces import Database
    from memu.database.models import RecallFile, Resource


# Default recall-file page size for ``list_all_recall_files`` (ADR 0014). Callers
# follow ``next_cursor`` to reassemble the full set; the page size only bounds the
# per-call read/serialization/response, not the total returned.
DEFAULT_PAGE_LIMIT = 50


def _encode_cursor(after: tuple[str, str, str] | None) -> str | None:
    """Opaque token for a ``(track, name, id)`` keyset position (``None`` = end)."""
    if after is None:
        return None
    return base64.urlsafe_b64encode(json.dumps(list(after)).encode()).decode()


def _decode_cursor(cursor: str | None) -> tuple[str, str, str] | None:
    """Inverse of :func:`_encode_cursor`; a blank/absent cursor starts at the top."""
    if not cursor:
        return None
    try:
        decoded = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
    except (binascii.Error, ValueError) as exc:
        msg = "invalid cursor"
        raise ValueError(msg) from exc
    if not isinstance(decoded, list) or len(decoded) != 3 or not all(isinstance(value, str) for value in decoded):
        msg = "invalid cursor"
        raise ValueError(msg)
    return (decoded[0], decoded[1], decoded[2])


async def _embed_one(embed_client: Any, text: str) -> list[float]:
    """One text in, one vector out.

    ``embed`` returns ``(vectors, raw_response)`` — the raw response carries
    provider usage metadata (see :class:`memu.embedding.base.EmbeddingClient`).
    Every call site here wants just the vector; indexing the tuple with ``[0]``
    would hand back the whole vectors list instead.
    """
    vectors: list[list[float]]
    vectors, _ = await embed_client.embed([text])
    return vectors[0]


_UNRESOLVED_TICKET = "embedding ticket redeemed without a planned vector"
_VECTOR_COUNT_MISMATCH = "embedding provider returned the wrong number of vectors"
_REINDEX_PAYLOAD = "reindex cannot be combined with recall_files, resource, or user"


class _EmbeddingBatch:
    """Collects every text a commit needs vectorized, then resolves them at once.

    Planning registers a text and gets back a ticket; the write phase redeems
    the ticket for a vector. That indirection is what lets a commit do all of
    its embedding in a single provider round-trip, before it has written
    anything — see :meth:`AgenticMixin.commit_results`. Identical texts share a
    ticket, so a line repeated across files is paid for once.
    """

    def __init__(self) -> None:
        self._tickets: dict[str, int] = {}
        self._texts: list[str] = []
        self._vectors: list[list[float]] = []

    def request(self, text: str) -> int:
        ticket = self._tickets.get(text)
        if ticket is None:
            ticket = len(self._texts)
            self._tickets[text] = ticket
            self._texts.append(text)
        return ticket

    async def resolve(self, embed_client: Any) -> None:
        """Embed every registered text — the one fallible step of a commit.

        A commit with nothing to embed (a re-commit whose descriptions, captions
        and content are all unchanged) must not call the provider at all.
        """
        if not self._texts:
            return
        vectors, _ = await embed_client.embed(self._texts)
        if len(vectors) != len(self._texts):
            raise ValueError(_VECTOR_COUNT_MISMATCH)
        self._vectors = vectors

    def vector(self, ticket: int | None) -> list[float]:
        """Redeem a ticket. ``None`` means planning and writing disagree."""
        if ticket is None:
            raise ValueError(_UNRESOLVED_TICKET)
        return self._vectors[ticket]


@dataclass
class _ResourcePlan:
    """One resource's pending write, its caption vector already requested.

    ``existing`` is the row the write updates in place, ``None`` for a url the
    store has never seen. ``caption_ticket`` is set only when a vector actually
    has to be fetched, so an unchanged caption keeps the one already stored.
    ``stale_ids`` are surplus rows for the same url, dropped after the survivor
    is written.
    """

    url: str
    caption: str | None
    caption_ticket: int | None
    existing: Resource | None
    stale_ids: list[str]


@dataclass
class _SegmentPlan:
    """One file's segment reconciliation: which to drop, which to insert."""

    stale_ids: list[str]
    additions: list[tuple[str, int]]


@dataclass
class _RecallFilePlan:
    """One recall file's pending write.

    ``create_ticket`` is set exactly when the file is new (it carries the
    file-level vector the row is created with); ``description_ticket`` exactly
    when an existing file's description changed and needs re-embedding.
    """

    name: str
    track: str
    description: str
    content: str
    existing: RecallFile | None
    create_ticket: int | None
    description_ticket: int | None
    segments: _SegmentPlan


class AgenticMixin:
    if TYPE_CHECKING:
        _get_database: Callable[[], Database]
        _normalize_where: Callable[[Mapping[str, Any] | None], dict[str, Any]]
        _model_dump_without_embeddings: Callable[[BaseModel], dict[str, Any]]
        _get_embedding_client: Callable[..., Any]
        _get_embedding_space: Callable[..., str]
        progressive_retrieve_config: ProgressiveRetrieveConfig
        user_model: type[BaseModel]

    async def list_all_recall_files(
        self,
        where: dict[str, Any] | None = None,
        *,
        cursor: str | None = None,
        limit: int = DEFAULT_PAGE_LIMIT,
    ) -> dict[str, Any]:
        """List one keyset page of RecallFiles across every track (ADR 0014).

        No ``track`` filter is forced (ADR 0006), so skill-track files are
        included alongside memory-track ones. The page is ordered by
        ``(track, name, id)`` and returned with ``next_cursor``; a ``None``
        ``next_cursor`` marks the last page. Callers follow the cursor to walk
        the full set — ordering on the domain identity ``(track, name)`` (unique
        within a scope, immutable under commit) is what makes that walk skip- and
        duplicate-free.
        """
        if limit < 1:
            msg = "limit must be greater than zero"
            raise ValueError(msg)
        store = self._get_database()
        where_filters = self._normalize_where(where)
        recall_files, next_after = store.recall_file_repo.list_recall_files_page(
            where_filters, after=_decode_cursor(cursor), limit=limit
        )
        recall_files_list = [self._model_dump_without_embeddings(recall_file) for recall_file in recall_files]
        return {"recall_files": recall_files_list, "next_cursor": _encode_cursor(next_after)}

    async def progressive_retrieve(
        self,
        query: str,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Single-shot, LLM-free retrieval over the segment/file/resource layers.

        The stages run sequentially in-line: the query is embedded once and used
        to rank two layers by vector similarity; no intention routing,
        sufficiency checks, or summarization:

        * ``segments``: :class:`RecallFileSegment` slices ranked by embedding,
          ``file.top_k`` of them.
        * ``files``: the :class:`RecallFile`\\ s pointed to by those segments — not
          a ranked search, just a roll-up. Each file's score is the max score of
          the segments that point to it.
        * ``resources``: workspace-track resources ranked by embedding,
          ``resource.top_k`` of them.

        Returns ``segments``, ``files``, and ``resources``.
        """
        if not query or not query.strip():
            raise ValueError("empty_query")
        store = self._get_database()
        embedding_space = self._get_embedding_space()
        store.assert_embedding_space(embedding_space, initialize=False)
        where_filters = self._normalize_where(where)
        config = self.progressive_retrieve_config
        embed_client = self._get_embedding_client("embedding")
        query_vector = await _embed_one(embed_client, query)
        store.assert_embedding_space(embedding_space)

        segment_hits, segment_pool = self._recall_segments(
            store=store, where_filters=where_filters, query_vector=query_vector, enabled=config.file.enabled
        )
        file_hits, file_pool = self._collect_files(
            store=store, where_filters=where_filters, segment_hits=segment_hits, segment_pool=segment_pool
        )
        resource_hits, resource_pool = self._recall_resources(
            store=store, where_filters=where_filters, query_vector=query_vector, enabled=config.resource.enabled
        )

        return {
            "segments": self._materialize_hits(segment_hits, segment_pool),
            "files": self._materialize_hits(file_hits, file_pool),
            "resources": self._materialize_hits(resource_hits, resource_pool),
        }

    def _recall_segments(
        self,
        *,
        store: Database,
        where_filters: dict[str, Any],
        query_vector: list[float],
        enabled: bool,
    ) -> tuple[list[tuple[str, float]], dict[str, Any]]:
        """Rank :class:`RecallFileSegment` slices by embedding similarity.

        The ranking belongs to the repo (:meth:`RecallFileSegmentRepo.vector_search_segments`),
        which is what lets a backend with a native vector index answer from one
        indexed query; backends without one inherit a brute-force scan of the
        same scope. Either way the scope is optionally narrowed to the
        configured tracks via the denormalized ``track``.

        The returned pool holds only the hits — everything downstream
        (:meth:`_collect_files`, :meth:`_materialize_hits`) looks up hit ids and
        nothing else, so there is no reason to carry the full corpus along.
        """
        if not enabled:
            return [], {}

        segment_where = dict(where_filters)
        tracks = self.progressive_retrieve_config.file.tracks
        if tracks:
            segment_where["track__in"] = list(tracks)
        hits = store.recall_file_segment_repo.vector_search_segments(
            query_vector,
            self.progressive_retrieve_config.file.top_k,
            where=segment_where,
        )
        return [(seg.id, score) for seg, score in hits], {seg.id: seg for seg, _ in hits}

    def _collect_files(
        self,
        *,
        store: Database,
        where_filters: dict[str, Any],
        segment_hits: list[tuple[str, float]],
        segment_pool: dict[str, Any],
    ) -> tuple[list[tuple[str, float]], dict[str, Any]]:
        """Roll the ranked segments up to their files (no ranked file search).

        Every file pointed to by a top segment is returned; a file's score is the
        max score across the segments that point to it.
        """
        file_pool = store.recall_file_repo.list_recall_files(where_filters)

        file_scores: dict[str, float] = {}
        for seg_id, score in segment_hits:
            seg = segment_pool.get(seg_id)
            if seg is None:
                continue
            fid = seg.recall_file_id
            if fid not in file_pool:
                continue
            score = float(score)
            if fid not in file_scores or score > file_scores[fid]:
                file_scores[fid] = score

        # Preserve descending-score order so the response reads best-first.
        file_hits = sorted(file_scores.items(), key=lambda kv: kv[1], reverse=True)
        return file_hits, file_pool

    def _recall_resources(
        self,
        *,
        store: Database,
        where_filters: dict[str, Any],
        query_vector: list[float],
        enabled: bool,
    ) -> tuple[list[tuple[str, float]], dict[str, Any]]:
        """Rank workspace-track resources by embedding similarity.

        Only ``track="workspace"`` resources (the kind :meth:`commit_results`
        writes) are surfaced; other tracks are excluded.
        """
        if not enabled:
            return [], {}

        resource_where = {**where_filters, "track": "workspace"}
        resource_pool = store.resource_repo.list_resources(resource_where)
        resource_hits = store.resource_repo.vector_search_resources(
            query_vector, self.progressive_retrieve_config.resource.top_k, where=resource_where
        )
        return resource_hits, resource_pool

    def _materialize_hits(self, hits: Sequence[tuple[str, float]], pool: dict[str, Any]) -> list[dict[str, Any]]:
        """Expand ``(id, score)`` hits into scored, embedding-free dicts."""
        out = []
        for _id, score in hits:
            obj = pool.get(_id)
            if not obj:
                continue
            data = self._model_dump_without_embeddings(obj)
            data["score"] = float(score)
            out.append(data)
        return out

    async def commit_results(
        self,
        *,
        recall_files: list[dict[str, Any]] | None = None,
        resource: list[dict[str, Any]] | None = None,
        user: dict[str, Any] | None = None,
        reindex: bool = False,
    ) -> dict[str, Any]:
        """Persist externally-prepared resources and recall files into the store.

        Takes items that were already preprocessed/synthesized off-service (see
        :mod:`memu.hosts.bridging.pipeline`), so it runs no ingest/preprocess/LLM
        steps — just create-or-update straight into storage:

        - ``resource`` — a list of ``{path, description}`` records. Each is a
          :class:`Resource` keyed by ``url`` (``= path``); the description becomes the
          embedded caption used for INDEX/resource recall.
        - ``recall_files`` — a list of ``{name, track, description, content}`` records. Each
          is a :class:`RecallFile` keyed by ``name`` within its ``track`` (``memory``/``skill``),
          with the same track-specific segment (re)generation as the workspace path.

        A commit that cannot reach the embedding provider writes nothing at all, so
        callers may retry it wholesale — which is what makes the bridging pipeline's
        "advance state on durable success, not intent" (#518) hold. Storage failures
        carry no such guarantee; only the embedding step is hoisted clear of the writes.
        """
        store = self._get_database()
        embedding_space = self._get_embedding_space()
        if reindex:
            if recall_files or resource or user:
                raise ValueError(_REINDEX_PAYLOAD)
            return await self._reindex_embeddings(store=store, embedding_space=embedding_space)
        store.assert_embedding_space(embedding_space, initialize=False)
        user_scope = self.user_model(**user).model_dump() if user is not None else None
        embed_client = self._get_embedding_client("embedding")
        user_data = dict(user_scope or {})

        # Plan, embed, write — strictly in that order, never interleaved. Each
        # repo call commits its own transaction, so there is no rollback to fall
        # back on: anything written before a failure stays written. Embedding is
        # the only step here that can fail (a rate limit, a dead provider), so
        # hoisting all of it ahead of the first write is what makes a failed
        # commit a no-op rather than a half-applied one. Planning reads freely —
        # reads leave nothing behind.
        batch = _EmbeddingBatch()
        resource_plans = self._plan_resources(resource or [], store=store, user_scope=user_scope, batch=batch)
        file_plans = self._plan_recall_files(recall_files or [], store=store, user_data=user_data, batch=batch)

        await batch.resolve(embed_client)
        store.assert_embedding_space(embedding_space)

        committed_resources = self._write_resources(resource_plans, store=store, user_data=user_data, batch=batch)
        committed_files = self._write_recall_files(file_plans, store=store, user_data=user_data, batch=batch)
        return {
            "resources": [self._model_dump_without_embeddings(r) for r in committed_resources],
            "recall_files": [self._model_dump_without_embeddings(f) for f in committed_files],
        }

    async def _reindex_embeddings(self, *, store: Database, embedding_space: str) -> dict[str, int]:
        """Replace every stored vector in one backend transaction."""
        batch = _EmbeddingBatch()
        resource_tickets = {
            item.id: batch.request(item.caption)
            for item in store.resource_repo.list_resources().values()
            if item.caption
        }
        file_tickets = {
            item.id: batch.request(f"{item.name}: {item.description}" if item.description else item.name)
            for item in store.recall_file_repo.list_recall_files().values()
        }
        segment_tickets = {item.id: batch.request(item.text) for item in store.recall_file_segment_repo.list_segments()}
        await batch.resolve(self._get_embedding_client("embedding"))
        store.replace_all_embeddings(
            resources={item_id: batch.vector(ticket) for item_id, ticket in resource_tickets.items()},
            recall_files={item_id: batch.vector(ticket) for item_id, ticket in file_tickets.items()},
            segments={item_id: batch.vector(ticket) for item_id, ticket in segment_tickets.items()},
            embedding_space=embedding_space,
        )
        return {
            "resources": len(resource_tickets),
            "recall_files": len(file_tickets),
            "segments": len(segment_tickets),
        }

    def _plan_resources(
        self,
        resources: list[dict[str, Any]],
        *,
        store: Database,
        user_scope: dict[str, Any] | None,
        batch: _EmbeddingBatch,
    ) -> list[_ResourcePlan]:
        """Resolve each ``{path, description}`` against the store and request its vector.

        A url the store already holds is planned as an in-place update, and its caption
        re-embedded only when it actually changed — the same rule the recall-file path
        applies to descriptions. A row that somehow carries a caption but no vector is
        re-embedded regardless, so a legacy or half-written row heals on recommit.

        Reads and requests only — see :meth:`commit_results` for why no write
        may happen here. Repeated paths within one payload collapse to their
        last occurrence: every plan is built against the same pre-commit
        snapshot, so two plans for one url would each miss the other's write and
        leave a duplicate behind.
        """
        deduped: dict[str, dict[str, Any]] = {}
        for item in resources:
            url = (item.get("path") or "").strip()
            if url:
                deduped[url] = item
        if not deduped:
            return []

        # One listing for the whole payload; this used to be re-read per item.
        existing = list(store.resource_repo.list_resources(where=user_scope or None).values())
        plans: list[_ResourcePlan] = []
        for url, item in deduped.items():
            caption = (item.get("description") or "").strip() or None
            # The first row for this url is the one the write keeps; any others are
            # duplicates an older commit path left behind.
            matches = [res for res in existing if res.url == url]
            current = matches[0] if matches else None

            caption_ticket = None
            if caption is not None and (current is None or current.caption != caption or not current.embedding):
                caption_ticket = batch.request(caption)

            plans.append(
                _ResourcePlan(
                    url=url,
                    caption=caption,
                    caption_ticket=caption_ticket,
                    existing=current,
                    stale_ids=[res.id for res in matches[1:]],
                )
            )
        return plans

    def _write_resources(
        self,
        plans: list[_ResourcePlan],
        *,
        store: Database,
        user_data: dict[str, Any],
        batch: _EmbeddingBatch,
    ) -> list[Resource]:
        """Apply the planned resource writes, every vector already in hand.

        A url the store already holds is updated in place, so its ``id`` and
        ``created_at`` survive a recommit the way a recall file's do; only a genuinely
        new url creates a row. Nothing is deleted to make room for a write — surplus
        duplicates go after the survivor is written, so no failure can leave a url with
        no row at all.
        """
        committed: list[Resource] = []
        for plan in plans:
            embedding: list[float] | None
            if plan.caption_ticket is not None:
                embedding = batch.vector(plan.caption_ticket)
            elif plan.caption and plan.existing is not None:
                # Caption unchanged, so no vector was fetched: carry the stored one over.
                embedding = plan.existing.embedding
            else:
                # No caption, nothing to rank on. Clears whatever the row held.
                embedding = None

            if plan.existing is None:
                written = store.resource_repo.create_resource(
                    url=plan.url,
                    local_path=plan.url,
                    caption=plan.caption,
                    embedding=embedding,
                    user_data=dict(user_data),
                    # progressive_retrieve's resource layer filters on track="workspace";
                    # commit is now the only resource writer, so tag it accordingly.
                    track="workspace",
                )
            else:
                written = store.resource_repo.update_resource(
                    resource_id=plan.existing.id,
                    local_path=plan.url,
                    caption=plan.caption,
                    embedding=embedding,
                    # Re-tagged on every write, not only on create: a row an earlier
                    # writer left on another track has to become findable again.
                    track="workspace",
                )
            for stale_id in plan.stale_ids:
                store.resource_repo.delete_resource(stale_id)
            committed.append(written)
        return committed

    def _plan_recall_files(
        self,
        recall_files: list[dict[str, Any]],
        *,
        store: Database,
        user_data: dict[str, Any],
        batch: _EmbeddingBatch,
    ) -> list[_RecallFilePlan]:
        """Resolve each ``{name, track, description, content}`` and request its vectors.

        Keyed by ``name`` within the record's ``track`` (``memory``/``skill``). New files embed
        their ``name: description`` for file-level recall. Existing files always take the new
        content and re-embed only when the description actually changed — commit always carries
        a description (read from the local file), but it's usually unchanged.

        Reads and requests only (see :meth:`commit_results`). Repeated ``(track, name)`` pairs
        collapse to their last occurrence, for the same reason paths do in
        :meth:`_plan_resources`.
        """
        deduped: dict[tuple[str, str], dict[str, Any]] = {}
        for item in recall_files:
            name = (item.get("name") or "").strip()
            if name:
                deduped[(item.get("track") or "memory", name)] = item

        # One listing per distinct track; this used to be re-read per file.
        existing_by_track: dict[str, dict[str, RecallFile]] = {
            track: {
                f.name: f
                for f in store.recall_file_repo.list_recall_files(where={**user_data, "track": track}).values()
            }
            for track in {track for track, _ in deduped}
        }

        plans: list[_RecallFilePlan] = []
        for (track, name), item in deduped.items():
            description = (item.get("description") or "").strip()
            content = (item.get("content") or "").strip()
            existing = existing_by_track[track].get(name)

            create_ticket = None
            description_ticket = None
            if existing is None:
                create_ticket = batch.request(f"{name}: {description}" if description else name)
            elif description and description != existing.description:
                description_ticket = batch.request(f"{name}: {description}")

            # The description the row will hold *after* the write — which is what the
            # skill track builds its segment text from, so it must be resolved here
            # rather than read back off a freshly-updated file.
            # ``description_ticket is not None``, never a truthiness test: ticket 0 is
            # a perfectly good ticket and the first one every commit hands out.
            settled_description = (
                description if existing is None or description_ticket is not None else existing.description
            )
            plans.append(
                _RecallFilePlan(
                    name=name,
                    track=track,
                    description=description,
                    content=content,
                    existing=existing,
                    create_ticket=create_ticket,
                    description_ticket=description_ticket,
                    segments=self._plan_segments(
                        name=name,
                        description=settled_description,
                        content=content,
                        file_track=track,
                        existing=existing,
                        store=store,
                        batch=batch,
                    ),
                )
            )
        return plans

    def _plan_segments(
        self,
        *,
        name: str,
        description: str,
        content: str,
        file_track: str,
        existing: RecallFile | None,
        store: Database,
        batch: _EmbeddingBatch,
    ) -> _SegmentPlan:
        """Diff a file's stored segments against the texts it will have after the write.

        Drop-and-add on the difference only: segments whose text disappeared are deleted and
        only genuinely new texts are embedded and inserted, so unchanged lines keep their
        embedding.
        """
        new_texts = self._commit_segment_texts_for_file(
            name=name, description=description, content=content, file_track=file_track
        )
        # A file that does not exist yet cannot have stored segments, so it needs no read.
        stored = store.recall_file_segment_repo.list_segments_for_file(existing.id) if existing else []
        stored_texts = {seg.text for seg in stored}
        new_set = set(new_texts)
        return _SegmentPlan(
            stale_ids=[seg.id for seg in stored if seg.text not in new_set],
            additions=[(text, batch.request(text)) for text in new_texts if text not in stored_texts],
        )

    def _write_recall_files(
        self,
        plans: list[_RecallFilePlan],
        *,
        store: Database,
        user_data: dict[str, Any],
        batch: _EmbeddingBatch,
    ) -> list[RecallFile]:
        """Apply the planned recall-file and segment writes, every vector already in hand."""
        committed: list[RecallFile] = []
        for plan in plans:
            file = plan.existing
            if file is None:
                file = store.recall_file_repo.get_or_create_recall_file(
                    name=plan.name,
                    description=plan.description,
                    embedding=batch.vector(plan.create_ticket),
                    user_data=user_data,
                    track=plan.track,
                )
            redescribed = plan.description_ticket is not None
            file = store.recall_file_repo.update_recall_file(
                recall_file_id=file.id,
                description=plan.description if redescribed else None,
                embedding=batch.vector(plan.description_ticket) if redescribed else None,
                content=plan.content,
            )
            for stale_id in plan.segments.stale_ids:
                store.recall_file_segment_repo.delete_segment(stale_id)
            for text, ticket in plan.segments.additions:
                store.recall_file_segment_repo.create_segment(
                    recall_file_id=file.id,
                    track=plan.track,
                    text=text,
                    embedding=batch.vector(ticket),
                    user_data=dict(user_data),
                )
            committed.append(file)
        return committed

    @staticmethod
    def _commit_segment_texts_for_file(*, name: str, description: str, content: str, file_track: str) -> list[str]:
        """Compute a file's searchable segment texts (ADR 0007 L2 items), track-specific.

        Takes the values the file will hold once written rather than a persisted
        :class:`RecallFile`, so the texts — and their embeddings — can be settled before
        anything is written.

        - ``skill``: a single ``name: ...\\ndescription: ...`` segment for the whole skill.
        - ``memory``: one segment per content line, skipping blank lines and markdown
          headings, de-duplicated while preserving order.
        """
        if file_track == "skill":
            return [f"name: {name}\ndescription: {description}"]

        texts: list[str] = []
        for line in (content or "").split("\n"):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            texts.append(stripped)
        return list(dict.fromkeys(texts))
