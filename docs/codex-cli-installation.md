# Codex CLI 安装契约

状态：开发中。`memu-codex install` 尚未实现。本次提供程序准备命令：

```sh
memu-codex prepare-cli --json
memu-codex prepare-cli --install-missing --json
memu-codex prepare-cli --codex /path/to/codex --json
```

默认只查找程序并验证启动；显式传入 `--install-missing` 才允许安装，命令不会弹出交互提问。
结果包含 `stage`、`status`、`executable`，以及 `version` 或诊断字段 `reason`、`detail`。
退出码为 0（通过）、2（受阻）、1（失败）。共享配置接入、hook 注册和迁移需要后续步骤完成。

## 目标

终端用户与安装 Agent 使用同一个 `memu-codex install` 入口。
安装代码负责执行顺序、配置修改与完成判定；Agent 收集输入并解释结果。
复用现有配置、doctor 和双 hook 注册实现。

## 安装阶段

| 阶段 | 职责 | 通过条件 |
| --- | --- | --- |
| 检查现状 | CLI 读取 memU config.env、~/.codex 和已有双 hook；Agent 通过 Desktop 发现旧任务 | 明确复用的配置与待注册入口；任务清单未知时保留迁移阻碍 |
| 准备后端 | 通过现有命令复用或配置后端 | doctor 通过，已有存储及 embedding identity 保留 |
| 准备宿主 | CLI 查找 Codex 程序，缺失时安装并验证启动，复用 ~/.codex 中的 CLI/Desktop 共享配置 | Codex 程序可启动，共享配置沿用 ~/.codex |
| 配置集成 | 注册检索与记忆 handler | Codex 确认两者已加载且受信任，检索支持异步 |
| 完成交接 | Agent 通过 Desktop 工具清理已确认旧任务；CLI 验证集成及处理状态 | 旧任务清理证据完整，处理状态及其他集成保留 |

这些是内部职责边界，不要求用户经历五次提问。
每阶段返回通过、受阻或失败，以及明确的下一步；所有适用门槛通过后才可报告安装完成。
用户提交后的真实检索交付与记忆提交属于独立运行验收。

## 目标全流程

用户先安装 memu-cli Python 包，再进入此流程。本次仅实现其中的程序准备部分。

```mermaid
flowchart TD
    Start{安装入口}
    Start -->|Agent 对话| A1
    Start -->|直接使用终端| C1
    subgraph Agent[Agent 负责]
        A1{当前会话已确认是 Full access 吗？}
        A1 -->|是| A3[调用安装 CLI]
        A1 -->|否或无法确认| U2
        A5[实时汇报阶段进度并解释最终结果]
        Legacy[通过 Desktop 查找旧 memU 任务并确认归属]
        Legacy --> LegacyFound{任务清单与归属已确认吗？}
        LegacyFound -->|否| Blocked
        LegacyFound -->|是| LegacyExists{存在旧 memU 任务吗？}
        LegacyExists -->|否| C9
        LegacyExists -->|是| Pause[保存定义并通过 Desktop 暂停旧触发，等待 worker 结束]
        Pause --> C9
        Cleanup[通过 Desktop 删除已确认旧任务并核对结果]
        Cleanup --> Evidence[向 CLI 提供宿主迁移结果]
        Evidence --> C11
    end
    subgraph Host[宿主与用户负责]
        U2[用户切换到 Full access 后继续]
        U2 --> A1
    end
    subgraph CLI[CLI 负责]
        C1[读取 memU config.env 和 ~/.codex]
        C1 --> InspectHooks[读取 hooks.json 中的 memU 双 hook]
        InspectHooks --> C2[复用或配置后端并运行 doctor]
        C2 --> C3[查找 Codex 程序，缺失时安装并验证启动]
        C3 --> SharedConfig[复用 Codex CLI 与 Desktop 共享配置]
        SharedConfig --> C7{已确认是无需迁移的新装吗？}
        C7 -->|否或未知| HostNeeded[返回需要 Desktop Agent 处理迁移的状态]
        C7 -->|是| C9[注册检索与记忆双 hook]
        C9 --> C10[验证加载、异步检索、信任状态及程序路径]
        C10 --> Migration{本次涉及旧任务交接吗？}
        Migration -->|是| Cleanup
        Migration -->|否| C11[验证迁移结果、集成与处理状态完整]
        C11 --> Done[报告安装完成]
        Blocked[返回受阻或失败的阶段与下一步]
    end
    A3 --> C1
    C1 -. 实际访问被拒绝 .-> Blocked
    HostNeeded --> Handoff{Desktop Agent 可用吗？}
    Handoff -->|是| Legacy
    Handoff -->|否| Blocked
    Pause -. 无法安全交接 .-> Blocked
    Cleanup -. 无法确认删除结果 .-> Blocked
    C1 -. 阶段进度 .-> Progress{当前安装入口}
    C2 -. 阶段进度 .-> Progress
    C3 -. 阶段进度 .-> Progress
    C9 -. 阶段进度 .-> Progress
    C11 -. 阶段进度 .-> Progress
    Progress -->|Agent 对话| A5
    Progress -->|直接终端| TerminalProgress[终端实时显示阶段进度]
    Done --> Route{由 Agent 调用吗？}
    Blocked --> Route
    Route -->|是| A5
    Route -->|否| Terminal[终端显示结果与下一步]
    Done -. 下一次用户提交 .-> Runtime[独立验收真实检索交付与记忆提交]
    classDef agent fill:#dbeafe,stroke:#2563eb,color:#172554;
    classDef cli fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef host fill:#ffedd5,stroke:#ea580c,color:#7c2d12;
    class A1,A3,A5,Legacy,LegacyFound,LegacyExists,Pause,Cleanup,Evidence agent;
    class C1,InspectHooks,C2,C3,SharedConfig,C7,HostNeeded,C9,C10,Migration,C11,Done,Blocked cli;
    class U2 host;
```

蓝色表示 Agent 职责，绿色表示 CLI 职责，橙色表示用户操作。
颜色区分职责，不表示实现进度。本次已实现的是程序发现、可选安装及启动验证。

## 权限与交接边界

- Agent 调用安装 CLI 前，只确认当前会话已处于 Full access。
  未开启或无法确认时，提示用户切换；用户继续后重新确认有效模式，再调用 CLI。
- Full access 属于宿主会话属性，由 Agent 确认；CLI 负责实际安装操作的执行与结果检查。
- 直接终端调用跳过 Agent 权限检查。两条入口中的 CLI 都检查实际访问能力、报告操作失败并返回结构化结果，
  不修改调用方的沙箱或审批策略。
- Agent 调用应使用非交互选项；缺少必要输入时返回阻碍，由 Agent 解释。
  两条路径采用同一组安装完成条件。
- Codex CLI 与 Desktop 统一复用 `~/.codex` 中的共享配置及认证，注册的后台命令也使用该目录；
  从 CLI 安装时复用当前程序，从 Desktop 安装时由安装器发现或补装独立 Codex CLI。
- 目标流程沿用现有 Codex INSTALL.md 的 Full-access 前提。
- 所有必要门槛均须通过，才能执行依赖它的操作。无法盘点旧入口属于阻碍，不能当作入口不存在。
- 启用新触发前，旧 worker 必须空闲；保留恢复定义直到替代入口验证通过。
  无法确认归属或安全交接时暂停迁移。重跑时检查真实状态，不假定之前的阶段仍有效。
- 用户提交后的实际模型执行与记忆提交属于运行验收。

## 用户可见的阶段进度

两条入口均展示阶段进度。Agent 及时汇报 CLI 阶段结果及宿主迁移操作的真实结果：

| 用户看到的阶段 | 对应工作 |
| --- | --- |
| 🔐 [1/5] 检查安装条件 | Agent 确认 Full access；CLI 读取已有配置与集成状态 |
| 📦 [2/5] 准备 memU 与记忆后端 | 复用或配置后端并运行 doctor |
| 🛠️ [3/5] 准备 Codex CLI | 复用或安装程序，验证启动并沿用共享配置 |
| 🔔 [4/5] 配置自动记忆与检索 | 注册并验证双 hook；涉及迁移时先满足安全交接条件 |
| ✅ [5/5] 完成交接与安装检查 | 验证适用的旧入口清理和处理状态保留，报告结果并邀请下一次用户提交 |

Agent 在开始各阶段时展示标题，取得阶段结果后及时汇报通过或阻碍，再继续下一阶段。
只依据 CLI 或 Desktop 工具已返回的证据汇报，不用预计进度代替实际完成状态。
直接终端安装由 CLI 展示同样的阶段与结果；非交互调用提供机器可读的阶段信息。

不能假定同步工具调用期间 Agent 能读取流并发言。后续实现需提供阶段执行边界，
让 Agent 在阶段之间取得结果并汇报；宿主支持可靠的异步进度时可消费阶段事件。
两种方式共用 CLI 的阶段逻辑和完成条件，不让 Agent 自行编排安装内部操作。
目前 `prepare-cli` 只返回程序准备阶段结果，上述完整进度机制尚待实现。

## 旧任务迁移的宿主边界

Windows 只读调查检查了独立 Codex CLI 0.163.0 和 Desktop 内置 CLI 0.162.0-alpha.17.2：
命令帮助及含实验方法的 app-server 协议中均未发现定时任务管理入口。
实际枚举 Desktop 26.1007.9446.0 的工具，确认 `automation_update` 提供 create、view、update、delete，
状态支持 ACTIVE/PAUSED；未提供任务列表工具，其说明要求读取 automations 目录查找任务 ID。
本轮未执行真实任务的创建、暂停或删除，完整操作闭环仍需验收。

当前将旧任务发现、归属确认、暂停、等待 worker 和删除交给 Desktop Agent，通过宿主工具完成。
CLI 返回需要宿主迁移的状态；宿主准备好交接后，CLI 继续注册与验证双 hook，
替代入口验证通过后由 Agent 删除旧任务并核对结果，最后 CLI 记录迁移结果并完成检查。
宿主操作结果如何传回、证据如何校验以及阶段恢复入口，均待实现；不能仅凭一个调用参数宣布迁移完成。

确认无需迁移的新装可以直接走 CLI。迁移需求未知、Desktop 工具不可用、任务归属不明或操作失败时，
返回迁移受阻，保留旧入口和处理状态。当前设计不依赖独立 CLI 管理 Desktop 自动化任务。

## 第一片：准备 Codex 程序

1. 优先使用显式指定的程序；指定无效时返回阻碍。
2. 否则先查 PATH，再查 CODEX_INSTALL_DIR；未设置时查当前平台的官方默认安装目录。
3. 找到后复用并检查启动；已有程序损坏时报告启动错误，不把它当作缺失。
4. 确实缺失时，必须有 `--install-missing` 才调用官方原生安装器。
   本命令不提问，完整安装入口以后可先收集用户选择。
5. 安装器输出诊断，并有执行时限；失败或超时立即停止，不自动尝试其他包管理器。
6. 安装后重新查找程序，处理父进程 PATH 未刷新的情况。验证启动成功，并保留绝对路径供注册使用。
   安装器退出码为零本身不足以证明程序就绪。

本片不修改 hook 或旧任务。依赖补装属于可恢复的准备操作，不应仅因发现缺失就上报安装失败。
最终阻碍只报告一次，遥测发送是否成功不影响本地安装判定。

## 后续切片

- 将 `~/.codex` 中的共享配置接入注册命令，验证双 hook 使用该目录和绝对程序路径。
- 将后端准备、程序准备和现有 `install-prompt-hook` 串入 `install`。
- 接入 Desktop Agent 的旧任务迁移交接，定义宿主结果证据及 CLI 恢复方式；不可用时返回受阻。
- CLI 接管相应行为后，再精简 INSTALL.md。

## 可执行场景测试

通过真实实现调用与子进程边界检查行为，使用临时 home 和配置。
普通 CI 替代外部安装器与 Codex 进程，真实协议另外验收。

| 场景 ID | 初始条件 | 必须观察到的结果 |
| --- | --- | --- |
| codex.host.explicit | 显式指定程序 | 使用该程序，不另行发现或安装 |
| codex.host.explicit-invalid | 显式路径无效 | 返回受阻，不静默替换程序 |
| codex.host.reuse | PATH 上已有可用程序 | 验证启动，不调用安装器 |
| codex.host.stale-path | 程序仅存在于安装目录 | 能发现并复用，不重复安装 |
| codex.host.missing | 程序缺失且允许安装 | 调用选定安装器，重新发现并验证绝对路径 |
| codex.host.noninteractive-missing | 程序缺失且未授权安装 | 及时返回受阻，不提问、不安装 |
| codex.host.install-failed | 安装器失败或超时 | 停止，不注册 hook、不清理旧入口 |
| codex.host.install-incomplete | 安装器成功但程序仍缺失或损坏 | 返回受阻或失败，不报告就绪 |
| codex.host.broken | 已有程序无法启动 | 报告启动失败，不自动重装 |

后续用同样方式覆盖共享配置复用、注册去重、第三方配置保留、部分失败后重试及迁移。
安装与升级始终保留正式及 pending cursor、self-session 记录、待恢复任务与结果、日志、共享配置和记忆。

真实验收记录绑定场景 ID/修订、memU commit/包版本、宿主版本、OS、所选配置、结果和证据位置。
Agent 引导运行还记录 Agent/model，以及实际渲染引导的哈希与来源。证据不得包含凭据。
跳过或未观察到的检查不能记为通过；CI 可重复执行不代表 Desktop hook 交付或真实登录已验证。
