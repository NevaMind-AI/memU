# memU

Terms for evolving application-owned conversations into durable knowledge.
用于将应用持有的会话演化为持久知识的领域术语。

## Language

**Developer memorize run（开发者记忆运行）**:
An independent unit of work that evolves a batch of completed application-owned sessions into durable knowledge.
将一批应用持有的已完成会话演化为持久知识的独立工作单元。
_Avoid_: session（一次 run 可以包含多个 session）

**Evolve selection（演化类型选择）**:
The knowledge kinds chosen for one developer memorize run to evolve and persist.
一次开发者记忆运行要演化并保存的知识类型选择。
_Avoid_: scope, user scope

**User scope（用户归属范围）**:
The identity conditions that delimit ownership and visibility of stored knowledge.
界定持久知识归属及可见范围的身份条件。
_Avoid_: evolve selection

**RecallFile track（召回文件类型）**:
The classification of durable recall content as user memory or a reusable skill.
将持久召回内容区分为用户记忆或可复用技能的分类。
_Avoid_: resource track

**Resource（资源）**:
A workspace source file represented by its location and description, separately from user memories and reusable skills.
以位置和描述表示的工作区源文件，与用户记忆及可复用技能分别管理。
_Avoid_: memory file, skill
