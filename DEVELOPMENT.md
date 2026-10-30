# Development

`badhope/badhope` 是「主页面 kit」在 GitCode 的部署实例：`accounts.py` 是唯一数据源，
`scripts/generate.py` 渲染 README 与 SVG，`data/*.json` 是定时刷新得到的数据快照。

## 环境

- Python 3.10+（仅标准库，无第三方依赖）
- Node.js 18+（仅 `scripts/render_cards.mjs` 需要，可选）
- 任意 Chromium 系浏览器（仅 `scripts/rasterize.py` 生成 hero PNG 时需要，可选）

## 常用命令

```bash
make verify         # 离线自检：schema/资产引用/账号串号/幂等/统计一致性
make test           # 单元测试（stdlib unittest，28 个用例）
make gen            # 按 profile.json 原地重建 README 与 assets
make gen-if-changed # 增量：输入未变则不写任何文件（约快 50 倍）
make preview        # 生成 dist/ 与 preview/index.html
make pack ACCOUNT=gitcode_badhope
make bench          # 性能基准
make links          # 在线校验 accounts.py 中全部链接（需要网络）
```

无 `make` 时直接调用：

```bash
python scripts/verify.py [--online]
python -m unittest discover -s tests -v
python scripts/generate.py --here [--skip-if-unchanged] [--jobs N]
python scripts/generate.py --preview
python scripts/generate.py --pack <account>
python scripts/rasterize.py --account <account>
python scripts/bench.py
python -m kit all --out dist          # 新的包级 CLI
```

## 可选依赖

核心只需要 Python 3.10+。装了以下任一依赖会自动启用增强路径，没装自动降级：

```bash
python -m pip install -r requirements-optional.txt
```

| 依赖 | 启用后 | 未装时 |
|---|---|---|
| `httpx` | HTTP/2 + 连接池 | `http.client` 长连接池（功能等价） |
| `markdown-it-py` | 完整 CommonMark 渲染预览页 | 内置子集解析器 |
| `jsonschema` | stats/works/writing 第二遍结构校验 | 内置 schema 校验器 |
| `pillow` | PNG 优化多一条候选路径 | zlib level 9 无损重压缩 |

## 目录

| 路径 | 作用 |
|---|---|
| `kit/` | 生成器包：`textutil` → `icons` → `cards` → `readme` → `build` → `pack`/`preview`/`cli`；`plugins`+`cardset` 卡片注册表；`net`/`schema`/`pngopt`/`mdrender` 横切能力 |
| `ARCHITECTURE.md` | 分层、数据流、与 6 个同类项目的差距矩阵、性能数据 |
| `accounts.py` | 账号、文案、作品目录（唯一数据源） |
| `scripts/generate.py` | 兼容入口（转发到 `kit`）；`--here` 原地重建，`--pack` 打部署包 |
| `scripts/bench.py` | 性能基准：串行 vs 并行、增量短路、资产体积 |
| `scripts/refresh.py` | 唯一联网组件：刷新 star / repo / follower / 上游合并数 |
| `scripts/refresh_sections.py` | 分区刷新编排，无变化不写盘 |
| `scripts/discover_works.py` | 从三平台 API 发现真实仓库，写入 `data/works.json` |
| `scripts/verify.py` | 离线自检 + 可选在线链接校验 |
| `scripts/rasterize.py` | hero SVG → 2x PNG（README `<picture>` 兜底） |
| `scripts/render_cards.mjs` | 官方 github-readme-stats 卡片种子（仅 GitHub 账号） |
| `scripts/mirror-shared.sh` | 把账号无关共享层同步到 GitCode / Gitee 镜像仓库 |
| `tests/` | 离线单元测试 |
| `data/` | 数据快照：`stats.json` / `works.json` / `writing.json` / `icons/` |

## 数据流

```
平台 API ──refresh.py / discover_works.py──> data/*.json
                                              │
                    accounts.py（文案）────────┴──generate.py──> README + assets
                                                              │
                                              scripts/verify.py（门禁）
```

## 发布与镜像

1. GitHub 侧由 Actions 定时跑刷新 + 卡片渲染，生成物提交回仓库。
2. `scripts/mirror-shared.sh <gitcode|gitee>` 只同步账号无关的共享层，
   然后在目标仓库内执行 `generate.py --here` 按目标 `profile.json` 重建页面，
   避免把 GitHub 账号的 hero / 技能卡 / 贡献图带到镜像站点。
3. 提交前至少跑 `make verify && make test`；CI 里 `.gitcode/workflows/verify.yml`
   还会校验“生成物与提交内容一致”。

## 新增一个账号

1. 在 `accounts.py` 的 `ACCOUNTS` 加条目（`platform` / `handle` / 文案 / `works`）。
2. 在 `ACCOUNT_ORDER` 里追加 key。
3. `python scripts/generate.py --pack <key>` 生成部署树，推到对应仓库。
4. `make verify` 确认资产引用与账号串号检查通过。

## 坑

- `data/works.json` 的仓库描述是外部输入，渲染前会中和 `|`、`[`、`]`。
- 官方卡片只对 GitHub 账号有意义；GitCode / Gitee 账号不要放 `data/cards/<key>`。
- 贡献图依赖 `data/contrib/<key>/snake*.svg`，缺失时该段整体不渲染。
- 生成器不联网；任何数字都必须先进 `data/*.json`。
