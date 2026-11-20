# ADR 0025：本地与托管 Postgres 共用记忆核心

- 状态：提案；仅供设计审阅
- 议题：MEM-13
- 关联：[ADR 0002](0002-pluggable-storage-and-vector-strategy.md)、[ADR 0012](0012-cloud-backed-agentic-backend.md)、[ADR 0014](0014-paginated-list-all-recall-files.md)
- 后续背景：[PR #814](https://github.com/NevaMind-AI/memU/pull/814) 在本边界审阅期间暂停推进；该草稿已预留 ADR 编号 0024。
- [English](0025-shared-postgres-core.md)

## 问题与证据 {#problem}

托管集成复用 `AgenticMixin`，但使用独立 Postgres 仓库，并覆盖 segment 排名和文件汇总。因此，仅共享 mixin 不等于共享存储行为、事务保障或全部检索阶段。修改 memU 自带的 Postgres 后端不会自动修改该适配器。

本提案基于两侧源码核实，不包含复制的私有源码、凭据、生产记录或部署证据。观察到的适配器行为是兼容性输入，不直接定义正确行为。

| 领域 | 开源实现 | 观察到的托管集成 | 需要对齐的内容 |
| --- | --- | --- | --- |
| Segment 排名 | `RecallFileSegmentRepo.vector_search_segments` 返回排序后的记录和分数；Postgres 已在 SQL 内执行 pgvector 排名 | host 覆盖方法调用另一个名字的原生排名方法 | 使用已有仓库方法和继承的检索阶段 |
| 文件汇总 | `AgenticMixin._collect_files` 携带 `id__in` 和 scope 调用 `list_recall_files` | 另一 host 覆盖方法调用独立按 ID 查找函数；通用过滤翻译不接受 `id` | 在租户约束下支持已有的有界 ID 过滤，再使用继承的汇总 |
| 同分排名 | 开源 Postgres 按距离排序；托管查询还按 ID 排同分项 | 同分项选择可能不同 | 在声称结果一致前，明确并测试确定性同分规则 |
| 原子性 | Inmemory/SQLite 实现 `AtomicDatabase`；Postgres 仓库各自提交 | 观察到的适配器也使用独立仓库事务 | 声称 Postgres 批次原子性前，先统一事务所有权 |
| 模型 | 默认表保存文件和 segment 向量，支持可配置 scope 模型 | 产品表有额外身份/位置约束，不保存文件级向量 | 通过明确映射保留数据和行为，不能直接替换表结构 |
| 作用域 | `UserConfig.model` 校验调用方过滤，通用仓库执行过滤 | 仓库额外绑定鉴权后的租户条件 | 租户绑定独立于调用方过滤；无过滤条件时同样有效 |
| Embedding | provider 无关的客户端和客户端池 | 产品选定的 provider/配置及用量记录 | 注入客户端，产品运行配置与计费留在核心之外 |

当前相关源码：[agentic 操作](../../src/memu/app/agentic.py)、[segment 协议](../../src/memu/database/repositories/recall_file_segment.py)、[Postgres 排名](../../src/memu/database/postgres/repositories/recall_file_segment_repo.py)、[Postgres store](../../src/memu/database/postgres/postgres.py)、[过滤翻译](../../src/memu/database/postgres/repositories/base.py)、[SQL 模型容器](../../src/memu/database/postgres/schema.py)、[事务协议](../../src/memu/database/interfaces.py)。

## Postgres 源码逐项比较 {#source-comparison}

比较版本：memU `ee7e251f4cd5f4f984577edf3233e9358b921ed9`（运行代码基线 `12d144c`）与 hippocampus-server `cca499a63d5404c156903fe9de37d076f504faca`。以下是 checkout 源码观察，不代表当前线上部署。证据中 M 路径相对于 `src/memu/database/postgres/`；H 相对于 `services/memu-service/`。私有链接需要仓库权限，只引用，不复制源码。

| # | 具体差异 | memU Postgres | hipp Postgres | 影响 / 对齐方向 | 代码证据 |
| --- | --- | --- | --- | --- | --- |
| 1 | 持久化入口 | 一套同步 Postgres 仓库 | mixin 用同步 `MemuV4Store`，产品操作另用异步 `MemoryFileRepo` | 只统一同步适配器不能覆盖 Dashboard 删除/segment 编辑，两条链都需盘点 | M `postgres.py:30`；H `app/infrastructure/memu/store.py:514`、`app/infrastructure/persistence/repositories/memory_files.py:118` |
| 2 | 模型 / ID / 父字段 | SQLModel；字符串 ID；`recall_file_id` | SQLAlchemy declarative；Postgres UUID；`memory_file_id` | 需要字段/记录映射和非法 ID 处理，不能直接替换 ORM | M `models.py:31`、`models.py:65`；H `app/infrastructure/persistence/models/memu_v4_memory_file_segment.py:25`、异步仓库 `_is_uuid:101` |
| 3 | 租户边界 | 调用方 scope 过滤，没有独立鉴权租户绑定 | 同步仓库绑定 organization/project；异步 selector 携带租户条件 | 每条 SQL 都要保留受信任约束，包括修改和重试查找 | M `repositories/base.py:67`；H 同步 store `_scoped:140`、异步仓库 `_file_conditions:52` |
| 4 | 身份与展示名 | 查找比较全部传入 `user_data`；模型可能包含展示名 | `_scope_ids` 使用 user/agent ID，展示名作元数据 | 先商定身份字段，展示名修改不能意外产生另一归属 | M `repositories/recall_file_repo.py:95`；H 同步 store `_scope_ids:50`、`_find:245` |
| 5 | 文件唯一性 | 默认 `schema.get_sqlalchemy_models` 没传 `unique_with_scope`，已提交基线没有对应 scope 身份唯一键；另一个 builder 传 name + scope，却未含 track | 明确唯一 `(organization, project, user, agent, track, name)` | 先解决开源 bootstrap/helper 不一致，新增约束前检查存量重复项 | M `schema.py:75`、`models.py:164`、`migrations/versions/20260703_0001_initial_schema.py`；H `app/infrastructure/persistence/models/memu_v4_memory_file.py:12` |
| 6 | 并发创建 | 文件仓库先查再插，没有显式 `IntegrityError` 收敛 | 文件插入遇唯一冲突后重读赢家；segment 插入最多重试 3 次 | 共享经测试的冲突语义；方法名一致或局部重试不代表整批原子性 | M `repositories/recall_file_repo.py:95`；H 同步 store `get_or_create_recall_file:206`、`create_segment:375` |
| 7 | Segment 结构/归属 | text、track、父 ID、向量，ID 外键级联 | 额外 index、起止位置、冗余身份，序号唯一约束，以及均级联的 ID/身份外键 | 保留产品约束，额外字段在所属事务中生成 | M `models.py:65`；H `app/infrastructure/persistence/models/memu_v4_memory_file_segment.py:25` |
| 8 | 向量持久化 | 文件及 segment 均有 `Vector()`，这些模型不固定维度 | 文件无向量列，segment 向量固定 1024 维 | 明确文件向量存储可选；维度变化需重建索引/schema 计划 | M `models.py:57`、`models.py:73`；H 文件/segment 模型、`app/domains/memory_files/model.py:22` |
| 9 | 原生排名 | `vector_search_segments`，按距离排序，可选 Python fallback | `top_segments_by_similarity`，距离后按 ID 排序；此方法无对应 fallback；产品有 HNSW 部分索引 | 统一仓库调用及同分规则，区分精确查询检查与近似索引执行计划 | M `repositories/recall_file_segment_repo.py:63`；H 同步 store `top_segments_by_similarity:314`、segment 模型索引 |
| 10 | 命中文件读取 | 通用过滤支持 `id__in`，mixin 汇总有界命中项 | 通用过滤白名单排除 `id`，另有 `list_recall_files_by_ids`，host 覆盖汇总 | 适配器支持带 scope 的有界 ID 过滤，再移除重复 host 阶段 | M `repositories/base.py:67`；H 同步 store `_apply_where:65`、`list_recall_files_by_ids:152`；H `app/infrastructure/memu/engine.py:110` |
| 11 | 分页 | 相同 `(track,name,id)` keyset / limit+1 算法；默认 schema 无对应复合分页索引 | 相同算法，并有 scope/track/name/ID 覆盖索引 | 复用逻辑，另验实际查询计划及迁移索引 | M `repositories/recall_file_repo.py:41`、基线迁移；H 同步 store `list_recall_files_page:171`、文件模型索引 |
| 12 | Session / 事务 | 自有引擎和 session manager，仓库提交，Postgres 未实现 `AtomicDatabase` | 注入同步 session factory，方法内事务；异步仓库也按方法持有事务 | 先明确共享事务与引擎所有权，再承诺批次回滚 | M `session.py:15`、`postgres.py:38`；H 同步 store、异步仓库模块契约 |
| 13 | 缓存表示 | 读写填充共享 `DatabaseState`，segment 缓存不替换相同 ID 的已有项 | 同步适配器状态属性为空协议占位，每次从新读行映射记录 | 不给服务端引入过期共享缓存，验证回滚和跨实例读回 | M `repositories/recall_file_segment_repo.py:46`、文件仓库 `_cache_recall_file`；H 同步 store `_file_record:87`、构造函数 |
| 14 | 物理删除 / 审计 | 文件 clear 和 segment 删除原语，已提交基线无等价历史触发器 | 同步 clear、异步 scoped delete；Dashboard 用异步删除；触发器保存 before-image，但不保存 segment 向量 | 两条路径都保留级联/审计；历史不等于现成恢复 API 或保留保证 | M 文件仓库 `clear_recall_files:70`；H 异步仓库 `delete_files:244`、Dashboard `delete_file:360`、历史迁移 `d7e2b9c4f8a3` |
| 15 | Resource 支持 | 真正的 resource 仓库、存储及排名 | `EmptyResourceRepo`；engine 禁用资源检索，HTTP 丢弃资源写入 | 保留明确能力边界，不隐式扩成托管资源存储 | M `postgres.py:74`；H 同步 store `EmptyResourceRepo:478`、engine 和公共路由 |
| 16 | Schema 生命周期 | store 构造执行 memU Alembic（`create`）；`validate` 目前只查表存在，即使传入自定义模型也如此 | 产品独立拥有 Alembic 历史、产品表、索引和触发器 | 区分外部 schema 所有权与本地 bootstrap；仅查表不足以验证兼容 | M `postgres.py:60`、`migration.py:36`；H `alembic/versions/` |

证据入口：[比较版本的 memU 源码](https://github.com/NevaMind-AI/memU/tree/ee7e251f4cd5f4f984577edf3233e9358b921ed9/src/memu/database/postgres)、[hipp 同步 store](https://github.com/NevaMind-AI/hippocampus-server/blob/cca499a63d5404c156903fe9de37d076f504faca/services/memu-service/app/infrastructure/memu/store.py)、[hipp 异步仓库](https://github.com/NevaMind-AI/hippocampus-server/blob/cca499a63d5404c156903fe9de37d076f504faca/services/memu-service/app/infrastructure/persistence/repositories/memory_files.py)、[hipp 模型](https://github.com/NevaMind-AI/hippocampus-server/tree/cca499a63d5404c156903fe9de37d076f504faca/services/memu-service/app/infrastructure/persistence/models)。

## 六步对齐计划 {#steps}

各步顺序推进，每步有可审阅出口。Step 1–5 对齐已有能力，Step 6 验集成与上线；删除/恢复功能继续单独暂停。

| Step | 工作 / 归属 | 交付与验收门槛 |
| --- | --- | --- |
| 1. 固定比较基线与行为契约 | 两侧负责人审阅第 1–16 项；memU 提供可复用检查 | 明确身份/展示字段、scope 默认值、同分、文件向量省略和 resource 能力。测试使用合成向量，覆盖租户/track 隔离、有界读取、分页与并发；明确现存差异，不声称已通过。 |
| 2. 通过已有协议对齐检索 | 托管负责人改 adapter/host；memU 仅按需补约定的契约覆盖/同分规则 | 实现 `vector_search_segments`、scoped `id__in`，移除 `_recall_segments` / `_collect_files` 覆盖及无用辅助函数。真实隔离 PG 验证分数、同分规则、SQL LIMIT/有界 ID 读取。 |
| 3. memU Postgres 支持产品模型复用 | memU 扩展具体模型/记录/session/受信任条件接缝；托管提供映射 | 合成产品形状 schema 使用共享仓库，不自动迁移或关闭产品引擎。CRUD、父检查和重试读均受租户约束；UUID、可选文件向量、额外 segment 字段往返正确。审计默认 schema 唯一性及迁移/重复处理。 |
| 4. 统一事务与并发写入 | 共享核心负责人配合托管集成负责人 | 在复合操作之上持有事务，无内部提交拆批。测试文件/segment 约束和有界重试。真实 PG 故障注入证明回滚、缓存不发布和跨实例可见；embedding 调用不占用长写事务。 |
| 5. 替换重复持久化路径 | 托管同步 mixin 路径采用共享仓库，异步产品重叠写操作委托共享核心；memU 补必要接缝 | 移除通用 CRUD/排名 SQL 重复，保留产品专属审计/查询投影和 schema 迁移。同时验 Dashboard 删除/segment 编辑与 API-key commit、级联和历史触发器；同步异步桥接不阻塞事件循环。 |
| 6. 集成升级与验证 | 两侧跑共同检查；托管负责依赖/lockfile、迁移和部署 | 默认 memU 与产品形状 PG schema 均通过，HTTP 往返通过；隔离数据 staging，显式依赖升级和回滚计划。生产发布仍需单独授权；生命周期所需存储保障和删除契约审阅后再恢复功能工作。 |

本 PR 只完成 Step 1 的源码清单/计划部分；可执行跨仓库检查和所有运行迁移步骤仍未实现。最终目标是共享 SQL 与行为，不是两套实现仅通过方法形状检查。

## 建议边界 {#boundary}

目标是通用记忆行为和 Postgres 操作只有一套共享实现，产品侧保留小型适配层。仅统一方法名、继续独立维护算法，只能是过渡步骤。

| 在 memU 中共享 | 留在托管产品侧 |
| --- | --- |
| Commit 身份/规范化规则、segment 生成与对账 | HTTP DTO、API-key/session 鉴权、CSRF 与权限 |
| 检索阶段、分数语义、分页与过滤契约 | 解析鉴权后的租户，并构造绑定租户的 store |
| 通用 Postgres CRUD、原生向量排名、事务/session 所有权 | 现有表名、额外字段、约束、审计触发器和产品迁移 |
| 后端契约检查与通用扩展接缝 | 运行时 embedding provider/model/endpoint/凭据选择，用量账本和计费 |
| 单独商定后的生命周期规则 | 部署配置、依赖锁定、上线与回滚 |

通用 Voyage 支持可以继续开源；托管产品选用 Voyage 的决定、运行配置、凭据与用量核算属于产品。核心继续 embedding-only，不依赖产品 LLM 工厂或 settings 单例。

Scope 校验与租户授权是不同职责。受信任的租户约束是不可变 store 上下文；请求过滤只能收窄，不能替换或放宽它。空过滤仍须受租户约束。不在公共服务 API 中加入租户凭据或产品授权逻辑。

## 首步实现：复用现有检索契约 {#first-slice}

此步不需要新公共入口、仓库方法或配置开关：

1. 用固定合成向量和带 scope 的记录固定现有排名/汇总契约。明确同分、无向量、空 ID 与 track 过滤行为。两侧运行同一组检查。
2. 在托管适配器所属工作区，用现有原生查询实现 `vector_search_segments`。文件过滤接受 `id`/`id__in`，始终保留鉴权后的租户条件。必须是有界 SQL 查询，不能读全表再用 Python 过滤。
3. 共享 `AgenticMixin` 不变并通过检查后，移除托管排名和汇总覆盖方法。适配器专用辅助函数没有调用方后再删除。
4. 在隔离托管环境对比权威检索响应，保留分数、文件汇总、track/scope 过滤及有界查询行为。同分排序变化应明确审阅，不能静默算作一致。

这一步移除服务算法的重复，但还没有合并两套原生 SQL 实现；后者属于下一步。首步可以独立审阅，不需要重写产品表或更换 embedding 模型。

## 下一步：合并 Postgres 实现 {#postgres}

先审查已有 `sqla_models`、记录转换、scope 模型和 session 接缝。只有第二个真实使用方确实需要时才扩展这些具体接缝，不引入新存储框架或可配置查询语言。

共享仓库需要支持：

- 把领域字段映射到现有列，包括 segment 父文件 ID，并明确转换为 memU 记录。产品专属 segment 位置/序号字段由窄范围适配 hook 或数据库默认值在同一事务内提供。
- 托管时每次读写都必须带受信任条件，包含 ID 查找、segment 父文件检查、清空、重试和向量检索。默认本地 store 不依赖产品租户仍可使用。
- 可注入的 session/事务所有权。传入产品 session factory 不能意外关闭其引擎。内部 `commit()` 不能拆散复合操作，缓存不能发布已回滚状态。
- 明确 user/agent 身份和展示元数据的区别；修改精确匹配、读过滤省略/`None` 语义前先达成契约。不得静默把无 scope 本地数据迁移进托管默认 scope。
- 明确支持托管侧不保存文件向量。当前基于 segment 的检索不使用文件向量，但后续写入不能假设它一定持久化。可检索正文仍需 segment 向量。

现有产品 schema/迁移继续由产品拥有。共享生命周期或仓库变更必须附带各支持 schema 的明确迁移要求。不能把开源 bootstrap 指向产品表并自动创建/修改它们。保留 ID、时间戳、归属身份、track/name 唯一性、segment 归属/级联和审计行为。生产变更前需审阅基线备份和迁移回滚。

模型无法满足某操作时，应在集成时明确报不支持，而不是接受后静默丢弃行为。目标适配器只映射模型和产品上下文，不另写 CRUD、排名或生命周期算法。

## 兼容检查与发布门槛 {#validation}

在 memU 测试支持中提供一小组可复用 pytest 断言/fixture，托管集成能够导入，不依赖源码 checkout 中的 `tests` 包。具体打包机制在首步实现时确定，不提议新增包或插件框架。SQL 行为需在真实隔离 Postgres 实例验证；仅 inmemory/SQLite 通过不能证明 Postgres 一致。

| 检查 | 必须满足的结果 |
| --- | --- |
| 相同合成语料/查询向量 | scope 内 top-k 分数与汇总一致，有明确且经测试的同分策略 |
| 两租户、user、agent，跨 track 同名项 | 即使空过滤或传入其他归属的 ID，也不能越界读写 |
| 无向量、空 ID、未知过滤 | 一致且有文档的结果或可见错误，不放宽查询 |
| 重复提交与并发插入 | 稳定文件身份、正确 segment 对账，约束保留 |
| 分页 | `(track, name, id)` 顺序，静态语料无重复/遗漏，游标正确结束 |
| SQL 访问模式 | 排名在 SQL 内 ORDER BY/LIMIT，汇总只读取命中 ID，不加载整个语料 |
| 事务失败与双实例读回 | 承诺原子性时整批成败，回滚/缓存状态正确，持久可见 |
| 产品 schema 兼容 | 已有 ID、额外字段、级联与审计行为保留 |
| Embedding 注入 | 无产品密钥即可使用合成客户端，运行配置和用量记录在核心之外 |

事务检查是共享事务型 Postgres 这一步的门槛，不表示现有独立提交实现已经通过。检索对齐可以先落地，但不能静默扩大其保障。

产品固定依赖已发布 memU 版本。共享源码不绕过版本管理：按正常授权发布流程发布，明确升级产品依赖/lockfile，运行契约和 HTTP 集成检查，先部署隔离环境再上线。保留此前依赖/部署版本供兼容回滚，schema 降级需独立方案。发布、部署和线上数据库改动分别授权。

产品升级 memU 时，两侧 CI 应运行相同检查。协议形状检查发现缺少方法，行为检查发现方法齐全但语义不同。开源提交不会自动影响线上。

## 范围、决定与验收 {#acceptance}

本 PR 只提出边界与顺序，不修改运行代码、存储 schema、依赖版本或已部署服务。本次仅文档变更，没有执行后端一致性套件或托管运行验证。检查源码引用和双语 Markdown 链接。

待审阅决定：

1. 将检索契约对齐作为首个实现步骤。
2. 以明确的模型/租户/session 接缝实现共享 Postgres 仓库，保留产品 schema 所有权。
3. 在托管集成实施前，确定契约检查的分发方式和托管改动所属工作区。

后续迁移以删去重复 host 覆盖方法、再删去通用 SQL 重复逻辑，以及两侧通过上述检查作为验收。允许保留私有适配器，但它应映射产品上下文，不独立定义记忆行为。生命周期工作在所需共享存储保障和独立删除契约达成一致后恢复；本文不决定保留期策略。
