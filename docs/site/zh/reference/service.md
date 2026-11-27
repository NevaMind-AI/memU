# MemoryService

`MemoryService` 是 Local 模式中仅使用 Embedding 的组合根。Agent 或应用在调用前准备好记忆内容；服务本身不通过 LLM 生成内容。

## 配置服务

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

此示例需要在进程环境变量中设置 `OPENAI_API_KEY`，默认模型为 `text-embedding-3-small`。构造函数接受 `database_config`、`embedding_profiles`、`progressive_retrieve_config` 和 `user_config`。

显式凭据使用 Embedding profile 中的 `api_key`；覆盖模型使用 `embed_model`。存储选项及独立的 CLI 环境变量加载方式见[配置参考](./configuration.md)。

## 三个异步入口

| 方法 | 输入 | 返回 |
| --- | --- | --- |
| `list_all_recall_files` | `where=None`，仅限关键字的 `cursor=None`、`limit` | `recall_files`、`next_cursor` |
| `progressive_retrieve` | `query`、`where=None` | `segments`、`files`、`resources` |
| `commit_results` | 仅限关键字的 `recall_files=None`、`resource=None`、`user=None` | `recall_files`、`resources` |

`list_all_recall_files` 返回跨 track 的一页结果，沿 `next_cursor` 读取直到其为 `None`；`limit` 必须大于零。`progressive_retrieve` 拒绝空白查询，通过 Embedding 对文件片段和资源排序；文件列表由命中片段汇总得到。

`commit_results` 接受准备好的 recall file（`name`、`track`、`description`、`content`）和资源（`path`、`description`）。注意输入关键字为单数 `resource`，输出键为复数 `resources`。Recall file 由用户 scope、track 和 name 共同确定身份。

## 提交、检索和列举

配置好上面的 `service` 后，可在脚本中使用 `asyncio.run(example())` 运行：

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

此示例会请求 Embedding 并写入 SQLite。尝试时请使用测试数据库。

## Scope 与失败处理

默认用户模型包含 `user_id` 和 `agent_id`，需要时通过 `user_config` 配置自定义模型。写入传入对应 `user`，读取传入 `where`。未知过滤字段会抛出 `ValueError`；省略 scope 不会提供租户隔离。

`commit_results` 中的 Embedding 失败发生在写入之前。存储失败则可能留下部分写入，整个调用不构成原子的存储事务。应用推进处理状态前应明确处理错误。

检索配置位于 `progressive_retrieve_config.file` 和 `.resource`，包括启用开关和 top-k；file 还支持 tracks。宿主适配器使用另一种紧凑的结果展示，见[宿主接入](../hosts/index.md)。
