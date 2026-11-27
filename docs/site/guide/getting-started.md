# Getting started

memU shares memory and reusable skills between agent sessions. Ask your agent to install it, or run the commands yourself. **Choose one approach.**

## Ask your agent to install

Send this message to the agent you use:

> Read [https://memu.pro/SKILL.md](https://memu.pro/SKILL.md), use uv to install or upgrade memu-cli, and follow the current host's guide to configure and install the integration.

Supply your Cloud API key or Local model settings when prompted. Cloud / Local determines where memory lives; both installation approaches support either option.

## Run the commands yourself

Follow the four steps below. Hosts with a direct installer use `install`; see [Host adapters](../hosts/index.md) for the guide entry points for other hosts.

## 1. Install the package

We recommend [uv](https://docs.astral.sh/uv/getting-started/installation/) to install memU in an isolated tool environment:

```sh
uv tool install memu-cli
```

uv selects a compatible Python version and automatically downloads it if needed, so you do not need to manage a system Python installation. If the installed commands are not found, run `uv tool update-shell` and reopen your terminal. To upgrade later, run `uv tool upgrade memu-cli`.

The package includes `memu` and the host binaries. For example:

```sh
memu-codex --help
memu-pi --help
```

## 2. Choose a backend

Choose where your memories live. **For a first setup, we recommend Cloud: it is free and works across devices.**

| | ☁️ Cloud | 🗂️ Local |
| --- | --- | --- |
| Memory storage | Cloud database at memu.so | SQLite on your computer, or self-managed Postgres |
| Model service | Free embeddings for memory retrieval | Configure your own embedding service |
| Benefits | Share across devices; view memories online | Control your storage and model |
| What to prepare | Sign in at [memu.so](https://memu.so) for an API key | Database location and model service settings |

Continue with installation after choosing; the installer saves your settings. See [Configuration](../reference/configuration.md) for Local costs, network requirements, and detailed settings.

## 3. Install your host integration {#_3-follow-the-host-installation-guide}

Run the command for your agent:

| Agent | Install command |
| --- | --- |
| Codex | `memu-codex install` |
| Claude Code | `memu-claude-code install` |
| pi | `memu-pi install` |
| Hermes | `memu-hermes install` |

Follow the terminal prompts to choose and configure a backend. The installer saves your settings and reuses existing configuration. If installation fails, follow its diagnostic.

After installation, run `/reload` in pi or open a new session. Open a new session in Claude Code and Hermes. Restart running Hermes processes when the installer requests it.

See [Host adapters](../hosts/index.md) for other agents.

## 4. Verify the connection

Use your host's binary:

```sh
memu-pi doctor
memu-pi retrieve "What should I remember about this project?"
```

An empty result can be normal for a new store. Backend verification confirms connectivity; a subsequent real conversation checks retrieval delivery and background memory processing inside the host. See [Troubleshooting](../troubleshooting/index.md) if these checks fail.

## Uninstall

Run your host's uninstall command. For pi:

```sh
memu-pi uninstall
```

For Codex, Claude Code, and Hermes, use `memu-codex uninstall`, `memu-claude-code uninstall`, and `memu-hermes uninstall`, respectively. After uninstalling, follow the terminal instructions to reload or restart your agent.

These commands remove the host integration and preserve shared settings and memory data. See [Host adapters](../hosts/index.md) for other hosts.
