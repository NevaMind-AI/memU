# memU Host Retrieval / 宿主检索

Terms used by the host retrieval integrations. / 宿主检索集成使用的领域术语。

## Language / 术语

**Retrieval task（检索任务）**:
One attempt to obtain memory context for a specific user input in a host session.
针对宿主会话中的一次用户输入获取记忆上下文的任务。

**Query extraction（查询提取）**:
The preparation step that turns a long user input into a short memory-search query using the host's model.
使用宿主模型将长用户输入转换成简短记忆检索查询的准备步骤。
_Avoid_: retrieval / 检索（它还包括后续记忆查询与上下文交付）。

**Prefix fallback（前缀回退）**:
A memory-search query formed from the beginning of the original user input when an extracted query is unavailable.
无法获得提取查询时，由原始用户输入的前部内容构成的记忆检索查询。
_Avoid_: retry / 重试（回退查询本身不代表重新执行提取）。
