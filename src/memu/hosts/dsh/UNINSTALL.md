# 卸载 DSH 的 memU

## 任务身份

- 当前任务名：`{{task_name}}`
- 历史任务名：{{former_task_names}}
- 迁移与移除时会被识别的名字：{{all_task_names}}

1. 移除桥接调度：DSH 自己的定时器（`schedule_*` 工具）里删掉 `{{task_name}}`；
   若用操作系统级调度，删掉对应的计划任务 / launchd / crontab 条目，然后确认它
   已经不存在。
2. 从 DSH profile 移除插件 bundle：

   ```sh
   dsh plugin --profile <profile> remove dsh-memu
   ```

   随后确认 profile 的 `package.json` 里 `dependencies` 与 `dsh.profile.bundles`
   都不再含 `dsh-memu`。重新加载 DSH 后 `memu_retrieve` 等工具应当消失。
3. 若当初是用托管块接入的检索指令，再执行 `memu-dsh remove-instruction`
   （安装时用了自定义 `--path` / `--skills-dir` 就传同样的值）。它只删 memU 的
   托管块与 `memu-retrieve` skill，用户自己的内容保持原样。
4. 除非用户明确要求抹掉记忆，否则保留 `~/.memu/config.env`、记忆存储，以及
   `~/.memu/hosts/dsh/.session_manifest.dsh.json`。其余 `~/.memu/hosts/dsh/` 下的
   文件可以清掉；`~/.dsh/memu/transcripts/` 是导出中间产物，删掉只会让**未挖掘**的
   对话失去素材，已提交的记忆不受影响——要先问用户。
5. 删包之前先上报卸载：

   ```sh
   memu-dsh report uninstall
   ```

   失败时用 `memu-dsh report error --stage uninstall --detail "<出了什么问题>"`。
   上报是尽力而为的，不得包含凭据 (credential)、绝对路径 (absolute path)、
   命令输出 (command output)、记忆或转录文本。
6. Remove `memu-cli` —— 只有在没有别的宿主适配器还在用时才做；还有别的宿主时，
   事件 spool 与共享记忆配置也一并保留。
