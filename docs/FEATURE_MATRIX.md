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
| CDF 百分位 Rank 环 | GRS | `src/calculateRank.js` | 🔄 | `kit/rank.py:calculate_rank()`；当前快照将 commits/prs/issues/reviews 置零，属于无 GraphQL 明细的降级口径 |
| Rank 环进度弧 | GRS | `src/cards/stats.js` | 🔄 | `rank.py` 输出 level/percentile，环画在 stats 卡 |
| 阈值奖杯（SSS→C） | trophy | `src/trophy_list.ts` | ✅ | `kit/rank.py:TROPHY_TABLE` |
| 下一档进度条 | trophy | `src/icons.ts:getNextRankBar` | ✅ | `kit/achievements.py:_panel` 80px bar |
| 成就系统（C/B/A/S） | metrics | `plugins/achievements/list/users.mjs` | 🔄 | `kit/rank.py:ACHIEVEMENT_TABLE`；仅实现本地快照可推导子集，token 明细项未启用 |
| 秘密成就 ($) | metrics | 同上 `secrets: yes` | ❌ | 依赖 Puppeteer 抓 github.com 页面 |
| Rank 配色 | metrics | 同上 rank colors | ✅ | `ACHIEVEMENT_COLORS` |
| **卡片** | | | | |
| 统计卡 | GRS | `src/cards/stats.js` | ✅ | `kit/cards.py:stats_svg` |
| 语言构成卡（多布局） | GRS | `src/cards/top-languages.js` | ✅ | `langs_svg`：bar / donut / compact / pie 四布局，`ACCOUNTS[key]["cards"]["langs_layout"]` 可选 |
| Repo pin 卡 | GRS | `src/cards/repo.js` | ⏳ | `scripts/render_cards.mjs` 可在 GitHub token/Node 核心可用时写入 `data/cards/<account>/pin-*.svg`；当前仓库无 pin 种子 |
| Gist 卡 | GRS | `src/cards/gist.js` | ❌ | 本项目无 gist 数据源 |
| WakaTime 卡 | GRS | `src/cards/wakatime.js` | ⏳ | `kit/wakatime.py`：token 可选插件；支持 `WAKATIME_API_URL` 与 en/zh-CN/ja 标签，但当前账号未启用 |
| 打字机动画 | typing-svg | `src/templates/main.php` | ✅ | `kit/typing.py`（SMIL 单行/多行模式） |
| 贡献蛇动画 | snk | `packages/solver` + `svg-creator` | ✅ | `kit/snake.py`：抓取+求解器+CSS 动画全移植；调色板 aurora 跟随主题 |
| 等距日历 | metrics | `plugins/isocalendar/index.mjs` | ❌ | 需要贡献日历数据（与 snake 共用数据源后可做） |
| 编码习惯 | metrics | `plugins/habits/index.mjs` | ❌ | 需要 GitHub events API（token 门槛） |
| 关注者头像墙 | metrics | `plugins/people/index.mjs` | ❌ | 需要头像 URL（GraphQL） |
| 项目看板 | metrics | `plugins/projects/index.mjs` | ❌ | 需要项目 GraphQL API |
| 徽章行（自渲染） | shields | `badge-maker/lib/badge-renderers.js` | ✅ | `kit/badge.py`：flat + flat-square，textLength 技巧；README 按实际 `badges-{lang}.svg` 产物引用 |
| 错误徽章语义 | shields | `core/base-service/errors.js` | ✅ | 卡片失败降级为占位卡（`plugins.py:_error_svg`） |
| **工程能力** | | | | |
| 逐卡开关/显示 | GRS | `?hide= / show=` | ✅ | `ACCOUNTS[key]["cards"]` dict |
| 自定义标题 | GRS | `?custom_title=` | ❌ | 当前仅支持逐卡开关与主题覆盖；没有通用 `<name>_title` 渲染逻辑，避免把未实现能力写成已实现 |
| 逐卡失败降级 | metrics | `data.plugins[name]=error` + `.field.error` | ✅ | `plugins.py:_error_svg` |
| 明暗双主题 | snk | `@media (prefers-color-scheme: dark)` | ✅ | snake 卡 CSS 变量；其余卡单色（与 GRS 一致） |
| 字宽精确测量 | shields | `anafanafo`（Verdana 11px 表） | 🔄 | `text_w()` 估算（CJK 1.0em/拉丁 0.6em）；Python 无 Verdana 表 |
| textLength 锁宽 | shields | `badge-renderers.js` | ✅ | `badge.py` font-size=110 + scale(.1) + textLength |
| 亮度对比度 | shields | `color.js:colorsForBackground` | ✅ | `badge.py:_brightness`（阈值 0.69） |
| 命名色/别名 | shields | `color.js:NAMED_COLORS` | ✅ | `badge.py:NAMED_COLORS` |
| 数字缩写 | GRS/metrics | `kFormatter`, `formatBytes` | ✅ | `rank.py:fmt_compact` |
| 渐变背景 | GRS | `bg_color=angle,c1,c2` | ✅ | `cards.py:_bg_fill`，theme_custom["bg1"] 支持渐变，贯穿 stats/langs/achievements 卡 |
| locale 国际化 | GRS | `src/translations.js` (46 种) | 🔄 | 3 语言（en/zh-CN/ja），标签在 accounts.py；扩展即加 dict |
| emoji 短代码 | GRS | `html.js` + emoji-name-map | ✅ | `kit/emoji.py`（200+），works 表/typing/badge/achievements 文案管道共用 |
| Linguist 语言色 | GRS | `languageColors.json`（649 色） | ✅ | `kit/linguist.py` + `data/linguist_colors.json` 全量 |
| Rank 环 | GRS | `cards/stats.js` rankCircle | ✅ | `stats_svg(rank=...)` r=40 圆周 dashoffset，rank_icon 三模式 |
| 输出格式 SVG/PNG/JSON | metrics | `config_output` | 🔄 | SVG 全量；PNG 仅 hero（rasterize.py）；JSON = data/*.json |
| 模板系统 | metrics | `source/templates/*` | ❌ | 单模板（星夜极光）；多模板需要 EJS 等价物 |
| ETag 条件请求 | GRS | `cache.js` + HTTP headers | ✅ | `kit/net.py`（304/ETag/Last-Modified 条件缓存；无本地 TTL） |
| 重试 + token 池 | GRS | `src/common/retryer.js` | 🔄 | `net.py` 指数退避；token 池因单 token 无多池需求 |
| 速率限制处理 | shields | `config/default.yml` | ✅ | `net.py` 按主机最小间隔 |
| 预设组合 | metrics | `presets.mjs` | ❌ | 单用户场景暂不需要 |
| Actions 自动提交 | metrics/GRS | `action/*.mjs` | ✅ | GitHub `refresh.yml` 日更/周卡自动提交并镜像到 GitCode/Gitee；GitCode `.gitcode/workflows/verify.yml` 负责验证门禁（本仓库只保留验证 workflow） |

## 未移植项的原因说明

| 类别 | 原因 |
|---|---|
| 需要 GitHub token 的（commits/issues/reviews 明细、followup、notable、traffic） | 公开 API 有 60/h 限额，数据已在 `stats.json` 的 repos/followers/stars 覆盖核心指标 |
| 需要第三方服务的（Spotify/Steam/LeetCode/Twitter/StackOverflow） | 与本项目定位无关（个人 profile 不是数据面板） |
| 需要 Puppeteer 的（skyline/screenshot/height 度量） | 静态生成器自算布局，不依赖浏览器运行期 |
| 运行期专属（HTTP 缓存头、CDN 策略、Web 实例） | 产物是 git 里的字节，没有服务端 |
