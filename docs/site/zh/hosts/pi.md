# pi：检索与注入

## 触发与查询 {#trigger}

`memu-pi install` 将托管扩展安装到 `~/.pi/agent/extensions/memu-retrieval.ts`；设置 `PI_CODING_AGENT_DIR` 时安装到对应目录。执行 `/reload` 或开启新会话加载。

扩展在 `input` 时异步启动 `prompt-hook`，并返回 `continue`，主响应可立即开始。它忽略扩展来源输入、空文本和 bridging 运行。查询使用[共享策略](retrieval.md#query)。可选提取通过隔离的 pi 请求执行，使用当前 provider/model，禁用工具、扩展、skills 和上下文文件，不保存会话。提取默认关闭，限时 12 秒。

## 注入时机 {#injection}

检索返回非空上下文字符串后，扩展发送隐藏的 `memu-retrieval` 消息，设置 `deliverAs: "steer"` 和 `triggerTurn: true`。结果可能进入正在运行的回合，也可能在首轮响应后触发继续处理，不保证在首个回答前到达。检索成功但无命中时，仍会渲染状态上下文。

会话关闭时，扩展终止所追踪的检索子进程并使回调失效；投递前还会检查会话身份。Hook 失败时显示警告，不注入记忆上下文。

## 稳定后写入 {#recording}

提交用户输入会标记待处理记忆。`agent_settled` 仅在 pi 空闲且所有追踪中的检索完成后启动记忆 hook。分离的 worker 共用工作区锁和 30 分钟冷却期，不保证每次响应后都提交记忆；获准处理后仍需要可用的 provider。

## 激活与验证 {#verify}

```sh
memu-pi doctor
memu-pi retrieve "已保存的主题"
```

重载扩展，发送真实输入，再检查 `~/.memu/hosts/pi/log/hooks/retrieve/`（或自定义 base 目录）。核对查询来源、状态及返回上下文。注入消息设置 `display: false`，因此聊天界面不显示该消息是正常行为；应检查上下文实际使用和诊断。请保密追踪内容。

配置见[配置参考](../reference/configuration.md)，安装细节通过 `memu-pi docs install` 查看。
