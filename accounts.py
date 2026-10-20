# -*- coding: utf-8 -*-
"""主页面 kit — 账号与文案的唯一数据源（纯数据文件，无副作用）。

五个账号同一套模板：WORKS 是作品目录，ACCOUNTS 是每处主页的配置，
生成器（scripts/generate.py）据此渲染出各账号的 README + SVG 资产。

数据来源：2026-10-14 对各平台 API 的实查结果（仓库列表、star 数、
已合并/在评 PR 清单见 CONTRIB_* 注释）。改文案只改本文件。
"""

KIT_VERSION = "1.0.0"

SERIF = "Georgia, 'Times New Roman', 'Songti SC', 'SimSun', serif"
SANS = "Helvetica, Arial, 'PingFang SC', 'Microsoft YaHei', sans-serif"
MONO = "ui-monospace, 'SF Mono', Menlo, Consolas, 'PingFang SC', monospace"

# 设计 v2 ——「星夜极光」：午夜蓝底 + 靛蓝/青绿极光渐变 + 星光点缀
THEME = {
    "bg0": "#04060E",
    "bg1": "#0A1122",
    "panel": "#0E1630",
    "panel2": "#131D3D",
    "gold": "#D9B876",
    "gold_bright": "#F2DC9E",
    "ink": "#F4F7FF",
    "muted": "#9AA8CC",
    "faint": "#5C6A94",
    "star": "#DFE8FF",
    "deep_blue": "#24356B",
    "indigo": "#6C8CFF",
    "teal": "#4FE3C1",
}

LANGS = ("md", "zh-CN", "ja")
README_NAME = {"md": "README.md", "zh-CN": "README.zh-CN.md", "ja": "README.ja.md"}
STATS_NAME = {"md": "stats-en.svg", "zh-CN": "stats-zh-CN.svg", "ja": "stats-ja.svg"}
# 官方卡片渲染核心（github-readme-stats 血统）的 locale 标识与 kit 语言的映射
CARD_LOCALE = {"md": "en", "zh-CN": "cn", "ja": "ja"}

# 技能图标（vendored 于 data/icons/，来源 devicon@master 与 simple-icons@15）：
# 键 = 图标文件名后缀，值 = (展示名, 首选文件名)。文件不存在时按 simple-icons → devicon 顺序回退。
SKILL_LABELS = {
    "typescript": "TypeScript", "javascript": "JavaScript", "python": "Python",
    "rust": "Rust", "go": "Go", "java": "Java", "kotlin": "Kotlin", "dart": "Dart",
    "react": "React", "vuejs": "Vue", "nodejs": "Node.js", "electron": "Electron",
    "tauri": "Tauri", "flutter": "Flutter", "docker": "Docker", "git": "Git",
    "linux": "Linux", "vscode": "VS Code", "mysql": "MySQL", "postgresql": "PostgreSQL",
    "redis": "Redis", "nginx": "Nginx", "graphql": "GraphQL", "markdown": "Markdown",
    "nixos": "NixOS", "vitejs": "Vite", "bash": "Bash", "swift": "Swift",
    "wechat": "WeChat", "openai": "OpenAI", "ollama": "Ollama",
    "huggingface": "Hugging Face", "anthropic": "Claude",
}

# 图标解析顺序：simple-icons 版优先（单 path、体积小），其次 devicon 版
ICON_PREFIXES = ("si", "dev")

# 平台徽标（「在别处」表格用，图标同样 vendored）
PLATFORM_ICON = {"github": "si-github.svg", "gitcode": "si-gitcode.svg", "gitee": "si-gitee.svg"}

# 写作区（同一个人，三处公开笔迹）：(平台名, 主页 URL, 本地图标文件)
WRITING = [
    ("CSDN", "https://blog.csdn.net/weixin_56622231", "si-csdn.svg"),
    ("Juejin", "https://juejin.cn/user/2350111542479753", "si-juejin.svg"),
    ("Zhihu", "https://www.zhihu.com/people/e7c851hd", "si-zhihu.svg"),
]

# 人工维护的站外文章（curated，无 RSS 来源；zhihu 三篇 2026-10-15/16 经发布 API 实测）。
# refresh.py 的 fetch_writing 会把本列表合并进 data/writing.json（curated 优先、URL 去重、
# 按日期倒序），RSS 抓取失败也不会丢失——新增文章只改这里。
CURATED_POSTS = [
    {
        "title": "MCP 落地一年，我总结了 6 个没人告诉你的工程真相",
        "url": "https://zhuanlan.zhihu.com/p/2094232145015453253",
        "date": "2026-10-16",
    },
    {
        "title": "本地优先 AI：当所有人都在上云，我为什么把 AI 装回自己电脑",
        "url": "https://zhuanlan.zhihu.com/p/2094233605513991576",
        "date": "2026-10-16",
    },
    {
        "title": "AI Agent 上线前必须过的 5 道关：一个真实项目的工程手记",
        "url": "https://zhuanlan.zhihu.com/p/2094218858789856836",
        "date": "2026-10-16",
    },
]

# 精选格言（离线、确定性轮换：index = (月-1) % len；每月一句，避免每日变更造成刷新 PR 噪音）
QUOTES = [
    {"en": "Make it work, make it right, make it fast.", "zh": "先能跑，再跑对，再跑快。", "author": "Kent Beck"},
    {"en": "Simplicity is the soul of efficiency.", "zh": "简洁是效率的灵魂。", "author": "Austin Freeman"},
    {"en": "The best way to predict the future is to invent it.", "zh": "预测未来的最好方式，是把它创造出来。", "author": "Alan Kay"},
    {"en": "Talk is cheap. Show me the code.", "zh": "少废话，放码过来。", "author": "Linus Torvalds"},
    {"en": "Premature optimization is the root of all evil.", "zh": "过早优化是万恶之源。", "author": "Donald Knuth"},
    {"en": "Programs must be written for people to read.", "zh": "程序首先是写给人读的。", "author": "Harold Abelson"},
    {"en": "Done is better than perfect.", "zh": "完成胜于完美。", "author": "Sheryl Sandberg"},
    {"en": "Stay hungry, stay foolish.", "zh": "求知若饥，虚心若愚。", "author": "Steve Jobs"},
    {"en": "Everything should be made as simple as possible, but not simpler.", "zh": "尽可能简单，但不过于简单。", "author": "Albert Einstein"},
    {"en": "First, solve the problem. Then, write the code.", "zh": "先解决问题，再写代码。", "author": "John Johnson"},
    {"en": "Slow is smooth, and smooth is fast.", "zh": "慢即是稳，稳即是快。", "author": "—"},
    {"en": "An investment in knowledge pays the best interest.", "zh": "对知识的投资，回报最丰厚。", "author": "Benjamin Franklin"},
]

LABELS = {
    "md": {
        "about": "About",
        "now": "Now",
        "works": "Selected work",
        "contrib": "Open source",
        "numbers": "Numbers",
        "writing": "Writing",
        "writing_latest": "Latest writing",
        "contrib_graph": "Contribution graph",
        "elsewhere": "Elsewhere",
        "stat_repos": "public repos",
        "stat_stars": "stars",
        "stat_followers": "followers",
        "stat_merged": "upstream merges",
        "as_of": "as of",
        "all_repos": "All public repositories:",
        "mirror_note": "One identity, five homes — these five accounts mirror the same person.",
        "here": "you are here",
        "merged_heading": "Merged upstream",
        "review_heading": "In review",
        "shared_line": "Patches merged upstream into ohmyzsh, tldr, icalendar, NUR and more — details on the two GitHub accounts",
        "skills": "Toolbox",
        "skills_note": "Icons vendored in this repository (devicon / simple-icons)",
        "badge_repos": "repos",
        "badge_followers": "followers",
        "platform": "Platform",
        "account": "Account",
        "role": "Role",
        "langs": "Languages",
        "activity": "Activity",
        "date": "Date",
        "article": "Article",
        "pinned": "Pinned work",
        "also_on": "Also on",
    },
    "zh-CN": {
        "about": "关于",
        "now": "近期",
        "works": "精选作品",
        "contrib": "开源足迹",
        "numbers": "数据",
        "writing": "写作",
        "writing_latest": "最新文章",
        "contrib_graph": "贡献图",
        "elsewhere": "在别处",
        "stat_repos": "公开仓库",
        "stat_stars": "累计 Star",
        "stat_followers": "关注者",
        "stat_merged": "上游合并",
        "as_of": "数据截至",
        "all_repos": "全部公开仓库：",
        "mirror_note": "同一身份，五处安放 —— 这五个账号同属一人，互为镜像。",
        "here": "你在这里",
        "merged_heading": "已合并上游",
        "review_heading": "评审中",
        "shared_line": "补丁已合入 ohmyzsh · tldr · icalendar · NUR 等上游项目，明细见两个 GitHub 账号",
        "skills": "工具箱",
        "skills_note": "图标已随仓库自带（devicon / simple-icons）",
        "badge_repos": "仓库",
        "badge_followers": "关注者",
        "platform": "平台",
        "account": "账号",
        "role": "定位",
        "langs": "语言构成",
        "activity": "活跃度",
        "date": "日期",
        "article": "文章",
        "pinned": "置顶作品",
        "also_on": "同步发布",
    },
    "ja": {
        "about": "について",
        "now": "近況",
        "works": "主な作品",
        "contrib": "オープンソース",
        "numbers": "数字で見る",
        "writing": "執筆",
        "writing_latest": "最新の記事",
        "contrib_graph": "コントリビューション",
        "elsewhere": "ほかの場所",
        "stat_repos": "公開リポジトリ",
        "stat_stars": "累計スター",
        "stat_followers": "フォロワー",
        "stat_merged": "上流へのマージ",
        "as_of": "データ時点",
        "all_repos": "全公開リポジトリ：",
        "mirror_note": "同一人物の5つの拠点 — これらのアカウントは同じ人のミラーです。",
        "here": "現在地",
        "merged_heading": "上流マージ済み",
        "review_heading": "レビュー中",
        "shared_line": "パッチは ohmyzsh・tldr・icalendar・NUR などにマージ済み — 詳細は GitHub の2アカウントへ",
        "skills": "道具箱",
        "skills_note": "アイコンはリポジトリに同梱（devicon / simple-icons）",
        "badge_repos": "リポジトリ",
        "badge_followers": "フォロワー",
        "platform": "プラットフォーム",
        "account": "アカウント",
        "role": "役割",
        "langs": "言語構成",
        "activity": "アクティビティ",
        "date": "日付",
        "article": "記事",
        "pinned": "ピン留め作品",
        "also_on": "同時掲載",
    },
}

# --------------------------------------------------------------------------
# 作品目录（只收录 2026-10-14 实查存在的仓库；links 里的 URL 均来自当日 API）
# --------------------------------------------------------------------------
WORKS = {
    "xiaoman": {
        "title": "Xiaoman 小满",
        "desc": {
            "md": "Chat-first personal finance agent — local-first, LangGraph orchestration",
            "zh-CN": "对话优先的个人理财 Agent —— 本地优先，LangGraph 编排",
            "ja": "会話ファーストの個人金融エージェント — ローカル優先・LangGraph 編成",
        },
        "tags": {"md": "AI · Finance", "zh-CN": "AI · 金融", "ja": "AI · 金融"},
        "links": {
            "github": [
                "https://github.com/X33834/xiaoman",
                "https://github.com/Morningstar202604/xiaoman",
                "https://github.com/badhope/xiaoman",
            ],
            "gitcode": "https://gitcode.com/badhope/xiaoman",
        },
    },
    "shopcash": {
        "title": "ShopCash 店收宝",
        "desc": {
            "md": "Offline shop checkout and ledger — the software never touches the money",
            "zh-CN": "单机门店收银与收款记账 —— 软件零资金介入，钱只进商家自己的商户号",
            "ja": "単店舗向けレジ・売上帳 — ソフトは資金に一切関与しません",
        },
        "tags": {"md": "Tools · Payments", "zh-CN": "工具 · 支付", "ja": "ツール · 決済"},
        "links": {
            "github": [
                "https://github.com/X33834/shopcash",
                "https://github.com/Morningstar202604/shopcash",
                "https://github.com/badhope/shopcash",
            ],
        },
    },
    "digilegacy": {
        "title": "DigiLegacy 归零",
        "desc": {
            "md": "Local-first digital legacy planner",
            "zh-CN": "数字遗产管理系统 —— 本地优先",
            "ja": "ローカル優先のデジタル遺産管理",
        },
        "tags": {"md": "Tools · Privacy", "zh-CN": "工具 · 隐私", "ja": "ツール · プライバシー"},
        "links": {
            "github": [
                "https://github.com/X33834/digilegacy",
                "https://github.com/Morningstar202604/digilegacy",
                "https://github.com/badhope/digilegacy",
            ],
            "gitcode": "https://gitcode.com/badhope/digilegacy",
        },
    },
    "naiwa-pet": {
        "title": "Naiwa 奶蛙",
        "desc": {
            "md": "A Live2D desktop pet — eye tracking, expressions, always on top (Electron + PixiJS)",
            "zh-CN": "Live2D 桌面宠物 —— 眼神跟随、动作表情、可拖动置顶（Electron + PixiJS）",
            "ja": "Live2D デスクトップペット — 視線追従・表情モーション（Electron + PixiJS）",
        },
        "tags": {"md": "Desktop · Fun", "zh-CN": "桌面 · 趣味", "ja": "デスクトップ · お楽しみ"},
        "links": {
            "github": [
                "https://github.com/X33834/naiwa-pet",
                "https://github.com/Morningstar202604/naiwa-pet",
                "https://github.com/badhope/naiwa-pet",
            ],
            "gitcode": "https://gitcode.com/badhope/naiwa-pet",
            "gitee": "https://gitee.com/badhope/naiwa-pet",
        },
    },
    "spark": {
        "title": "Spark",
        "desc": {
            "md": "Local-first AI coding agent — approval gate, prompt-injection defence",
            "zh-CN": "本地优先的 AI 编程代理 —— 审批门禁与提示注入防护",
            "ja": "ローカル優先の AI コーディングエージェント（承認ゲート付き）",
        },
        "tags": {"md": "AI · DevTools", "zh-CN": "AI · 编程", "ja": "AI · 開発"},
        "links": {
            "github": [
                "https://github.com/X33834/spark",
                "https://github.com/Morningstar202604/spark",
                "https://github.com/badhope/spark",
            ],
            "gitcode": "https://gitcode.com/badhope/spark",
        },
    },
    "workbench": {
        "title": "Workbench",
        "desc": {
            "md": "A local-first desktop workbench (Tauri 2 + React 19) with live tooling",
            "zh-CN": "本地优先的桌面工作台（Tauri 2 + React 19）",
            "ja": "ローカル優先のデスクトップワークベンチ（Tauri 2 + React 19）",
        },
        "tags": {"md": "Desktop · Productivity", "zh-CN": "桌面 · 效率", "ja": "デスクトップ · 生産性"},
        "links": {
            "github": [
                "https://github.com/X33834/workbench",
                "https://github.com/Morningstar202604/workbench",
                "https://github.com/badhope/workbench",
            ],
            "gitcode": "https://gitcode.com/badhope/workbench",
            "gitee": "https://gitee.com/badhope/workbench",
        },
    },
    "sciflow": {
        "title": "SciFlow",
        "desc": {
            "md": "Local-first AI research agent workbench — multi-agent pipeline, planner, memory",
            "zh-CN": "本地优先的 AI 科研智能体工作台 —— 多 Agent 编排与记忆",
            "ja": "ローカル優先の AI 研究エージェント作業台 — マルチエージェント編成",
        },
        "tags": {"md": "AI · Research", "zh-CN": "AI · 科研", "ja": "AI · 研究"},
        "links": {
            "github": [
                "https://github.com/X33834/sciflow",
                "https://github.com/Morningstar202604/sciflow",
                "https://github.com/badhope/sciflow",
            ],
            "gitcode": "https://gitcode.com/badhope/sciflow",
        },
    },
    "lingxi": {
        "title": "ZhiXi 智犀",
        "desc": {
            "md": "A 24/7 full-stack digital-employee engine",
            "zh-CN": "24 小时全栈数字员工引擎",
            "ja": "24時間フルスタック「デジタル従業員」エンジン",
        },
        "tags": {"md": "AI · Agents", "zh-CN": "AI · Agent", "ja": "AI · エージェント"},
        "links": {
            "github": [
                "https://github.com/X33834/lingxi",
                "https://github.com/Morningstar202604/lingxi",
                "https://github.com/badhope/lingxi",
            ],
            "gitcode": "https://gitcode.com/badhope/lingxi",
        },
    },
    "chushi-radar": {
        "title": "Chushi Radar 人情世故雷达",
        "desc": {
            "md": "A lightweight local-first social-intelligence assistant",
            "zh-CN": "人脉经营 · 人情账本 · 社交修炼，本地优先的轻量个人助手",
            "ja": "ローカル優先の軽量ソーシャル知能アシスタント",
        },
        "tags": {"md": "Tools · Social", "zh-CN": "工具 · 社交", "ja": "ツール · ソーシャル"},
        "links": {
            "github": [
                "https://github.com/X33834/chushi-radar",
                "https://github.com/Morningstar202604/chushi-radar",
            ],
            "gitcode": "https://gitcode.com/badhope/chushi-radar",
        },
    },
    "awesome-ai-devkit": {
        "title": "Awesome AI DevKit",
        "desc": {
            "md": "Cross-platform AI coding config ecosystem — turn CLI agents into a full dev team",
            "zh-CN": "跨平台场景化 AI 编程配置生态 —— 把 CLI Agent 变成完整 AI 开发团队",
            "ja": "クロスプラットフォーム AI 開発設定エコシステム",
        },
        "tags": {"md": "AI · Toolchain", "zh-CN": "AI · 工具链", "ja": "AI · ツールチェーン"},
        "links": {
            "github": [
                "https://github.com/X33834/awesome-ai-devkit",
                "https://github.com/Morningstar202604/awesome-ai-devkit",
            ],
        },
    },
    "awesome-skillkit": {
        "title": "Awesome SkillKit",
        "desc": {
            "md": "Curated Agent Skills scene packs (57 packs / 403 skills)",
            "zh-CN": "Agent Skills 场景包精选集（57 packs / 403 skills）",
            "ja": "Agent Skills シーンパック集（57 packs / 403 skills）",
        },
        "tags": {"md": "AI · Skills", "zh-CN": "AI · 技能库", "ja": "AI · スキル"},
        "links": {"github": ["https://github.com/X33834/awesome-skillkit"]},
    },
    "agent-builder": {
        "title": "Agent Builder",
        "desc": {
            "md": "Production-grade AI agent reference — 24 TypeScript guides",
            "zh-CN": "AI Agent 全栈构建参考 —— 24 篇生产级 TypeScript 指南",
            "ja": "プロダクション向け AI エージェント実装ガイド（TypeScript 24 篇）",
        },
        "tags": {"md": "AI · Guides", "zh-CN": "AI · 教程", "ja": "AI · ガイド"},
        "links": {
            "github": [
                "https://github.com/X33834/agent-builder",
                "https://github.com/Morningstar202604/agent-builder",
                "https://github.com/badhope/agent-builder",
            ],
            "gitcode": "https://gitcode.com/badhope/agent-builder",
            "gitee": "https://gitee.com/badhope/agent-builder",
        },
    },
    "CodePocket": {
        "title": "CodePocket",
        "desc": {
            "md": "An offline-first Python IDE for Android (native CPython)",
            "zh-CN": "离线优先的 Android 端 Python IDE（原生 CPython）",
            "ja": "オフライン優先の Android 向け Python IDE（ネイティブ CPython）",
        },
        "tags": {"md": "Mobile · Offline", "zh-CN": "移动端 · 离线", "ja": "モバイル · オフライン"},
        "links": {
            "github": [
                "https://github.com/X33834/CodePocket",
            ],
            "gitcode": "https://gitcode.com/badhope/CodePocket",
        },
    },
    "zhike": {
        "title": "Zhike 知客",
        "desc": {
            "md": "Online support agent — QQ / WeChat gateway, console, RAG pipeline",
            "zh-CN": "在线客服 Agent —— QQ / 微信渠道网关 + 可视化控制台 + RAG 管线",
            "ja": "オンライン客服エージェント — QQ / WeChat 連携・コンソール・RAG",
        },
        "tags": {"md": "AI · Support", "zh-CN": "AI · 客服", "ja": "AI · サポート"},
        "links": {
            "gitcode": "https://gitcode.com/badhope/zhike",
            "gitee": "https://gitee.com/badhope/zhike",
        },
    },
    "vaultx": {
        "title": "VaultX",
        "desc": {
            "md": "Agent-first personal vault — one encrypted local file, CLI / Web / MCP access",
            "zh-CN": "agent-first 个人密钥库 —— 单个加密本地文件，CLI / Web / MCP 三种入口",
            "ja": "エージェント優先の個人鍵保管庫 — 暗号化ローカルファイル + MCP",
        },
        "tags": {"md": "Security · Tools", "zh-CN": "安全 · 工具", "ja": "セキュリティ · ツール"},
        "links": {"gitcode": "https://gitcode.com/badhope/vaultx"},
    },
    "bot4cj": {
        "title": "bot4cj",
        "desc": {
            "md": "Hardware robot control framework in the Cangjie language",
            "zh-CN": "基于仓颉语言的硬件机器人控制框架",
            "ja": "Cangjie 言語によるハードウェアロボット制御フレームワーク",
        },
        "tags": {"md": "Hardware · Robotics", "zh-CN": "硬件 · 机器人", "ja": "ハードウェア · ロボット"},
        "links": {"gitcode": "https://gitcode.com/qingss0/bot4cj"},
    },
    "mashang-python": {
        "title": "码上 Python · PY//NOW",
        "desc": {
            "md": "Cyberpunk offline Python learning terminal — 30 quests, assert grading",
            "zh-CN": "赛博朋克风离线 Python 学习终端 —— 30 讲闯关 · assert 判题",
            "ja": "サイバーパンク風オフライン Python 学習ターミナル",
        },
        "tags": {"md": "Education", "zh-CN": "教育", "ja": "教育"},
        "links": {"gitcode": "https://gitcode.com/badhope/mashang-python"},
    },
    "scholarhub": {
        "title": "ScholarHub",
        "desc": {
            "md": "Multi-tenant journal and preprint platform — submission / review / reading",
            "zh-CN": "学术期刊与预印本多租户平台 —— 投稿 / 评审 / 阅读",
            "ja": "学術ジャーナル・プレプリントのマルチテナント基盤",
        },
        "tags": {"md": "SaaS · Academia", "zh-CN": "SaaS · 学术", "ja": "SaaS · 学術"},
        "links": {"gitcode": "https://gitcode.com/badhope/scholarhub"},
    },
    "content-harbor": {
        "title": "Harbor 内容港",
        "desc": {
            "md": "Multi-platform publishing hub — AI drafting, compliance gate, one-click delivery",
            "zh-CN": "多平台内容发布中枢 —— AI 写稿 + 合规门禁 + 一键分发",
            "ja": "マルチプラットフォーム投稿ハブ — AI 執筆・コンプライアンスゲート",
        },
        "tags": {"md": "Content · Toolchain", "zh-CN": "内容 · 工具链", "ja": "コンテンツ · ツール"},
        "links": {
            "github": ["https://github.com/X33834/content-harbor-fixed"],
            "gitcode": "https://gitcode.com/badhope/content-harbor",
        },
    },
    "GlobalEcom-AI": {
        "title": "GlobalEcom AI",
        "desc": {
            "md": "AI-native cross-border commerce platform — storefront, seller desk, 5 agents",
            "zh-CN": "AI 原生跨境出货台 —— 买家商城 + 卖家工作台 + 5 个 AI Agent",
            "ja": "AI ネイティブ越境EC基盤 — ストアフロント・セラー台・5 エージェント",
        },
        "tags": {"md": "Commerce · AI", "zh-CN": "电商 · AI", "ja": "EC · AI"},
        "links": {"gitcode": "https://gitcode.com/badhope/GlobalEcom-AI"},
    },
    "melee": {
        "title": "Melee AI 大乱斗",
        "desc": {
            "md": "LLM battle arena — live spectating, dual-track judging, sandboxed code duels",
            "zh-CN": "多个大模型同台竞技 —— 实时观战 + 双轨裁判 + 沙箱代码战场",
            "ja": "LLM バトルアリーナ — リアルタイム観戦・二重審判・サンドボックス",
        },
        "tags": {"md": "AI · Playground", "zh-CN": "AI · 实验", "ja": "AI · 実験"},
        "links": {"gitcode": "https://gitcode.com/badhope/melee"},
    },
    "lens": {
        "title": "Lens",
        "desc": {
            "md": "A lens for your AI coding agent — turn transcripts into a visual map",
            "zh-CN": "AI 编程代理透镜 —— 把对话流转为可视化全景",
            "ja": "AI コーディングエージェントのレンズ — 対話ログを可視化",
        },
        "tags": {"md": "AI · Visualisation", "zh-CN": "AI · 可视化", "ja": "AI · 可視化"},
        "links": {"gitcode": "https://gitcode.com/badhope/lens"},
    },
    "world-walker": {
        "title": "World Walker 万界·行者",
        "desc": {
            "md": "AI-driven interactive text fiction engine",
            "zh-CN": "AI 驱动的文字互动小说引擎",
            "ja": "AI 駆動のテキストインタラクティブ小説エンジン",
        },
        "tags": {"md": "Games · Writing", "zh-CN": "游戏 · 写作", "ja": "ゲーム · 執筆"},
        "links": {"gitcode": "https://gitcode.com/badhope/world-walker"},
    },
    "KeBaiPay": {
        "title": "KeBaiPay 科佰收单",
        "desc": {
            "md": "Self-hosted compliant payment intake — licensed channels, open API, reconciliation",
            "zh-CN": "自托管开源合规聚合收单 —— 持牌通道 + 开放 API + 渠道对账",
            "ja": "セルフホスト型コンプライアント決済収単基盤",
        },
        "tags": {"md": "Payments · Compliance", "zh-CN": "支付 · 合规", "ja": "決済 · コンプラ"},
        "links": {
            "github": ["https://github.com/Morningstar202604/KeBaiPay"],
            "gitcode": "https://gitcode.com/badhope/KeBaiPay",
        },
    },
    "p2wlan": {
        "title": "p2wlan",
        "desc": {
            "md": "Cross-platform P2P virtual LAN — NAT traversal, IPv6 direct, room networking",
            "zh-CN": "跨平台 P2P 虚拟局域网 —— NAT 穿透 / IPv6 直连 / 房间组网",
            "ja": "クロスプラットフォーム P2P 仮想 LAN — NAT 穿越・IPv6・ルーム網",
        },
        "tags": {"md": "Networking · Tools", "zh-CN": "网络 · 工具", "ja": "ネットワーク · ツール"},
        "links": {"github": ["https://github.com/Morningstar202604/p2wlan"]},
    },
    "novel-engine": {
        "title": "Novel Engine",
        "desc": {
            "md": "Novel-writing engine — story bible, cross-chapter memory, rule-based consistency audit",
            "zh-CN": "长篇小说写作引擎 —— 设定集 / 跨章记忆 / 一致性审计（0 LLM 成本规则审计）",
            "ja": "長編小説エンジン — 設定集・章間記憶・一貫性監査",
        },
        "tags": {"md": "Writing · AI", "zh-CN": "写作 · AI", "ja": "執筆 · AI"},
        "links": {"github": ["https://github.com/Morningstar202604/novel-engine"]},
    },
    "DU": {
        "title": "DU 渡",
        "desc": {
            "md": "A client-side Chinese metaphysics toolkit — 49 tools",
            "zh-CN": "纯客户端中文术数工具箱 —— 49 件工具",
            "ja": "クライアントサイド中国術数ツールキット — 49 ツール",
        },
        "tags": {"md": "Tools · Culture", "zh-CN": "工具 · 文化", "ja": "ツール · 文化"},
        "links": {"github": ["https://github.com/badhope/DU"]},
    },
    "API-Market": {
        "title": "API Market",
        "desc": {
            "md": "A searchable catalogue of 14,000+ public APIs",
            "zh-CN": "14,000+ 公共 API 的可搜索目录",
            "ja": "14,000+ の公開 API を検索できるカタログ",
        },
        "tags": {"md": "Data · Index", "zh-CN": "数据 · 索引", "ja": "データ · 索引"},
        "links": {"github": ["https://github.com/badhope/API-Market"]},
    },
    "MCP-HUB": {
        "title": "MCP Hub",
        "desc": {
            "md": "A curated registry of 4,400+ MCP servers and resources",
            "zh-CN": "4,400+ MCP 服务器与资源精选登记册",
            "ja": "4,400+ の MCP サーバー＆リソース登録簿",
        },
        "tags": {"md": "AI · Index", "zh-CN": "AI · 索引", "ja": "AI · 索引"},
        "links": {"github": ["https://github.com/badhope/MCP-HUB"]},
    },
    "NetTools-Hub": {
        "title": "NetTools Hub",
        "desc": {
            "md": "An index of 120+ actively maintained networking tools",
            "zh-CN": "120+ 活跃维护的网络工具索引",
            "ja": "120+ のネットワークツール索引",
        },
        "tags": {"md": "Networking · Index", "zh-CN": "网络 · 索引", "ja": "ネットワーク · 索引"},
        "links": {"github": ["https://github.com/badhope/NetTools-Hub"]},
    },
    "ExamPrediction": {
        "title": "ExamPrediction",
        "desc": {
            "md": "CET-6 option-pattern research — measured hit rate 27–30% vs 25% random",
            "zh-CN": "CET-6 选项规律研究 —— 实测命中率 27–30% vs 随机 25%",
            "ja": "CET-6 選択肢パターン研究 — 実測 27〜30% vs ランダム 25%",
        },
        "tags": {"md": "Research · Education", "zh-CN": "研究 · 教育", "ja": "研究 · 教育"},
        "links": {"github": ["https://github.com/badhope/ExamPrediction"]},
    },
    "urban-pulse": {
        "title": "Urban Pulse",
        "desc": {
            "md": "An open urban-economy observatory — 10 Chinese cities, 16 years of data",
            "zh-CN": "开源城市经济观测站 —— 10 座中国城市 × 16 年数据",
            "ja": "オープンな都市経済観測所 — 中国 10 都市・16 年分のデータ",
        },
        "tags": {"md": "Data · Visualisation", "zh-CN": "数据 · 可视化", "ja": "データ · 可視化"},
        "links": {"github": ["https://github.com/badhope/urban-pulse"]},
    },
    "OnlineCode": {
        "title": "OnlineCode / DocForge",
        "desc": {
            "md": "An offline-first dev toolbox — 20 browser tools and multi-language notes",
            "zh-CN": "离线优先的开发者工具箱 —— 20 个浏览器工具 + 多语言笔记",
            "ja": "オフライン優先の開発者ツールボックス — ブラウザツール 20 種",
        },
        "tags": {"md": "Tools · Offline", "zh-CN": "工具 · 离线", "ja": "ツール · オフライン"},
        "links": {"github": ["https://github.com/badhope/OnlineCode"]},
    },
    "campushub": {
        "title": "CampusHub",
        "desc": {
            "md": "Self-hosted campus community platform — marketplace, lost and found, guides",
            "zh-CN": "自托管开源校园社区平台 —— 二手市集 / 失物招领 / 校园指南",
            "ja": "セルフホスト型キャンパスコミュニティ基盤",
        },
        "tags": {"md": "SaaS · Campus", "zh-CN": "SaaS · 校园", "ja": "SaaS · キャンパス"},
        "links": {
            "gitcode": "https://gitcode.com/badhope/campushub",
            "gitee": "https://gitee.com/badhope/campushub",
        },
    },
}

# --------------------------------------------------------------------------
# 开源足迹（2026-10-14 经 GitHub 搜索 API 实查：author:<user> type:pr）
# --------------------------------------------------------------------------
CONTRIB = {
    "own": {
        "gh_x33834": {
            "merged": [
                ("apache/airflow", "https://github.com/apache/airflow", ["73099"],
                 "Support Table objects in BigQueryHook.create_table"),
            ],
            "review": [
                ("chaitin/MonkeyCode", "https://github.com/chaitin/MonkeyCode", ["1298"],
                 "frontend auto-resize fix"),
                ("y1s11564/simona-desktop-app", "https://github.com/y1s11564/simona-desktop-app",
                 ["1", "2", "3", "4", "5", "6"], "upstream patch series"),
            ],
        },
        "gh_morningstar": {
            "merged": [
                ("ohmyzsh/ohmyzsh", "https://github.com/ohmyzsh/ohmyzsh", ["14006", "14021", "14027"],
                 "git locale · pipenv activation · aws stderr"),
                ("tldr-pages/tldr", "https://github.com/tldr-pages/tldr", ["23780"], "doctl pages"),
                ("collective/icalendar", "https://github.com/collective/icalendar", ["1731", "1750", "1751"],
                 "public exports · deprecations · TYPE_CHECKING"),
                ("nix-community/NUR", "https://github.com/nix-community/NUR", ["1220"],
                 "SSL errors treated as transient"),
                ("jaychouchannel/claude-tool-agent", "https://github.com/jaychouchannel/claude-tool-agent",
                 ["30", "31", "33", "34", "35"], "mention parsing · markdown safety"),
                ("Hydrooxzgen/EnderBridge", "https://github.com/Hydrooxzgen/EnderBridge", ["12"],
                 "docs: Message mod"),
                ("deepset-ai/haystack", "https://github.com/deepset-ai/haystack", ["13011"],
                 "docs: merge_super_component_pipelines"),
            ],
            "review": [
                ("ohmyzsh/ohmyzsh", "https://github.com/ohmyzsh/ohmyzsh",
                 ["14140", "14141", "14148", "14149"], "diagnose locale · vi-mode · extract · dirhistory"),
                ("funstory-ai/BabelDOC", "https://github.com/funstory-ai/BabelDOC", ["621", "623"],
                 "translator guards"),
                ("PDFMathTranslate/PDFMathTranslate", "https://github.com/PDFMathTranslate/PDFMathTranslate",
                 ["1202", "1203", "1206"], "qwen-mt · zhipu errors · line splitting"),
                ("getmoto/moto", "https://github.com/getmoto/moto", ["10287"], "EC2 MaxCount"),
            ],
        },
    },
    "shared": "shared",
}

GITHUB_ACCOUNTS_FOR_SHARED = [
    ("X33834", "https://github.com/X33834"),
    ("Morningstar202604", "https://github.com/Morningstar202604"),
]

# --------------------------------------------------------------------------
# 作品卡片图标（data/icons/ 内的文件名后缀；缺图即用通用方块）
# --------------------------------------------------------------------------
WORK_ICONS = {
    "xiaoman": "python", "shopcash": "typescript", "digilegacy": "typescript",
    "naiwa-pet": "electron", "spark": "rust", "workbench": "tauri",
    "sciflow": "python", "lingxi": "nodejs", "chushi-radar": "javascript",
    "awesome-ai-devkit": "openai", "awesome-skillkit": "anthropic",
    "agent-builder": "typescript", "CodePocket": "python", "zhike": "wechat",
    "vaultx": "rust", "bot4cj": "java", "mashang-python": "python",
    "scholarhub": "nodejs", "content-harbor": "openai", "GlobalEcom-AI": "react",
    "melee": "ollama", "lens": "vscode", "world-walker": "markdown",
    "KeBaiPay": "postgresql", "p2wlan": "go", "novel-engine": "huggingface",
    "DU": "javascript", "API-Market": "graphql", "MCP-HUB": "nodejs",
    "NetTools-Hub": "nginx", "ExamPrediction": "python", "urban-pulse": "javascript",
    "OnlineCode": "vscode", "campushub": "vuejs",
}

# --------------------------------------------------------------------------
# 五个账号 —— 同一套模板的五个落点
# --------------------------------------------------------------------------
ACCOUNTS = {
    "gh_x33834": {
        "platform": "github",
        "handle": "X33834",
        "home": "https://github.com/X33834",
        "home_display": "github.com/X33834",
        "repo_path": "X33834/X33834",
        "deploy_state": "needs-repo",
        "role": {
            "md": "Upstream OSS · tools and works",
            "zh-CN": "上游开源 · 工具与作品",
            "ja": "上流 OSS · ツールと作品",
        },
        "tagline": {
            "md": "Ship small, ship often.",
            "zh-CN": "小步快跑，持续交付。",
            "ja": "小さく作って、頻繁に出す。",
        },
        "about": {
            "md": "I build small tools that do one thing well, and send the fixes back upstream — merged into apache/airflow and friends. TypeScript and Python daily; Rust when it fits.",
            "zh-CN": "把想法做成能用的小工具，也把修好的补丁送回上游 —— 已合入 apache/airflow 等项目。日常 TypeScript / Python，合适的地方写 Rust。",
            "ja": "小さく使える道具を作り、直したパッチは上流へ返します（apache/airflow などにマージ済み）。日常は TypeScript / Python。",
        },
        "now": {
            "md": [
                "Polishing the ShopCash and Xiaoman product lines",
                "Small upstream patches — MonkeyCode #1298 in review",
                "Exploring local-first AI workflows",
            ],
            "zh-CN": [
                "打磨 ShopCash 与 Xiaoman 两条产品线",
                "给上游递小补丁 —— MonkeyCode #1298 评审中",
                "探索本地优先的 AI 工作流",
            ],
            "ja": [
                "ShopCash と Xiaoman の磨き込み",
                "上流への小さなパッチ（MonkeyCode #1298 レビュー中）",
                "ローカル優先の AI ワークフロー探究",
            ],
        },
        "contrib_graph": True,
        "skills": ["typescript", "python", "rust", "nodejs", "react", "docker", "git", "linux", "postgresql", "nginx"],
        "works": [
            "xiaoman", "shopcash", "digilegacy",
            "agent-builder", "workbench", "awesome-ai-devkit", "awesome-skillkit",
        ],
        "contrib": "own",
    },
    "gh_morningstar": {
        "platform": "github",
        "handle": "Morningstar202604",
        "home": "https://github.com/Morningstar202604",
        "home_display": "github.com/Morningstar202604",
        "repo_path": "Morningstar202604/Morningstar202604",
        "deploy_state": "needs-repo",
        "role": {
            "md": "Portfolio · long-horizon works",
            "zh-CN": "作品集 · 长期项目",
            "ja": "ポートフォリオ · 長期プロジェクト",
        },
        "tagline": {
            "md": "Code under the stars, ship with the dawn.",
            "zh-CN": "夜观星象，以代码作舟。",
            "ja": "星を観て、コードを舟に。",
        },
        "about": {
            "md": "Long-horizon projects live here — a novel-writing engine, a compliant payments intake, P2P networking. Engineering completeness first: docs before code, audits before merges. Patches already merged upstream at ohmyzsh, tldr, icalendar, NUR and more.",
            "zh-CN": "长期项目放在这里慢慢打磨：小说引擎、收单系统、P2P 组网。偏工程完整度 —— 文档先于代码，审计先于合并。已有一批补丁合入 ohmyzsh / tldr / icalendar / NUR 等上游项目。",
            "ja": "長期プロジェクトの拠点 — 小説エンジン、決済収単、P2P ネットワーキング。ドキュメント優先・監査優先で育てています。ohmyzsh・tldr・icalendar・NUR などにマージ実績あり。",
        },
        "now": {
            "md": [
                "Iterating the rule-based consistency audit in Novel Engine",
                "Reconciliation module for KeBaiPay",
                "A batch of upstream PRs in review — ohmyzsh, moto, PDFMathTranslate",
            ],
            "zh-CN": [
                "迭代 Novel Engine 的规则一致性审计",
                "KeBaiPay 渠道对账模块",
                "一批上游 PR 在评：ohmyzsh / moto / PDFMathTranslate",
            ],
            "ja": [
                "Novel Engine の一貫性監査を反復改良",
                "KeBaiPay の照合モジュール",
                "上流 PR をレビュー中 — ohmyzsh・moto・PDFMathTranslate",
            ],
        },
        "contrib_graph": True,
        "skills": ["python", "typescript", "go", "vitejs", "nixos", "docker", "postgresql", "redis", "huggingface", "ollama"],
        "works": [
            "novel-engine", "KeBaiPay", "p2wlan", "xiaoman",
            "shopcash", "sciflow", "spark",
        ],
        "contrib": "own",
    },
    "gh_badhope": {
        "platform": "github",
        "handle": "badhope",
        "home": "https://github.com/badhope",
        "home_display": "github.com/badhope",
        "repo_path": "badhope/badhope",
        "deploy_state": "exists",
        "deploy_protected": True,
        "role": {
            "md": "Profile · full-stack toolshop",
            "zh-CN": "个人主页 · 全栈工具馆",
            "ja": "プロフィール · ツール小屋",
        },
        "tagline": {
            "md": "A full-stack developer turning abstract ideas into working interfaces.",
            "zh-CN": "把抽象想法落地为可交互界面的全栈开发者。",
            "ja": "抽象的なアイデアを、動くインターフェースに落とし込む開発者。",
        },
        "about": {
            "md": "My GitHub home — tools, indexes and small software experiments, all in the open. I like offline-first, single-file things that just run; the craft is in the details.",
            "zh-CN": "这是我在 GitHub 的主页：工具、索引与小型软件实验都公开在这里。偏爱离线优先、单文件、拿起来就能跑的小东西 —— 精巧之处藏在细节里。",
            "ja": "GitHub の拠点 — ツール・索引・小さなソフトウェア実験を公開しています。オフライン優先・シングルファイルな道具が好きです。",
        },
        "now": {
            "md": [
                "Maintaining the API-Market and MCP-HUB indexes",
                "Advancing digilegacy and spark",
                "Documenting the 49-tool DU collection",
            ],
            "zh-CN": [
                "维护 API-Market / MCP-HUB 两个索引的数据",
                "digilegacy 与 spark 持续迭代",
                "整理 49 件术数工具集（DU）的文档",
            ],
            "ja": [
                "API-Market / MCP-HUB 索引のデータ整備",
                "digilegacy と spark の継続開発",
                "49 種のツール集（DU）のドキュメント整備",
            ],
        },
        "contrib_graph": True,
        "skills": ["javascript", "python", "react", "nodejs", "vuejs", "electron", "docker", "mysql", "nginx", "markdown"],
        "works": [
            "digilegacy", "spark", "agent-builder", "workbench",
            "sciflow", "DU", "API-Market", "MCP-HUB",
        ],
        "contrib": "shared",
    },
    "gitcode_badhope": {
        "platform": "gitcode",
        "handle": "badhope",
        "home": "https://gitcode.com/badhope",
        "home_display": "gitcode.com/badhope",
        "repo_path": "badhope/badhope",
        "deploy_state": "exists",
        "role": {
            "md": "Mobile dev · offline tools",
            "zh-CN": "移动端开发 · 离线工具",
            "ja": "モバイル開発 · オフラインツール",
        },
        "tagline": {
            "md": "Software that runs even when the cloud does not.",
            "zh-CN": "把软件做成离线也能跑的东西。",
            "ja": "オフラインでも動くソフトウェアを。",
        },
        "about": {
            "md": "The domestic mirror of my GitHub work, plus a mobile lab — an offline Python IDE, a cyberpunk learning terminal, a Cangjie robot framework.",
            "zh-CN": "GitHub 作品的国内镜像站 + 移动端实验场：离线 Python IDE、学习终端、仓颉机器人框架都在这里。",
            "ja": "GitHub 作品の中国ミラー＋モバイル実験場 — オフライン IDE・学習ターミナル・Cangjie ロボットフレームワーク。",
        },
        "now": {
            "md": [
                "Polishing the CodePocket offline IDE",
                "Demoing the bot4cj robot framework in Cangjie",
                "Archiving notes for the tool directory",
            ],
            "zh-CN": [
                "打磨 CodePocket 离线 IDE",
                "仓颉语言机器人框架 bot4cj 的演示",
                "把工具站的资料陆续归档",
            ],
            "ja": [
                "CodePocket オフライン IDE の磨き込み",
                "Cangjie 製ロボットフレームワーク bot4cj",
                "ツール資料のアーカイブ整理",
            ],
        },
        "skills": ["python", "dart", "kotlin", "java", "flutter", "wechat", "linux", "git", "markdown"],
        "works": [
            "zhike", "xiaoman", "workbench",
            "spark", "sciflow", "scholarhub", "bot4cj",
        ],
        "contrib": "shared",
    },
    "gitee_badhope": {
        "platform": "gitee",
        "handle": "badhope",
        "home": "https://gitee.com/badhope",
        "home_display": "gitee.com/badhope",
        "repo_path": "badhope/badhope",
        "deploy_state": "token-expired",
        "role": {
            "md": "Mirror · mini-programs",
            "zh-CN": "作品镜像 · 小程序",
            "ja": "ミラー · ミニアプリ",
        },
        "tagline": {
            "md": "A quiet mirror where the work also lives.",
            "zh-CN": "镜像站：作品另一处安放。",
            "ja": "作品のもうひとつの置き場。",
        },
        "about": {
            "md": "The Gitee mirror of selected works — synced from GitHub and GitCode, with room for mini-program experiments on the side.",
            "zh-CN": "Gitee 镜像站：同步 GitHub / GitCode 的部分作品，顺带做小程序方向的实验。",
            "ja": "Gitee ミラー — GitHub / GitCode の作品を同期し、ミニアプリの実験も。",
        },
        "now": {
            "md": [
                "Syncing the latest agent-builder and campushub",
                "Mini-program experiments",
            ],
            "zh-CN": [
                "同步 agent-builder / campushub 最新版",
                "小程序方向的小实验",
            ],
            "ja": [
                "agent-builder / campushub の同期",
                "ミニアプリの実験",
            ],
        },
        "skills": ["python", "wechat", "vuejs", "mysql", "nginx", "git", "markdown"],
        "works": ["agent-builder", "campushub", "workbench", "zhike"],
        "contrib": "shared",
    },
}

ACCOUNT_ORDER = ("gh_x33834", "gh_morningstar", "gh_badhope", "gitcode_badhope", "gitee_badhope")


def work_url(work_id, acct):
    """Resolve the best link for a work on the given account's platform."""
    links = WORKS[work_id]["links"]
    chain = [acct["platform"], "github", "gitcode", "gitee"]
    for plat in chain:
        cand = links.get(plat)
        if not cand:
            continue
        if isinstance(cand, str):
            return cand
        for url in cand:
            if "/%s/" % acct["handle"] in url:
                return url
        return cand[0]
    return acct["home"]
