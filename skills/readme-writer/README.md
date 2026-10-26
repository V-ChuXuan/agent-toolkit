# README Writer

基于项目文件和可核实的来源处理 README。先检查证据，再组织内容；扫描器和检查器用于辅助验证，不能代替对主张真实性的判断。

| 字段 | 内容 |
| --- | --- |
| 用途 | 写作、更新、精简、审查 README，以及保持内容的 Markdown 格式整理 |
| 触发场景 | 用户明确要求处理 README 或类似 Markdown 项目文档；不自动用于一般文章、设计稿或 API 规格 |
| 输入 | 目标项目目录、当前文档、用户意图，以及可读取的项目证据 |
| 输出 | 按模式生成或修改文档，或输出只读审查结果；内容模式默认中文与英文两份，用户指定语言时从其要求 |
| 依赖 | 支持读取 Skill 的 Agent；辅助脚本需要 Python 3.11+，只使用标准库 |
| 验证方式 | 运行自检、目标 README 检查，并逐条复核关键主张；命令见下文 |
| 当前状态 | `experimental`：脚本可单独检查，模型写作质量需按实际任务验证 |
| 版本 | `0.1.0` |

## 使用

入口为 [SKILL.md](SKILL.md)。把整个 `readme-writer/` 目录交给支持 Skill 的宿主，并按宿主的方式明确调用。`references/` 和 `scripts/` 都是该资产的一部分，不能只复制入口文件。

| 模式 | 行为 |
| --- | --- |
| New | 根据项目证据新写或完整重写 README |
| Update | 复核现有主张后原位更新 |
| Trim | 将长参考内容下沉，保留摘要和链接 |
| Audit | 只读检查并报告，不改文件 |
| Format | 保持内容与语言，仅整理选中文档的格式 |

完整写入、备份和预览约定以 `SKILL.md` 为准。辅助脚本路径应从该 Skill 所在目录解析，不能假定目标项目里也有同一目录。

## 验证

从 Agent Toolkit 仓库根目录运行：

```sh
python -B -X utf8 skills/readme-writer/scripts/selftest.py
python -B -X utf8 skills/readme-writer/scripts/check_readme.py README.md
```

处理其他项目时，把检查命令最后的 `README.md` 换成目标文档路径。扫描器和检查器的参数以各自 `--help` 为准。

自检使用临时夹具，不会验证某次生成文档的事实，也不代表所有宿主都能发现或执行 Skill。

## 来源与安装副本

来源说明保留在 `SKILL.md` 末尾；上游许可证见[第三方声明](../../THIRD_PARTY_NOTICES.md)。本目录用于维护分享源，复制它不会修改已有安装目录、全局发现入口或同步其他副本。
