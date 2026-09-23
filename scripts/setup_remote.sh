#!/usr/bin/env bash
# 首次把「自动化流程」推上远端，让之后的每一批提交都走门禁（项目主体不在本脚本范围内）。
#
# 用法（Git Bash / WSL / Linux 均可，仓库根目录执行）：
#   bash scripts/setup_remote.sh              # 只推送自动化骨架到远端 main
#   bash scripts/setup_remote.sh --protect    # 推送后再开启 main 分支保护（需首次 CI 已跑完）
#
# 可用环境变量覆盖：BOOTSTRAP_BRANCH / REMOTE / TARGET_BRANCH / REPO
set -euo pipefail

BRANCH="${BOOTSTRAP_BRANCH:-chore/ci-bootstrap}"
REMOTE="${REMOTE:-origin}"
TARGET="${TARGET_BRANCH:-main}"
REPO="${REPO:-duyanta123/Intelligent-Transportation}"

cd "$(git rev-parse --show-toplevel)"

if ! git rev-parse --verify --quiet "$BRANCH" >/dev/null; then
  echo "[FAIL] 本地找不到分支 $BRANCH，请先在准备机器上生成自动化骨架提交" >&2
  exit 1
fi

if ! git remote get-url "$REMOTE" >/dev/null 2>&1; then
  echo "[FAIL] 没有配置远端 $REMOTE，先执行：git remote add origin https://github.com/$REPO.git" >&2
  exit 1
fi

echo "即将推送：$BRANCH → $REMOTE/$TARGET"
git --no-pager log -1 --format='  提交：%h %s' "$BRANCH"
echo "  文件清单（应只有自动化相关内容，不含 backend/ frontend/ sql/ 等项目主体）："
git --no-pager ls-tree -r --name-only "$BRANCH" | sed 's/^/    /'

echo
echo "检查远端 $TARGET 是否已有提交……"
set +e
git ls-remote --exit-code --heads "$REMOTE" "$TARGET" >/dev/null 2>&1
probe=$?
set -e
case "$probe" in
  0)
    echo "[FAIL] 远端 $TARGET 已有提交：说明项目已在推进，此时按流程应改为「开分支 + 提 PR」。" >&2
    echo "       不要覆盖远端分支（本脚本从不使用 --force）。" >&2
    exit 1
    ;;
  2)
    echo "远端 $TARGET 为空，可以推送。"
    ;;
  *)
    echo "[FAIL] 无法访问远端 $REMOTE（网络/凭据问题，退出码 $probe）：先解决连通性（或代理）再推送。" >&2
    exit 1
    ;;
esac

git push -u "$REMOTE" "$BRANCH:$TARGET"

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
