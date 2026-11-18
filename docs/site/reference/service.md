# MemoryService

`MemoryService` is the local, embedding-only composition root. Agents or applications prepare memory content before calling the service; the service does not generate it with an LLM.

## Configure the service

```python
from memu.app import MemoryService

service = MemoryService(
    database_config={
        "metadata_store": {
            "provider": "sqlite",
            "dsn": "sqlite:///memu.sqlite3",
        },
    },
    embedding_profiles={"default": {"provider": "openai"}},
)
```

Set `OPENAI_API_KEY` in the process environment for this example. The default model is `text-embedding-3-small`. Constructor options are `database_config`, `embedding_profiles`, `progressive_retrieve_config`, and `user_config`.

For explicit credentials use `api_key` inside an embedding profile; use `embed_model` for a model override. See [Configuration](./configuration.md) for storage choices and the separate CLI environment loader.

## Three async entry points

| Method | Inputs | Result |
| --- | --- | --- |
| `list_all_recall_files` | `where=None`, keyword-only `cursor=None`, `limit` | `recall_files`, `next_cursor` |
| `progressive_retrieve` | `query`, `where=None` | `segments`, `files`, `resources` |
| `commit_results` | Keyword-only `recall_files=None`, `resource=None`, `user=None` | `recall_files`, `resources` |

`list_all_recall_files` returns one page across tracks. Follow `next_cursor` until it is `None`; `limit` must be positive. `progressive_retrieve` rejects blank queries and ranks file segments and resources using embeddings. Its file list rolls up the matched segments.

`commit_results` accepts prepared recall files (`name`, `track`, `description`, `content`) and resources (`path`, `description`). Notice the singular input keyword `resource`, and plural output key `resources`. Recall-file identity is the name within its track and user scope.

## Commit, retrieve, and list

After configuring `service` above, run this with `asyncio.run(example())` in a script:

```python
async def example():
    scope = {"user_id": "alice"}
    await service.commit_results(
        recall_files=[{
            "name": "Project preferences",
            "track": "memory",
            "description": "Alice's repository preferences",
            "content": "# Preferences\nUse small, verified changes.",
        }],
        user=scope,
    )
    result = await service.progressive_retrieve(
        "How should I change this repository?", where=scope,
    )
    for segment in result["segments"]:
        print(segment["text"])

    cursor = None
    while True:
        page = await service.list_all_recall_files(
            where=scope, cursor=cursor, limit=20,
        )
        print([item["name"] for item in page["recall_files"]])
        cursor = page["next_cursor"]
        if cursor is None:
            break
```

This example makes embedding requests and writes to the SQLite store. Use a test database when trying it.

## Scope and failure handling

The default user model provides `user_id` and `agent_id`. Configure a custom model through `user_config` when needed. Pass the intended `user` on writes and `where` on reads. Unknown filter fields raise `ValueError`; an omitted scope does not provide tenant isolation.

An embedding failure during `commit_results` occurs before writes. Storage failures may leave partial writes; the whole call is not an atomic storage transaction. Handle errors explicitly before advancing application processing state.

Retrieval settings live under `progressive_retrieve_config.file` and `.resource` (enabled flags and top-k; file also supports tracks). Host adapter output is a separate, compact presentation described in [Host adapters](../hosts/index.md).
