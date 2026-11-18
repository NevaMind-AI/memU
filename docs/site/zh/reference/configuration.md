# 配置

下面用 `memu-pi` 举例。使用 Codex 就换成 `memu-codex`，其他命令见[宿主接入](../hosts/index.md)。配置一次，各宿主共用。

## Cloud：填入 API key

登录 [memu.so](https://memu.so) 获取 API key，替换命令里的 `YOUR_MEMU_KEY`：

```sh
memu-pi config --cloud --cloud-api-key "YOUR_MEMU_KEY"
```

云端数据库和 Embedding 免费提供，不需要另外配置。

## Local：指定数据库和模型

以 **本机 SQLite + OpenAI Embedding** 为例：

```sh
memu-pi config --local --db "path-to-your-database/memu.sqlite3" --embed-provider openai --embed-model text-embedding-3-small --embed-api-key "YOUR_EMBEDDING_KEY"
```

运行前替换两处：

- `path-to-your-database/memu.sqlite3`：替换为数据库文件的**绝对路径**。
- `YOUR_EMBEDDING_KEY`：模型服务的 API key，和 memU Cloud 的 key 不同。

使用其他模型服务时，修改 `--embed-provider` 和 `--embed-model`；自定义接口地址加 `--embed-base-url "URL"`。完整参数见 `memu-pi config --help`。

远程模型服务会接收用于检索的文本，可能收费；完全离线使用需配置本地 Embedding 服务。

## 检查是否配好

```sh
memu-pi config show
memu-pi doctor
```

`config show` 查看已保存的配置；`doctor` 检查后端连接。通过后，回到[快速开始](../guide/getting-started.md#_3-按宿主指南安装)继续安装宿主集成。失败时查看[故障排查](../troubleshooting/index.md)。

::: tip 已有配置？
配置保存在 `~/.memu/config.env`，请勿分享其中的密钥。若切换后端、数据库或模型时命令拒绝修改，先核对当前配置；更换模型不会自动转换已有记忆的向量，不要直接强制覆盖。
:::
