#!/bin/bash
# 履歴の中の座標を、~/座標の置き換え.txt の表で書き換える（作者だけが走らせる）。
#
# 使い方: scripts/座標の履歴/2-書き換える.sh [REPO] [表] [控え]
#   REPO 既定は今の repo の頂、表 既定は ~/座標の置き換え.txt、
#   控え 既定は ~/seed-書き換え前.bundle（本物の値を含む。repo の外。確かめた後に作者が消す）
#
# 注意: backup-before-filter の枝は filter-repo が他の枝と一緒に書き換えるので、
# 枝だけでは控えにならない（偽の repo で確かめた）。書き換える前の履歴は bundle に取る。
#
# この script は値を出さない。表を読んで、左辺ごとに残っているコミットの数だけ出す。
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="${1:-$(git -C "$HERE" rev-parse --show-toplevel)}"
TABLE="${2:-$HOME/座標の置き換え.txt}"
BUNDLE="${3:-$HOME/seed-書き換え前.bundle}"
ORIGIN_URL="${ORIGIN_URL:-git@github.com:aiseed-dev/seed.git}"

[ -s "$TABLE" ] || { echo "表が無い: $TABLE（先に 1-表を作る.py）"; exit 1; }
cd "$REPO"

# git-filter-repo を探す（seed の .venv か、PATH）
if [ -x "$REPO/.venv/bin/python" ] && "$REPO/.venv/bin/python" -c "import git_filter_repo" 2>/dev/null; then
  FILTER=("$REPO/.venv/bin/python" -m git_filter_repo)
elif [ -n "${FILTER_PY:-}" ] && "$FILTER_PY" -c "import git_filter_repo" 2>/dev/null; then
  FILTER=("$FILTER_PY" -m git_filter_repo)
elif command -v git-filter-repo >/dev/null; then
  FILTER=(git-filter-repo)
else
  echo "git-filter-repo が無い。入れる: cd $REPO && .venv/bin/pip install git-filter-repo"
  exit 1
fi

[ -z "$(git status --porcelain --untracked-files=no)" ] || { echo "作業中の変更がある。先にコミットするか片付ける。"; exit 1; }

if [ -e "$BUNDLE" ]; then
  echo "控えは既にある（作り直さない）: $BUNDLE"
else
  git bundle create "$BUNDLE" --all
  chmod 600 "$BUNDLE"
  echo "書き換える前の履歴の控え: $BUNDLE（戻すなら git clone \"$BUNDLE\"）"
fi
git bundle verify "$BUNDLE" >/dev/null 2>&1 || { echo "控えの bundle が壊れている: $BUNDLE"; exit 1; }

# 枝も作る（指す先の名前として。中身は書き換えられる）
if git rev-parse --verify -q refs/heads/backup-before-filter >/dev/null; then
  echo "backup-before-filter は既にある（作り直さない）"
else
  git branch backup-before-filter
  echo "backup-before-filter を作った"
fi

had_origin=0
git remote get-url origin >/dev/null 2>&1 && had_origin=1

# blob の中身と、コミットのメッセージの両方を同じ表で
"${FILTER[@]}" --replace-text "$TABLE" --replace-message "$TABLE" --force

# filter-repo は origin を外す
if [ "$had_origin" = 1 ] && ! git remote get-url origin >/dev/null 2>&1; then
  git remote add origin "$ORIGIN_URL"
  echo "origin を戻した: $ORIGIN_URL"
fi

# 確かめ: 表の左辺ごとに、まだ値が出てくるコミットの数（値は出さない）
echo "--- 確かめ（左辺ごとの残りのコミット数。全部 0 なら消えた。backup-before-filter の枝は数えない）"
refs=$(git for-each-ref --format='%(refname)' | grep -v '^refs/heads/backup-before-filter$' | grep -v '^refs/remotes/' || true)
n=0; bad=0
while IFS= read -r line; do
  [ -z "$line" ] && continue
  n=$((n+1))
  left="${line%%==>*}"
  if [[ "$left" == regex:* ]]; then
    # regex:(?<![\d.])<値>(?![\d]|\.\d) から値（エスケープ済み）を取り出す
    v="${left#"regex:(?<![\d.])"}"
    v="${v%"(?![\d]|\.\d)"}"
    ere="(^|[^0-9.])${v}([^0-9]|\$)"
  else
    ere="$(printf '%s' "$left" | sed 's/[.[\*^$()+?{}|]/\\&/g')"
  fi
  # shellcheck disable=SC2086
  c1=$(git log $refs --format=%H -G "$ere" --extended-regexp | wc -l)
  # shellcheck disable=SC2086
  c2=$(git log $refs --format=%H --extended-regexp --grep "$ere" | wc -l)
  echo "行 $n: 中身 ${c1} コミット、メッセージ ${c2} コミット"
  [ "$c1" = 0 ] && [ "$c2" = 0 ] || bad=1
done < "$TABLE"
if [ "$bad" = 0 ]; then echo "全部 0。消えた。"; else echo "0 でない行がある。表を作者が見直す。"; exit 3; fi
echo "次: 3-ハッシュを直す.py"
