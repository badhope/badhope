#!/usr/bin/env bash
# 把 github/badhope 的「共享层」同步到 GitCode 或 Gitee 的同名仓库。
#
# 只覆盖 SHARED_PATHS（数据源/数据/资产/脚本），保留对方自己的 README 与 profile.json。
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

: "${TOKEN:?TOKEN 未设置 —— 跳过 $PLATFORM 镜像}"
OWNER="${OWNER:-badhope}"
REPO="${REPO:-badhope}"
SRC="${WORKSPACE:-$PWD}"

SHARED_PATHS="${SHARED_PATHS:-accounts.py data assets scripts .gitignore}"
KEEP_PATHS="${KEEP_PATHS:-README.md README.zh-CN.md README.ja.md profile.json .github}"

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

remote="https://oauth2:${TOKEN}@${HOST}/${OWNER}/${REPO}.git"
git clone --quiet --depth 1 "$remote" "$work/target"
target="$work/target"

# 清掉目标仓库里的共享层，再整体拷贝源端的共享层
for p in $SHARED_PATHS; do
  rm -rf "${target:?}/$p"
done
for p in $SHARED_PATHS; do
  if [ -e "$SRC/$p" ]; then
    cp -a "$SRC/$p" "$target/$p"
  fi
done

cd "$target"
git add -A
# 同样必须在 add 之后判定：镜像端新增文件也是变更
if git diff --cached --quiet; then
  echo "$PLATFORM: 共享层无变化，跳过"
  exit 0
fi

git config user.name  "profile-kit"
git config user.email "profile-kit@users.noreply.github.com"
git commit -m "chore: sync shared layer from github/badhope"
git push --quiet origin HEAD:main
echo "$PLATFORM: 共享层已同步（README/profile.json 保持不变）"
