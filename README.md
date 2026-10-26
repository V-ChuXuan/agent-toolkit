<div align="center">

# Agent Toolkit

**把个人开发实践提炼成可按需采用的 Agent 资产。**

面向使用 Agent 的开发者，收录 Prompts、Skills、MCP 工具、Hooks 和工作方法。

[浏览资产](#资产索引) · [使用说明](#用法) · [简体中文](README.md) · [English](README.en.md)

</div>

## 快速开始

按要解决的问题选择资产，再阅读它的独立说明。采用 Skill 时保留完整目录；接入 Hook 前先确认宿主能力。

### 资产索引

| 资产 | 解决的问题 | 适用场景 | 状态 | 版本 |
| --- | --- | --- | --- | --- |
| [README Writer](skills/readme-writer/README.md) | 按项目证据写作、更新、精简、审查和格式化 README | 明确要求处理 README 或类似 Markdown 项目文档 | `experimental` | `0.1.0` |
| [Session Title](hooks/session-title/README.md) | 为宿主准备一次会话命名请求 | 宿主支持 Hook 或扩展，并能确认当前标题状态 | `experimental` | `0.1.0` |

`experimental` 表示已有可运行内容，仍需在自己的宿主和任务上验证。Python 检查通过不代表模型输出质量或宿主自动改名已得到保证。

处理 README 时，让 Agent 先阅读 [README Writer 的 SKILL.md](skills/readme-writer/SKILL.md)，再按其中的模式、证据、预览和写入流程执行。

需要会话命名时，先读 [Session Title 的宿主接入](hooks/session-title/README.md#宿主接入)。它准备命名请求，实际改名还依赖宿主原生能力。

## 用法

### 目录

| 目录 | 内容 | 当前情况 |
| --- | --- | --- |
| [skills/](skills/README.md) | 以 `SKILL.md` 为入口的工作技能，连同所需脚本和引用资料 | README Writer |
| [hooks/](hooks/README.md) | 由宿主事件触发的脚本与适配器 | Session Title |
| [prompts/](prompts/README.md) | 可独立使用的任务提示词与输入输出约定 | 暂无资产 |
| [mcp/](mcp/README.md) | MCP 工具、服务或可分享的接入说明 | 暂无资产 |
| [patterns/](patterns/README.md) | 可复用的工作方法、判断步骤和验证方式 | 暂无资产 |
| [experiments/](experiments/README.md) | 尚未形成正式资产的实验与观察 | 暂无资产 |

先看索引中的问题和场景，再读目标资产的 README。Skill 的详细行为在它的 `SKILL.md` 中；Hook 的宿主要求在其接入说明中。

### 使用

仓库没有统一安装器。按目标资产的说明，复制完整资产目录，或让宿主引用该目录。宿主的发现规则、权限和版本要求各不相同。

- **Skills**：从资产 README 进入 `SKILL.md`，连同 `references/` 和 `scripts/` 使用。README Writer 需要明确调用，不因文档中出现 README 一词自动启用。
- **Hooks**：先阅读输入输出和宿主限制，再按说明接入；保留已有配置的恢复方式。
- **Prompts、MCP、Patterns**：当前暂无可安装内容，后续资产会提供独立说明。

本仓库中的文件是后续维护源。已经安装在 `.codex/hooks`、`.codex/skills`、`.agents/skills` 或全局目录的副本属于安装或适配位置。**复制文件不会改变现有安装入口，也不会建立自动同步。** 更新安装副本前应先检查差异，再运行该资产的验证。

## 参与

### 生命周期

| 状态 | 含义 | 采用建议 |
| --- | --- | --- |
| `draft` | 用途或接口还在整理，缺少完整验证 | 作为草稿阅读 |
| `experimental` | 有实现或可复现步骤，契约仍可能调整 | 在受控场景试用 |
| `stable` | 契约、依赖和验证方式明确，已有实际复用记录 | 按说明采用并验证目标环境 |
| `retired` | 停止推荐，保留原因和替代入口 | 仅用于理解历史或迁移 |

状态变化只更新资产说明和索引，不自动安装、卸载或删除文件。资产版本单独维护；改变输入输出或接入方式时，写明兼容性与迁移方法。

### 添加资产

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

## 开发

### 验证

Python 脚本使用标准库，项目基线为 Python 3.11+。在仓库根目录运行：

```sh
python -B -X utf8 skills/readme-writer/scripts/selftest.py
python -B -X utf8 -m unittest discover -s hooks/session-title -p "test_*.py" -q
python -B -X utf8 skills/readme-writer/scripts/check_readme.py README.md --pair README.en.md
```

自检和单测覆盖脚本规则、输入输出与受控夹具。文档检查器检查结构和链接，不证明正文主张；真实宿主、模型质量和外部服务需要按资产说明另行验证。

上述命令在独立临时副本中执行，环境为 Windows、Python 3.15.0。自检和单测通过，双语文档检查无错误或警告。该结果不代表其他 Python 版本或操作系统的运行验证。

## 什么时候不该用

当前资产均为 `experimental`。模型输出质量、Codex Desktop 自动改名和 Pi/OMP 当前兼容性未在本次验证；缺少宿主所需原生能力时，Hook 无法替代它。

需要统一安装器、自动同步或现成 MCP 服务时，当前仓库尚不能提供。Prompts、MCP、Patterns 和 Experiments 目前只有目录说明。

## 许可证

自有内容采用 [MIT License](LICENSE)。改编内容的来源和上游许可见 [第三方声明](THIRD_PARTY_NOTICES.md)。

## 致谢

- [QingYunA/readme-skill](https://github.com/QingYunA/readme-skill)：README 工作流、复核约定和写作规范。
- [NewTurn2017/readme-writer](https://github.com/NewTurn2017/readme-writer)：分类、模板和证据清单结构。
- [RichardLitt/standard-readme](https://github.com/RichardLitt/standard-readme)：章节命名与顺序参考。

<p align="center"><sub>如果这些资产对你有帮助，欢迎点亮 ⭐，让更多有同样需求的人发现它。</sub></p>
