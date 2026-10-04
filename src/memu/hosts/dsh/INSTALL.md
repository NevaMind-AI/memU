# 为 DSH 安装 memU

## 任务身份

- 当前任务名：`{{task_name}}`
- 历史任务名：{{former_task_names}}
- 迁移与移除时会被识别的名字：{{all_task_names}}

> **读者是 agent。** 自上而下执行，任何验证门禁失败就停在那里，不要继续往下做。
> 结束时按最后一节汇报结果。

DSH 接入 memU 分三步：配置共享的记忆后端、把 `dsh-memu` 插件装进 DSH profile、
让 DSH 在回答前能取到记忆。

## 第一步 —— 安装并配置 memU

```sh
uv tool install --editable <memU 检出目录>
memu-dsh --help
```

若 `memu-dsh` 不在 `PATH` 上，说明装的是旧版本，或脚本目录不在 `PATH` 里。
不想装成全局工具时，也可以只在本机跑 `uv run --project <memU 检出目录> memu-dsh ...`。

配置共享的记忆后端。已经由别的宿主配好过就复用它，重复配置是幂等的：

```sh
memu-dsh config --local --db /absolute/path/memu.sqlite3 --embed-provider openai --embed-api-key <key>
memu-dsh config --cloud --cloud-api-key <memU key>
```

`--db` 必须给绝对路径，只存在于当前 shell 的环境变量到不了自动化运行。
不要手改 `~/.memu/config.env`，用 `memu-dsh config show` 查看。

### 验证第一步

```sh
memu-dsh doctor
```

必须正常退出。新的 store 检索命中 0 条是正常的。

## 第二步 —— 安装 `dsh-memu` 插件

插件把 DSH 的会话事件导出成 memU 能挖的 JSONL，并提供 `memu_retrieve` 等工具。
它是一个独立的公开仓库 `Swcmb/dsh-memu`，同时以 git submodule 的形式挂在本仓库的
`dsh-memu/` 下——两种拿法都行：

```sh
# 方式一：随本仓库一起 checkout（需要 clone 时带 --recurse-submodules，
#         或在本仓库根目录执行 git submodule update --init）
dsh plugin --profile desktop add link:<memU 检出目录>/dsh-memu

# 方式二：单独克隆独立仓库
git clone https://github.com/Swcmb/dsh-memu.git
dsh plugin --profile desktop add link:<克隆路径>
```

`--profile` 换成用户实际在用的 profile（桌面应用通常是 `desktop`）。装完确认
profile 的 `package.json` 里 `dependencies` 与 `dsh.profile.bundles` 都出现了
`dsh-memu`；只进了 `dependencies` 时补上 bundles 条目。

### 验证第二步

重载 DSH：**改过插件 JS 之后必须重启桌面应用**（只新开会话不会重新导入已缓存的模块）。
随后：

```sh
memu-dsh prepare
```

它必须报出会话数；没有新对话时 0 是正确结果。同时确认
`~/.dsh/memu/transcripts/<encoded-cwd>/<session-id>.jsonl` 已经生成并随对话增长，
且文件里**不含** `system/message`、`request/header` 这类噪音行。

## 第三步 —— 让 DSH 能取到记忆

插件默认已经把常驻指令接进系统提示词，正常的安装到此为止。若用户明确要求改由
指令文件承载（例如插件被关掉但指令要留着），改用托管块：

```sh
memu-dsh install-instruction
memu-dsh install-instruction --path ~/.dsh/AGENTS.md --skills-dir ~/.dsh/skills
```

该命令只新增一个托管块和 `skills/memu-retrieve/SKILL.md`，已有内容原样保留，
重复执行是幂等的。

### 验证第三步

```sh
memu-dsh retrieve "smoke test"
```

在 DSH 里调用一次 `memu_retrieve` 工具，确认它返回结构化结果或结构化错误
（未配 embedding 密钥时报错即放行，不算安装失败）。命中列表为空是合法的。

## 排障：profile 起不来 / 工具不见了

- `dsh: cannot resolve profile bundle "dsh-memu" …` —— 手工往 `package.json` 里加了
  `dependencies` 与 `dsh.profile.bundles`，但没让包管理器真的装上。补一次

  ```sh
  dsh plugin --profile <profile> install
  ```

  之后 profile 的 `node_modules/dsh-memu` 应该指向检出目录（`link:` 安装时是 junction）。
- `plugin tree failed to load … Cannot find package '@deepseek-ai/dsh-agent-preset'`
  （或任何别的 `@deepseek-ai/dsh-*`）—— 启动这个 profile 的 `dsh` 与 profile 里手写 patch
  所针对的 DSH 版本不是同一棵闭包：那个包属于 DSH 0.2.0-rc.2，而本机 npm 全局 CLI 是
  0.1.5-rc.3。属于 **DSH 版本错配，与 memU 插件无关**；要么把 CLI 对齐到同一版本，
  要么让这个 profile 不再引用那个包。
- 插件装了但 agent 看不到 `memu_*` 工具 —— 先确认 profile 里真的有插件条目
  （`dsh --profile <p> --dump-config` 应输出 `dsh-memu`），再确认当前宿主进程是**重启后**
  的新进程：`link:` 插件的 JS 在一个进程里只 import 一次，改过插件代码必须重启才生效。

## 把结果报回 memU

所有门禁都通过：

```sh
memu-dsh report install
```

中途停下：

```sh
memu-dsh report error --stage install --detail "<哪一步失败、试过什么、怀疑的原因>"
```

上报是尽力而为的。不要带上凭据 (credential)、绝对路径 (absolute path)、记忆内容、
转录文本或原始命令输出 (command output)。

## 完成

告诉用户选了哪个后端、插件装进了哪个 profile、记忆挖掘由什么触发，以及检索从
下一个 DSH 会话开始生效。
