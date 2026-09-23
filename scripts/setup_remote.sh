#!/usr/bin/env bash
# 把「自动化流程」推上远端 main，让之后的每一批提交都走门禁（项目主体不在本脚本范围内）。
#
# 脚本行为（全程不使用 --force）：
#   1. 先探测远端 main 现状，打印它的提交与"远端独有文件"（例如建仓时的测试提交留下的 README）
#   2. 远端 main 为空     → 骨架作为首个提交推上去
#   3. 远端 main 已有提交 → 把骨架接到它上面（快进推送，保留远端历史）
#   4. 远端 main 上已有别人的后续提交（非快进）→ 直接失败，提示改走「开分支 + 提 PR」
#   5. 远端不可达         → 明确报错退出，不做任何改动
#
# 用法（Git Bash / WSL / Linux 均可，仓库根目录执行）：
#   bash scripts/setup_remote.sh --inspect    # 只看远端现状，不推送
#   bash scripts/setup_remote.sh              # 推送自动化骨架
#   bash scripts/setup_remote.sh --protect    # 推送后开启 main 分支保护（需首次 CI 已跑完）
#
# 可用环境变量覆盖：BOOTSTRAP_BRANCH / REMOTE / TARGET_BRANCH / REPO
# REMOTE 既可以是 remote 名（默认 origin），也可以直接给完整 URL
set -euo pipefail

BRANCH="${BOOTSTRAP_BRANCH:-chore/ci-bootstrap}"
REMOTE="${REMOTE:-origin}"
TARGET="${TARGET_BRANCH:-main}"
REPO="${REPO:-duyanta123/Intelligent-Transportation}"
INSPECT=0
if [ "${1:-}" = "--inspect" ]; then INSPECT=1; fi
# 精简环境可能没有 rm（例如受限沙箱），有才清理临时索引文件
HAVE_RM=0
if command -v rm >/dev/null 2>&1; then HAVE_RM=1; fi

cd "$(git rev-parse --show-toplevel)"

if ! git rev-parse --verify --quiet "$BRANCH" >/dev/null; then
  echo "[FAIL] 本地找不到分支 $BRANCH，请先在准备机器上生成自动化骨架提交" >&2
  exit 1
fi

case "$REMOTE" in
  *"://"*|*@*:*)
    REMOTE_URL="$REMOTE"
    USING_URL=1
    ;;
  *)
    if ! REMOTE_URL="$(git remote get-url "$REMOTE" 2>/dev/null)"; then
      echo "[FAIL] 没有配置远端 $REMOTE，先执行：git remote add origin https://github.com/$REPO.git" >&2
      exit 1
    fi
    USING_URL=0
    ;;
esac

echo "即将推送：$BRANCH → $TARGET（远端：$REMOTE_URL）"
git --no-pager log -1 --format='  提交：%h %s' "$BRANCH"
echo "  文件清单（应只有自动化相关内容，不含 backend/ frontend/ sql/ 等项目主体）："
git --no-pager ls-tree -r --name-only "$BRANCH"

echo
echo "检查远端 $TARGET 是否已有提交……"
set +e
git ls-remote --exit-code --heads "$REMOTE_URL" "$TARGET" >/dev/null 2>&1
probe=$?
set -e
case "$probe" in
  0)
    git fetch --quiet "$REMOTE_URL" "$TARGET"
    remote_head="$(git rev-parse FETCH_HEAD)"
    echo "远端 $TARGET 当前提交："
    git --no-pager log --format='    %h %an %s' -5 "$remote_head"

    remote_only=""
    both_differ=""
    while IFS= read -r path; do
      [ -n "$path" ] || continue
      if git cat-file -e "$BRANCH:$path" 2>/dev/null; then
        if [ "$(git rev-parse "$BRANCH:$path")" != "$(git rev-parse "$remote_head:$path")" ]; then
          both_differ="${both_differ}${path}"$'\n'
        fi
      else
        remote_only="${remote_only}${path}"$'\n'
      fi
    done < <(git ls-tree -r --name-only "$remote_head")

    if [ -n "$remote_only" ]; then
      echo "  远端已有、骨架里没有的文件（推送后仍然保留）："
      while IFS= read -r path; do
        [ -n "$path" ] && echo "    $path"
      done <<< "$remote_only"
    fi
    if [ -n "$both_differ" ]; then
      echo "  两边都有但内容不同的文件（将采用骨架版本，旧内容仍留在历史里）："
      while IFS= read -r path; do
        [ -n "$path" ] && echo "    $path"
      done <<< "$both_differ"
    fi

    if git merge-base --is-ancestor "$remote_head" "$BRANCH"; then
      echo "  骨架已包含远端提交，本次为快进推送。"
    elif [ "$(git rev-list --count "$BRANCH")" = "1" ]; then
      # 骨架是"根提交"（与远端历史无关）：改成挂在远端提交之下，从而可以快进推送、不覆盖历史
      if [ "$INSPECT" = "1" ]; then
        echo "  骨架是独立根提交，推送时会先接到远端 $TARGET 之上（保留远端历史），再快进推送。"
      else
        echo "  骨架是独立根提交，正在接到远端 $TARGET 之上（保留远端历史）……"
        # 新树 = 骨架的 12 个文件 + 远端独有文件（同名文件以骨架版本为准），保证不误删远端已有内容
        idx_file="$(git rev-parse --git-dir)/st-bootstrap-index.$$"
        if [ "$HAVE_RM" = "1" ]; then rm -f "$idx_file"; fi
        GIT_INDEX_FILE="$idx_file" git read-tree "$BRANCH"
        while IFS= read -r -d '' entry; do
          path="${entry#*$'\t'}"
          if ! git cat-file -e "$BRANCH:$path" 2>/dev/null; then
            mode="${entry%% *}"
            rest="${entry#* }"
            sha="${rest#* }"
            sha="${sha%%$'\t'*}"
            GIT_INDEX_FILE="$idx_file" git update-index --add --cacheinfo "$mode,$sha,$path"
          fi
        done < <(git ls-tree -r -z "$remote_head")
        tree="$(GIT_INDEX_FILE="$idx_file" git write-tree)"
        if [ "$HAVE_RM" = "1" ]; then rm -f "$idx_file"; fi
        message="$(git log -1 --format=%B "$BRANCH")"
        old_commit="$(git rev-parse "$BRANCH")"
        new_commit="$(git commit-tree "$tree" -p "$remote_head" -m "$message")"
        # 用 update-ref 而不是 branch -f：即使该分支正处于检出状态也能安全改写（树内容不变，工作区不受影响）
        git update-ref "refs/heads/$BRANCH" "$new_commit" "$old_commit"
        echo "  新提交：$(git --no-pager log -1 --format='%h %s' "$BRANCH")"
      fi
    else
      echo "[FAIL] 远端 $TARGET 上有骨架之外的后续提交，直接推会变成非快进。" >&2
      echo "       此时按流程应改为「开分支 + 提 PR」，不要强制推送。" >&2
      exit 1
    fi
    ;;
  2)
    echo "远端 $TARGET 为空，骨架将作为首个提交推送。"
    ;;
  *)
    echo "[FAIL] 无法访问远端 $REMOTE_URL（网络/凭据问题，退出码 $probe）：先解决连通性（或代理）再推送。" >&2
    exit 1
    ;;
esac

if [ "${1:-}" = "--inspect" ]; then
  echo
  echo "（--inspect：只查看，未推送任何内容）"
  exit 0
fi

if [ "$USING_URL" = "1" ]; then
  git push "$REMOTE_URL" "$BRANCH:$TARGET"
else
  git push -u "$REMOTE" "$BRANCH:$TARGET"
fi

echo
echo "推送完成。接下来："
echo "  1) 打开 https://github.com/$REPO/actions 看首次流水线是否全绿（骨架阶段后端/前端作业会显示 skipped，属预期）"
echo "  2) 跑完一次后执行：bash scripts/setup_remote.sh --protect"
echo "  3) 之后每批提交都走：开 feature 分支 → PR 到 main → CI 全绿 + 1 人评审 → 合并"

if [[ "${1:-}" == "--protect" ]]; then
  echo
  echo "开启 main 分支保护（Require PR 1 人评审 + 必选检查「CI 全部通过」）……"
  gh api -X PUT "repos/$REPO/branches/$TARGET/protection" \
    --input scripts/remote-branch-protection.json
  echo "分支保护已开启。"
fi
