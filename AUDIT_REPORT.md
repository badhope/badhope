# 工程审计报告 · badhope/badhope

- 审计对象：GitCode `badhope/badhope`（`main`，审计时 HEAD `62dcbca`）
- 审计时间：2026-10-28
- 审计范围：仓库管理规范、文档、版本与提交、依赖与构建、测试与 CI、代码质量、安全、数据准确性
- 结论：**工程骨架清晰（纯 stdlib 生成器 + 单一数据源 + 数据/渲染分离），但缺少最基本的工程护栏：没有测试、没有 CI、没有 LICENSE、没有构建入口；并且镜像仓库的资产串号导致线上页面展示的是另一个账号的 hero 与技能栈，作品区有 14 个失效链接。** 本次已修复全部可修复项并补上门禁。

## 1. 审计方法与证据

| 手段 | 结果 |
|---|---|
| `git clone` + 全量阅读 116 个文件 / 3.7k 行脚本 | 完成 |
| `python -m py_compile` 全部 Python | 通过 |
| XML 解析 100 个 SVG | 全部合法 |
| 三平台 API 实查仓库清单（GitHub / GitCode / Gitee） | 完成 |
| 78 个仓库链接 HTTP 实测 | 14 个 404 |
| `generate.py --here` 在副本运行并 diff | 发现资产串号 |
| `generate.py --preview` / `--pack` | 均失败（见 P1-1、P1-2） |
| 浏览器渲染预览页 | 通过（修复后） |

## 2. 仓库管理评估（修复前）

| 维度 | 状态 | 说明 |
|---|---|---|
| 目录结构 | 良 | `accounts.py` 单一数据源；`scripts/` 按职责拆分；`data/` 与 `assets/` 分离 |
| 文档 | 差 | 仅有对外展示的 README（3 语言），无 DEVELOPMENT / CHANGELOG / LICENSE |
| 版本管理 | 差 | 无 tag、无 `KIT_VERSION` 使用点、无 CHANGELOG；116 次提交里 87 次是 `chore: sync` |
| 构建入口 | 差 | 没有 Makefile / task runner；关键命令只散落在 docstring |
| 测试 | 无 | 0 个测试文件 |
| CI | 无 | 仓库内没有任何 workflow（GitCode 侧）；生成物靠人工提交 |
| 依赖管理 | 良 | 生成器零依赖；node 依赖仅在 kit 源仓库（本镜像未携带） |
| 代码质量 | 中 | 无类型标注但结构清楚；存在死代码、全局计数误判、死链等问题 |
| 安全 | 中 | 无硬编码密钥；但镜像脚本把 `TOKEN` 拼进 remote URL 且无任何脱敏说明 |
| 数据准确性 | 差 | 首页数字与 `stats.json` 不一致；作品表 14 条死链 |

## 3. 问题清单与修复

### P0（线上可见错误，已修复）

| ID | 问题 | 证据 | 修复 |
|---|---|---|---|
| P0-1 | **镜像页面展示 GitHub 账号资产**：`gitcode.com/badhope` 的 hero 写着 `github.com/badhope`，hero PNG 也是 GitHub 版；技能卡是 gh_badhope 的 JS/React 栈而不是 GitCode 账号的 Python/Dart/Kotlin 栈 | `assets/hero.svg` 内 `github.com/badhope`；`assets/skills-md.svg` 的 aria-label 与 `ACCOUNTS["gitcode_badhope"]["skills"]` 不一致 | 生成器按 `profile.json` 重建全部资产；删除 `data/cards/gh_badhope`、`data/contrib/gh_badhope`、`assets/cards/*`、`assets/github-contribution-grid-snake*.svg`；镜像脚本改为只同步账号无关层并在目标仓库内重建 |
| P0-2 | **作品区 14 个死链**：整条 `WORKS` 条目（`lingxi`、`awesome-ai-devkit`、`lens`、`KeBaiPay`、`p2wlan`、`novel-engine`、`API-Market`、`ExamPrediction`）以及多条改名仓库旧地址返回 404 | `curl -I` / 平台 API 实测 | 重写 `WORKS` 为 18 个全部可访问的仓库；`xiaoman→moneyhelper`、`mashang-python→mashang`、`scholarhub→rubbish`、`content-harbor→harbour`、`GlobalEcom-AI→Flow`；Gitee 补全 |
| P0-3 | **统计数字自相矛盾**：README 的 alt 写 26 repos/11 stars，`stats.json` 是 25/12/0，`assets/stats-en.svg` 又是 25/239/22/15（GitHub 账号数据） | `README.md:57` vs `data/stats.json` vs `assets/stats-en.svg` | 统一由同一次渲染生成；跑 `refresh_sections.py` 刷新为实查值（26 repos / 12 stars / 0 followers） |
| P0-4 | **hero PNG 兜底是错的账号**，且生成器只在 `assets/png/<key>/hero.png` 存在时复制——镜像仓库里从来没有该文件 | `generate.py:943`（原） | 新增 `scripts/rasterize.py` 生成 `assets/png/gitcode_badhope/hero.png`；无 PNG 时 README 只引用 SVG，不再写指向不存在文件的 `<source>` |

### P1（功能不可用 / 维护陷阱，已修复）

| ID | 问题 | 证据 | 修复 |
|---|---|---|---|
| P1-1 | `generate.py --preview` 直接 `ModuleNotFoundError: No module named 'brand'`（`brand.py`、`preview.py` 不在仓库） | 运行输出 | 内置降级模板 `PREVIEW_FALLBACK`，仅在模块存在时走上游实现；`--out` 的 dist 改为与 preview 同级，相对路径可解析 |
| P1-2 | `generate.py --pack gh_badhope` 抛 `FileNotFoundError`（缺 `workflows/`、`package.json`、`.gitleaks.toml`） | 运行输出 | 可选文件逐项检查，缺失告警跳过；`--pack gitcode_badhope` 正常 |
| P1-3 | `refresh_sections.py:108` 有不可达的 `return False` | 静态检查 | 删除 |
| P1-4 | `discover_works.py` 只比较仓库名，star/描述/更新时间变了也不写盘，作品表长期停留在旧数字 | `discover_works.py:162`（原） | 改为整块 `old != repos` 比对 |
| P1-5 | `render_cards.mjs` 用全局 `rendered/skipped` 判断单账号失败，前面账号成功会掩盖后面账号全失败 | `render_cards.mjs:216`（原） | 改为按账号 `acctRendered/acctSkipped` 计数 |
| P1-6 | `render_cards.mjs` 在账号无 token 时借用 `default` 账号的 token，会渲染成别人的数据 | `render_cards.mjs:88-90`（原） | 删除跨账号回退 |
| P1-7 | 贡献图段在缺少 `data/contrib/<key>/snake*.svg` 时仍输出 `<img>`，产生裂图 | README 引用 vs 文件缺失 | 仅在种子存在时渲染该段；`contrib_graph` 对两个镜像账号关掉 |
| P1-8 | 格言按“系统当前月份”轮换，每月 1 号无数据变化也会产生 diff，破坏“同输入同输出” | `generate.py:712`（原） | 改用 `stats.json` 的 `as_of` 月份 |
| P1-9 | 仓库描述是外部输入，含 `|` 时截断 Markdown 表格（实测 `mashang` 描述含竖线） | `data/works.json` | 渲染前中和 `|`、`[`、`]` |
| P1-10 | GitCode/Gitee 的 `human_name` 形如 `badhope / no-money`，表格里又拼 owner，出现重复前缀 | `data/works.json` | `_norm()` 去掉 `owner/` 前缀 |

### P2（工程规范缺口，已补齐）

| ID | 问题 | 修复 |
|---|---|---|
| P2-1 | 无测试 | `tests/test_generate.py`：20 个用例覆盖渲染、资产引用、幂等、账号串号、写作合并、仓库归一化 |
| P2-2 | 无自检入口 | `scripts/verify.py`：792 条断言，含 `--online` 链接校验 |
| P2-3 | 无构建入口 | `Makefile`：`verify / test / gen / preview / pack / links / clean` |
| P2-4 | 无 CI | `.gitcode/workflows/verify.yml`：单测 + 离线自检 + “生成物可复现”门禁 + 手动链接检查 |
| P2-5 | 无 LICENSE / CHANGELOG / DEVELOPMENT | 已补（MIT + 第三方图标许可说明） |
| P2-8 | 镜像脚本没有可离线验证的集成测试 | 用本地裸仓库跑通 `mirror-shared.sh` 全流程（共享层同步 → 目标端重建 → 幂等），并加入 `MIRROR_BASE` 测试入口 |
| P2-6 | 无版本标记 | `KIT_VERSION` 保留并在 `profile.json` 中随包携带；CHANGELOG 从 1.0.0 起记 |
| P2-7 | `refresh.py` 在 `HOME` 不可判定时于 import 阶段崩溃 | 加 `_default_secrets_path()` 兜底 |

### P3（记录不修）

| ID | 问题 | 原因 |
|---|---|---|
| P3-1 | 116 次提交中 87 次是 `chore: sync shared layer`，历史噪声大 | 重写历史会影响已部署仓库与镜像，收益低 |
| P3-2 | `accounts.py` 无类型标注、947 行 | 纯数据文件，拆分会增加维护成本 |
| P3-3 | 无 tag | 建议随 CHANGELOG 打 `v1.1.0`，需仓库管理员在平台操作 |
| P3-4 | `deploy_state` / `deploy_protected` / `repo_path` 三个字段未被任何代码读取 | 可能是外部部署脚本使用，保留 |
| P3-5 | 未合并分支 `origin/261007-fix-gitcode-platform-form` 把仓库改成了另一套无生成器的静态页面 | 属于产品方向选择，需作者决定，不在本次修复范围 |

## 4. 修复后验证

```
python -m unittest discover -s tests        -> 20 tests OK
python scripts/verify.py                    -> 792 assertions, 0 failed
python scripts/generate.py --here           -> 幂等（二次运行 diff 为空）
python scripts/generate.py --preview        -> preview/index.html，80 个资产引用全部存在
python scripts/generate.py --pack gitcode_badhope  -> 成功
python scripts/generate.py --pack gh_badhope       -> 成功（缺省文件告警跳过）
python scripts/verify.py --online           -> 869 assertions, 0 failed
                                                （GitHub 侧 403/URLError 为限流，仅告警；
                                                  15 分钟内实查 404 的真实死链已全部修复）
node --check scripts/render_cards.mjs       -> OK
bash -n scripts/mirror-shared.sh            -> OK
Edge headless 渲染 preview                   -> 版式正常
```

推送后远端复核（GitCode API + 页面实测）：

| 检查项 | 结果 |
|---|---|
| `main` HEAD | `4f3f9c3`（与本地一致） |
| 远端 `assets/hero.svg` | `aria-label="badhope — gitcode.com/badhope"`，`github.com/badhope` 出现 0 次 |
| 远端 `assets/skills-md.svg` | `python, dart, kotlin, java, flutter, wechat, linux, git, markdown`（GitCode 账号技能） |
| 远端 README alt | `26 public repos · 12 stars · 0 followers` |
| 远端 `data/cards`、`assets/cards`、贡献图 | 已删除（404） |
| 远端 `scripts/rasterize.py`、`tests/`、`Makefile`、`LICENSE`、`.gitcode/workflows/verify.yml` | 已存在（200） |

## 5. 仍存在的风险

1. **修复需要同步回 GitHub 源仓库（最高优先级）**：本仓库是 `github.com/badhope/badhope`
   的镜像落点，`scripts/mirror-shared.sh` 会从 GitHub 覆盖 `accounts.py`、`data/`、
   `scripts/`。本次修复若只留在 GitCode 侧，下一次镜像同步会把死链、资产串号、
   统计不一致全部带回来。必须把本仓库的 `accounts.py`、`scripts/`、`tests/`、
   `Makefile` 等同步到 GitHub 源仓库（本机无 GitHub 凭据，未执行）。
2. **GitHub token 缺失**：本机无 GitHub 凭据，`gh_x33834` / `gh_morningstar` /
   `gh_badhope` 的 stars/followers 沿用旧值（GitHub 公开 API 限流 60 次/小时，未认证时不可靠）。
   建议在 Actions 里配置 `GITHUB_TOKEN` 或本机凭据库。
3. **官方卡片不会自动更新**：`render_cards.mjs` 需要
   `@stats-organization/github-readme-stats-core` 与 token，本仓库未携带
   `package.json`；卡片保持上一次快照，属既有设计。
4. **GitCode Actions 未实跑**：`.gitcode/workflows/verify.yml` 按官方文档的
   `name/on/jobs/runs-on/steps` 结构编写，本地只能做语法级检查；首次推送后需在
   平台确认一次运行结果。
