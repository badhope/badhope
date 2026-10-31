# 架构与设计取舍

本文回答三个问题：这个项目到底是什么、为什么这样分层、每个模块为什么是自研而不是直接用现成库。

## 1. 项目定位

它不是「个人主页模板」，也不是「README 徽章服务」。它是一台**静态 profile 资产编译器**：

```
accounts.py（唯一数据源）  ─┐
data/*.json（实查快照）     ─┼─► kit（渲染/编排）─► README × 3 语言 + 17 个 SVG + 2 个 PNG
profile.json（部署账号）    ─┘                        ↓
                                              多平台镜像作业（GitCode / Gitee）
```

### 1.1 先说它不是什么

排除掉这些，剩下的才是它真正的差异：

- **不是「本地优先」**。这个词对标项目里五个有四个都在用（self-hosted / local-first /
  no telemetry），说了等于没说。判断标准应该是「服务挂了页面还在不在」，而不是
  「数据存哪」。
- **不是「高性能」**。0.09 秒生成 5 个账号，这个量级谈性能没有意义；真正的成本在
  CI 分钟数和提交噪音上。
- **不是「模块化」**。所有项目都这么说。有意义的问法是：加一张卡片要改几个文件、
  能不能被测试枚举出来。
- **不是「可定制主题」**。那是 `github-readme-stats` 的强项（20+ 内置主题 + 自定义
  参数），本项目只有一套「星夜极光」视觉，这是取舍不是缺陷。

### 1.2 三条可验证的硬差异

| 差异 | 对照项目的问题 | 本项目的做法 | 怎么验证 |
|---|---|---|---|
| **产物是构建物，不是服务响应** | `github-readme-stats` 公共实例被暂停过（issue #4737）；`github-profile-trophy` README 直接建议自托管以规避实例停服 | 页面上每个像素都是 git 里的字节，没有任何运行期进程、函数、第三方存活依赖 | 断网打开仓库，页面完整；`git log -- assets/` 就是全部历史 |
| **五落点共用一套数据源且互不污染** | 通用方案是「一个 URL 一个账号」，没有「同一身份多处部署」的概念；镜像通常整目录覆盖，导致 A 账号的 hero 出现在 B 账号页面 | `accounts.py` 描述五个账号，`profile.json` 声明当前仓库身份；镜像只同步账号无关层（`accounts.py`/`data/*.json`/`kit/`），资产在目标仓库按本账号重建 | `python scripts/verify.py` 里的账号串号断言；`scripts/mirror-shared.sh` 的本地裸仓库集成测试 |
| **构建结果字节级可复现，且有门禁** | 六个对标项目里只有 GRS 用 Jest 快照锁 SVG，没有一个校验「提交的产物是否等于重新生成的产物」 | 用 CRC32(账号) 做种子、用 `stats.json` 的月份选格言、不写时间戳；输入指纹写 `.build-manifest.json`；CI 跑 `generate --here` 后 `git diff` 必须为空 | `python scripts/generate.py --here` 连跑两次 diff 为空；`--skip-if-unchanged` 命中时零写盘 |

### 1.3 次要但真实的优势

- **零依赖可跑，增强全部可选**：核心只吃 Python 3.10+ 标准库，`httpx` /
  `markdown-it-py` / `jsonschema` / `Pillow` 装了才启用，没装自动降级且功能不减
  （`python scripts/doctor.py` 会列出当前走哪条路径）。这是「部署面最小」，不是
  「本地优先」。
- **数据准确性有硬门禁**：`kit/schema.py` 对 accounts + 三份快照做声明式校验；
  `verify.py --online` 只把 404/410 判死，403/限流仅告警——避免把限流误报成死链。
- **CI 成本低**：增量短路 55×（0.0007s vs 0.04s），且输入未变时一个字节都不写，
  mtime 稳定，不会产生「无意义提交」。
- **卡片是注册项，不是硬编码**：加一张卡 = 在 `cardset.py` 加一行 `@card(...)`，
  `build.py` / `verify.py` / `pack.py` 零改动，`verify.py` 会自动枚举校验。

## 2. 分层

| 层 | 模块 | 职责 | 依赖方向 |
|---|---|---|---|
| L0 纯函数 | `textutil` | 转义、裁剪、数字格式、确定性随机 | 无 |
| L1 资源 | `icons` | 图标解析 + 进程级缓存 | L0 |
| L2 渲染 | `cards` | hero / stats / skills / works / activity / langs / footer | L0, L1 |
| L2 渲染 | `readme` | 三语言 README 模板 | L0, L1, `cards` |
| L3 编排 | `plugins` + `cardset` | 卡片插件注册表（声明式） | L2 |
| L3 编排 | `build` | 写出、增量清单、并行、原地重建 | L2, L3 |
| L4 交付 | `pack` / `preview` | 部署包 / 本地预览页 | L3 |
| L4 交付 | `cli` / `__main__` | 命令行 | L4 |
| 横切 | `net` / `schema` / `pngopt` / `mdrender` | 网络 / 校验 / 图片 / Markdown | 无（可独立测试） |

`scripts/generate.py` 现在是**兼容垫片**：把 `kit` 的公开符号重新导出，
旧脚本、CI、镜像作业无需改动即可继续用 `generate.hero_svg(...)` 这类调用。

### 为什么用插件注册表

原实现里 `write_account_files()` 硬编码了「有哪些卡片」：加一张卡要改三处
（渲染调用、`wanted` 集合、README 引用）。现在卡片是一个注册项：

```python
@card("langs", "langs-{lang}.svg", priority=70,
      when=lambda acct, ctx: bool(ctx["discovered"]["accounts"][ctx["key"]]["repos"]))
def _langs(acct, key, lang, ctx):
    return cards.langs_svg(key, lang, ctx.get("discovered"))
```

`build.py` 只调 `render_all()` / `render_static()` / `filenames()`，
不知道任何具体卡片；`verify.py` 直接遍历 `describe()` 校验命名唯一性。
这是 lowlighter/metrics 的目录即插件模型的简化版（单文件注册，不引入
metadata.yml + 代码生成的复杂度）。

## 3. 六个对标项目与差距矩阵

深度调研结论（源码级，非 README 摘要）：

| 项目 | 运行模型 | 缓存策略 | 渲染 | 对本项目的可迁移经验 |
|---|---|---|---|---|
| **anuraghazra/github-readme-stats** | Vercel serverless | 按卡片分级 TTL（stats 1d / langs 6d / pin 10d）+ `stale-while-revalidate` | 模板字符串拼 SVG，CSS keyframes | ①失败也要产出合法 SVG；②TTL 按数据易变度分级；③fetcher 与 renderer 分层 |
| **lowlighter/metrics** | GitHub composite action + Docker | 无持久缓存，渲染前预检 rate limit | EJS + `<foreignObject>`，Puppeteer 量高回写 | ①目录即插件 + metadata 声明；②单插件失败降级为 warning 不中断 |
| **ryo-ma/github-profile-trophy** | Vercel + Deno，另有 composite action | CDN 头 + `/tmp` 静态再生 6h + 可选 Redis | 固定坐标模板字符串 | ①阈值表优于算分；②composite action 是零运行时范式 |
| **Platane/snk** | Docker action / node16 单文件 | 无 | 纯 CSS keyframes，每节蛇身一个 rect | ①抓 HTML 避开 API 配额；②SVG 声明式动画比 GIF 小一个量级 |
| **badges/shields** | 长驻 Node + Cloudflare | HTTP 头分级 + 进程内 resourceCache | `badge-maker` + 预计算字宽 | ①错误徽章也是产品；②上游失败不重试，直接给语义化错误 |
| **DenverCoder1/readme-typing-svg** | PHP on Heroku | 当天 23:59 过期 + 强制回源 | SMIL + textPath | ①参数清洗回退默认优于报错；②字体必须内嵌 |

### 差距与处理

| 差距 | 来源 | 本项目处理 |
|---|---|---|
| 无分级缓存 | GRS / trophy | 静态模式下「缓存」= 数据快照 + 输入指纹短路。`--skip-if-unchanged` 实测 **53× 加速**；网络层另加 ETag（304 不重下） |
| 无重试/退避 | C++ 之外几乎所有项目都缺 | `kit/net.py`：指数退避 + 抖动，503/429 重试 3 次，404 立即失败 |
| 无连接复用 | typing-svg / GRS 都没设超时 | `http.client` 长连接池（默认），有 httpx 时升级 HTTP/2 |
| 无参数/结构校验 | typing-svg 有 query 清洗，其他基本没有 | `kit/schema.py`：accounts/works/stats/writing 四类声明式 schema，821 条离线断言 |
| 无插件扩展点 | metrics 有，其余没有 | `kit/plugins.py` 注册表，加卡片零改 build |
| 错误不可诊断 | GRS 打日志，trophy 抛 HTML | `SchemaError` 带字段路径；`HttpError` 带 status/url/body 片段 |
| 字体/宽度靠猜 | shields 用 anafanafo 预计算字宽 | 已有 `text_w()` 估算（CJK 1.0em / 拉丁 0.6em），与 shields 同思路但不引依赖 |
| 无 golden 回归 | GRS 用 Jest 快照 | `tests/` 28 个用例 + `verify.py` 821 断言 + `--skip-if-unchanged` 幂等 |
| 产物体积未优化 | snk 有 benchmark job | `kit/pngopt.py` 无损重压缩（-7%），`scripts/bench.py` 记录各资产体积 |

**仍然不如它们的地方（诚实记录）**：

- 没有服务端实时渲染，因此不支持「访问者输入任意用户名」这种玩法——这是定位选择，不是缺陷。
- 没有 HTTP/2（未装 httpx 时），对 5 个账号 × 3 平台这种量级无影响。
- 无 CDN 语义；但产物是 git 里的静态文件，由平台 CDN 接管，反而更简单。

## 4. 性能数据

`python scripts/bench.py`（Python 3.14.9，8 核 Windows）：

| 指标 | 重构前 | 重构后 | 变化 |
|---|---|---|---|
| 全量生成（5 账号） | 0.262s | 0.104s 串行 / 0.085s 并行 | -60% / -68% |
| 单账号生成 | 0.044s | 0.019s | -57% |
| 增量构建（输入未变） | 全量重写 | 0.0008s 短路 | **53×** |
| hero.png | 997 KB | 922–926 KB | -7% |
| 单元测试 | 0 | 28 | — |
| 离线断言 | 0 | 821 | — |

提速来源，按贡献排序：

1. **图标解析缓存**（`functools.lru_cache` + mtime/size 键）：原实现每次调用都
   `open/read/regex`，一次全量生成 492 次调用；现在同进程内只读一次。
2. **线程池并行账号**（5 个账号彼此独立，瓶颈是文件 I/O）。
   试过 `ProcessPoolExecutor`，Windows 上解释器启动比整个构建还慢（0.44s），
   改线程后稳定在 0.085s。
3. **确定性随机数复用**：`rng()` 每次构造 `random.Random`，改为按 (account, salt)
   缓存实例。
4. **原子写入**：`os.replace` 替代直接覆盖，避免半截文件被下游读到。

## 5. 数据流与失败语义

```
平台 API ──kit/net（重试 + ETag）──► refresh / discover_works ──► data/*.json
                                                                    │
                              schema.py 校验（失败即中止，不写坏数据）
                                                                    ↓
                                       kit.build（插件渲染）──► assets/ + README
                                                                    ↓
                                        verify.py（821 断言）──► CI 门禁
```

- **抓取失败**：保留旧值（`refresh_*` 内部 try/except），统计不会掉零。
- **数据非法**：`schema.py` 在写盘前拦截，`SchemaError` 列出全部问题路径。
- **渲染失败**：插件层先生成 `card failed:` 占位 SVG，保证单卡失败不拖垮整批构建；
  `verify.py` 随后把任何错误卡视为硬失败，阻止错误产物出库。
- **构建无变化**：`--skip-if-unchanged` 只读输入指纹，不重写文件，保持 mtime 稳定。

## 6. 新增一张卡片要做什么

1. 在 `kit/cards.py` 写渲染函数（返回 SVG 字符串或 None）。
2. 在 `kit/cardset.py` 加一行 `@card(...)`。
3. 若要在 README 里展示，在 `kit/readme.py` 对应 section 加 `<img>`。

`build.py`、`verify.py`、`pack.py` 都不用改。

## 7. 已知取舍

- **`accounts.py` 保持 Python 模块而非 YAML/TOML**：它需要表达式（`links` 里的
  按平台回退、`work_url()` 的逻辑），YAML 会逼出一套自制的求值规则。
- **预览页不引前端框架**：单文件 + 几十行原生 JS，够用且零构建。
- **不接第三方统计服务**：徽章是唯一外部依赖（shields.io），且只在 GitHub 账号出现，
  失败时只是不显示，不影响页面。
