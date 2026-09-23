#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""仓库卫生与提交规范自检：本地一键执行，GitHub Actions 复用同一套规则。

用法（在仓库根目录、即 smart-traffic/ 下执行）：
    python scripts/ci_check.py                     # 全量扫描 + 校验最近一次提交信息
    python scripts/ci_check.py --base origin/main  # 全量扫描 + 校验 origin/main..HEAD 的提交信息
    python scripts/ci_check.py --skip-commits      # 只做文件级检查

规则出处：AGENTS.md 第 5/6/8 节 + docs/分工/00-分工总览.md 第 6.5 节「每批必过门槛」。
CI 侧由 .github/workflows/ci.yml 的 repo-guard 作业用相同参数调用，保证本地与远端口径一致。
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MAX_FILE_MB = 5.0
MAX_SCAN_BYTES = 2 * 1024 * 1024

# 禁止入库的路径（相对仓库根的 POSIX 风格路径）
FORBIDDEN_PATHS: list[tuple[str, str]] = [
    (r"(^|/)\.env$", "真实 .env 含密钥，只提交 .env.example"),
    (r"^backend/venv/", "Python 虚拟环境 venv/ 不入库"),
    (r"(^|/)node_modules/", "node_modules/ 不入库"),
    (r"^frontend/dist/", "前端构建产物 dist/ 不入库"),
    (r"^logs/", "运行日志不入库"),
    (r"^backend/uploads/(?!\.gitkeep$)", "上传图片目录不入库（仅保留 .gitkeep 占位）"),
    (r"\.onnx$", "模型权重不入库（HyperLPR3 首次运行自动下载）"),
    (r"(^|/)\.hyperlpr3/", "模型缓存 .hyperlpr3/ 不入库"),
    (r"(^|/)__pycache__/|\.pyc$", "Python 字节码不入库"),
    (r"(^|/)\.pytest_cache/|(^|/)\.ruff_cache/", "工具缓存目录不入库"),
]

# 高置信度密钥特征：任意文件命中即失败
SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("AWS Access Key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("GitHub 令牌", re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}")),
    ("OpenAI 风格密钥", re.compile(r"\bsk-[A-Za-z0-9_\-]{24,}")),
    ("Slack 令牌", re.compile(r"xox[baprs]-[A-Za-z0-9\-]{10,}")),
    ("私钥内容", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]

# 赋值型密钥：代码/脚本里写死即失败；文档与模板属示例性质，不在此列
ASSIGNMENT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("JWT_SECRET 被写死", re.compile(r"JWT_SECRET\s*[:=]\s*[\"']?([A-Za-z0-9+/=_\-]{16,})")),
    ("DB_PASSWORD 被写死", re.compile(r"DB_PASSWORD\s*[:=]\s*[\"']?([^\s\"'#]{4,})")),
]
ASSIGNMENT_SKIP_SUFFIXES = (".md", ".env.example")
PLACEHOLDER_HINTS = (
    "your", "change", "example", "placeholder", "todo", "xxx", "***", "<", ">",
    "示例", "必填", "密码", "待填", "请填", "dev-", "test", "ci-", "root", "123456", "$",
)

# 提交信息：type(scope): 简体中文描述（AGENTS.md 第 5 节）
COMMIT_RE = re.compile(r"^(feat|fix|docs|test|chore|refactor|style|perf|build|ci|revert)(\([^)]+\))?: \S")
COMMIT_SKIP_PREFIXES = ("Merge ", 'Revert "', "fixup!", "squash!", "Initial commit")

# 与 .env.example 对账时忽略的字段（仅测试期使用的开关）
ENV_IGNORED_KEYS = {"TESTING"}

# --self-test 用的样本：证明规则能抓到违规，也不会误伤正常写法
SELF_TEST_BAD_PATHS = [
    "backend/.env",
    "frontend/.env",
    "backend/venv/Lib/site-packages/x.py",
    "frontend/node_modules/vue/index.js",
    "frontend/dist/index.html",
    "logs/app.log",
    "backend/uploads/entry.jpg",
    "backend/app/models/lpr.onnx",
    ".hyperlpr3/model.bin",
    "backend/app/__pycache__/main.cpython-313.pyc",
    "backend/.ruff_cache/0.16.8/cache",
]
SELF_TEST_GOOD_PATHS = [
    "backend/.env.example",
    "backend/uploads/.gitkeep",
    "frontend/src/main.ts",
    "scripts/ci_check.py",
    "docs/分工/00-分工总览.md",
]
# 违规样本用字符串拼接构造：既保留"必须被抓到"的样例，又不会让检查脚本自己被扫成硬编码密钥
SELF_TEST_BAD_SECRETS = [
    'aws_key = "AKIA' + "IOSFODNN7EXAMPLE" + '"',
    'token = "ghp_' + "0123456789abcdefghijklmnopqrstuvwxyz" + '"',
    "JWT_SECRET=" + "8f3d9a2c1b7e4f60a5d3c9b1e7f2a486",
    "DB_PASSWORD=" + "Sup3rPwd123",
]
SELF_TEST_GOOD_SECRETS = [
    "JWT_SECRET=",
    "DB_PASSWORD=            # 必填，提示用户填写，勿提交真实值",
    'JWT_SECRET="dev-secret-please-change"',
    "DB_PASSWORD=your_password_here",
    "# 测试账号密码均为 123456（种子数据，非密钥）",
]
SELF_TEST_BAD_COMMITS = ["更新代码", "fix bug", "feat 新增接口"]
SELF_TEST_GOOD_COMMITS = [
    "feat(停车): 出场结算调用计费纯函数",
    "fix(违章): 车牌格式校验漏新能源 8 位",
    "chore: 脚手架与依赖锁定",
    "docs(分工): 更新协作文档",
    "test(大屏): 缓存命中与降级用例",
]


def git(*args: str) -> str:
    """执行 git 命令并返回标准输出（UTF-8 解码，避免中文乱码）。"""
    proc = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        print(f"[FAIL] git {' '.join(args)} 执行失败：{proc.stderr.strip()}")
        sys.exit(2)
    return proc.stdout


def tracked_files() -> list[str]:
    return [path for path in git("ls-files", "-z").split("\0") if path]


def read_bytes(rel_path: str) -> bytes:
    try:
        return (REPO_ROOT / rel_path).read_bytes()
    except OSError:
        return b""


def is_binary(data: bytes) -> bool:
    return b"\0" in data[:8000]


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def check_forbidden_paths(files: list[str], errors: list[str]) -> None:
    section("禁止入库的文件路径")
    hits = 0
    for rel_path in files:
        for pattern, reason in FORBIDDEN_PATHS:
            if re.search(pattern, rel_path):
                errors.append(f"{rel_path}：{reason}")
                hits += 1
                break
    print(f"[PASS] {len(files)} 个已跟踪文件，无禁止入库路径" if hits == 0 else f"[FAIL] 命中 {hits} 个禁止入库文件")


def check_large_files(files: list[str], max_mb: float, errors: list[str]) -> None:
    section(f"单文件体积（上限 {max_mb:g} MB）")
    limit = max_mb * 1024 * 1024
    hits = 0
    for rel_path in files:
        size = len(read_bytes(rel_path))
        if size > limit:
            errors.append(f"{rel_path}：{size / 1024 / 1024:.1f} MB，超过 {max_mb:g} MB（大文件请走外部存储）")
            hits += 1
    print("[PASS] 无超大文件" if hits == 0 else f"[FAIL] 命中 {hits} 个超大文件")


def check_secrets(files: list[str], errors: list[str]) -> None:
    section("密钥与口令硬编码扫描")
    hits = 0
    for rel_path in files:
        data = read_bytes(rel_path)
        if not data or len(data) > MAX_SCAN_BYTES or is_binary(data):
            continue
        text = data.decode("utf-8", errors="replace")
        skip_assignment = rel_path.endswith(ASSIGNMENT_SKIP_SUFFIXES)
        for lineno, line in enumerate(text.splitlines(), start=1):
            for label, pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    errors.append(f"{rel_path}:{lineno}：疑似 {label}")
                    hits += 1
            if skip_assignment:
                continue
            for label, pattern in ASSIGNMENT_PATTERNS:
                match = pattern.search(line)
                if not match:
                    continue
                value = match.group(1).lower()
                if any(hint in value for hint in PLACEHOLDER_HINTS):
                    continue
                errors.append(f"{rel_path}:{lineno}：{label}（请改为从 .env 读取）")
                hits += 1
    print("[PASS] 未发现硬编码密钥/口令" if hits == 0 else f"[FAIL] 命中 {hits} 处疑似硬编码密钥")


def check_bat_files(files: list[str], errors: list[str], warnings: list[str]) -> None:
    section(".bat 脚本编码（CRLF + UTF-8 无 BOM + chcp 65001）")
    bats = [path for path in files if path.lower().endswith(".bat")]
    if not bats:
        print("[INFO] 仓库内没有 .bat 脚本")
        return
    if not bat_eol_pinned():
        errors.append(".gitattributes 缺少 `*.bat text eol=crlf`：.bat 的行尾必须由 Git 强制钉住，否则换个平台取出来就是 LF")
    bad = 0
    for rel_path in bats:
        data = read_bytes(rel_path)
        problems: list[str] = []
        if data.startswith(b"\xef\xbb\xbf"):
            problems.append("含 UTF-8 BOM（cmd 会把首行 @echo off 读成乱码）")
        if re.search(rb"(?<!\r)\n", data):
            problems.append("存在 LF 行尾（Windows 下必须是 CRLF）")
        if b"\r\r\n" in data:
            problems.append("存在 CR CR LF（重复回车，多由行尾工具叠加转换造成，请重写为 CRLF）")
        if b"chcp 65001" not in data.lower():
            warnings.append(f"{rel_path}：建议第二行加 chcp 65001 >nul 以正常显示中文")
        if problems:
            errors.append(f"{rel_path}：{'；'.join(problems)}")
            bad += 1
    print(f"[PASS] {len(bats)} 个 .bat 脚本编码合规" if bad == 0 else f"[FAIL] {bad} 个 .bat 脚本编码不合规")


def bat_eol_pinned() -> bool:
    attributes = REPO_ROOT / ".gitattributes"
    if not attributes.exists():
        return False
    text = attributes.read_text(encoding="utf-8", errors="replace")
    return re.search(r"^\s*\*\.bat\s+.*\beol=crlf\b", text, re.M) is not None


def check_env_contract(errors: list[str], warnings: list[str]) -> None:
    section("配置项与 .env.example 对账")
    checks: list[tuple[str, set[str], str, set[str]]] = []

    config_py = REPO_ROOT / "backend/app/core/config.py"
    backend_example = REPO_ROOT / "backend/.env.example"
    if config_py.exists() and backend_example.exists():
        declared = set(re.findall(r"^\s{4}([A-Z][A-Z0-9_]*)\s*:", config_py.read_text(encoding="utf-8"), re.M))
        checks.append(("backend", declared, "backend/.env.example", read_env_keys(backend_example)))

    frontend_dir = REPO_ROOT / "frontend"
    frontend_example = frontend_dir / ".env.example"
    if frontend_example.exists():
        used: set[str] = set()
        for path in (frontend_dir / "src").rglob("*"):
            if path.suffix in {".ts", ".vue", ".js"}:
                used |= set(re.findall(r"import\.meta\.env\.([A-Z0-9_]+)", path.read_text(encoding="utf-8", errors="replace")))
        checks.append(("frontend", used, "frontend/.env.example", read_env_keys(frontend_example)))

    if not checks:
        print("[INFO] 未找到 .env.example，跳过")
        return
    for scope, declared, example_name, example_keys in checks:
        missing = declared - example_keys - ENV_IGNORED_KEYS
        extra = example_keys - declared
        for key in sorted(missing):
            errors.append(f"{scope} 配置项 {key} 已定义但未写入 {example_name}（新人照模板配置会漏项）")
        for key in sorted(extra):
            warnings.append(f"{example_name} 中的 {key} 在代码里找不到引用，确认是否已废弃")
        print(f"[PASS] {scope}：{len(declared)} 个配置项与 {example_name} 一致" if not missing else f"[FAIL] {scope}：{len(missing)} 个配置项未写入模板")


def read_env_keys(path: Path) -> set[str]:
    keys: set[str] = set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        keys.add(stripped.split("=", 1)[0].strip())
    return keys


def self_test() -> int:
    """校验规则本身：违规样本必须被拦下，正常写法必须放行（防止检查形同虚设）。"""
    section("自检规则自测")

    def path_hit(rel_path: str) -> bool:
        return any(re.search(pattern, rel_path) for pattern, _ in FORBIDDEN_PATHS)

    def secret_hit(line: str, rel_path: str) -> bool:
        if any(pattern.search(line) for _, pattern in SECRET_PATTERNS):
            return True
        if rel_path.endswith(ASSIGNMENT_SKIP_SUFFIXES):
            return False
        for _, pattern in ASSIGNMENT_PATTERNS:
            match = pattern.search(line)
            if match and not any(hint in match.group(1).lower() for hint in PLACEHOLDER_HINTS):
                return True
        return False

    problems: list[str] = []
    for rel_path in SELF_TEST_BAD_PATHS:
        if not path_hit(rel_path):
            problems.append(f"违规路径未被拦截：{rel_path}")
    for rel_path in SELF_TEST_GOOD_PATHS:
        if path_hit(rel_path):
            problems.append(f"正常路径被误判：{rel_path}")
    for line in SELF_TEST_BAD_SECRETS:
        if not secret_hit(line, "backend/app/config_probe.py"):
            problems.append(f"硬编码密钥未被拦截：{line}")
    for line in SELF_TEST_GOOD_SECRETS:
        if secret_hit(line, "backend/app/config_probe.py"):
            problems.append(f"正常写法被误判：{line}")
    for subject in SELF_TEST_BAD_COMMITS:
        if COMMIT_RE.match(subject):
            problems.append(f"违规提交信息未被拦截：{subject}")
    for subject in SELF_TEST_GOOD_COMMITS:
        if not COMMIT_RE.match(subject):
            problems.append(f"合规提交信息被误判：{subject}")

    if problems:
        for item in problems:
            print(f"[FAIL] {item}")
        print(f"[FAIL] 自测发现 {len(problems)} 个规则缺陷")
        return 1
    samples = sum(
        len(group)
        for group in (
            SELF_TEST_BAD_PATHS,
            SELF_TEST_GOOD_PATHS,
            SELF_TEST_BAD_SECRETS,
            SELF_TEST_GOOD_SECRETS,
            SELF_TEST_BAD_COMMITS,
            SELF_TEST_GOOD_COMMITS,
        )
    )
    print(f"[PASS] {samples} 个样本全部符合预期（能拦违规、不误伤正常写法）")
    return 0


def commit_subjects(base: str) -> list[tuple[str, str]]:
    if base:
        raw = git("log", "--no-merges", "--format=%h%x09%s", f"{base}..HEAD")
    else:
        raw = git("log", "-1", "--format=%h%x09%s", "HEAD")
    rows: list[tuple[str, str]] = []
    for line in raw.splitlines():
        if "\t" in line:
            short_hash, subject = line.split("\t", 1)
            rows.append((short_hash, subject.strip()))
    return rows


def rev_exists(rev: str) -> bool:
    proc = subprocess.run(["git", "rev-parse", "--verify", "--quiet", rev], cwd=REPO_ROOT, capture_output=True)
    return proc.returncode == 0


def check_commits(base: str, errors: list[str]) -> None:
    scope = f"{base}..HEAD" if base else "最近一次提交"
    section(f"提交信息格式（{scope}）")
    rows = commit_subjects(base)
    if not rows:
        print("[INFO] 该范围内没有提交需要校验")
        return
    bad = 0
    for short_hash, subject in rows:
        if subject.startswith(COMMIT_SKIP_PREFIXES) or COMMIT_RE.match(subject):
            continue
        errors.append(f"{short_hash} {subject}：不符合 type(scope): 描述（type ∈ feat/fix/docs/test/chore/refactor）")
        bad += 1
    print(f"[PASS] {len(rows)} 条提交信息均符合规范" if bad == 0 else f"[FAIL] {bad}/{len(rows)} 条提交信息不符合规范")


def check_doc_sync(files: list[str], warnings: list[str]) -> None:
    section("文档同步提示（不阻断）")
    before = len(warnings)
    for rel_path in files:
        if rel_path.startswith("sql/") and not any(item.startswith("docs/03-") for item in files):
            warnings.append("本次改动了 sql/，建议同步 docs/03-数据库设计说明书.md")
            break
    for rel_path in files:
        if rel_path.startswith(("backend/app/routers/", "frontend/src/views/")) and "docs/PROGRESS.md" not in files:
            warnings.append("本次改动了业务代码，按 AGENTS.md 第 8 节建议同步 docs/PROGRESS.md")
            break
    added = len(warnings) - before
    print("[INFO] 无文档同步提示" if added == 0 else f"[INFO] {added} 条文档同步提示")


def changed_files(base: str) -> list[str]:
    if base:
        diff_base = base
    elif rev_exists("HEAD~1"):
        diff_base = "HEAD~1"
    else:
        return tracked_files()
    raw = git("diff", "--name-only", f"{diff_base}..HEAD")
    return [line.strip() for line in raw.splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="仓库卫生与提交规范自检（本地与 CI 共用）")
    parser.add_argument("--base", default="", help="对比基线（如 origin/main）；给了就校验 base..HEAD，否则只查最近一次提交")
    parser.add_argument("--skip-commits", action="store_true", help="跳过提交信息校验")
    parser.add_argument("--max-file-mb", type=float, default=MAX_FILE_MB, help="单文件体积上限（MB，默认 5）")
    parser.add_argument("--self-test", action="store_true", help="只校验检查规则本身（用违规/合规样本验证规则有效性）")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    errors: list[str] = []
    warnings: list[str] = []

    files = tracked_files()
    print(f"仓库根：{REPO_ROOT}")
    print(f"已跟踪文件：{len(files)} 个" + (f"；对比基线：{args.base}" if args.base else ""))

    check_forbidden_paths(files, errors)
    check_large_files(files, args.max_file_mb, errors)
    check_secrets(files, errors)
    check_bat_files(files, errors, warnings)
    check_env_contract(errors, warnings)
    if not args.skip_commits:
        check_commits(args.base, errors)
    check_doc_sync(changed_files(args.base), warnings)

    print("\n=== 结果 ===")
    for item in warnings:
        print(f"[WARN] {item}")
    for item in errors:
        print(f"[FAIL] {item}")
    if errors:
        print(f"\n自检未通过：{len(errors)} 个问题需要修复（详见上方 [FAIL] 行）")
        return 1
    print(f"\n自检通过：0 个阻断问题，{len(warnings)} 条提示")
    return 0


if __name__ == "__main__":
    sys.exit(main())
