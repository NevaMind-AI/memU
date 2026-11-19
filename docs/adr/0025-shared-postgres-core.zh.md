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
