# 能力对标矩阵 · FEATURE MATRIX

对标方式：**源码级盘点**（非 README 摘要），六个仓库已 clone 到本地逐文件阅读。
「状态」列：✅ 已移植 / 🔄 部分移植 / ⏳ 需要 token（可选插件） / ❌ 不适用（运行期或需交互）。

| 能力 | 来源项目 | 来源文件 | 状态 | 本项目实现 |
|---|---|---|---|---|
| **主题系统** | | | | |
| 多主题预设 | GRS (75), trophy (25) | `themes/index.js`, `src/theme.ts` | ✅ | `kit/theme.py`：13 套 GRS 精选 + aurora 默认 |
| 逐账号主题 | GRS | `?theme=` query | ✅ | `ACCOUNTS[key]["theme"]` |
| 自定义色覆盖 | GRS | `?title_color=` 等逐色参数 | ✅ | `ACCOUNTS[key]["theme_custom"]` dict |
| **Rank / 成就** | | | | |
| CDF 百分位 Rank 环 | GRS | `src/calculateRank.js` | 🔄 | `kit/rank.py:calculate_rank()` 使用快照中提供的统计字段；GitHub 有 token 时可采集过去一年贡献数，缺失字段按零计算；时间窗口与上游全量口径不同 |
| Rank 环进度弧 | GRS | `src/cards/stats.js` | 🔄 | `rank.py` 输出 level/percentile，环画在 stats 卡 |
| 阈值奖杯（SSS→C） | trophy | `src/trophy_list.ts` | 🔄 | `kit/rank.py:TROPHY_TABLE` 覆盖 stars/merged/repos；成就表另含 gists/orgs/starred/following |
| 下一档进度条 | trophy | `src/icons.ts:getNextRankBar` | ✅ | `kit/achievements.py:_panel` 80px bar |
| 成就系统（C/B/A/S） | metrics | `plugins/achievements/list/users.mjs` | 🔄 | `kit/rank.py:ACHIEVEMENT_TABLE` 已覆盖 9 类可快照推导成就；仍缺项目/讨论/赞助等 GraphQL 明细 |
| 秘密成就 ($) | metrics | 同上 `secrets: yes` | ⏳ | `refresh_extras.py` 通过公开 GPG/Topics 页面检测 Verified/Explorer，写入 `data/extras.json`；无检测结果为不出卡，不伪造 |
| Rank 配色 | metrics | 同上 rank colors | ✅ | `ACHIEVEMENT_COLORS` |
| **卡片** | | | | |
| 统计卡 | GRS | `src/cards/stats.js` | ✅ | `kit/cards.py:stats_svg` |
| 语言构成卡（多布局） | GRS | `src/cards/top-languages.js` | ✅ | `langs_svg`：bar / donut / compact / pie 四布局，`ACCOUNTS[key]["cards"]["langs_layout"]` 可选 |
| Repo pin 卡 | GRS | `src/cards/repo.js` | ⏳ | `scripts/render_cards.mjs` 可在 GitHub token/Node 核心可用时写入 `data/cards/<account>/pin-*.svg`；当前仓库无 pin 种子 |
| Gist 卡 | GRS | `src/cards/gist.js` | ⏳ | `scripts/refresh_extras.py` 通过 GitHub API 采集 gist，`kit/extras.py:gist_svg` 渲染；无 gist 时不生成卡片 |
| 等距日历 | metrics | `plugins/isocalendar/index.mjs` | ⏳ | 由 GitHub events 采集日期计数，`isocalendar_svg` 渲染；受 events API 时间/权限限制 |
| 编码习惯 | metrics | `plugins/habits/index.mjs` | ⏳ | 仅在 events 返回语言字段时生成；当前公开 events 通常不含该字段，保持空态 |
| 关注者头像墙 | metrics | `plugins/people/index.mjs` | ⏳ | GitHub REST followers 采集 login，`people_svg` 渲染；头像 URL 未使用 |
| 项目看板 | metrics | `plugins/projects/index.mjs` | ⏳ | GitHub repos owner 采集名称/描述，`projects_svg` 渲染，非 GraphQL Projects |
| 徽章行（自渲染） | shields | `badge-maker/lib/badge-renderers.js` | ✅ | `kit/badge.py`：flat + flat-square，textLength 技巧；README 按实际 `badges-{lang}.svg` 产物引用 |
| 错误徽章语义 | shields | `core/base-service/errors.js` | 🔄 | 插件失败渲染 `card failed:` 占位 SVG；`verify.py` 将错误卡判为发布失败，未实现 Shields 的错误徽章语义 |
| **工程能力** | | | | |
| 逐卡开关/显示 | GRS | `?hide= / show=` | ✅ | `ACCOUNTS[key]["cards"]` dict |
| 自定义标题 | GRS | `?custom_title=` | ✅ | README 区块用 `section_titles`，语言/作品/WakaTime/成就卡用 `card_titles` 按语言覆盖；未配置保持默认 |
| 逐卡失败降级 | metrics | `data.plugins[name]=error` + `.field.error` | ✅ | `plugins.py:_error_svg` |
| 明暗双主题 | snk | `@media (prefers-color-scheme: dark)` | ✅ | snake 卡 CSS 变量；其余卡单色（与 GRS 一致） |
| 字宽精确测量 | shields | `anafanafo`（Verdana 11px 表） | ✅ | `kit/fontmetrics.py` 内置 Verdana 宽度表，未知字符回退 CJK 1em / 拉丁 0.6em |
| textLength 锁宽 | shields | `badge-renderers.js` | ✅ | `badge.py` font-size=110 + scale(.1) + textLength |
| 亮度对比度 | shields | `color.js:colorsForBackground` | ✅ | `badge.py:_brightness`（阈值 0.69） |
| 命名色/别名 | shields | `color.js:NAMED_COLORS` | ✅ | `badge.py:NAMED_COLORS` |
| 数字缩写 | GRS/metrics | `kFormatter`, `formatBytes` | ✅ | `rank.py:fmt_compact` |
| 渐变背景 | GRS | `bg_color=angle,c1,c2` | ✅ | `cards.py:_bg_fill`，theme_custom["bg1"] 支持渐变，贯穿 stats/langs/achievements 卡 |
| locale 国际化 | GRS | `src/translations.js` (46 种) | 🔄 | 默认 3 语言；README 导航支持 `locales` 配置扩展，标签仍需补齐对应翻译 |
| emoji 短代码 | GRS | `html.js` + emoji-name-map | ✅ | `kit/emoji.py`（200+），works 表/typing/badge/achievements 文案管道共用 |
| Linguist 语言色 | GRS | `languageColors.json`（649 色） | ✅ | `kit/linguist.py` + `data/linguist_colors.json` 全量 |
| Rank 环 | GRS | `cards/stats.js` rankCircle | ✅ | `stats_svg(rank=...)` r=40 圆周 dashoffset，rank_icon 三模式 |
| 输出格式 SVG/PNG/JSON | metrics | `config_output` | ✅ | SVG 全量；`scripts/rasterize.py --all-cards` 可把任意卡片栅格化为 PNG；JSON = data/*.json |
| 模板系统 | metrics | `source/templates/*` | ✅ | `kit/templates.py` 提供 classic/compact/minimal/portfolio 预设，控制区块顺序与可选区块；默认 classic 字节不变 |
| ETag 条件请求 | GRS | `cache.js` + HTTP headers | ✅ | `kit/net.py`（304/ETag/Last-Modified 条件缓存；无本地 TTL） |
| 重试 + token 池 | GRS | `src/common/retryer.js` | 🔄 | `net.py` 指数退避；token 池因单 token 无多池需求 |
| 速率限制处理 | shields | `config/default.yml` | ✅ | `net.py` 按主机最小间隔执行基础限流 |
| 预设组合 | metrics | `presets.mjs` | 🔄 | 模板预设与主题预设已可组合；未实现跨卡参数批量预设 |
| Actions 自动提交 | metrics/GRS | `action/*.mjs` | ✅ | GitHub `.github/workflows/refresh.yml` 定义日更/周卡提交并镜像到 GitCode/Gitee；GitCode `.gitcode/workflows/verify.yml` 负责验证门禁；运行结果需以平台 Actions 记录确认 |

## 未移植项的原因说明

| 类别 | 原因 |
|---|---|
| 需要 GitHub token 的（commits/issues/reviews 明细、followup、notable、traffic） | 公开 API 有 60/h 限额，数据已在 `stats.json` 的 repos/followers/stars 覆盖核心指标 |
| 需要第三方服务的（Spotify/Steam/LeetCode/Twitter/StackOverflow） | 与本项目定位无关（个人 profile 不是数据面板） |
| 需要 Puppeteer 的（skyline/screenshot/height 度量） | 静态生成器自算布局，不依赖浏览器运行期 |
| 运行期专属（HTTP 缓存头、CDN 策略、Web 实例） | 产物是 git 里的字节，没有服务端 |
