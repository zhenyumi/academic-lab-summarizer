# Academic Lab Summarizer Agent Skills 学术实验室总结技能包

一套面向 AI 编程代理的 evidence-first 技能，用于从实验室官网、近年论文和招聘信号中总结单个学术实验室。

[English version](README.md)

## 项目目标

`academic-lab-summarizer` 为 AI 代理提供一套结构化方法，用来生成可追溯的实验室画像。工作流重点关注三类不能靠猜的信息：实验室研究什么、近几年发表了什么、是否存在开放或可能开放的招聘机会。

每个输出都遵循“展示证据链”的原则。实验室结论要指向来源证据，论文匹配要保留来源和置信度层级，招聘信号必须区分 confirmed、likely、generic、closed/past、none 或 unknown。

目标用户包括希望在联系、申请或比较实验室前进行系统了解的学生、研究人员和科研岗位求职者。

## 环境要求

- **Python 3.9+**。随包脚本只使用 Python 标准库。
- 以下 AI 编程代理之一：
  - [Claude Code](https://claude.ai)
  - [Codex CLI](https://github.com/openai/codex)
  - [OpenCode](https://opencode.ai)
  - [OpenClaw](https://clawhub.ai)

## 安装

### Claude Code

```bash
git clone https://github.com/zhenyumi/academic-lab-summarizer.git
cd academic-lab-summarizer
./install-claude.sh                              # 全局安装所有技能
./install-claude.sh --project /path/to/project   # 或安装到指定项目
./install-claude.sh --categories "lab-site-evidence-extraction,lab-publication-profile"  # 只安装指定技能
./install-claude.sh --update                     # 只更新发生变化的技能
./install-claude.sh --list                       # 查看可用技能
./install-claude.sh --validate                   # 检查技能包结构
./install-claude.sh --verbose --dry-run          # 详细预览安装内容
./install-claude.sh --uninstall                  # 卸载已安装技能
```

### Codex CLI

```bash
git clone https://github.com/zhenyumi/academic-lab-summarizer.git
cd academic-lab-summarizer
./install-codex.sh                               # 全局安装所有技能
./install-codex.sh --project /path/to/project    # 或安装到指定项目
./install-codex.sh --categories "academic-lab-summarizer,lab-profile-synthesis"  # 只安装指定技能
./install-codex.sh --update                      # 只更新发生变化的技能
./install-codex.sh --list                        # 查看可用技能
./install-codex.sh --validate                    # 检查技能包结构
./install-codex.sh --verbose --dry-run           # 详细预览安装内容
./install-codex.sh --uninstall                   # 卸载已安装技能
```

### OpenCode

```bash
git clone https://github.com/zhenyumi/academic-lab-summarizer.git
cd academic-lab-summarizer
./install-opencode.sh                            # 全局安装所有技能
./install-opencode.sh --project /path/to/project # 或安装到指定项目
./install-opencode.sh --categories "academic-lab-summarizer"  # 只安装指定技能
./install-opencode.sh --update                   # 只更新发生变化的技能
./install-opencode.sh --list                     # 查看可用技能
./install-opencode.sh --validate                 # 检查技能包结构
./install-opencode.sh --verbose --dry-run        # 详细预览安装内容
./install-opencode.sh --uninstall                # 卸载已安装技能
```

### OpenClaw

```bash
git clone https://github.com/zhenyumi/academic-lab-summarizer.git
cd academic-lab-summarizer
./install-openclaw.sh                            # 全局安装所有技能
./install-openclaw.sh --project /path/to/project # 或安装到指定项目
./install-openclaw.sh --update                   # 只更新发生变化的技能
./install-openclaw.sh --list                     # 查看可用技能
./install-openclaw.sh --validate                 # 检查技能包结构
./install-openclaw.sh --verbose --dry-run        # 详细预览安装内容
./install-openclaw.sh --uninstall                # 卸载已安装技能
```

通用选项：`--categories` 用于只安装指定技能，`--update` 用于刷新已变化的技能，`--dry-run` 用于预览安装内容，`--verbose` 用于显示详细信息，`--force` 用于覆盖已安装的技能内容。

> **平台支持：** 安装脚本是 Bash 脚本，可在 macOS、Linux 和 Windows（通过 Git Bash、WSL 或其他兼容 Bash 的 shell）上运行。不要使用 `sh`、`zsh`、原生 PowerShell 或 CMD 运行它们。

## 报告与文件

工作流会在两个主要位置写入运行产物和报告：

```text
lab_summaries/<lab_id>/
  lab_summary_input.json
  lab_site_evidence.jsonl
  publication_search_plan.json
  publication_candidates.jsonl
  publications.curated.json
  publication_evidence.jsonl
  publication_audit.json
  research_theme_profile.json
  position_signals.json
  lab_summary_assessment.json
  lab_profile.json
  report.md
  lab_summary_audit.json
  lab_summary_manifest.json

reports/lab-summaries/<task_id>/
  report.html
  report.md
  report_manifest.json
  assets/
  artifacts/
```

`report.html` 是默认面向用户打开的交互式报告，支持导航、可点击证据引用和可折叠章节。`report.md` 是对应的 Markdown 版本。JSON 和 JSONL 产物会与报告一起保留，方便代理审计证据、重跑单个步骤，或解释某个结论是如何得出的。

## 技能分类

### 实验室证据

从一个已知实验室网站提取结构化来源材料。

| 技能 | 功能 |
|------|------|
| `lab-site-evidence-extraction` | 阅读实验室网站，提取实验室身份、PI 与机构、研究方向、成员、方法、经费或资源指标、论文引用、招聘或开放岗位语言等证据。 |

### 论文画像

论文分析是 v1 的核心合同，不是未来增强项。

| 技能 | 功能 |
|------|------|
| `lab-publication-profile` | 构建近年论文画像，包括分层搜索策略、来源 provenance、匹配层级、人工/规则策展状态、证据记录、审计输出和研究主题综合。实验室官网论文页首先搜索（Tier 0，零 API 成本）；然后搜索 OpenAlex 与 Semantic Scholar（Tier 1）；当实验室属于生物医学、临床、生命科学或神经科学相关领域时，PubMed 也是必须来源；Crossref 和预印本服务器作为补充或 fallback（Tier 2）。API 调用采用指数退避限速策略。 |

ambiguous 和 rejected 论文不得进入研究主题和实验室研究总结。confirmed 与 likely 论文可以生成结构化概览，包括研究问题、方法、关键发现和意义。

### 实验室综合

把官网证据和论文证据汇总为实验室画像。

| 技能 | 功能 |
|------|------|
| `lab-profile-synthesis` | 综合实验室身份、研究总结、近年论文主题、重要近期论文、开放岗位/招聘信号、方法、经费或资源指标、局限性、审计文件和面向用户的报告。 |

招聘分析是必填项。即使没有发现开放岗位，也必须输出 `position_signals.json`。支持的岗位类别包括 `phd`、`masters`、`undergraduate`、`postdoc`、`research_assistant`、`technician`、`lab_manager`、`staff_scientist`、`other` 和 `none`。泛泛的 “join us” 语言可以记录，但不能在没有角色级证据的情况下升级为 confirmed opening。

### 工作流

运行完整实验室总结流水线。

| 技能 | 功能 |
|------|------|
| `academic-lab-summarizer` | 协调实验室官网证据提取、论文画像和实验室综合。它负责追踪必需产物、验证步骤交接，并写出最终 manifest。 |

## 使用示例

安装完成后，可以直接与代理自然对话：

推荐的直接工作流调用方式：

```text
/academic-lab-summarizer <lab-homepage-or-profile-url>
```

也可以单独调用 worker：

```text
/lab-site-evidence-extraction <lab-homepage-url>
/lab-publication-profile <lab-name-or-pi-name>
/lab-profile-synthesis <lab-summary-artifact-directory>
```

示例：

```text
"对 <lab-url> 运行完整实验室总结。包括近年论文和招聘信号。"
"使用 OpenAlex、Semantic Scholar，并在相关领域使用 PubMed，总结这个实验室近几年的论文。"
"检查这个实验室是否有 PhD、postdoc、RA 或其他科研岗位的 confirmed openings。"
"为 <PI name> 的实验室生成带证据链的画像，并把局限性和已确认事实分开。"
"从这个实验室总结产物目录生成最终 HTML 和 Markdown 报告。"
```

## 报告功能

HTML 报告包含：

- **固定导航栏**，随滚动位置高亮当前章节
- **可点击证据引用**（`[site:N]`、`[pub:N]`），自动展开证据面板并滚动到目标条目，带高亮动画
- **出版物卡片**，带编号、作者显示（第一作者 + 最后作者，PI 姓名高亮）和结构化概览字段（研究问题、关键发现、方法、意义）
- **可折叠完整出版物列表**，来源于策展确认/可能的出版物
- **三档字体切换**（A⁻/A/A⁺），设置保存在 localStorage
- **返回按钮**，从证据引用跳转后可返回原位置
- **打印优化布局**和 `prefers-reduced-motion` 支持

## 幕后机制

每个技能都包含 runner scripts、templates、references 和 example artifacts。代理可以把模板复制到运行目录中的 tools 目录，再针对真实网站或 API 调用调整这些副本。随包代码优先保持标准库实现，便于检查、迁移和在受限环境中运行。

工作流刻意保持保守：它区分 confirmed、likely 与 ambiguous 证据，保留论文来源链，并记录招聘信号，但不会把弱招聘语言夸大成明确开放岗位。

## 验证

```bash
python lab-site-evidence-extraction/scripts/validate_lab_site_artifacts.py --examples
python lab-publication-profile/scripts/validate_publication_profile_artifacts.py --examples
python lab-profile-synthesis/scripts/validate_lab_summary_artifacts.py --examples
python academic-lab-summarizer/scripts/validate_lab_summary_manifest.py --examples
python academic-lab-summarizer/scripts/smoke_report_outputs.py
python academic-lab-summarizer/scripts/check_migration_policy.py
```

## 许可证

MIT License。详见 [LICENSE](LICENSE)。
