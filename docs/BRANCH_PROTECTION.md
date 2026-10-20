# 分支保护与推送流程

主页仓库的 `main` 可能启用分支保护，直接推送会被拒绝。本文记录实测到的规则与正确推送方式。

## 当前规则（badhope/badhope 实测 2026-10-20）

分支保护要求通过以下状态检查：

```
Required status check "Scan for secrets (gitleaks)" is expected.
```

直接 `git push origin main` 会被远端以 `protected branch hook declined` 拒绝。

因此 **`gitleaks.yml` 与 `.gitleaks.toml` 必须存在于仓库中**。它们是分支保护的一部分，
不是可清理的历史残留。`generate.py` 的 `pack()` 已把两者随包携带；删除会导致 main 无法推送。

## 正确流程

1. 推送功能分支：

   ```bash
   git checkout -b fix/whatever
   git push origin fix/whatever
   ```

2. 开 PR 到 `main`，让 gitleaks 在 PR 上跑（工作流订阅了 `pull_request`）。

3. 检查通过后合并。

## 各平台差异（实测）

| 平台 | main 保护 | 推送方式 |
|---|---|---|
| GitHub `badhope/badhope` | 有（gitleaks 必需检查） | 必须走 PR；直推被拒 |
| GitHub `X33834/X33834` | 无 | 可直接推 main |
| GitHub `Morningstar202604/...` | 无 | 可直接推 main |
| GitCode `badhope/badhope` | 无 | 直接推 main |
| Gitee `badhope/badhope` | 无 | 直接推 main |

## 凭据与权限边界

- 创建 PR 需要 token 具备 **Pull requests: write**。缺少该权限时
  `POST /repos/{owner}/{repo}/pulls` 返回 `Resource not accessible by personal access token`。
- 推送分支（`git push origin <branch>`）只需 `contents: write`。
- 补权限：给 classic PAT 勾选完整 `repo` 范围，或新建仅授予 `Pull requests: write` 的 fine-grained token。

## 关于旧的 lock/freeze 方案

早期尝试过「哈希 manifest + git tag + 冻结徽章 + PNG 快照」的内容锁定方案，已被
「分区动态刷新」取代。三个脚本保留在 `scripts/_deprecated/` 仅作参考，
**不参与任何线上流程**，也不应被打包进部署仓库。
