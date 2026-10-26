# Agent Toolkit

把个人开发实践中积累的 Prompts、Skills、MCP 工具、Hooks 和工作方法整理成可复用的 Agent 资产。每项资产独立说明用途、前提和验证方式，使用时按需选取。

这里维护的是去掉个人项目名、本机路径和私有配置后的源文件。你可以从 [README Writer](skills/readme-writer/README.md) 或 [会话标题 Hook](hooks/session-title/README.md) 开始；其余类别目前只有目录说明。

## 资产索引

| 资产 | 解决的问题 | 适用场景 | 状态 | 版本 |
| --- | --- | --- | --- | --- |
| [README Writer](skills/readme-writer/README.md) | 按项目证据写作、更新、精简、审查和格式化 README | 明确要求处理 README 或类似 Markdown 项目文档 | `experimental` | `0.1.0` |
| [Session Title](hooks/session-title/README.md) | 为宿主准备一次会话命名请求 | 宿主支持 Hook 或扩展，并能确认当前标题状态 | `experimental` | `0.1.0` |

`experimental` 表示已有可运行内容，仍需在自己的宿主和任务上验证。Python 检查通过不代表模型输出质量或宿主自动改名已得到保证。

## 目录

| 目录 | 内容 | 当前情况 |
| --- | --- | --- |
| [skills/](skills/README.md) | 以 `SKILL.md` 为入口的工作技能，连同所需脚本和引用资料 | README Writer |
| [hooks/](hooks/README.md) | 由宿主事件触发的脚本与适配器 | Session Title |
| [prompts/](prompts/README.md) | 可独立使用的任务提示词与输入输出约定 | 暂无资产 |
| [mcp/](mcp/README.md) | MCP 工具、服务或可分享的接入说明 | 暂无资产 |
| [patterns/](patterns/README.md) | 可复用的工作方法、判断步骤和验证方式 | 暂无资产 |
| [experiments/](experiments/README.md) | 尚未形成正式资产的实验与观察 | 暂无资产 |

先看索引中的问题和场景，再读目标资产的 README。Skill 的详细行为在它的 `SKILL.md` 中；Hook 的宿主要求在其接入说明中。

## 使用

仓库没有统一安装器。按目标资产的说明，复制完整资产目录，或让宿主引用该目录。宿主的发现规则、权限和版本要求各不相同。

- **Skills**：从资产 README 进入 `SKILL.md`，连同 `references/` 和 `scripts/` 使用。README Writer 需要明确调用，不因文档中出现 README 一词自动启用。
- **Hooks**：先阅读输入输出和宿主限制，再按说明接入；保留已有配置的恢复方式。
- **Prompts、MCP、Patterns**：当前暂无可安装内容，后续资产会提供独立说明。

本仓库中的文件是后续维护源。已经安装在 `.codex/hooks`、`.codex/skills`、`.agents/skills` 或全局目录的副本属于安装或适配位置。**复制文件不会改变现有安装入口，也不会建立自动同步。** 更新安装副本前应先检查差异，再运行该资产的验证。

## 生命周期

| 状态 | 含义 | 采用建议 |
| --- | --- | --- |
| `draft` | 用途或接口还在整理，缺少完整验证 | 作为草稿阅读 |
| `experimental` | 有实现或可复现步骤，契约仍可能调整 | 在受控场景试用 |
| `stable` | 契约、依赖和验证方式明确，已有实际复用记录 | 按说明采用并验证目标环境 |
| `retired` | 停止推荐，保留原因和替代入口 | 仅用于理解历史或迁移 |

状态变化只更新资产说明和索引，不自动安装、卸载或删除文件。资产版本单独维护；改变输入输出或接入方式时，写明兼容性与迁移方法。

## 添加资产

1. 选择对应目录，以一个具体问题命名资产；先搜索索引，避免重复。
2. 提取通用做法，把个人项目名、固定路径、账号信息和私有数据替换为参数或明确的示例。
3. Skill 使用 `skills/<name>/SKILL.md`，其余资产使用独立 README；保留实际依赖的脚本、引用资料与来源声明。
4. 写全下表，运行最小验证，再在本页索引中登记。未验证的部分直接标明。

| 字段 | 最低要求 |
| --- | --- |
| 用途 | 解决的具体问题 |
| 触发场景 | 什么时候用，什么时候跳过 |
| 输入 | 用户、宿主或文件需要提供什么 |
| 输出 | 产生的文件、文本或行为及副作用 |
| 依赖 | 运行时、宿主能力、权限及外部服务 |
| 验证方式 | 可执行命令或可复现的检查步骤 |
| 当前状态 | `draft`、`experimental`、`stable` 或 `retired` |
| 版本 | 当前资产版本与必要的兼容说明 |

不发布会话历史、真实凭据、个人配置或运行缓存。示例中的密钥只能是占位符；参考或改编的内容必须保留来源与许可证。

## 验证

Python 脚本使用标准库，项目基线为 Python 3.11+。在仓库根目录运行：

```sh
python -B -X utf8 skills/readme-writer/scripts/selftest.py
python -B -X utf8 -m unittest discover -s hooks/session-title -p "test_*.py" -q
python -B -X utf8 skills/readme-writer/scripts/check_readme.py README.md
```

自检和单测覆盖脚本规则、输入输出与受控夹具。文档检查器检查结构和链接，不证明正文主张；真实宿主、模型质量和外部服务需要按资产说明另行验证。

## 许可证

自有内容采用 [MIT License](LICENSE)。改编内容的来源和上游许可见 [第三方声明](THIRD_PARTY_NOTICES.md)。
