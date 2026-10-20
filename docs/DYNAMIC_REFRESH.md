# 动态刷新说明（Dynamic Refresh）

主页由**多个可视化分区**构成，每个分区都能**按自己的数据源动态刷新**，而不是把内容冻结成不变的图片。
刷新全部由平台 Actions 驱动，节奏克制、变更才提交，避免刷爆配额。

---

## 1. 哪些分区会动态更新

| 分区 | 数据来源 | 刷新方式 | 节奏 |
|---|---|---|---|
| Numbers（仓库数 / 关注者 / Star 总数） | GitHub / Gitee / GitCode 公开 API | **实时 shields 徽章**（浏览时拉取，零配额）+ 提交版 SVG 卡片 | 徽章实时；卡片随刷新更新 |
| Pinned work（置顶仓库卡） | GitHub API（按 `accounts.py` 的 works 选仓库） | 提交版 SVG（render_cards.mjs） | 每周 |
| Top languages（语言卡） | GitHub API | 提交版 SVG | 每周 |
| GitHub stats 卡 | GitHub API | 提交版 SVG | 每周 |
| Contribution graph（贡献蛇图） | GitHub 贡献数据 | 官方 `Platane/snk` 动作 | 每日 |
| Writing（文章列表） | CSDN RSS + `accounts.py` 手工维护 | `refresh_sections.py` 合并 | 每日 |
| About / Now / Open source / Elsewhere | `accounts.py` 文案 | 改文案即改，不参与自动刷新 | 手动 |

> 文字只作简短引导，视觉优先——英雄图、技能条、作品卡、统计卡、贡献蛇图均为 SVG 资产。

---

## 2. 整体节奏（不频繁、省配额）

- **每日 17:23 UTC**：`refresh` 作业拉取最新统计/文章（fail-soft，单账号失败保留旧值），离线重建 README，重绘贡献蛇图。
- **每周一 04:47 UTC**：`cards` 作业重渲染 stats/langs/pin 卡片（GitHub API 调用较多，故低频）。
- **变更闸门**：`git diff` 无变化即跳过提交。大多数日子是空跑，**几乎零配额消耗**——这正是「不要太频繁、别够余额」的实现。
- **GitCode / Gitee 镜像**：这两个平台没有原生定时器，由 `github/badhope` 仓库的 Action 在提交到 main 后，把成品推过去，保证「同一人、五处主页」一致。

---

## 3. 容错设计

- 每个账号独立刷新、独立 try/except：某个平台限流/失败，**只保留旧值，绝不整体崩溃、绝不清空已有数据**。
- 卡片渲染失败保留上一次成功产物（render_cards.mjs 对每次渲染结果做成功校验）。
- 贡献蛇图、README 重建均为离线/独立步骤，互不阻断。

---

## 4. 需要配置的 Secrets

在**每个 GitHub 仓库**的 `Settings → Secrets and variables → Actions → Repository secrets` 中：

| Secret | 作用 | 需要的地方 |
|---|---|---|
| `GITHUB_TOKEN` | 自动提供，无需手动建；用于 GitHub API 与推送本仓库 | 全部 GitHub 仓库（自动） |
| `GITCODE_TOKEN` | 镜像到 GitCode（Basic 鉴权，推送用 `oauth2:TOKEN@`） | 仅 `github/badhope` |
| `GITEE_TOKEN` | 镜像到 Gitee（推送用 `oauth2:TOKEN@`） | 仅 `github/badhope` |

> 脚本侧的读取规则：GitHub 读 `GH_<HANDLE>_TOKEN` → `GITHUB_TOKEN`/`GH_TOKEN`；
> Gitee 读 `GITEE_<HANDLE>_TOKEN` → `GITEE_TOKEN`；GitCode 读 `GITCODE_<HANDLE>_TOKEN` → `GITCODE_TOKEN`。
> 加平台前缀是因为 `badhope` 在三个平台同名，共用 `GH_<HANDLE>_TOKEN` 会让 Gitee/GitCode 拿到 GitHub 的令牌。

## 4.1 分支保护相关的必需工作流

`badhope/badhope` 的 `main` 启用了保护，要求 `Scan for secrets (gitleaks)` 检查通过。
因此 `.github/workflows/gitleaks.yml` 与 `.gitleaks.toml` **必须随包存在**，`pack()` 会一并复制。
删除它们会导致工作流提交与人工推送都被拒绝。

---

## 5. 分支保护说明

工作流以 `permissions: contents: write` **直接提交到 `main`**。

`badhope/badhope` 的 `main` 实际启用了保护并要求 gitleaks 检查，因此该仓库的自动提交会被拒绝，
需要改为走 PR 合并。其余四个仓库无保护，可直接提交。详见 `BRANCH_PROTECTION.md`。

---

## 6. 手动触发

在任何仓库的 `Actions → Refresh profile (dynamic) → Run workflow` 即可立即跑全部分区（数据 + 文章 + 蛇图 + 卡片）。
镜像仓库也可在 `Actions → Mirror to GitCode & Gitee` 手动全量同步一次。

---

## 7. 与「冻结卡片」方案的区别

早期版本曾尝试把实时徽章冻结为静态 SVG、把卡片栅格化为 PNG 并打不可变快照（lock）。
本方案**不采用**那种做法——卡片始终由 Action 周期重渲染、反映最新数据，做到你要求的「不要固定死卡片、每个部分都动态变化」。
旧的 `scripts/freeze_readme.py`、`scripts/snapshot_cards.mjs`、`scripts/lock.py` 已移至 `scripts/_deprecated/`，不再接入线上流程，仅作可选参考。
