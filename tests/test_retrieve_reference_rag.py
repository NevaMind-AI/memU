from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from memu.app import MemoryService


class _FakeEmbeddingClient:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [_vector_for_text(text) for text in texts]


def _vector_for_text(text: str) -> list[float]:
    lowered = text.lower()
    if "orthogonal" in lowered:
        return [0.0, 1.0, 0.0]
    return [1.0, 0.0, 0.0]


class _UserAgentScope(BaseModel):
    user_id: str | None = None
    agent_id: str | None = None


def _build_service(
    *,
    use_category_references: bool,
    top_k: int = 1,
    category_top_k: int = 1,
    user_model: type[BaseModel] | None = None,
) -> MemoryService:
    service = MemoryService(
        llm_profiles={"default": {"api_key": "test-key"}},
        database_config={"metadata_store": {"provider": "inmemory"}},
        user_config={"model": user_model} if user_model is not None else None,
        retrieve_config={
            "method": "rag",
            "route_intention": False,
            "sufficiency_check": False,
            "category": {"enabled": True, "top_k": category_top_k},
            "item": {
                "enabled": True,
                "top_k": top_k,
                "use_category_references": use_category_references,
            },
            "resource": {"enabled": False},
        },
    )
    service._get_embedding_client = lambda *args, **kwargs: _FakeEmbeddingClient()  # type: ignore[method-assign]
    return service


def _seed_item(
    service: MemoryService,
    *,
    summary: str,
    user_id: str,
    embedding: list[float],
    ref_id: str | None = None,
    agent_id: str | None = None,
) -> str:
    store = service.database
    user_data = {"user_id": user_id}
    if agent_id is not None:
        user_data["agent_id"] = agent_id
    resource = store.resource_repo.create_resource(
        url=f"mem://{user_id}/{summary}",
        modality="document",
        local_path="",
        caption=summary,
        embedding=None,
        user_data=user_data,
    )
    item = store.memory_item_repo.create_item(
        resource_id=resource.id,
        memory_type="knowledge",
        summary=summary,
        embedding=embedding,
        user_data=user_data,
    )
    if ref_id is not None:
        store.memory_item_repo.update_item(item_id=item.id, extra={"ref_id": ref_id})
    return item.id


def _seed_category(service: MemoryService, *, user_id: str, summary: str, agent_id: str | None = None) -> str:
    store = service.database
    user_data = {"user_id": user_id}
    if agent_id is not None:
        user_data["agent_id"] = agent_id
    category = store.memory_category_repo.get_or_create_category(
        name=f"Deployments {user_id} {agent_id or 'default'}",
        description="Deployment facts",
        embedding=[1.0, 0.0, 0.0],
        user_data=user_data,
    )
    store.memory_category_repo.update_category(category_id=category.id, summary=summary)
    return category.id


async def _retrieve(service: MemoryService, *, user_id: str = "u1", agent_id: str | None = None) -> dict[str, Any]:
    where = {"user_id": user_id}
    if agent_id is not None:
        where["agent_id"] = agent_id
    return await service.retrieve(
        queries=[{"role": "user", "content": {"text": "Which deployment memory matters?"}}],
        where=where,
    )


async def test_rag_reference_recall_returns_cited_in_scope_item() -> None:
    service = _build_service(use_category_references=True, top_k=1)
    cited_id = _seed_item(
        service,
        summary="API key was missing during deploy",
        user_id="u1",
        embedding=[0.0, 1.0, 0.0],
        ref_id="deploy-key",
    )
    _seed_item(service, summary="Vector-preferred deploy note", user_id="u1", embedding=[1.0, 0.0, 0.0])
    _seed_category(service, user_id="u1", summary="Deployment failed because a key was missing [ref:deploy-key].")

    result = await _retrieve(service)

    assert [item["id"] for item in result["items"]] == [cited_id]


async def test_rag_reference_recall_respects_scope() -> None:
    service = _build_service(use_category_references=True, top_k=2)
    _seed_item(
        service,
        summary="Out-of-scope secret deploy note",
        user_id="u2",
        embedding=[1.0, 0.0, 0.0],
        ref_id="secret-ref",
    )
    in_scope_id = _seed_item(
        service,
        summary="In-scope vector deploy note",
        user_id="u1",
        embedding=[1.0, 0.0, 0.0],
    )
    _seed_category(service, user_id="u1", summary="A different user has a cited secret [ref:secret-ref].")

    result = await _retrieve(service, user_id="u1")

    assert [item["id"] for item in result["items"]] == [in_scope_id]
    assert all(item["user_id"] == "u1" for item in result["items"])


async def test_rag_reference_recall_uses_scoped_ref_when_same_ref_exists_for_two_users() -> None:
    service = _build_service(use_category_references=True, top_k=1)
    in_scope_id = _seed_item(
        service,
        summary="In-scope deploy note with shared ref",
        user_id="u1",
        embedding=[0.0, 1.0, 0.0],
        ref_id="shared-ref",
    )
    _seed_item(
        service,
        summary="Out-of-scope deploy note with shared ref",
        user_id="u2",
        embedding=[1.0, 0.0, 0.0],
        ref_id="shared-ref",
    )
    _seed_category(service, user_id="u1", summary="The in-scope note is cited [ref:shared-ref].")

    result = await _retrieve(service, user_id="u1")

    assert [item["id"] for item in result["items"]] == [in_scope_id]
    assert all(item["user_id"] == "u1" for item in result["items"])


async def test_rag_reference_recall_respects_custom_agent_scope_for_same_ref() -> None:
    service = _build_service(use_category_references=True, top_k=1, user_model=_UserAgentScope)
    in_scope_id = _seed_item(
        service,
        summary="Agent A deploy note",
        user_id="u1",
        agent_id="agent-a",
        embedding=[0.0, 1.0, 0.0],
        ref_id="agent-shared-ref",
    )
    _seed_item(
        service,
        summary="Agent B deploy note",
        user_id="u1",
        agent_id="agent-b",
        embedding=[1.0, 0.0, 0.0],
        ref_id="agent-shared-ref",
    )
    _seed_category(
        service,
        user_id="u1",
        agent_id="agent-a",
        summary="Agent A category cites the shared ref [ref:agent-shared-ref].",
    )

    result = await _retrieve(service, user_id="u1", agent_id="agent-a")

    assert [item["id"] for item in result["items"]] == [in_scope_id]
    assert all(item["agent_id"] == "agent-a" for item in result["items"])


async def test_rag_reference_recall_ignores_out_of_scope_ref_among_multiple_refs() -> None:
    service = _build_service(use_category_references=True, top_k=2)
    in_scope_id = _seed_item(
        service,
        summary="In-scope cited deploy note",
        user_id="u1",
        embedding=[0.0, 1.0, 0.0],
        ref_id="in-scope-ref",
    )
    _seed_item(
        service,
        summary="Out-of-scope cited deploy note",
        user_id="u2",
        embedding=[0.0, 1.0, 0.0],
        ref_id="out-of-scope-ref",
    )
    vector_id = _seed_item(service, summary="In-scope vector deploy note", user_id="u1", embedding=[1.0, 0.0, 0.0])
    _seed_category(
        service,
        user_id="u1",
        summary="One cited note is visible [ref:in-scope-ref], one is not [ref:out-of-scope-ref].",
    )

    result = await _retrieve(service, user_id="u1")

    item_ids = [item["id"] for item in result["items"]]
    assert item_ids == [in_scope_id, vector_id]
    assert all(item["user_id"] == "u1" for item in result["items"])


async def test_rag_reference_recall_nonexistent_ref_continues_with_vector_hits() -> None:
    service = _build_service(use_category_references=True, top_k=1)
    vector_id = _seed_item(service, summary="Vector fallback deploy note", user_id="u1", embedding=[1.0, 0.0, 0.0])
    _seed_category(service, user_id="u1", summary="This category cites a missing item [ref:missing-ref].")

    result = await _retrieve(service, user_id="u1")

    assert [item["id"] for item in result["items"]] == [vector_id]


async def test_rag_reference_recall_dedupes_vector_hit() -> None:
    service = _build_service(use_category_references=True, top_k=3)
    cited_id = _seed_item(
        service,
        summary="Cited item also wins vector search",
        user_id="u1",
        embedding=[1.0, 0.0, 0.0],
        ref_id="dupe-ref",
    )
    _seed_item(service, summary="Other vector item", user_id="u1", embedding=[1.0, 0.0, 0.0])
    _seed_category(service, user_id="u1", summary="The cited item matters [ref:dupe-ref].")

    result = await _retrieve(service)

    item_ids = [item["id"] for item in result["items"]]
    assert item_ids.count(cited_id) == 1


async def test_rag_reference_recall_returns_all_same_scope_items_with_same_ref_id() -> None:
    service = _build_service(use_category_references=True, top_k=2)
    first_id = _seed_item(
        service,
        summary="First item sharing same ref",
        user_id="u1",
        embedding=[0.0, 1.0, 0.0],
        ref_id="ambiguous-ref",
    )
    second_id = _seed_item(
        service,
        summary="Second item sharing same ref",
        user_id="u1",
        embedding=[0.0, 1.0, 0.0],
        ref_id="ambiguous-ref",
    )
    _seed_category(service, user_id="u1", summary="The summary cites an ambiguous ref [ref:ambiguous-ref].")

    result = await _retrieve(service, user_id="u1")

    assert [item["id"] for item in result["items"]] == [first_id, second_id]


async def test_rag_reference_recall_respects_top_k_across_reference_and_vector_hits() -> None:
    service = _build_service(use_category_references=True, top_k=2)
    first_ref_id = _seed_item(
        service,
        summary="First cited deploy note",
        user_id="u1",
        embedding=[0.0, 1.0, 0.0],
        ref_id="first-ref",
    )
    second_ref_id = _seed_item(
        service,
        summary="Second cited deploy note",
        user_id="u1",
        embedding=[0.0, 1.0, 0.0],
        ref_id="second-ref",
    )
    vector_id = _seed_item(service, summary="Vector deploy note", user_id="u1", embedding=[1.0, 0.0, 0.0])
    _seed_category(service, user_id="u1", summary="Two refs should fill top_k [ref:first-ref,second-ref].")

    result = await _retrieve(service, user_id="u1")

    assert [item["id"] for item in result["items"]] == [first_ref_id, second_ref_id]
    assert vector_id not in [item["id"] for item in result["items"]]
    assert len(result["items"]) == 2


async def test_rag_reference_recall_returns_no_items_when_top_k_is_zero() -> None:
    service = _build_service(use_category_references=True, top_k=0)
    _seed_item(
        service,
        summary="Cited deploy note",
        user_id="u1",
        embedding=[0.0, 1.0, 0.0],
        ref_id="zero-limit-ref",
    )
    _seed_item(service, summary="Vector deploy note", user_id="u1", embedding=[1.0, 0.0, 0.0])
    _seed_category(service, user_id="u1", summary="The category cites a note [ref:zero-limit-ref].")

    result = await _retrieve(service, user_id="u1")

    assert result["items"] == []


async def test_rag_reference_recall_disabled_preserves_vector_only_behavior() -> None:
    service = _build_service(use_category_references=False, top_k=1)
    cited_id = _seed_item(
        service,
        summary="Cited but orthogonal deploy note",
        user_id="u1",
        embedding=[0.0, 1.0, 0.0],
        ref_id="disabled-ref",
    )
    vector_id = _seed_item(service, summary="Vector-preferred deploy note", user_id="u1", embedding=[1.0, 0.0, 0.0])
    _seed_category(service, user_id="u1", summary="The category cites the orthogonal note [ref:disabled-ref].")

    result = await _retrieve(service)

    item_ids = [item["id"] for item in result["items"]]
    assert item_ids == [vector_id]
    assert cited_id not in item_ids
