# Session Title 安装指南（Agent 执行版）

本文件写给执行安装的 Agent。按顺序执行，不要跳过验证；每一步的 `SKIP`
条件必须重新确认后才能继续。

## 0. 先确认边界

本资产只做两件事：在 `UserPromptSubmit` 注入一次命名要求；校验模型给出的标题。
它不能自己改标题，真正改名依赖宿主向模型暴露原生标题工具。

- 已验证：Python 核心、模拟 Codex 协议、独立入口、Codex app-server 标题探测路径。
- 未验证：当前版本 Codex Desktop 的自动改名、Pi 当前版本、OMP、Claude Code。
- 不支持：Claude Code、OMP。不要为这两个宿主安装本适配器。

缺少 `UserPromptSubmit` Hook 或原生标题工具时停止安装，报告缺哪一项。
不要用注入文本冒充改名能力。

## 1. 前置条件

| 检查 | 命令 | 通过标准 |
| --- | --- | --- |
| Python | `python -V` | 3.11 或更高 |
| Codex CLI | `codex --version` | 有版本输出 |
| Hook 配置 | 找到宿主的 `hooks.json` | 可读写，含 `UserPromptSubmit` 段 |
| 安装目录 | 自选固定路径 | 路径中有空格时必须加引号 |

POSIX 下把下文 `python` 换成 `python3`。

## 2. 复制资产

复制**整个** `session-title` 目录，不要只复制 `codex_hook.py`。

```powershell
$src = "<仓库根>\hooks\session-title"
$dst = "<安装根>\session-title"
New-Item -ItemType Directory -Force -Path (Split-Path $dst) | Out-Null
Copy-Item -Recurse -Force $src $dst
Get-ChildItem $dst
```

安装后必须包含：`session_title.py`、`codex_hook.py`、`hosts/codex.py`、
`hosts/pi.ts`、`README.md`。`__pycache__` 可以删除。

`codex_hook.py` 是独立入口，脚本所在目录会自动进入 `sys.path`，因此整个目录
复制到任意路径都能运行，不需要改代码或设置 `PYTHONPATH`。

## 3. 注册 Codex Hook

在 `hooks.json` 的 `UserPromptSubmit` 组里追加一条 `command`，不要替换或重排
已有条目。合并结果的最小形态：

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python -B -X utf8 \"D:/tools/session-title/codex_hook.py\"",
            "timeout": 15
          }
        ]
      }
    ]
  }
}
```

合并约束：

- `command` 用 `codex_hook.py` 的绝对路径，路径分隔符用 `/`，避免 JSON 转义问题。
- 追加到不带 `matcher` 的 `UserPromptSubmit` 组；已有 `matcher` 的组不要动。
- 全文只允许出现一条本资产的 command。
- 合并前备份 `hooks.json`；合并不成时恢复备份，不要继续。

合并后校验 JSON 可解析且条目数正确：

```powershell
python -B -X utf8 -c "import json,sys; d=json.load(open(sys.argv[1],encoding='utf-8')); c=[h['command'] for e in d['hooks']['UserPromptSubmit'] for h in e['hooks']]; print([x for x in c if 'session-title' in x]); assert sum('codex_hook.py' in x for x in c)==1" "<hooks.json>"
```

期望：打印包含该路径的一行，且断言通过。

## 4. 可选：项目 profile

需要项目级命名规则时，在**被命名项目**的根目录放 `.session-title.json`；
不要放进本资产目录，也不要提交到分享仓库。

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

不建 profile 时使用通用规则，无需额外配置。`SESSION_TITLE_PROFILE` 可指向其他
配置文件，但事件 cwd 不在该文件根目录内时会跳过。

## 5. 离线验证

在安装目录运行，不读写真实会话标题：

```powershell
python -B -X utf8 -m unittest discover -s "<安装根>\session-title" -p "test_*.py" -q
python -B -X utf8 "<安装根>\session-title\session_title.py" validate --title "项目 | 群脉 | 修复重复扫描"
python -B -X utf8 "<安装根>\session-title\session_title.py" validate --title "Agent Toolkit | 收紧标题状态"
python -B -X utf8 "<安装根>\session-title\session_title.py" validate --title ("项目 | " + ("超长" * 20))
```

期望：单测全通过；前两条 `valid` 为 `true`；第三条 `valid` 为 `false`，
`reason` 为 `too_long`。进程退出码始终为 0，必须读 JSON 字段，不能只看退出码。

## 6. 真实宿主验证

1. 新建一个会话，发出首个实质任务（不是在已有标题的会话里继续）。
2. 等该轮答复结束，观察宿主侧标题是否变成 `类型 | 对象 | 持续目标` 或
   `对象 | 持续目标`。
3. 主题不变时追问一轮，确认标题不会被重复改写。
4. 明确说“换个话题”或“更新标题”，确认只触发一次复核。

状态文件位置：

```text
%LOCALAPPDATA%\session-title\state\codex\<profile>\<hash>.json
```

阶段含义：`requested`（已请求未确认）、`review_requested`（复核请求）、
`applied`（已确认改名）、`manual`（用户改过，永久锁定）。状态文件不含 prompt、
标题内容或凭据。

## 7. 更新与卸载

更新：整目录替换安装副本，保留项目内 `.session-title.json` 和 state。
不要逐个文件手工打补丁。

卸载：从 `hooks.json` 删除本资产那一条 command，保留其他 Hook。
可选删除 `%LOCALAPPDATA%\session-title\state`；不清除也不影响宿主。

## 8. 排障

| 现象 | 可能原因 | 处理 |
| --- | --- | --- |
| 完全没有改名 | Hook 未执行、标题未知或宿主未暴露标题工具 | 先确认宿主版本支持该 Hook，再确认模型能看到改名工具 |
| 已有标题一直不变 | 命中人工标题保护 | 正常行为；手动改名即可 |
| 只改了一次 | 已达自动复核上限 2 次 | 正常行为；明确要求改名可再触发一次 |
| state 停在 `requested` | 模型没有调用标题工具 | 检查宿主的工具暴露与注入上下文 |
| 标题被判无效 | 空段、分隔符数量错误或超过 40 字符 | 正常校验；让模型重写标题 |
| `hooks.json` 解析失败 | 合并时破坏 JSON | 恢复备份后按第 3 节重新合并 |

不要通过修改安装副本里的 `session_title.py` 来“适配”宿主。需要改行为时修改
分享仓库的源文件，再整目录重装。

## 9. 完成标准

安装 Agent 报告结果时必须给出以下证据，缺一项就说明未完成：

- Python 版本与 `codex --version` 的实际输出。
- 安装目录的绝对路径与 `Get-ChildItem` 结果。
- `hooks.json` 校验命令的输出，确认只有一条本资产 command。
- 单测结果与三条 `validate` 的 JSON 结果。
- 真实会话的观察结论；未做真实验证时明确写“未验证”，不要写成成功。

不要提交 `.session-title.json`、state 目录、`__pycache__` 或任何会话数据。
