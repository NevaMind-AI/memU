# Configuration

Examples use `memu-pi`. For Codex, use `memu-codex`; see [Host adapters](../hosts/index.md) for other binaries. Configure once and share the settings across hosts.

## Cloud: supply your API key

Sign in at [memu.so](https://memu.so) for an API key, then replace `YOUR_MEMU_KEY`:

```sh
memu-pi config --cloud --cloud-api-key "YOUR_MEMU_KEY"
```

The cloud database and embeddings are free and need no further configuration.

## Local: choose a database and model

This example uses **SQLite on your computer + OpenAI embeddings**:

```sh
memu-pi config --local --db "path-to-your-database/memu.sqlite3" --embed-provider openai --embed-model text-embedding-3-small --embed-api-key "YOUR_EMBEDDING_KEY"
```

Replace two values before running:

- `path-to-your-database/memu.sqlite3`: replace with the database file's **absolute path**.
- `YOUR_EMBEDDING_KEY`: your model provider's API key, separate from a memU Cloud key.

For another model service, change `--embed-provider` and `--embed-model`. Add `--embed-base-url "URL"` for a custom endpoint. Run `memu-pi config --help` for all options.

Remote model services receive the text used for retrieval and may charge for usage. Fully offline use requires a local embedding service.

## Check your configuration

```sh
memu-pi config show
memu-pi doctor
```

`config show` displays saved settings; `doctor` checks the backend connection. Once it passes, return to [Getting started](../guide/getting-started.md#_3-follow-the-host-installation-guide) to install your host integration. See [Troubleshooting](../troubleshooting/index.md) if it fails.

::: tip Already configured?
Settings are saved in `~/.memu/config.env`; keep its keys private. If a command refuses a backend, database, or model change, check the current settings first. Changing models does not convert existing memory vectors, so do not force an overwrite without checking.
:::
