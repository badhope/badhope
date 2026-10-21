#!/usr/bin/env node
/**
 * 官方卡片种子渲染器（开发/CI 工具，不进生成器主链）。
 *
 * 用 stats-organization 的 github-readme-stats 渲染核心（MIT，github-readme-stats 血统）
 * 产出统计卡 / 语言卡 / 置顶卡 SVG，写入 data/cards/<key>/，由生成器以本地资产引用。
 * 生成器本身从不调用本脚本（保持 R5 离线可生成）；种子缺失时 README 自动降级为自绘卡。
 *
 * 用法：
 *   node scripts/render_cards.mjs                  # 渲染全部 GitHub 账号
 *   node scripts/render_cards.mjs gh_x33834        # 只渲染一个
 *   GITHUB_TOKEN=... node scripts/render_cards.mjs # 也可写入本机凭据库（自动读取）
 *
 * 凭据：按 账号专属环境变量 → 本机凭据库（~/.zcode/secrets/accounts.json）→ 通用环境变量
 * 顺序解析，只在内存中传递，不写入任何产物。
 */

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const CARD_LOCALE = { md: "en", "zh-CN": "cn", ja: "ja" };
const THEME = {
  title_color: "D9B876",
  icon_color: "F2DC9E",
  text_color: "F4F7FF",
  bg_color: "0E1630",
  border_color: "24356B",
  border_radius: 14,
  // 关闭入场动画：官方卡片默认 opacity:0 + 动画淡入，在不执行 CSS 动画的
  // 渲染器（部分 Markdown 预览、图片代理、静态截图）里会整卡空白。
  disable_animations: true,
};
const PIN_COUNT = 3;

const DUMP_PY = `
import json, sys
sys.path.insert(0, ${JSON.stringify(ROOT)})
import accounts as A
out = {"order": list(A.ACCOUNT_ORDER), "accounts": {}, "works": {}}
for k in A.ACCOUNT_ORDER:
    a = A.ACCOUNTS[k]
    out["accounts"][k] = {"handle": a["handle"], "platform": a["platform"], "works": list(a["works"])}
for wid, w in A.WORKS.items():
    links = w["links"]
    urls = links.get("github")
    if isinstance(urls, str):
        urls = [urls]
    out["works"][wid] = urls or []
print(json.dumps(out))
`;

function loadSite() {
  // GitHub ubuntu runner 只有 python3，(Windows 本地) 才是 python —— 依次探测
  const candidates = process.env.PYTHON ? [process.env.PYTHON] : ["python3", "python"];
  let lastErr = null;
  for (const py of candidates) {
    try {
      const raw = execFileSync(py, ["-c", DUMP_PY], { cwd: ROOT, encoding: "utf8" });
      return JSON.parse(raw);
    } catch (err) {
      lastErr = err;
    }
  }
  throw lastErr || new Error("no usable python interpreter found");
}

function resolveToken(handle) {
  const envNames = [`GH_${handle.toUpperCase()}_TOKEN`, "GITHUB_TOKEN", "GH_TOKEN"];
  for (const name of envNames) {
    const v = process.env[name];
    if (v && v.trim()) return v.trim();
  }
  try {
    const store = JSON.parse(
      fs.readFileSync(
        process.env.PROFILE_KIT_SECRETS ||
          path.join(os.homedir(), ".zcode", "secrets", "accounts.json"),
        "utf8"
      )
    );
    const accts = (store.platforms?.github?.accounts) || {};
    const rec = accts[handle] || {};
    if (rec.token && rec.token.trim()) return rec.token.trim();
    for (const v of Object.values(accts)) {
      if (v && v.default && v.token) return v.token.trim();
    }
  } catch {
    /* 无本机凭据库：继续降级 */
  }
  return null;
}

function pickPinnedRepos(acct, site) {
  const out = [];
  for (const wid of acct.works) {
    for (const url of site.works[wid] || []) {
      if (!url.includes(`/${acct.handle}/`)) continue;
      const repo = url.replace(/\/+$/, "").split("/").pop();
      if (repo && !out.includes(repo)) out.push(repo);
    }
    if (out.length >= PIN_COUNT) break;
  }
  return out.slice(0, PIN_COUNT);
}

function writeAtomic(file, content) {
  // 先写临时文件再 rename：避免进程被杀留下截断的 SVG
  const tmp = `${file}.tmp-${process.pid}`;
  fs.writeFileSync(tmp, content, "utf8");
  fs.renameSync(tmp, file);
}

async function main() {
  const only = process.argv[2];
  const site = loadSite();
  // 渲染核心在模块加载时读 process.env.PAT_1，函数参数里的 token 不参与鉴权。
  // 必须在 import 之前把各账号 token 注入 PAT_1/PAT_2/...，否则全部卡片渲染失败。
  const handles = site.order
    .map((k) => site.accounts[k])
    .filter((a) => a && a.platform === "github")
    .map((a) => a.handle);
  const tokens = [...new Set(handles.map(resolveToken).filter(Boolean))];
  if (!tokens.length) {
    console.error("无可用 GitHub token（GITHUB_TOKEN / GH_<HANDLE>_TOKEN / 本机凭据库）");
    process.exit(2);
  }
  tokens.forEach((t, i) => {
    process.env[`PAT_${i + 1}`] = t;
  });

  let core;
  try {
    core = await import("@stats-organization/github-readme-stats-core");
  } catch (err) {
    console.error(
      "缺少渲染核心：请先 `npm install`（@stats-organization/github-readme-stats-core）\n" + err.message
    );
    process.exit(2);
  }
  if (!core.getConfig().pats.length) {
    console.error("渲染核心未识别任何 token（check PAT_1）");
    process.exit(2);
  }

  let rendered = 0;
  let skipped = 0;
  let failedAccounts = [];
  for (const key of site.order) {
    const acct = site.accounts[key];
    if (!acct) continue;
    if (only && key !== only) continue;
    if (acct.platform !== "github") {
      console.log(`skip ${key}: 官方卡片仅用于 GitHub 账号`);
      continue;
    }
    const token = resolveToken(acct.handle);
    if (!token) {
      console.log(`skip ${key}: 无可用 token（GITHUB_TOKEN / 本机凭据库）`);
      skipped++;
      continue;
    }
    const outDir = path.join(ROOT, "data", "cards", key);
    fs.mkdirSync(outDir, { recursive: true });

    for (const [lang, locale] of Object.entries(CARD_LOCALE)) {
      const jobs = [
        ["stats", core.api, {
          username: acct.handle, show_icons: true, include_all_commits: true,
          card_width: 460, locale, ...THEME,
        }],
        ["langs", core.topLangs, {
          username: acct.handle, layout: "compact", langs_count: 6,
          card_width: 460, locale, ...THEME,
        }],
      ];
      for (const [kind, fn, params] of jobs) {
        try {
          const res = await fn(params, token);
          if (res?.status === "success" && res.content?.includes("<svg")) {
            writeAtomic(path.join(outDir, `${kind}-${locale}.svg`), res.content);
            rendered++;
          } else {
            console.warn(`  ${key}/${kind}-${locale}: ${res?.status || "empty"} — 保留旧文件`);
            skipped++;
          }
        } catch (err) {
          console.warn(`  ${key}/${kind}-${locale}: ${err.message} — 保留旧文件`);
          skipped++;
        }
      }
    }

    for (const [i, repo] of pickPinnedRepos(acct, site).entries()) {
      for (const [lang, locale] of Object.entries(CARD_LOCALE)) {
        try {
          const res = await core.pin(
            { username: acct.handle, repo, card_width: 320, locale, ...THEME },
            token
          );
          if (res?.status === "success" && res.content?.includes("<svg")) {
            writeAtomic(path.join(outDir, `pin-${i + 1}-${locale}.svg`), res.content);
            rendered++;
          } else {
            skipped++;
          }
        } catch (err) {
          console.warn(`  ${key}/pin-${i + 1}-${locale}: ${err.message}`);
          skipped++;
        }
      }
    }
    if (rendered === 0 && skipped > 0) failedAccounts.push(key);
    console.log(`rendered ${key}: ${acct.handle}`);
  }
  console.log(`\ncards: ${rendered} written, ${skipped} skipped`);
  // 一张都没渲染 = 硬失败；有渲染但仍有跳过 = 部分失败，也应以非 0 退出让 CI 暴露，
  // 否则线上会静默保留上一次的旧卡片，数字与 stats 长期分叉。
  if (rendered === 0) {
    console.error("渲染全部失败");
    process.exit(1);
  }
  if (skipped > 0) {
    // 部分失败：保留旧卡片并告警，但不阻断整条流水线。
    // 单张卡偶发限流不该让整个 refresh 失败；全量失败（上面）才是硬错误。
    console.warn(`::warning::部分卡片未渲染（${skipped} 张），已保留旧图`);
    if (failedAccounts.length) {
      console.warn(`::warning::受影响账号：${failedAccounts.join(", ")}`);
    }
  }
  process.exit(0);
}

main().catch((err) => {
  console.error("FATAL", err);
  process.exit(1);
});
