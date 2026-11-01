#!/usr/bin/env bash
# 把 github/badhope 的「共享层」同步到 GitCode 或 Gitee 的同名仓库。
#
# 共享层只包含**账号无关**的数据源、数据与脚本；README、profile.json 与
# 各账号专属资产（hero / PNG / 技能卡 / 贡献图）不跨账号复制，而是在目标仓库里
# 按目标 profile.json 原地重建，避免 GitHub 账号的图跑到 GitCode 页面上。
# 用法：bash mirror-shared.sh <gitcode|gitee>
#   - 需要环境变量 TOKEN（对应平台令牌）
#   - WORKSPACE 默认为当前目录（GitHub Actions 的 checkout 根）
set -euo pipefail

PLATFORM="${1:?usage: mirror-shared.sh <gitcode|gitee>}"
case "$PLATFORM" in
  gitcode) HOST="gitcode.com" ;;
  gitee)   HOST="gitee.com" ;;
  *) echo "unknown platform: $PLATFORM" >&2; exit 2 ;;
esac

OWNER="badhope"
REPO="badhope"
SRC="${WORKSPACE:-$PWD}"
if ! SRC="$(cd "$SRC" && pwd)"; then
  echo "source workspace is not accessible" >&2
  exit 2
fi
[ -f "$SRC/profile.json" ] || { echo "source profile.json missing" >&2; exit 2; }
[ -x "$SRC/scripts/git-askpass.sh" ] || { echo "source askpass helper missing or not executable" >&2; exit 2; }

# 账号无关的共享层（绝不含 assets/ 卡片、data/cards/、data/contrib/）
# 清单只在这一处维护：mirror.yml / refresh.yml 不再覆盖，防止两处漂移回灌旧版。
SHARED_PATHS="accounts.py kit data/stats.json data/works.json data/writing.json data/icons data/linguist_colors.json scripts tests docs ARCHITECTURE.md Makefile requirements-optional.txt .gitattributes .gitignore"

PYTHON_BIN="${PYTHON_BIN:-}"
if [ -z "$PYTHON_BIN" ]; then
  if command -v python3 >/dev/null 2>&1; then PYTHON_BIN=python3
  elif command -v python >/dev/null 2>&1; then PYTHON_BIN=python
  else echo "no python interpreter found" >&2; exit 2
  fi
fi

work="$(mktemp -d)"
cleanup() {
  rm -rf "$work"
  unset TOKEN GIT_ASKPASS GIT_TERMINAL_PROMPT
}
trap cleanup EXIT

# MIRROR_BASE 仅用于本地集成测试（file:// 裸仓库），生产留空即可
if [ -n "${MIRROR_BASE:-}" ]; then
  remote="${MIRROR_BASE}/${REPO}.git"
else
  : "${TOKEN:?TOKEN 未设置 —— 跳过 $PLATFORM 镜像}"
  export GIT_ASKPASS="${SRC}/scripts/git-askpass.sh"
  export GIT_TERMINAL_PROMPT=0
  remote="https://${GIT_MIRROR_USERNAME:-oauth2}@${HOST}/${OWNER}/${REPO}.git"
fi
git clone --quiet --depth 1 "$remote" "$work/target"
target="$work/target"

account="$("$PYTHON_BIN" -c 'import json,sys;print(json.load(open(sys.argv[1]))["account"])' "$target/profile.json")"

# 清掉目标仓库里的共享层，再整体拷贝源端的共享层
for p in $SHARED_PATHS; do
  rm -rf "${target:?}/$p"
done
for p in $SHARED_PATHS; do
  if [ -e "$SRC/$p" ]; then
    mkdir -p "$(dirname "$target/$p")"
    cp -a "$SRC/$p" "$target/$p"
  fi
done

# 目标仓库里可能残留别的账号的卡片/贡献图种子（历史同步遗留），一并清掉
for group in cards contrib; do
  if [ -d "$target/data/$group" ]; then
    find "$target/data/$group" -mindepth 1 -maxdepth 1 -type d ! -name "$account" -exec rm -rf {} +
  fi
done
if [ -d "$target/assets" ]; then
  find "$target/assets" -mindepth 1 -maxdepth 1 ! -name 'png' -exec rm -rf {} +
  if [ -d "$target/assets/png" ]; then
    find "$target/assets/png" -mindepth 1 -maxdepth 1 -type d ! -name "$account" -exec rm -rf {} +
    find "$target/assets/png" -mindepth 1 -maxdepth 1 -type f -delete
  fi
fi

# 按目标账号原地重建 README 与全部 SVG（README 用目标仓库自己的 profile 与文案）
( cd "$target" && "$PYTHON_BIN" scripts/generate.py --here )

cd "$target"
git add -A
# 必须在 add 之后判定：镜像端新增/删除文件同样是变更
if git diff --cached --quiet; then
  echo "$PLATFORM: 共享层无变化，跳过"
  exit 0
fi

git config user.name  "profile-kit"
git config user.email "profile-kit@users.noreply.github.com"
git commit -m "chore: sync shared layer from github/badhope"
git push --quiet origin HEAD:main
echo "$PLATFORM: 共享层已同步（README 已按 $account 重建）"
