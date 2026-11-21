# 0025：为每次开发者记忆运行持久化演化类型选择

状态：Accepted。

[English](0025-developer-evolve-selection.md) · 关联：[#697](https://github.com/NevaMind-AI/memU/issues/697)、[ADR 0019](0019-developer-run-workspaces.md)

开发者应用有时只需要更新用户记忆。为这次运行生成技能和资源任务，会增加与目标知识类型无关的工作。默认行为仍是完整的 memory、skill 和 resource 流程。

## 决策

`memu memorize prepare --only memory` 和 Python 生命周期入口的 `only="memory"` 选择仅演化 memory。Prepare 将 `evolve_selection` 以 `memory` 或 `all` 写入运行标记。Commit 沿用这份选择，不提供覆盖参数。旧标记缺少此字段时兼容完整流程，未知选择在提交前明确报错。

这份选择共同约束任务、本地镜像、内容快照、变更文件收集和知识提交。N 个会话在 memory-only 模式下生成 N 个 memory 任务，默认仍生成 2N + 1 个任务。Memory-only 跳过 skill 和 resource 模板解析。额外的 skill 文件和资源清单即使格式错误，也不解析、不提交；Python 调用方的工作目录原本就可能包含这些文件，因此不能仅因其存在而拒绝本次运行。

选择属于已经准备好的运行，而不只是执行器提示词：执行器与 commit 分开执行，仅靠提示词无法约束 commit 读取哪些结果。如果允许在 commit 时重新选择，提交内容也会与准备好的任务和快照脱节。

## 影响

- 保留 canonical 输入、两种 JSONL 投影以及现有交接响应字段。本次改动只选择执行工作，不重做输入物化，也不增加 skill-only。
- 后端 API 保持不变。Prepare 仍遍历全部召回文件类型的分页，只在本地物化所选文件；这不代表减少后端或 Cloud 数据传输。
- 保留现有提交确认、重试和清理规则。CLI 成功后删除整个私有运行目录，包括被忽略的额外产物；Python 生命周期函数仍保留调用方持有的目录，并保持未选中的 skill 和资源产物原样。
- 新版本可以完成没有选择字段的旧运行，反向兼容则不适用于 memory-only：旧版本会忽略新标记字段，按完整流程提交。降级前，应使用支持演化类型选择的版本完成或丢弃这些运行。
- Host adapter 流程维持完整的默认行为。演化类型选择与用于界定知识归属的 user scope 分别表达不同概念。
