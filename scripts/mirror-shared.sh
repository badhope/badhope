#!/usr/bin/env bash
# 把 github/badhope 的「共享层」同步到四个镜像仓库：
#   gitcode / gitee / github-x33834 / github-morningstar
#
# 共享层只包含**账号无关**的数据源、数据与脚本；README、profile.json 与
# 各账号专属资产（hero / 星图 / 作品卡）不跨账号复制，而是在目标仓库里按
# 目标 profile.json 原地重建，避免 GitHub 账号的图跑到 GitCode 页面上。
# 用法：bash mirror-shared.sh <gitcode|gitee|github-x33834|github-morningstar>
#   - 需要环境变量 TOKEN（对应平台令牌）
#   - WORKSPACE 默认为当前目录（GitHub Actions 的 checkout 根）
set -euo pipefail

PLATFORM="${1:?usage: mirror-shared.sh <gitcode|gitee>}"
case "$PLATFORM" in
  gitcode)            HOST="gitcode.com";  OWNER="badhope";           REPO="badhope";           USERNAME="oauth2" ;;
  gitee)              HOST="gitee.com";    OWNER="badhope";           REPO="badhope";           USERNAME="oauth2" ;;
  github-x33834)      HOST="github.com";   OWNER="X33834";            REPO="X33834";            USERNAME="x-access-token" ;;
  github-morningstar) HOST="github.com";   OWNER="Morningstar202604"; REPO="Morningstar202604"; USERNAME="x-access-token" ;;
  *) echo "unknown platform: $PLATFORM" >&2; exit 2 ;;
esac
SRC="${WORKSPACE:-$PWD}"
if ! SRC="$(cd "$SRC" && pwd)"; then
  echo "source workspace is not accessible" >&2
  exit 2
fi
[ -f "$SRC/profile.json" ] || { echo "source profile.json missing" >&2; exit 2; }
[ -x "$SRC/scripts/git-askpass.sh" ] || { echo "source askpass helper missing or not executable" >&2; exit 2; }

# 账号无关的共享层（绝不含 assets/ 与账号专属 profile.json）
# 清单只在这一处维护：mirror.yml / refresh.yml 不再覆盖，防止两处漂移回灌旧版。
SHARED_PATHS="build.py data/stats.json scripts tests Makefile .gitattributes .gitignore CHANGELOG.md LICENSE"

# 旧设计留在镜像里的文件；每次同步顺手清掉，避免旧数据/旧 CI 继续存在。
LEGACY_PATHS=".github/workflows/snake.yml .github/workflows/refresh.yml .gitee .gitcode .github/ISSUE_TEMPLATE .github/PULL_REQUEST_TEMPLATE.md CODE_OF_CONDUCT.md CONTRIBUTING.md SECURITY.md data/cards data/contrib data/extras.json data/icons data/linguist_colors.json data/works.json data/writing.json assets/png"

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
  export GIT_MIRROR_USERNAME="${GIT_MIRROR_USERNAME:-$USERNAME}"
  export GIT_ASKPASS="${SRC}/scripts/git-askpass.sh"
  export GIT_TERMINAL_PROMPT=0
  remote="https://${GIT_MIRROR_USERNAME:-$USERNAME}@${HOST}/${OWNER}/${REPO}.git"
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

# 清掉旧设计留下的数据、图标、平台 CI 与旧工作流
for p in $LEGACY_PATHS; do
  rm -rf "${target:?}/$p"
done

# 按目标账号原地重建 README 与全部 SVG（README 用目标仓库自己的 profile 与文案）
( cd "$target" && "$PYTHON_BIN" scripts/generate.py --here )

# 镜像端也要过一遍离线门禁，坏页面不允许推上去
( cd "$target" && "$PYTHON_BIN" scripts/doctor.py && "$PYTHON_BIN" -m unittest discover -s tests -q && "$PYTHON_BIN" scripts/verify.py )

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
