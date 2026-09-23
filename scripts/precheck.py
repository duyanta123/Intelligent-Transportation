#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""本地一键自检：把远程 CI 门禁的四条命令在本地跑一遍，避免推上去才发现红叉。

用法（在仓库根目录、即 smart-traffic/ 下执行）：
    python scripts/precheck.py                # 全部检查（仓库卫生 + 后端 + 前端）
    python scripts/precheck.py --guard-only   # 只跑仓库卫生自检（秒级，适合每次提交前）
    python scripts/precheck.py --skip-build   # 跳过前端构建（省时间）

前置条件：MySQL80 与 Redis 服务已启动（pytest 要连独立测试库 smart_traffic_test）。
与 CI 的关系：`.github/workflows/ci.yml` 跑的 ruff / pytest / eslint / vitest / build / 仓库自检
与本脚本一致；本地通过 ≠ 必然通过 CI（CI 还要装依赖、跑 Linux 环境），但能挡掉绝大多数问题。
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TAIL_LINES = 8


def backend_python() -> str:
    for candidate in ("backend/venv/Scripts/python.exe", "backend/venv/bin/python"):
        path = REPO_ROOT / candidate
        if path.exists():
            return str(path)
    print("[WARN] 未找到 backend/venv，改用当前解释器；建议先按 AGENTS.md 第 4 节建虚拟环境")
    return sys.executable


def run_step(title: str, command: str, workdir: Path) -> bool:
    print(f"\n--- {title} ---")
    print(f"$ {command}   （{workdir.relative_to(REPO_ROOT) or '.'}）")
    started = time.time()
    proc = subprocess.run(command, cwd=workdir, shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
    elapsed = time.time() - started
    output = (proc.stdout or "") + (proc.stderr or "")
    lines = [line for line in output.splitlines() if line.strip()]
    for line in lines[-TAIL_LINES:]:
        print(f"    {line}")
    status = "通过" if proc.returncode == 0 else "失败"
    print(f"[{'PASS' if proc.returncode == 0 else 'FAIL'}] {title}：{status}（{elapsed:.1f}s）")
    return proc.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description="本地一键自检（CI 门禁的本地版）")
    parser.add_argument("--guard-only", action="store_true", help="只跑仓库卫生自检")
    parser.add_argument("--skip-tests", action="store_true", help="跳过 pytest 与 vitest")
    parser.add_argument("--skip-build", action="store_true", help="跳过前端构建")
    args = parser.parse_args()

    python = backend_python()
    backend_dir = REPO_ROOT / "backend"
    frontend_dir = REPO_ROOT / "frontend"

    plan: list[tuple[str, str, Path]] = [("仓库卫生与提交规范", f'"{sys.executable}" scripts/ci_check.py', REPO_ROOT)]
    if not args.guard_only:
        plan.append(("后端 ruff 静态检查", f'"{python}" -m ruff check .', backend_dir))
        if not args.skip_tests:
            plan.append(("后端 pytest", f'"{python}" -m pytest -q', backend_dir))
        plan.append(("前端 eslint", "npm run lint", frontend_dir))
        if not args.skip_tests:
            plan.append(("前端 vitest", "npm run test", frontend_dir))
        if not args.skip_build:
            plan.append(("前端构建", "npm run build", frontend_dir))

    print(f"仓库根：{REPO_ROOT}")
    print(f"后端解释器：{python}")
    print(f"检查项：{len(plan)} 个" + ("（仅仓库卫生）" if args.guard_only else ""))

    failed: list[str] = []
    started = time.time()
    for title, command, workdir in plan:
        if not run_step(title, command, workdir):
            failed.append(title)

    print("\n=== 自检结果 ===")
    for title, _, _ in plan:
        print(f"  {'失败' if title in failed else '通过'}  {title}")
    print(f"总耗时 {time.time() - started:.1f}s")
    if failed:
        print(f"\n未通过 {len(failed)} 项：{'、'.join(failed)}；修好后再推送，避免 PR 门禁变红")
        return 1
    print("\n全部通过，可以推送并开 PR")
    return 0


if __name__ == "__main__":
    sys.exit(main())
