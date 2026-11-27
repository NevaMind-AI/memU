# 配置

下文用 `memu-pi` 举例，其他宿主替换为[对应命令](../hosts/index.md)。所有适配器共用配置，记忆写入与检索使用同一个后端。

## 文件与优先级 {#file}

配置按 **进程环境变量 → `~/.memu/config.toml` → 默认值** 的顺序解析。设置 `MEMU_CONFIG` 可指定其他 TOML 路径。后台进程需要读取同一配置文件；只在交互式终端中导出的变量，不一定能传给宿主及其 worker。

`init` 和 `config` 会创建或更新文件。文件包含明文密钥，请限制访问，分享诊断前先脱敏。POSIX 下 memU 会收紧文件权限；Windows 下继承目录 ACL。

如果已有 `config.env` 且 TOML 尚不存在，首次读取时自动迁移。原文件保持不变，可用于回退；TOML 创建后请修改 TOML。自动迁移失败会报告警告并继续读取旧文件。`MEMU_CONFIG_ENV` 仍可指定旧文件位置；未设置 `MEMU_CONFIG` 时，迁移目标位于旧文件旁。客户端身份单独保存在相邻的 `config.state.toml` 文件。

## Cloud {#cloud}

在 [memu.so](https://memu.so) 获取 key，然后执行：

```sh
memu-pi config --cloud --cloud-api-key "YOUR_MEMU_KEY"
```

Cloud 提供数据库与 Embedding。对应 TOML：

```toml
mode = "cloud"

[cloud]
api_key = "YOUR_MEMU_KEY"
# base_url = "https://api.memu.so/api/v4/memory/"
```

自定义 Cloud 端点使用 `--cloud-base-url "URL"`。Cloud 目前保存 memory 和 skill recall files；工作区 resources 可以提交，但云端尚未持久化或检索这些资源。

## Local {#local}

以 SQLite + 本地 Ollama Embedding 为例：先安装 Ollama，运行 `ollama pull nomic-embed-text`，并确认服务已在 `http://localhost:11434` 启动（尚未运行时执行 `ollama serve`）：

```sh
memu-pi config --local --db "~/.memu/memu.sqlite3" --embed-provider openai --embed-model nomic-embed-text --embed-base-url "http://localhost:11434/v1" --embed-api-key "ollama"
```

下面的 TOML 默认使用 Ollama，并附有 OpenAI 和豆包替换配置。切换服务时，将四个生效的 Embedding 值替换为对应的注释值，不要同时启用两组配置。memU Cloud key 不能用于 Embedding 服务认证。

```toml
mode = "local"

[local]
db = "~/.memu/memu.sqlite3"

[embedding]
# Ollama：先运行 `ollama pull nomic-embed-text` 并启动本地服务。
# 使用 Ollama 的 OpenAI 兼容 API，因此 provider 填 "openai"。
# 本地服务无需真实 API key，但这里需要填写非空占位值。
provider = "openai"
model = "nomic-embed-text"
base_url = "http://localhost:11434/v1"
api_key = "ollama"

# OpenAI：将上方四个生效值替换为：
# provider = "openai"
# model = "text-embedding-3-small"
# base_url = "https://api.openai.com/v1"
# api_key = "your-openai-key"

# 豆包（火山引擎 Ark）：将上方四个生效值替换为：
# provider = "doubao"
# model = "doubao-embedding-large-text-250515"
# base_url = "https://ark.cn-beijing.volces.com/api/v3"
# api_key = "your-ark-key"
# 使用你的 Ark 账号已开通的 Embedding 模型或 endpoint ID。

# 可选：服务限制每次请求的输入数量时，可调低此值。
# batch_size = 10
```

这里的 `provider` 选择 API 适配器，`base_url` 选择实际服务。Ollama 的 `/v1` 接口兼容 OpenAI，因此 `provider = "openai"` 是正确的；地址指向 Ollama 时，请求不会发往 OpenAI。其他 localhost 服务如果使用不同协议，需要对应的适配器。

这些宿主配置默认使用 OpenAI SDK 客户端，会在 `base_url` 后追加 `/embeddings`：

| 服务 | 实际 Embedding 请求 |
| --- | --- |
| Ollama | `POST http://localhost:11434/v1/embeddings` |
| OpenAI | `POST https://api.openai.com/v1/embeddings` |
| 豆包 | `POST https://ark.cn-beijing.volces.com/api/v3/embeddings` |

用浏览器 GET 访问 API 根地址不是 Embedding 请求，可能返回 Not Found。如果 `doctor` 报 404，请核对完整请求路径，以及账号是否已开通所填模型或 endpoint ID。直接通过 Python 使用 `client_backend="httpx"` 时，豆包适配器会自行追加 `/api/v3/embeddings`，该客户端的 base URL 应只填域名。

memU 会将数据库文件路径中的 `~` 展开为用户主目录。升级时保留已有数据库路径。Windows 显式路径可写成 `db = 'C:\data\memu.sqlite3'`（TOML 字面量字符串）或 `db = "C:/data/memu.sqlite3"`。更换服务使用 `--embed-provider` / `--embed-model`；自定义接口使用 `--embed-base-url`。`embedding.batch_size` 必须是正整数。不填写模型、密钥、端点或批大小时，使用 provider 默认值及其支持的环境变量。

| 存储 | `local.db` 值 | 用途 |
| --- | --- | --- |
| SQLite | 绝对路径或 `sqlite:///...` URL | 本地持久化；同时只支持一个写入者 |
| Postgres | `postgresql://...` 或 `postgres://...` DSN | 并发访问；安装 `memu-cli[postgres]` |
| 内存 | `:memory:` 或 `inmemory` | 临时测试；不同 CLI 进程之间不持久化 |

宿主适配器要求显式配置 Local 存储。写入与检索需使用相同数据库、provider 和模型。远程 Embedding 服务会接收被嵌入的文本，且可能收费；完全离线运行需要本地 Embedding。

## 检索设置 {#retrieval}

Codex、Claude Code 和 pi hook 共用以下开关：

```toml
[retrieval]
extract_query = false
```

默认 `false`：hook 取输入的前 800 个字符。设为 `true` 后，输入超过 800 且不超过 32,000 个字符时，由宿主模型提取聚焦的查询。提取限时 12 秒，可能产生模型费用；失败、超时或输入过长时回退到前 800 个字符。`retrieve` 命令本身只做 Embedding 检索，不会额外调用查询提取模型。详见[检索与注入](../hosts/retrieval.md)。

分数阈值按当前后端和查询类别区分：

```toml
[retrieval.cloud.min_score]
short = 0.55
long = 0.60
extracted = 0.58

# Local 默认不按分数过滤；校准后可添加：
# [retrieval.local.min_score]
# short = 0.55
# long = 0.60
# extracted = 0.58
```

`short` / `long` 使用独立的 **200 个非空白字符**分界；hook 根据原始输入分类，手动检索根据传入的查询分类。提取成功使用 `extracted`。阈值必须是 -1 到 1 之间的有限数值。Local 应按实际 Embedding 模型校准。分数过滤作用于匹配片段及其来源文件；resources 独立返回。相似度不保证语义相关。

## 环境变量覆盖 {#environment}

| TOML 键 | 环境变量 |
| --- | --- |
| `mode` | `MEMU_MEMORY_MODE` |
| `local.db` | `MEMU_DB` |
| `cloud.api_key` / `cloud.base_url` | `MEMU_CLOUD_API_KEY` / `MEMU_CLOUD_BASE_URL` |
| `embedding.provider` / `embedding.model` | `MEMU_EMBED_PROVIDER` / `MEMU_EMBED_MODEL` |
| `embedding.api_key` / `embedding.base_url` | `MEMU_API_KEY` / `MEMU_BASE_URL` |
| `embedding.batch_size` | `MEMU_EMBED_BATCH_SIZE` |
| `retrieval.extract_query` | `MEMU_QUERY_EXTRACT_ENABLED` |
| `retrieval.cloud.min_score.short/long/extracted` | `MEMU_CLOUD_RETRIEVE_MIN_SCORE_SHORT/LONG/EXTRACTED`（每类一个变量） |
| `retrieval.local.min_score.short/long/extracted` | `MEMU_LOCAL_RETRIEVE_MIN_SCORE_SHORT/LONG/EXTRACTED`（每类一个变量） |
| `network.proxy` | `MEMU_HTTP_PROXY` |
| `network.no_proxy` / `network.no_proxy_lowercase` | `NO_PROXY` / `no_proxy` |
| `telemetry.enabled` / `telemetry.debug` | `MEMU_TELEMETRY` / `MEMU_EVENTS_DEBUG` |
| `telemetry.base_url` / `telemetry.spool` | `MEMU_EVENTS_BASE_URL` / `MEMU_EVENTS_SPOOL` |
| `debug` | `MEMU_DEBUG` |
| `hosts.cowork.roots` | `MEMU_COWORK_ROOTS`（TOML 中使用路径数组） |
| `sources.docs` / `sources.templates` | `MEMU_DOCS_BASE_URL` / `MEMU_TEMPLATE_BASE_URL` |

使用 TOML 原生布尔值、数值和数组。空的 `sources.docs` / `sources.templates` 禁用远程刷新；空的 `telemetry.base_url` 禁用事件投递。旧别名 `MEMU_LLM_PROVIDER` 仍可读取；新配置使用 `embedding.provider`。

## 验证与安全修改 {#verify}

```sh
memu-pi config show
memu-pi doctor
memu-pi config --help
```

`config show` 报告已保存的后端配置及部分环境变量覆盖，不会列出所有最终生效值。`doctor` 验证后端访问。通过后按[快速开始](../guide/getting-started.md#_3-按宿主指南安装)激活集成，再测试一次真实对话。

命令会保护已有数据库、provider、模型身份，并拦截可能隐藏现有记忆的后端切换。使用 `--force` 前先核对配置。切换后端不会迁移记忆，更换 Embedding 模型不会转换已有向量。`init --cloud-api-key` 会选择 Cloud，离开已配置的 Local 存储时给出警告；不带 key 的 `init` 保留已有模式。保留备份，有计划地更换存储或模型。连接问题见[故障排查](../troubleshooting/index.md)。
