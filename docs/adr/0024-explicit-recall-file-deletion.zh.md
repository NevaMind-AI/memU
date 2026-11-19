# ADR 0024：RecallFile 显式删除与恢复

- 状态：提案；生命周期实现前需完成契约审阅
- 议题：MEM-13；使用方：MEM-9
- 范围：本地存储、Cloud 传输、CLI 与 host 镜像的 RecallFile 生命周期
- [English](0024-explicit-recall-file-deletion.md)

## 已核实的起点

`AgenticMixin`、`AgenticMemoryBackend` 和 `CloudMemoryClient` 恰好提供
`list_all_recall_files`、`progressive_retrieve`、`commit_results` 三个入口。
`commit_results` 按 `(scope, track, name)` 新增或更新，省略文件从不表示删除。
`hosts/bridging/manifest.py` 只记录相对路径与字节哈希，`diff_tracked` 忽略缺失文件。
bridging 和开发者 memorize 均使用它；其中没有后端身份、作用域或版本。

两条 prepare 路径都会把列出的文件写入镜像，但不会移除本地多余文件。因此，仅在后端
隐藏文件仍不够：旧镜像可能再次提交它。本地删除同样不够：prepare 会把权威文件写回来。

仓库已有 `clear_recall_files(where)` 和 `delete_segments_for_file(id)`，但没有可恢复
生命周期。顺序调用这两个方法不能作为安全公共删除接口。SQLite/inmemory 实现了
`AtomicDatabase`，Postgres 没有，其仓库方法各自提交。记录只有时间戳，没有并发版本或
删除标记。

Cloud 当前映射 GET/POST `/api/v4/memory` 和 POST `/api/v4/memory/search`。
客户端未暴露删除。ADR 0014 描述了私有服务端适配器，但当前工作区没有该源码。
本轮匿名 GET `https://api.memu.so/openapi.json` 返回 404。这既不能证明也不能否认
服务端已有删除或恢复能力，仍需服务端契约及隔离测试作用域。本轮没有为测试删除而读取或
改动生产记忆。

## 推荐方案

使用显式 delete 命令，后端采用软删除。普通 commit 继续只新增或更新。本地缺失可以作为
镜像差异报告，但绝不构成删除授权。第一版直接执行显式生命周期命令，暂不引入文件系统
待提交队列。

| 选择 | 意图与安全边界 | 兼容与恢复 |
| --- | --- | --- |
| 从镜像缺失推导删除 | 无法区分误删、列表不完整、目录错误、旧基线和真实意图 | 改变普通 commit 语义，仍需权威基线与恢复机制 |
| 带版本的显式删除 | 精确选定后端目标，拒绝过期决定 | 显式启用，后端回收站支持恢复 |
| 显式暂存意图，由 commit 消费 | 仍需相同目标、版本检查和持久回执 | 可后续增加，但需额外处理队列确认及部分失败 |

保留服务三个入口。为 `commit_results` 增加可选 `recall_file_operations`，接受显式
`delete`/`restore` 记录。生命周期批次不得混入普通 recall-file/resource 写入。
每项操作原子执行，整个生命周期批次也必须原子提交。初期大规模清洗调用方每次只提交一个
目标，让每份文件的成功与重试边界清晰。
为 `list_all_recall_files` 增加 `state="active"|"deleted"`，默认 active，支持按作用域
列回收站。分页游标只能在相同作用域和状态内使用。这些是拟议签名，当前尚不能调用。

这样不增加第四个服务入口。CLI `delete-file` 和 `restore-file` 是调用 `commit_results`
的用户操作。两者均不推进会话游标，不把删除成功当作对话记录成功。服务继续 embedding-only。

## 精确目标与请求契约

拟议调用示例（当前不可执行）：

```python
await backend.commit_results(
    user={"user_id": "isolated-user", "agent_id": "isolated-agent"},
    recall_file_operations=[{
        "operation": "delete",
        "operation_id": "caller-generated-uuid",
        "id": "backend-file-id",
        "track": "memory",
        "name": "exact-backend-name",
        "expected_revision": 7,
    }],
)
```

后端校验全部字段，拒绝未知操作字段及非法 track，按 **ID + 精确 name + track + 全部已配置
scope 字段** 匹配。生命周期查找不规范化名称。目标缺失或不匹配时返回错误，不降级成
按名字搜索或通配匹配。允许明确指定 `skill`；`resource`、工作区文件和原资源 URL 不在
此操作范围内。不提供目录、前缀、通配或整库删除形式。

scope 来自 `UserConfig.model`。先用 `_normalize_where` 校验字段，再强制完整作用域及
精确等值，不允许 `__in`、省略字段或让 `None` 表示通配。只有已配置模型确实没有 scope
字段时，才允许本地无作用域数据库。默认模型已有的无作用域记录需先明确迁移到具体 scope
值，再执行生命周期操作。Cloud 的字面量 `default` 是明确等值，本地 `None` 不得静默
转换为它。Cloud 若还有服务端/project 租户身份，必须由鉴权后的服务配置和回执绑定，
不能信任客户端输入。

调用方先从权威后端列出目标，使用其 ID/revision。本地 manifest 仅是可选提示，不是
删除依据。旧 manifest 需要重新查询；缺失或不完整 manifest 不能授权删除。目标改变后
应基于新 revision 重新审阅，而不是自动换版本重试。普通改名仍是新文件加旧 ID 的显式
删除，不从相似内容或路径消失推导改名。

## 存储、并发与恢复

为 RecallFile 增加 `revision`（正整数、单调递增）和可空 `deleted_at`。
已有记录从 active、revision 1 开始。增加以 `(精确 scope, operation_id)` 为键的持久
操作回执，保存规范请求摘要与结果。保留回执和已删除记录，直到未来另行定义显式清除策略；
本版不自动清除。**推荐第一版无限期保留**，存在存储和隐私成本，不等于安全擦除。
此保留选择需在实现前与用户达成一致。恢复能力以数据库仍然存在为前提；inmemory 的回收站
随进程/数据库丢弃而消失。SQLite/Postgres 可跨重启保留，仍需正常数据库备份。

删除在一次写事务/锁内执行：

1. 先查回执。相同操作 ID 和完全相同请求返回原结果，即使之后已恢复。相同操作 ID 配不同
   请求则冲突。
2. 校验精确 scope 和目标，在取得写所有权后比较 revision。
3. 标记 deleted、递增 revision、删除该文件全部 segment/vector，并在同一事务写入回执。
   为恢复保留正文、description、文件级 embedding 和身份。

普通列表、所有文件查找/向量检索及 segment 检索都必须排除已删除文件。segment 检索还需
在 top-k 排名前关联或过滤 active 父文件，排除历史孤立或过期 segment。只在 top-k 后过滤
会让旧命中挤占有效结果。已删除 description 和文件 embedding 不参与 active 召回。
SQL 缓存只能在提交后失效/发布；预热缓存及其他服务实例必须观察到相同生命周期状态。

普通 commit 写入已删除的 `(scope, track, name)` 必须冲突，即使请求未带 revision。
删除标记继续占用名称，从而阻止旧镜像复活数据。active 写入和生命周期写入都递增 revision；
CAS 与行锁串行化并发更新/删除。更新先完成则删除冲突，删除先完成则更新冲突。
不支持复用名称或隐式恢复。新的操作 ID 携带当前 deleted revision 再次删除，返回
`already_deleted`，不延长保留时间；过期 revision 仍冲突。重复恢复同理返回 `already_active`。

恢复使用相同目标字段、`operation="restore"` 和当前 deleted revision。先按当前 track
切片规则和 embedding profile 重建 segment，包含 description embedding，再发布。
provider 失败时文件仍为 deleted。embedding 返回后在取得写所有权时重新校验 revision；
CAS 冲突不改变存储。原子发布 active 文件、segment、revision 和回执。保留稳定文件 ID、
scope、name、正文及原创建时间。不提供覆盖其他文件的选项。embedding 模型不兼容变更
仍需对整个 active 语料执行正常重建索引；生命周期恢复不负责迁移混用模型的语料库。

超时或崩溃后重试使用完全相同的操作 ID 和请求，取得已保存结果。回执与数据改动必须共同
提交。提交前出错不改变任何数据。批次失败不发布任何项并给出可见错误；成功则每项返回
`operation_id`、目标身份/scope、结果 revision、状态、`deleted_at` 与保留策略。
成功回执的重放表示历史成功，不代表当前状态；后续操作前需刷新目标。后端成功、本地清理
失败时，不得生成新操作 ID 重做数据改动。

## Host 与镜像规则

- 普通文件丢失、空目录、目录选错、旧/缺失/不完整 manifest、prepare 分页不完整均不生成
  删除操作。
- 显式 CLI 目标来自权威列表。展示精确后端、scope、ID、track、name、revision 供审阅，
  要求显式目标参数。执行遵循现有授权，不从文件系统状态推断同意。
- 收到后端回执后，仅在字节仍与已审阅快照一致时删除对应受管理镜像。若本地已编辑则保留并
  明确报告冲突。持久保存回执以重试清理，不推进会话游标。
- 镜像身份元数据独立于可编辑 Markdown，包含后端指纹、精确 scope、ID、track、name、
  revision、内容哈希。只有完整成功的列表读取才能发布新对账代次；中断/部分列表不得清理。
  旧哈希 manifest 继续用于普通 commit，但不能作为删除元数据。
- prepare 根据权威 active/trash 状态对账旧受管理镜像，不清扫不明用户文件。retrieval
  镜像写入也需遵循后端 revision，避免进行中的旧 retrieval 在对账后重建已删除镜像。
  即使旧本地文件残留，删除标记的写入保护仍应守住后端。
- 恢复后读取新权威记录并更新镜像/身份元数据。保留有冲突的本地编辑并报告路径。后端成功、
  镜像失败时保持成功事实，同时明确报告待清理事项。

## 后端与 Cloud 实现前提

生命周期命令启用前，需在 inmemory、SQLite、Postgres 和实际 Cloud 适配器实现协议。
若扩展共享 `AtomicDatabase` 会不必要地改变现有 commit 行为，可增加自行持有事务的
生命周期仓库操作；不能依赖多个仓库独立提交。SQLite 既要处理新库 bootstrap，也要升级
已有数据库；Postgres 增加 Alembic revision。scope/身份唯一性包含 deleted 行；回执具有
scope/operation ID 唯一约束。需验证回滚和多实例可见性。

Cloud 需由维护方明确：

1. 已有删除/恢复能力、路由/schema、鉴权/scope 要求；
2. 存储与独立切片路径的事务、CAS、回执保障；
3. 回收站保留、列表状态和迁移/回填行为；
4. 用于端到端验证的非生产 scope 与版本。

旧服务端可能静默忽略未知可选字段。列表响应需明确宣告 `recall_file_lifecycle_v1` 能力；
Cloud CLI 缺少能力时拒绝操作，成功响应缺少匹配操作回执时按协议错误处理。
旧服务端不能产生删除成功假象。不得猜测 DELETE 路由或降级为清空正文。
私有服务端改动属于其已分配工作区/维护方，本任务不部署它。

## 验证与交付状态

本次已实现：`tests/test_agentic.py` 的回归覆盖，包含 inmemory 和真实 SQLite、bridging
和开发者 memorize、单文件缺失、空镜像、缺失/不完整/过期 manifest、错误目录。
检查普通 commit 后权威文件身份/正文、可检索 segment 与 resource 均保留。
embedding 使用确定性测试替身，不是 Cloud 验证。
验证：`uv run python -m pytest tests/test_agentic.py -q` 的 113 项全部通过，包含新增的
24 个丢失场景。Ruff lint/format、`git diff --check` 及 ADR 相对 Markdown 链接检查通过。
未修改站点源码。

下表是生命周期实现的验收计划，**尚未通过这些测试**：

| 情况 | 必须观察到的后端结果 |
| --- | --- |
| 删除 memory，另一 scope/track 有同名项 | 仅精确目标从 active 读回、description 与 segment/vector 召回消失，其他项不变 |
| 恢复及重启 | 原 ID/正文可读，当前 segment 可用且可检索，SQL 持久性有效 |
| 响应丢失、操作 ID 重复、请求改变 | 同一回执只执行一次，请求改变则冲突，后续恢复后不因重试再次删除 |
| 两实例并发更新/删除/恢复 | 串行结果或版本冲突，无部分状态或过期缓存 |
| 每个改动/回执边界注入失败 | 整批回滚，相同请求重试成功 |
| 恢复时 provider 失败 | 仍为 deleted，不出现部分可检索 segment |
| 旧/空/错误/部分镜像及旧 retrieval | 不隐式删后端或复活数据，冲突可见 |
| 同名删除标记及旧普通 commit | 冲突，不隐式恢复 |
| 旧 Cloud 服务端/缺能力或回执 | 可见的不支持/协议错误，不误报成功 |
| Cloud 隔离删除/恢复 | 实际权威读回与检索证实排除/恢复，无关记录不变 |

待决定：确认此三入口扩展和无限期可恢复保留，并取得 Cloud 契约/隔离测试 scope。
在此之前没有可用生命周期命令/API，不改变存储 schema，MEM-9 不得使用拟议示例删除
生产记忆。实现后 MEM-9 应刷新精确目标，每个已审阅目标使用稳定操作 ID，保存回执，
验证 active 列表/检索，并使用 trash revision 恢复。MEM-9 快照计数是历史证据，不是
当前删除清单。
