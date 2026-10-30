# Changelog

本文件记录主页面 kit 的可观察变更。格式参考 Keep a Changelog，
版本号遵循语义化版本（kit 版本见 `accounts.py` 的 `KIT_VERSION`）。

## [2.0.0] - 2026-10-29

架构重构与能力补齐。命令行参数只增不减；产物新增语言构成卡，其余 README 结构不变。

### Added

- **`kit/` 生成器包**：`textutil` → `icons` → `cards` → `readme` → `build` →
  `pack`/`preview`/`cli` 六层，`scripts/generate.py` 退化为兼容垫片，
  旧调用（`generate.hero_svg` 等）全部保留。
- **卡片插件注册表**（`kit/plugins.py` + `kit/cardset.py`）：新增卡片只需
  `@card(...)` 一行注册，`build.py` 不再认识具体卡片类型。
- **语言构成卡**（`langs-<lang>.svg`）：由 `data/works.json` 的语言字段聚合，
  不依赖 GitHub top-langs 卡片，GitCode / Gitee 账号同样有语言图。
- **`kit/net.py`**：连接复用、ETag 条件请求缓存、指数退避重试、按主机限流；
  有 httpx 时自动升级 HTTP/2，没有则用 `http.client` 长连接池。
- **`kit/schema.py`**：accounts / stats / works / writing 四类声明式校验，
  错误信息带字段路径；装了 jsonschema 时再做一遍结构校验。
- **`kit/pngopt.py`**：PNG 无损重压缩（剥离元数据 + zlib level 9，实测 -7%）；
  装了 Pillow 时多一条候选路径。
- **`kit/mdrender.py`**：预览页 Markdown 双引擎，有 markdown-it-py 时用
  CommonMark 完整实现，没有则用内置子集解析器。
- **增量构建**：`--skip-if-unchanged` + `.build-manifest.json` 输入指纹，
  输入未变时零写盘（实测 55× 加速）。
- **原子写入**：所有产物经临时文件 + `os.replace`，中断不再留下半截 SVG。
- **`scripts/bench.py`**：可重复的性能基准（串行/并行/增量/资产体积）。
- **`ARCHITECTURE.md`**：分层说明、数据流、与 6 个同类项目的差距矩阵，
  以及「本项目不是什么」的排除式定位（明确不把 local-first / 高性能 / 模块化这类
  无差异标签当卖点）。
- **`tests/test_infra.py`**：HTTP 重试/ETag、增量指纹、PNG 优化、插件注册表，共 8 个用例。
- **`requirements-optional.txt`**：可选加速依赖清单。

### Changed

- 账号生成默认走线程池（`--jobs 0` 自动），串行与并行输出字节一致。
- `discover_works.py` 归一化结果新增 `language` 字段。
- `refresh.py` 改用 `kit.net`，账号刷新并发执行，末尾输出 HTTP 统计。
- `Makefile` 新增 `bench` / `gen-if-changed`，`clean` 覆盖更多构建产物。

### Performance

| 指标 | 之前 | 之后 |
|---|---|---|
| 全量生成（5 账号） | 0.26s | 0.09–0.10s（并行 0.088s） |
| 单账号生成 | 0.044s | 0.020s |
| 增量构建（输入未变） | 全量重写 | 0.0007s（55×） |
| hero.png | 997 KB | 922–926 KB |
| 单元测试 | 20 | 28 |
| 离线断言 | 793 | 821 |

## [Unreleased]

### Fixed

- **镜像账号资产串号**：GitCode / Gitee 页面曾直接沿用 GitHub 账号的
  `assets/hero.svg`、`assets/png/hero.png`、`assets/skills-*.svg`、官方卡片与
  贡献图，导致 `gitcode.com/badhope` 首页写着 `github.com/badhope`、技能栈也
  是另一个账号的。现在生成器按 `profile.json` 的账号重建全部资产，镜像脚本
  只同步账号无关的共享层，并清理目标仓库里其他账号的卡片/贡献图种子。
- **死链清零**：`accounts.py` 的 78 个仓库链接中有 14 个 404（`lingxi`、
  `awesome-ai-devkit`、`lens`、`KeBaiPay`、`p2wlan`、`novel-engine`、
  `API-Market`、`ExamPrediction` 等），已按三平台 API 实查结果重写作品目录；
  重命名过的仓库（`xiaoman`→`moneyhelper`、`mashang-python`→`mashang`、
  `scholarhub`→`rubbish`、`content-harbor`→`harbour`、`GlobalEcom-AI`→`Flow`）
  全部换到真实地址。
- **统计口径**：README 的 `alt` 文本沿用旧快照（26 repos / 11 stars），与
  `stats.json` 和统计卡不一致；现在由同一次渲染统一生成，并刷新到实查值。
- `refresh_sections.py` 删除 `return True` 之后的死代码 `return False`。
- `discover_works.py` 只比较仓库名，star/描述/更新时间变化不落盘；改为整块比对。
- `render_cards.mjs` 用全局计数判断账号失败，前一个账号成功会掩盖后一个账号
  全失败；改为按账号计数。凭据解析不再借用其他账号的 token。
- `mirror-shared.sh` 在目标仓库内按 `profile.json` 重建 README 与资产，
  不再把源仓库的 `assets/`、`data/cards/`、`data/contrib/` 整体覆盖过去。
- `generate.py --pack` 在缺少 `workflows/`、`package.json`、`tests/` 的检出里
  直接 `FileNotFoundError`；改为逐项检查并告警跳过。
- `generate.py --preview` 依赖不存在的 `brand.py` / `preview.py`；补内置降级
  模板，任意 checkout 都能出预览；`--out` 的 dist 位置改为与 preview 同级。
- README 引用的贡献图在缺少种子时会产生裂图；改为仅在种子存在时渲染该段。
- 生成器原引用“当前月份”选格言，导致每月 1 号无数据变化也产生 diff；改用
  `stats.json` 的月份，保证同一输入字节级可复现。

### Added

- `scripts/verify.py`：离线自检（目录完整性、资产引用、账号串号、幂等、数据一致性），
  可选 `--online` 校验全部仓库链接。
- `scripts/rasterize.py`：用本机 Chromium 系浏览器把 hero SVG 栅格化为
  2x PNG，零额外依赖；浏览器缺失时优雅退出。
- `tests/test_generate.py`：20 个 stdlib unittest 用例。
- `Makefile`：`verify / test / gen / preview / pack / links / clean`。
- `.gitcode/workflows/verify.yml`：GitCode Actions 上的测试 + 离线自检 +
  “生成物可复现”门禁。
- `DEVELOPMENT.md`、`LICENSE`、`CHANGELOG.md`。

### Changed

- `generate.py` 新增 `--assets-only`（配合 `--here` 只重建资产、保留 README），
  供镜像作业使用。
- “精选作品”表格限制为最近 6 个仓库，避免 18 行表格淹没页面。

## [1.0.0]

- 初始公开版本：五账号共用一套模板，生成 README.md / README.zh-CN.md /
  README.ja.md 与 SVG 资产，数字来自 `data/stats.json`。
