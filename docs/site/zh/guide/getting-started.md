# 快速开始

memU 在 Agent 会话之间共享记忆和可复用技能。可以让 Agent 帮你安装，也可以自己运行命令，**选一种即可**。

## 让 Agent 帮你安装

将下面这段话发给你正在使用的 Agent：

> 请阅读 [https://memu.pro/SKILL.md](https://memu.pro/SKILL.md)，使用 uv 安装或升级 memu-cli，并按照当前宿主的指南完成配置和安装。

按 Agent 提示提供 Cloud API key 或 Local 模型配置即可。Cloud / Local 决定记忆存在哪里，两种安装方式都支持。

## 自己运行命令

按下面四步操作。支持直接安装的宿主运行 `install`；其他宿主的指南入口见[宿主接入](../hosts/index.md)。

## 1. 安装软件包

推荐使用 [uv](https://docs.astral.sh/uv/getting-started/installation/)，将 memU 安装到独立的工具环境：

```sh
uv tool install memu-cli
```

uv 会选择兼容的 Python 版本，并在需要时自动下载，无需自己安装和管理系统 Python。安装后若找不到命令，运行 `uv tool update-shell`，再重新打开终端。以后升级使用 `uv tool upgrade memu-cli`。

软件包包含 `memu` 及各宿主命令，例如：

```sh
memu-codex --help
memu-pi --help
```

## 2. 选择后端

选择记忆存在哪里。**初次使用推荐 Cloud：免费，也方便跨设备使用。**

| | ☁️ Cloud 云端 | 🗂️ Local 本地 |
| --- | --- | --- |
| 记忆存储 | memu.so 云端数据库 | 本机 SQLite，也可自建 Postgres |
| 模型服务 | 免费提供 Embedding（用于记忆检索） | 自行配置 Embedding 模型服务 |
| 使用特点 | 跨设备共享，网页查看记忆 | 自己掌控存储和模型 |
| 需要准备 | 登录 [memu.so](https://memu.so) 获取 API key | 数据库位置和模型服务配置 |

选好后继续安装，安装器会保存配置。Local 的费用、联网要求及详细设置见[配置参考](../reference/configuration.md)。

## 3. 安装宿主集成 {#_3-按宿主指南安装}

选择你使用的 Agent，运行对应命令：

| Agent | 安装命令 |
| --- | --- |
| Codex | `memu-codex install` |
| Claude Code | `memu-claude-code install` |
| pi | `memu-pi install` |
| Hermes | `memu-hermes install` |

按终端提示选择后端并填入配置，安装器会保存设置；已有配置会复用。安装报错时按诊断处理。

安装成功后，pi 运行 `/reload` 或开启新会话；Claude Code 和 Hermes 开启新会话。Hermes 提示重启时，重启正在运行的 Hermes 进程。

其他 Agent 的安装入口见[宿主接入](../hosts/index.md)。

## 4. 验证连接

使用自己宿主的命令：

```sh
memu-pi doctor
memu-pi retrieve "这个项目有什么需要记住的？"
```

新存储返回空结果可能是正常情况。后端验证说明连接可用；还需要在宿主中进行一次真实对话，检查检索投递和后台记忆处理。检查失败时参阅[故障排查](../troubleshooting/index.md)。

## 卸载

运行对应宿主的卸载命令，例如 pi：

```sh
memu-pi uninstall
```

Codex、Claude Code、Hermes 分别使用 `memu-codex uninstall`、`memu-claude-code uninstall`、`memu-hermes uninstall`。卸载完成后，按终端提示重载或重启所用的 Agent。

这些命令移除宿主集成，保留共享配置和记忆数据。其他宿主见[宿主接入](../hosts/index.md)。
