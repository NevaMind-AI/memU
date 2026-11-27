# Configuration

Examples use `memu-pi`. Replace it with your [host's binary](../hosts/index.md). All adapters share the same configuration for memory writes and retrieval.

## File and precedence {#file}

Settings resolve in order: **process environment → `~/.memu/config.toml` → defaults**. Set `MEMU_CONFIG` to use another TOML path. Background processes need access to the same file; a variable exported only in an interactive shell may not reach the host or its workers.

`init` and `config` create or update the file. It contains plaintext credentials: keep it private and redact keys before sharing diagnostics. On POSIX, memU restricts file permissions; on Windows, it inherits directory ACLs.

An existing `config.env` migrates automatically on first access when no TOML file exists. The original remains intact for rollback; once TOML exists, edit that file. Failed automatic migration reports a warning and keeps legacy reads available. `MEMU_CONFIG_ENV` still selects a legacy location, with the TOML target beside it unless `MEMU_CONFIG` is set. Client identity is stored separately in the adjacent `config.state.toml` file.

## Cloud {#cloud}

Get a key from [memu.so](https://memu.so), then run:

```sh
memu-pi config --cloud --cloud-api-key "YOUR_MEMU_KEY"
```

Cloud provides the database and embeddings. The corresponding TOML is:

```toml
mode = "cloud"

[cloud]
api_key = "YOUR_MEMU_KEY"
# base_url = "https://api.memu.so/api/v4/memory/"
```

Use `--cloud-base-url "URL"` for a custom Cloud endpoint. Cloud currently stores memory and skill recall files; workspace resources can be submitted but are not yet persisted or retrieved by Cloud.

## Local {#local}

For SQLite with OpenAI embeddings:

```sh
memu-pi config --local --db "ABSOLUTE_PATH/memu.sqlite3" --embed-provider openai --embed-model text-embedding-3-small --embed-api-key "YOUR_EMBEDDING_KEY"
```

Replace the path with an absolute database file path and supply the embedding provider's key. A memU Cloud key does not authenticate an embedding provider. The corresponding TOML is:

```toml
mode = "local"

[local]
db = "/absolute/path/memu.sqlite3"

[embedding]
provider = "openai"
model = "text-embedding-3-small"
api_key = "YOUR_EMBEDDING_KEY"
# base_url = "https://your-compatible-endpoint/v1"
# batch_size = 10
```

On Windows, use a path such as `db = 'C:\data\memu.sqlite3'` (TOML literal string) or `db = "C:/data/memu.sqlite3"`. Change `--embed-provider` / `--embed-model` for another service; use `--embed-base-url` for a custom endpoint. `embedding.batch_size` must be a positive integer; lower it when a provider limits inputs per request. Omitted model, key, endpoint and batch size follow provider defaults and supported provider environment variables.

| Store | `local.db` value | Use |
| --- | --- | --- |
| SQLite | Absolute path or `sqlite:///...` URL | Local persistence; one writer at a time |
| Postgres | `postgresql://...` or `postgres://...` DSN | Concurrent access; install `memu-cli[postgres]` |
| In-memory | `:memory:` or `inmemory` | Disposable testing; no persistence across CLI processes |

Host adapters require an explicit local store. Keep the same database, provider and model for recording and retrieval. Remote embedding services receive the text being embedded and may charge for usage; fully offline operation requires local embeddings.

## Retrieval settings {#retrieval}

Codex, Claude Code and pi hooks share this switch:

```toml
[retrieval]
extract_query = false
```

It defaults to `false`: hooks use the first 800 characters of a prompt. Set it to `true` to ask the host model for a focused query when input exceeds 800 characters and is at most 32,000 characters. Extraction has a 12-second deadline and can incur model cost; failure, timeout or oversized input falls back to the first 800 characters. The `retrieve` command itself performs embedding retrieval without a query-extraction model call. See [Retrieval and injection](../hosts/retrieval.md).

Score cutoffs depend on the active backend and query category:

```toml
[retrieval.cloud.min_score]
short = 0.55
long = 0.60
extracted = 0.58

# Local has no score cutoff by default. Add calibrated values if needed:
# [retrieval.local.min_score]
# short = 0.55
# long = 0.60
# extracted = 0.58
```

`short` / `long` use a separate boundary of **200 non-whitespace characters**; hooks classify the original prompt, while manual retrieval classifies the supplied query. A successful extraction uses `extracted`. Cutoffs must be finite numbers between -1 and 1. Calibrate Local values against your embedding model. Score filtering applies to matched segments and their files; resources are independent. Similarity is not a guarantee of semantic relevance.

## Environment overrides {#environment}

| TOML key | Environment variable |
| --- | --- |
| `mode` | `MEMU_MEMORY_MODE` |
| `local.db` | `MEMU_DB` |
| `cloud.api_key` / `cloud.base_url` | `MEMU_CLOUD_API_KEY` / `MEMU_CLOUD_BASE_URL` |
| `embedding.provider` / `embedding.model` | `MEMU_EMBED_PROVIDER` / `MEMU_EMBED_MODEL` |
| `embedding.api_key` / `embedding.base_url` | `MEMU_API_KEY` / `MEMU_BASE_URL` |
| `embedding.batch_size` | `MEMU_EMBED_BATCH_SIZE` |
| `retrieval.extract_query` | `MEMU_QUERY_EXTRACT_ENABLED` |
| `retrieval.cloud.min_score.short/long/extracted` | `MEMU_CLOUD_RETRIEVE_MIN_SCORE_SHORT/LONG/EXTRACTED` (one variable per category) |
| `retrieval.local.min_score.short/long/extracted` | `MEMU_LOCAL_RETRIEVE_MIN_SCORE_SHORT/LONG/EXTRACTED` (one variable per category) |
| `network.proxy` | `MEMU_HTTP_PROXY` |
| `network.no_proxy` / `network.no_proxy_lowercase` | `NO_PROXY` / `no_proxy` |
| `telemetry.enabled` / `telemetry.debug` | `MEMU_TELEMETRY` / `MEMU_EVENTS_DEBUG` |
| `telemetry.base_url` / `telemetry.spool` | `MEMU_EVENTS_BASE_URL` / `MEMU_EVENTS_SPOOL` |
| `debug` | `MEMU_DEBUG` |
| `hosts.cowork.roots` | `MEMU_COWORK_ROOTS` (TOML uses an array of paths) |
| `sources.docs` / `sources.templates` | `MEMU_DOCS_BASE_URL` / `MEMU_TEMPLATE_BASE_URL` |

Use native TOML booleans, numbers and arrays. Empty `sources.docs` / `sources.templates` disable remote refresh; an empty `telemetry.base_url` disables event delivery. The legacy `MEMU_LLM_PROVIDER` alias remains readable; new configuration uses `embedding.provider`.

## Verify and change safely {#verify}

```sh
memu-pi config show
memu-pi doctor
memu-pi config --help
```

`config show` reports saved backend settings and selected environment overrides; it is not a dump of every resolved setting. `doctor` verifies backend access. Then follow [Getting started](../guide/getting-started.md#_3-follow-the-host-installation-guide) to activate the integration and test a real turn.

Commands protect an existing store/provider/model identity and backend switches that could hide existing memories. Inspect the current settings before using `--force`. Switching backend does not migrate memories; changing an embedding model does not convert stored vectors. `init --cloud-api-key` selects Cloud with a warning when leaving a configured Local store; bare `init` preserves the existing mode. Keep backups and plan any store or model replacement deliberately. See [Troubleshooting](../troubleshooting/index.md) for connection failures.
