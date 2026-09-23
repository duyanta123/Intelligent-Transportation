#!/usr/bin/env bash
# 把「自动化流程」推上远端 main，让之后的每一批提交都走门禁（项目主体不在本脚本范围内）。
#
# 脚本行为（全程不使用 --force）：
#   1. 先探测远端 main 现状，打印它的提交与「远端独有文件」
#   2. 远端 main 为空           → 骨架作为首个提交推上去
#   3. 远端 main 是骨架的祖先    → 直接快进推送（保留远端历史）
#   4. 远端 main 与骨架历史无关  → 把骨架接到远端提交之上，再快进推送
#                                （远端历史与远端独有文件都保留，同名文件以骨架版本为准）
#   5. 两边有共同历史、但远端不是祖先（远端已有别人的后续提交）
#                              → 拒绝推送，提示改走「开分支 + 提 PR」
#   6. 远端不可达              → 明确报错退出，不做任何改动
#
# 用法（Git Bash / WSL / Linux 均可，仓库根目录执行）：
#   bash scripts/setup_remote.sh --inspect    # 只看远端现状与将执行的动作，不推送、不改本地分支
#   bash scripts/setup_remote.sh              # 推送自动化骨架
#   bash scripts/setup_remote.sh --protect    # 只开启 main 分支保护（需首次 CI 已跑完）
#
# 可用环境变量覆盖：BOOTSTRAP_BRANCH / REMOTE / TARGET_BRANCH / REPO
# REMOTE 既可以是 remote 名（默认 origin），也可以直接给完整 URL
set -euo pipefail

BRANCH="${BOOTSTRAP_BRANCH:-chore/ci-bootstrap}"
REMOTE="${REMOTE:-origin}"
TARGET="${TARGET_BRANCH:-main}"
REPO="${REPO:-duyanta123/Intelligent-Transportation}"

show_usage() {
  echo "用法：bash scripts/setup_remote.sh [--inspect | --protect]"
  echo "  （不带参数）  推送自动化骨架到远端 $TARGET"
  echo "  --inspect     只查看远端现状与将要执行的动作，不推送、不改本地分支"
  echo "  --protect     只开启 $TARGET 分支保护（需首次 CI 已跑完）"
  echo "环境变量：BOOTSTRAP_BRANCH / REMOTE / TARGET_BRANCH / REPO"
}

fail() {
  echo "[FAIL] $*" >&2
  exit 1
}

MODE="push"
case "${1:-}" in
  ""|--push) MODE="push" ;;
  --inspect) MODE="inspect" ;;
  --protect) MODE="protect" ;;
  -h|--help) show_usage; exit 0 ;;
  *) show_usage >&2; fail "未知参数：$1（可用：--inspect / --protect / --help）" ;;
esac
if [ "$#" -gt 1 ]; then
  show_usage >&2
  fail "一次只能用一个参数（收到 $# 个）"
fi

cd "$(git rev-parse --show-toplevel)"

# 开分支保护是独立操作：不重跑推送流程，也不会因为推送状态而失败
if [ "$MODE" = "protect" ]; then
  if ! command -v gh >/dev/null 2>&1; then
    fail "未找到 gh 命令：先安装 GitHub CLI 并执行 gh auth login"
  fi
  [ -f scripts/remote-branch-protection.json ] || fail "缺少 scripts/remote-branch-protection.json"
  echo "[提示] 分支保护现已改用 GitHub 规则集（Rulesets）配置并生效，本模式仅作存档备用；"
  echo "       无意叠加 classic 保护时不要再执行（详见 docs/分工/06 第 5.3 节）。"
  echo "开启 $TARGET 分支保护（Require PR 1 人评审 + 必选检查「CI 全部通过」「密钥泄露扫描」）……"
  gh api -X PUT "repos/$REPO/branches/$TARGET/protection" \
    --input scripts/remote-branch-protection.json
  echo "分支保护已开启。"
  exit 0
fi

if ! git rev-parse --verify --quiet "$BRANCH" >/dev/null; then
  fail "本地找不到分支 $BRANCH，请先在准备机器上生成自动化骨架提交"
fi

case "$REMOTE" in
  *"://"*|*@*:*)
    REMOTE_URL="$REMOTE"
    USING_URL=1
    ;;
  *)
    if ! REMOTE_URL="$(git remote get-url "$REMOTE" 2>/dev/null)"; then
      fail "没有配置远端 $REMOTE，先执行：git remote add origin https://github.com/$REPO.git"
    fi
    USING_URL=0
    ;;
esac

echo "即将推送：$BRANCH → $TARGET（远端：$REMOTE_URL）"
git -c core.quotepath=false --no-pager log -1 --format='  提交：%h %s' "$BRANCH"
echo "  文件清单（应只有自动化相关内容，不含 backend/ frontend/ sql/ 等项目主体）："
while IFS= read -r path; do
  printf '    %s\n' "$path"
done < <(git -c core.quotepath=false --no-pager ls-tree -r --name-only "$BRANCH")

echo
echo "检查远端 $TARGET 是否已有提交……"
set +e
git ls-remote --exit-code --heads "$REMOTE_URL" "$TARGET" >/dev/null 2>&1
probe=$?
set -e

remote_head=""
remote_only_entries=()
remote_only_paths=()
both_differ_paths=()
action=""

case "$probe" in
  0)
    if ! git fetch --quiet "$REMOTE_URL" "$TARGET"; then
      fail "已探测到远端 $TARGET，但拉取失败（网络/凭据问题）：先解决连通性（或代理）再试"
    fi
    remote_head="$(git rev-parse --verify --quiet FETCH_HEAD || true)"
    [ -n "$remote_head" ] || fail "已探测到远端 $TARGET，但拉取后拿不到提交号"

    echo "远端 $TARGET 当前提交："
    git -c core.quotepath=false --no-pager log --format='    %h %an %s' -5 "$remote_head"

    # 用 -z 遍历，中文/空格路径不会被 core.quotepath 转义影响判断
    while IFS= read -r -d '' entry; do
      path="${entry#*$'\t'}"
      if git cat-file -e "$BRANCH:$path" 2>/dev/null; then
        if [ "$(git rev-parse "$BRANCH:$path")" != "$(git rev-parse "$remote_head:$path")" ]; then
          both_differ_paths+=("$path")
        fi
      else
        remote_only_entries+=("$entry")
        remote_only_paths+=("$path")
      fi
    done < <(git ls-tree -r -z "$remote_head")

    if [ "${#remote_only_paths[@]}" -gt 0 ]; then
      echo "  远端已有、骨架里没有的文件（推送后仍然保留）："
      for path in "${remote_only_paths[@]}"; do
        printf '    %s\n' "$path"
      done
    fi
    if [ "${#both_differ_paths[@]}" -gt 0 ]; then
      echo "  两边都有但内容不同的文件（将采用骨架版本，旧内容仍留在历史里）："
      for path in "${both_differ_paths[@]}"; do
        printf '    %s\n' "$path"
      done
    fi

    if git merge-base --is-ancestor "$remote_head" "$BRANCH"; then
      action="fast-forward"
    elif git merge-base "$remote_head" "$BRANCH" >/dev/null 2>&1; then
      fail "远端 $TARGET 与骨架有共同历史，但远端不是骨架的祖先（已有别人的后续提交）。直接推会变成非快进；此时按流程应改为「开分支 + 提 PR」，不要强制推送。"
    else
      action="graft"
    fi
    ;;
  2)
    echo "远端 $TARGET 为空，骨架将作为首个提交推送。"
    action="first-push"
    ;;
  *)
    fail "无法访问远端 $REMOTE_URL（网络/凭据问题，退出码 $probe）：先解决连通性（或代理）再推送。"
    ;;
esac

if [ "$MODE" = "inspect" ]; then
  echo
  case "$action" in
    fast-forward)
      echo "（--inspect：远端已是骨架的祖先，正式推送为快进推送）"
      ;;
    graft)
      echo "（--inspect：远端与骨架历史无关，正式推送会先把骨架接到远端 $TARGET 之上，再快进推送）"
      echo "（          远端历史与远端独有文件保留；两边同名的文件以骨架版本为准）"
      ;;
    first-push)
      echo "（--inspect：远端为空，正式推送会把骨架作为首个提交推上去）"
      ;;
  esac
  echo "（--inspect：只查看，未推送任何内容，也未改动本地分支）"
  exit 0
fi

if [ "$action" = "graft" ]; then
  echo "  骨架与远端历史无关，正在接到远端 $TARGET 之上（保留远端历史与独有文件）……"
  HAVE_RM=0
  if command -v rm >/dev/null 2>&1; then HAVE_RM=1; fi
  idx_file="$(git rev-parse --git-dir)/st-bootstrap-index.$$"
  if [ "$HAVE_RM" = "1" ]; then rm -f "$idx_file"; fi

  # 新树 = 骨架全部文件 + 远端独有文件（同名文件以骨架版本为准，保证不误删远端已有内容）
  GIT_INDEX_FILE="$idx_file" git read-tree "$BRANCH"
  if [ "${#remote_only_entries[@]}" -gt 0 ]; then
    for entry in "${remote_only_entries[@]}"; do
      path="${entry#*$'\t'}"
      mode="${entry%% *}"
      rest="${entry#* }"
      sha="${rest#* }"
      sha="${sha%%$'\t'*}"
      GIT_INDEX_FILE="$idx_file" git update-index --add --cacheinfo "$mode,$sha,$path"
    done
  fi
  tree="$(GIT_INDEX_FILE="$idx_file" git write-tree)"
  if [ "$HAVE_RM" = "1" ]; then rm -f "$idx_file"; fi

  message="$(git log -1 --format=%B "$BRANCH")"
  old_commit="$(git rev-parse "$BRANCH")"
  new_commit="$(git commit-tree "$tree" -p "$remote_head" -m "$message")"
  # 用 update-ref 而不是 branch -f：即使该分支正处于检出状态也能安全改写（树内容不变，工作区不受影响）
  git update-ref "refs/heads/$BRANCH" "$new_commit" "$old_commit"
  echo "  新提交：$(git -c core.quotepath=false --no-pager log -1 --format='%h %s' "$BRANCH")"
fi

if [ "$USING_URL" = "1" ]; then
  git push "$REMOTE_URL" "$BRANCH:$TARGET"
else
  git push "$REMOTE" "$BRANCH:$TARGET"
fi

echo
echo "推送完成。接下来："
echo "  1) 打开 https://github.com/$REPO/actions 看首次流水线是否全绿（骨架阶段后端/前端作业会显示 skipped，属预期）"
echo "  2) 跑完一次后执行：bash scripts/setup_remote.sh --protect"
echo "  3) 之后每批提交都走：开 feature 分支 → PR 到 main → CI 全绿 + 1 人评审 → 合并"