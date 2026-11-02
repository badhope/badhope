# Changelog

本文件记录 profile-kit 的可观察变更。格式遵循
[Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

版本号的**唯一真源**是 `kit/version.py` 的 `VERSION`；
`kit/__init__.py`、`accounts.py`、打包产物的 `profile.json` 都从它派生。
发版前跑 `python scripts/release.py --check` 校验本节与版本号一致。

## [Unreleased]

## [3.0.0] - 2026-11-02

以「渲染期完全离线」为分界的主版本。产物从此只取决于仓库内容，
同一提交在任何机器、任何时间重建都得到逐字节相同的输出。

### Changed（破坏性）

- **渲染期彻底离线**。`snake` 与 `wakatime` 卡片此前在渲染时实时联网抓取，
  导致同一输入两次构建产出不同字节，违背「产物是构建物」的定位。
  现改为只读 `data/extras.json` 构建期快照；快照缺失即整卡不渲染，
  README 自动降级，不再产生 `card failed:` 占位。
- **版本号单一真源**。新增 `kit/version.py`；`accounts.py` 的 `KIT_VERSION`
  与 `kit.__version__` 均从它导入，不再各自硬编码。
- 模板预设 `compact` / `minimal` / `portfolio` 的区块编排改为先收集再重排，
  未知区块的内容与其标题保持相邻，不会在重排中散落或重复。

### Added

- `kit/extras.py`：Gist、等距日历、编码习惯、关注者、项目五类可选卡片。
  全部读快照，无数据时不生成空卡。
- `kit/templates.py`：四套 README 区块编排预设（classic / compact / minimal / portfolio），
  按账号配置 `template` 字段选择，未知值回退 `classic`。
- `kit/fontmetrics.py`：Verdana 11px 字宽查表 + CJK 回退，替代固定 0.6em 估算。
- `scripts/refresh_extras.py`：GraphQL 采集贡献日历（366 天）与公开项目，
  逐 section fail-soft，失败保留旧值；凭据缺失时跳过而非报错。
- `scripts/release.py`：发版前校验版本号、CHANGELOG 条目与 git 工作树状态。
- 扩展卡片支持按账号覆盖标题（`card_titles`）与 README 区块标题（`section_titles`）。
- `tests/test_snake_offline.py`：断言渲染不触网、结果确定、快照缺失时卡片不启用。
- 新增 10 个测试文件覆盖扩展卡、模板、字宽、Rank 输入、栅格化目标、秘密成就等。

### Fixed

- `kit/net.py`：`cache=False` 的请求不再写入条件请求缓存，避免私有响应落盘。
- `kit/wakatime.py`：自定义域名强制校验 scheme/hostname，拒绝带凭据或查询串的 URL。
- `scripts/rasterize.py`：`discover_targets` 支持指定构建根目录，跨账号栅格化不再串号。
- `scripts/refresh_extras.py`：GPG 与 starred-topics 探测改为三态判断，
  无法确认时抛错保留旧值，不再把「页面没匹配到」当成「确实没有」。

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
  以及「本项目不是什么」的排除式定位。
- **`tests/test_infra.py`**：HTTP 重试/ETag、增量指纹、PNG 优化、插件注册表。
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

## [1.0.0]

- 初始公开版本：五账号共用一套模板，生成 README.md / README.zh-CN.md /
  README.ja.md 与 SVG 资产，数字来自 `data/stats.json`。
