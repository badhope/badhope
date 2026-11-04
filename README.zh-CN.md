[English](README.md) | [中文](README.zh-CN.md) | [日本語](README.ja.md)

<p align="center">
  <img src="./assets/hero.svg" alt="badhope · github.com/badhope" width="100%" />
</p>

<p align="center">
  <img src="./assets/typing-zh-CN.svg" alt="把抽象想法落地为可交互界面的全栈开发者。" width="600" />
</p>

<p align="center"><sub>慢即是稳，稳即是快。</sub></p>

<table border="0">
<tr>
<td valign="top" width="58%">

### 关于

这里是我的 GitHub 主页，公开工具、索引与小型软件实验；当前重点是主页工具、AI Agent 和数据驱动的实用工具。

</td>
<td valign="top" width="42%">

### 近期

- 维护 API-Market / MCP-HUB 两个索引的数据
- digilegacy 与 spark 持续迭代
- 整理 49 件术数工具集（DU）的文档

</td>
</tr>
</table>

## 构建

主页资产编译器：用一份 Python 数据源生成 README 与 SVG 卡片，再镜像到 GitCode 与 Gitee。

**运行方式**

```bash
make gen       # rebuild README + every SVG from accounts.py
make verify    # offline gate: schema, asset refs, account isolation, idempotency
make release   # version / CHANGELOG / profile.json consistency
```

**保证**

- 渲染期不联网 —— 同一提交，同一字节
- 一条命令重建全部资产：<code>make gen</code>
- 离线门禁拦截过期或串号资产：<code>make verify</code>
- 版本号单一真源在 <code>kit/version.py</code>，由 <code>make release</code> 校验

**目录结构**

| Path | Purpose |
|---|---|
| `accounts.py` | single data source: accounts, copy, works catalogue |
| `kit/` | renderer package: textutil -> icons -> cards -> readme -> build |
| `data/*.json` | committed snapshots: stats, works, writing, extras |
| `scripts/` | refresh (only network component), verify, generate, release |
| `tests/` | stdlib unittest suite covering render, schema and gates |

## 工具箱

<p align="center">
  <img src="./assets/skills-zh-CN.svg" alt="工具箱" width="100%" />
</p>

## 精选作品

| 项目 | 星标 | 最近更新 |
| --- | --- | --- |
| [moneyhelper — 对话优先的个人理财 Agent —— 本地优先，LangGraph 编排](https://github.com/badhope/moneyhelper) | 92 | 2026-11-04 |
| [workbench — 本地优先的桌面工作台（Tauri 2 + React 19）](https://github.com/badhope/workbench) | 49 | 2026-11-04 |
| [spark — 本地优先的 AI 编程代理 —— 审批门禁与提示注入防护](https://github.com/badhope/spark) | 21 | 2026-11-04 |
| [world-walker — AI 驱动的文字互动小说引擎](https://github.com/badhope/world-walker) | 18 | 2026-11-04 |
| [sciflow — 本地优先的 AI 科研智能体工作台 —— 多 Agent 编排与记忆](https://github.com/badhope/sciflow) | 12 | 2026-11-04 |
| [DU — 纯客户端中文术数工具箱 —— 49 件工具](https://github.com/badhope/DU) | 11 | 2026-11-04 |

全部公开仓库： [github.com/badhope](https://github.com/badhope)

## 数据

<p align="center">
  <img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fapi.github.com%2Fusers%2Fbadhope&query=public_repos&style=flat&label=%E4%BB%93%E5%BA%93&labelColor=0E1630&color=D9B876" alt="仓库: badhope" />
  <img src="https://img.shields.io/github/stars/badhope?style=flat&labelColor=0E1630&color=D9B876" alt="累计 Star: badhope" />
  <img src="https://img.shields.io/github/followers/badhope?style=flat&labelColor=0E1630&color=D9B876" alt="关注者: badhope" />
</p>

<p align="center">
  <img src="./assets/cards/stats-cn.svg" alt="GitHub stats" width="49%" />
  <img src="./assets/cards/langs-cn.svg" alt="Top languages" width="49%" />
</p>

## 成就

<p align="center">
  <img src="./assets/snake-zh-CN.svg" alt="contribution snake" width="100%" />
</p>

<details>
<summary>开源足迹</summary>

补丁已合入 ohmyzsh · tldr · icalendar · NUR 等上游项目，明细见两个 GitHub 账号: [X33834](https://github.com/X33834) · [Morningstar202604](https://github.com/Morningstar202604)

</details>

## 活跃度

<p align="center">
  <img src="./assets/isocalendar-zh-CN.svg" alt="Isocalendar" width="100%" />
</p>

<p align="center">
  <img src="./assets/people-zh-CN.svg" alt="People" width="100%" />
</p>

## 置顶作品

<p align="center">
  <img src="./assets/cards/pin-1-cn.svg" alt="pinned work" width="32%" />
  <img src="./assets/cards/pin-2-cn.svg" alt="pinned work" width="32%" />
  <img src="./assets/cards/pin-3-cn.svg" alt="pinned work" width="32%" />
</p>

## 写作

| 日期 | 文章 |
|---|---|
| 2026-11-04 | [把 AI Agent 接进业务系统，我踩了3 个挺蠢的坑](https://blog.csdn.net/weixin_56622231/article/details/170051167) |
| 2026-10-18 | [Gemini 4 Argon 全面开放：谷歌憋了半年的旗舰大招，到底行不行？](https://blog.csdn.net/weixin_56622231/article/details/168251657) |
| 2026-10-16 | [MCP 落地一年，我总结了 6 个没人告诉你的工程真相](https://zhuanlan.zhihu.com/p/2094232145015453253) |
| 2026-10-16 | [本地优先 AI：当所有人都在上云，我为什么把 AI 装回自己电脑](https://zhuanlan.zhihu.com/p/2094233605513991576) |
| 2026-10-16 | [AI Agent 上线前必须过的 5 道关：一个真实项目的工程手记](https://zhuanlan.zhihu.com/p/2094218858789856836) |

<sub>同步发布 <img src="./assets/icons/si-csdn.svg" width="15" alt="CSDN" /> <a href="https://blog.csdn.net/weixin_56622231">CSDN</a> · <img src="./assets/icons/si-juejin.svg" width="15" alt="Juejin" /> <a href="https://juejin.cn/user/2350111542479753">Juejin</a> · <img src="./assets/icons/si-zhihu.svg" width="15" alt="Zhihu" /> <a href="https://www.zhihu.com/people/e7c851hd">Zhihu</a></sub>

## 在别处

> 同一身份，五处安放 —— 这五个账号同属一人，互为镜像。

| | 平台 | 账号 | 定位 |
|---|---|---|---|
| <img src="./assets/icons/si-github.svg" width="18" alt="GitHub" /> | GitHub | **[X33834](https://github.com/X33834)** | 上游开源 · 工具与作品 |
| <img src="./assets/icons/si-github.svg" width="18" alt="GitHub" /> | GitHub | **[Morningstar202604](https://github.com/Morningstar202604)** | 作品集 · 长期项目 |
| <img src="./assets/icons/si-github.svg" width="18" alt="GitHub" /> | GitHub | **[badhope](https://github.com/badhope)** | 个人主页 · 全栈工具馆 ◆ *你在这里* |
| <img src="./assets/icons/si-gitcode.svg" width="18" alt="GitCode" /> | GitCode | **[badhope](https://gitcode.com/badhope)** | 移动端开发 · 离线工具 |
| <img src="./assets/icons/si-gitee.svg" width="18" alt="Gitee" /> | Gitee | **[badhope](https://gitee.com/badhope)** | 作品镜像 · 小程序 |

<p align="center">
  <img src="./assets/footer.svg" alt="" width="100%" />
</p>

<p align="center"><sub>© badhope</sub></p>
