# Hermes：检索与注入

## 触发与查询 {#trigger}

`memu-hermes install` 将按需检索流程写入当前 profile 的 `SOUL.md` 托管块，开启新 Hermes 会话后加载。`HERMES_HOME` 选择 profile；未设置时，Windows 默认 `%LOCALAPPDATA%\hermes`，Linux/macOS 默认 `~/.hermes`，平台默认路径还会应用 `HERMES_DATA_DIR_SUFFIX`。

Agent 判断缺失的偏好、历史决策或项目背景是否有帮助。问候和上下文完整的简单转换通常无需检索。需要时，它阅读完整请求，用用户语言形成简短主题查询，再调用 `memu-hermes retrieve`。这是普通工具调用，不存在逐输入检索 hook，也不额外调用查询提取模型。

## 注入时机 {#injection}

工具执行完成后，结果进入 Agent 对话。Agent 可以等待结果，使用适用的摘要，需要时读取来源路径，再继续原任务。长任务中出现具体不确定性时，也可再次搜索。返回内容遵循[共享结果格式](retrieval.md#results)。

指令要求尊重用户不检索的请求、复用当前上下文中的结果，空结果或失败时正常继续。分数不证明内容真实，检索文本只作为参考数据。

## 写入独立运行 {#recording}

安装同时注册并批准一个 `on_session_end` shell hook。成功完成、未失败且未中断的回合可以启动分离的记忆 worker。处理受工作区锁和 30 分钟冷却期约束；worker 会话 ID 会被后续扫描排除，后台处理需要可用的无头 Hermes 模型访问。该 hook 负责写入记忆，不注入检索上下文。

## 激活与验证 {#verify}

```sh
memu-hermes doctor
memu-hermes retrieve "已保存的主题"
memu-hermes install-instruction --dry-run
```

检查当前 profile 的 `SOUL.md`，开启新会话，询问已保存的偏好或决策。确认 Agent 实际调用 retrieve 并使用相关结果；工具界面可能显示结果。安装回读不能证明运行中已经激活。如果移除了旧 memU 插件，需重启运行中的 Hermes 进程。

配置见[配置参考](../reference/configuration.md)，profile、生命周期和迁移细节通过 `memu-hermes docs install` 查看。
