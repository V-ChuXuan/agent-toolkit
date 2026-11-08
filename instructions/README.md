# Instructions

项目级 Agent 指令模板。复制到目标项目根目录并填写占位符，作为该项目 `AGENTS.md`
的起点。

| 资产 | 用途 | 语言 | 状态 | 版本 |
| --- | --- | --- | --- | --- |
| [project-agents.md](project-agents.md) | 项目 `AGENTS.md` 模板 | English | `experimental` | `0.1.0` |
| [project-agents.zh-CN.md](project-agents.zh-CN.md) | 项目 `AGENTS.md` 模板 | 简体中文 | `experimental` | `0.1.0` |

## 行为约定

| 字段 | 内容 |
| --- | --- |
| 用途 | 给新项目提供一份可执行的项目级 Agent 指令起点 |
| 触发场景 | 新建项目、整理已有项目规则，或需要统一多个项目的 Agent 约定 |
| 输入 | 项目名称、目的、常用命令、不成文约定、专项规则入口 |
| 输出 | 目标项目根目录的 `AGENTS.md`，可选同目录 `CLAUDE.md` |
| 依赖 | 无运行时依赖；模板是纯 Markdown |
| 验证方式 | 占位符全部替换；按项目实际命令跑一次最小验证 |
| 状态 | `experimental` |
| 版本 | `0.1.0` |

## 使用

1. 选择语言版本，复制到目标项目根目录并命名为 `AGENTS.md`。
2. 替换全部 `{{...}}` 占位符，删除没有内容的条目和“填写后删除本句”之类的提示。
3. 需要 Claude Code 时，在同目录创建 `CLAUDE.md`，内容只有 `@AGENTS.md`。
4. 项目有专项规则文件时，在“专项规则入口”里写清文件、何时必须读、管什么。

占位符检查（PowerShell）：

```powershell
Select-String -Path "AGENTS.md" -Pattern "\{\{" -Encoding utf8
```

期望：无输出。有输出说明还有未填写的内容。

## 注意

- 模板不含工作区专用路径、个人项目名或凭据；采用时按项目实际情况补齐。
- 本目录是分享副本，不随工作区内的模板副本自动同步；更新时按 diff 手动同步。
- 不要把模板原样留在子目录并命名为 `AGENTS.md`：宿主会把子目录中的 `AGENTS.md`
  当成该目录树的真实指令加载，`{{...}}` 占位符会被误读。因此本目录使用
  `project-agents.md` 命名。
