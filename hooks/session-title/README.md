# Session Title

在首个实质任务完成前，向 Agent 提供一次会话命名请求。核心负责门控、上下文准备和标题校验；最终标题由模型结合当前任务生成，宿主负责实际改名。

| 字段 | 内容 |
| --- | --- |
| 用途 | 为长期任务生成可辨识的会话标题，保留人工标题 |
| 触发场景 | 宿主收到首个有效用户任务，当前标题已确认为空 |
| 输入 | host、session_id、cwd、prompt、current_title；可选 profile |
| 输出 | 核心返回 request_title 或 skip JSON；Codex 输出 additionalContext，Pi 注册标题工具 |
| 依赖 | Python 3.11+ 标准库；Codex 适配需可用的 Codex CLI，Pi 适配需相应扩展 API |
| 验证方式 | 下方 Python 单测；宿主实际改名需另做集成验证 |
| 状态 | experimental |
| 版本 | 0.1.0 |

## 快速检查

以下命令从本仓库根目录运行，不需要宿主、模型或凭据：

```sh
python -B -X utf8 -m unittest discover -s hooks/session-title -p "test_*.py" -q
python -B -X utf8 hooks/session-title/session_title.py validate --title "Example | Clarify hook behavior"
```

单测使用临时 profile 和模拟 app-server，不读取维护者工作区配置，也不修改真实会话标题。

## 行为约定

- 先完成首个实质任务，在发送最终答复前请求宿主原生标题工具改名一次。
- 推荐格式为 `模块名 | 持续目标`，目标 24 个 Unicode 字符，软上限 24，硬上限 80。
- 优先写具体对象、行为、错误现象或决策，避免空泛标题。
- 人工标题、未知标题、工具不可用、状态写入失败时静默跳过。
- 首个有效请求 claim 后，同一 host/profile/session 不再请求；请求并不证明改名成功。
- 不向用户展示标题建议或解释改名过程。

## 目录与入口

```text
session-title/
  session_title.py       # 核心 prepare/validate CLI
  codex_hook.py          # 可从任意 cwd 启动的 Codex 薄入口
  hosts/codex.py         # Codex command-hook 适配器
  hosts/pi.ts            # Pi 扩展适配器
  test_*.py              # 标准库单测
```

接入时保留完整目录。`hosts/codex.py` 供薄入口导入，直接启动请使用 `codex_hook.py`。

## Profile

从事件的 `cwd` 向上查找最近的 `.session-title.json`，该文件所在目录是 profile 根。找不到时使用已验证的 Git 根或当前目录的 generic 规则，无需创建 profile。

下面是可按项目目录调整的通用 profile 示例：

```json
{
  "version": 1,
  "name": "example",
  "language": "auto",
  "kind_rules": [
    {"prefix": "packages", "kind": "Package", "object_depth": 1},
    {"prefix": "docs", "kind": "Docs", "object": "Documentation"}
  ],
  "aliases": {"sample-app": "Sample App"},
  "domain_terms": ["Hook", "Agent"],
  "exclude": [".git", ".tmp", "node_modules"]
}
```

- `language` 可选 `auto`、`zh-CN` 或 `en`。
- `kind_rules` 使用最长路径组件前缀；`object_depth` 从前缀后的路径取对象名，或用 `object` 固定显示名。
- `aliases` 只改写对象显示名。
- `exclude` 匹配相对根目录的路径前缀；不会匹配任意中间目录段。
- `SESSION_TITLE_PROFILE` 可指定配置文件；事件 cwd 不在该 profile 根目录内时跳过。
- 个人 profile 留在使用项目中，不提交到此资产目录。

## 核心输入输出

`prepare` 从标准输入读取 JSON。例如：

```json
{
  "host": "codex",
  "session_id": "example-session",
  "cwd": ".",
  "prompt": "Review the login error handling",
  "current_title": null
}
```

`cwd` 由宿主传入实际工作目录。`current_title` 必须由适配器明确提供：缺失或不是字符串/null 表示未知并跳过；`null` 或空字符串表示已确认无标题；非空字符串表示已有标题，跳过且不占 state。

`prepare` 返回 `action=request_title` 或 `action=skip` 与 reason。JSON 中的 context 可包含完整 cwd 和 profile aliases，用于本地适配；不会保存原始 prompt。Codex 注入的消息仅保留目录提示、相对路径、领域词和命名要求，不包含原始 prompt、session id 或核心生成的最终标题。

`validate` 从 `--title` 或标准输入的 `title` 字段读取标题，返回 valid、reason、title、chars；超过软上限时附 warning。CLI 的 `--format json|text` 放在子命令前。进程退出码为 0，调用方需检查 action/valid，不能仅据退出码判断命名成功。

## 宿主接入

### Codex

先从仓库根目录取得独立入口的绝对路径。PowerShell 示例：

```powershell
$hook = (Resolve-Path "hooks/session-title/codex_hook.py").Path
$command = 'python -B -X utf8 "' + $hook + '"'
$command
```

将得到的命令手动加入宿主 `UserPromptSubmit` 的 command Hook，timeout 建议 15 秒。不要覆盖已有 Hook 列表。宿主的注册、信任和启用要求需按实际版本确认。

适配器通过 `codex app-server --stdio` 的 `thread/read` 探测标题；可用 `CODEX_EXECUTABLE` 指定可执行文件。它只请求命名并注入上下文，不直接写标题。真实自动改名还要求宿主向当前模型暴露安全的原生标题工具；工具不存在时保持跳过。

### Pi

显式加载 [hosts/pi.ts](hosts/pi.ts)。扩展内部相对定位 Python 核心，可通过 `SESSION_TITLE_PYTHON` 选择解释器。它注册 `set_session_title`，调用宿主 API 后读回验证。使用前需确认所用 Pi 版本的 ExtensionAPI 兼容性。

### 验证范围

历史集成记录曾观察到 Codex 首轮上下文注入和 app-server 改名原语、Pi 1.3.0 扩展改名读回；它们不是本次发布的当前端到端验证。本次只验证 Python 核心、模拟 Codex 协议和独立入口。

OMP 18.0.4 的历史有界试验停在模型请求超时，未达到支持门槛；Claude Code 没有本资产已验证的安全 Hook 改名接入。两者均不应默认安装此适配器。Codex Desktop 自动改名和 Pi 当前版本需使用者在自己的宿主中验证。

本次未运行宿主注册、Pi/OMP 启动或真实会话改名，以保留当前宿主配置与用户会话。

## 状态与隐私

- `SESSION_TITLE_STATE_ROOT` 可指定 state 根。默认使用 `LOCALAPPDATA` 下的 `session-title/state`；变量不可用时回退到用户目录下 `AppData/Local/session-title/state`。
- 分区为 host/profile/session-id 哈希；state 文件只含版本、host、profile、阶段和时间，不保存 prompt、完整 cwd、标题或凭据。
- 成功 claim 使用 `O_EXCL`，并发只有一个请求；调用时按 30 天 TTL 清理过期 state。
- 核心不读取 transcript、rollout、数据库或历史消息，不直接写宿主私有存储；Codex 适配器通过公开 app-server API 读取标题。

## 停用

从宿主配置移除本资产的 command 条目或显式扩展加载项，再按宿主要求重载。保留其他 Hook 与原有配置；无需为停用本资产清除 state。
