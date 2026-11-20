# ADR 0024：通过 commit 清空 memory 正文及本地镜像规则

- 状态：提案；设计审阅
- 议题：MEM-13
- 关联：[ADR 0012](0012-cloud-backed-agentic-backend.md)、[ADR 0014](0014-paginated-list-all-recall-files.md)
- [English](0024-memory-clearing-through-commit.md)

## 目标与范围 {#goal}

使用现有 `commit_results` 流程，减少过时 memory 正文对片段召回和本地文件的干扰：提交空正文，保留数据库文件记录，移除其 segments，并不保留对应本地 Markdown 镜像。

服务保持三个入口和 embedding-only 架构。共同服务流程继续位于 `AgenticMixin`，本地和托管仓库各自拥有模型与 scope 职责。首批改动只适用于 `memory`。PR #814 已关闭。

## 当前行为 {#evidence}

源码基线：memU 运行代码 `12d144c`；托管 checkout `cca499a` 固定 `memu-cli==0.11.0b3`。MEM-16 报告了隔离 inmemory/假 embedding 及临时文件检查，MEM-13 核实了源码；这些观察不代表线上 Cloud 行为。

| 路径 | 观察到的行为 |
| --- | --- |
| `src/memu/app/agentic.py` | 已有 memory 正文 strip 后更新；空正文不产生 segment 文本，对账移除旧 segments，文件记录保留。空 description 不清旧描述，文件向量可能保留。 |
| 同路径：skill 生成 | 空 skill 正文仍生成 name/description segment。 |
| `src/memu/hosts/bridging/recall_files.py` | 正文为空仍写 frontmatter。 |
| `src/memu/hosts/bridging/pipeline.py` | prepare 写列表返回的文件；commit 提交变更文件，后端成功后重拍目录快照。 |
| `src/memu/hosts/retrieval.py` | 返回的文件会落盘并提供路径。 |
| `src/memu/hosts/bridging/manifest.py` | 内容 diff 忽略缺失文件。 |

## 目标行为 {#behavior}

1. 通过现有 commit payload 提交目标 memory，保留定位元数据，正文为空或纯空白。沿用现有 scope/name 定位与普通 commit 语义。
2. commit 成功后正文为空，旧 segments 移除。数据库记录及元数据在 list/Dashboard 仍可见；片段移除成功后，当前片段检索不再命中该 memory。
3. 按解析后的正文 `body.strip()` 判空，不按 Markdown 总字节数。空 memory 不生成只有 frontmatter 的镜像；处理明确为空的 memory 时，移除正常目标路径上已有的镜像，只跳过写入会残留旧内容。
4. prepare/retrieve 使用相同空 memory 落盘规则；bridging commit 在后端成功后移除本次提交的空 memory 镜像。retrieve 不提供未实际落盘的路径。列表或检索未返回某项，本身不构成移除文件的依据。
5. 保持现有无声覆盖行为、快照/session 流程和错误传播。后端抛错不会进入成功后的清理；文件系统失败沿用普通 host 错误处理。
6. 本地文件缺失或目录为空仍不提交后端清空；skill 和 resource 行为不变。

保留数据库身份不代表保留旧正文。元数据及可能的文件级向量仍在，目标效果是停止片段召回、移除本地空壳。当前 Postgres 按方法提交不代表整批原子性；本提案不新增恢复保障。

## 实现计划 {#implementation}

| Commit | 范围 | 验收 |
| --- | --- | --- |
| 1. 固定 commit 行为 | 用合成数据检查已有 memory 空/空白正文、保留元数据、segment 移除与 scope/track 隔离。 | 明确当前行为，不改 payload 语义；区分 Local 结果和托管固定版本证据。 |
| 2. 应用空 memory 镜像规则 | 复用现有 writer/路径逻辑，调整 prepare/retrieve 调用方处理未落盘路径，bridging commit 成功后移除本次提交的空 memory 镜像。 | 不生成新空壳，旧目标镜像被移除；非空 memory、skill 保持现有无声写入行为；后端失败不执行成功后的移除。 |
| 3. 验证集成 | 隔离数据测试 list/prepare、retrieve 输出和 commit，跑相关后端/host 回归。 | 正文/segment 状态与镜像结果一致；本地缺失不清后端，manifest/session 行为沿用现状；Cloud 单独验证后才能给出 Cloud 结论。 |

当前源码把省略/null content 也当空正文。改变此行为、新建语义或名称定位需要单独兼容决定，不纳入本实现计划。

## 影响与验证 {#validation}

描述不变且没有新增片段文本的清空无需新增正文 embedding。现有按 track 列表、逐 segment 删除成本保留。本地落盘增加空正文判断，可能 unlink 正常镜像路径；此范围不需要冲突跟踪、新 manifest 格式或同步协议。按相关检查记录影响，不宣称已提速。

使用合成 scoped 记录及临时目录，覆盖空/空白 memory、保留 ID/description、零 segments 与检索排除、旧镜像移除、不生成空壳、不提供不存在的检索路径、skill/非空写入保持不变、后端失败及本地缺失。真实 Postgres 和托管行为需独立隔离验证，inmemory 测试不能证明其原子性。

## 交付 {#delivery}

PR #816 当前仅含设计文档。按小型提交实现已约定行为，双语同步测试结果，保持仓库 scope 校验及适用后端一致要求。本文不授权生产记忆清洗、发布或部署。
