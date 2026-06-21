#!/usr/bin/env python3
"""
阶段145: 代码质量门禁脚本

用法:
    python scripts/quality_gate.py          # 检查全部
    python scripts/quality_gate.py --lint   # 仅lint
    python scripts/quality_gate.py --type   # 仅类型检查
    python scripts/quality_gate.py --format # 仅格式检查
    python scripts/quality_gate.py --fix    # 自动修复lint问题

退出码:
    0 — 通过（非阻塞模式：lint/format/type建议不阻塞门禁）
    1 — 仅在--fix失败或脚本异常时返回

设计原则（第一性原理）:
    质量门禁在秩序化阶段为非阻塞，提供建议而非阻断开发流程。
    真正的阻塞条件由CI配置（如GitHub Actions）决定，而非此脚本。
"""

import argparse
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TARGETS = [
    "self_evolving_agent",
    "main.py",
    "cli.py",
    "tests",
    "examples",
]


def run_ruff_check(fix: bool = False) -> int:
    """运行ruff lint检查"""
    cmd = ["ruff", "check"]
    if fix:
        cmd.append("--fix")
    cmd.extend(TARGETS)
    print(f"[lint] {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return result.returncode


def run_ruff_format(check_only: bool = True) -> int:
    """运行ruff format检查"""
    cmd = ["ruff", "format"]
    if check_only:
        cmd.append("--check")
    cmd.extend(TARGETS)
    print(f"[format] {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return result.returncode


def run_mypy() -> int:
    """运行mypy类型检查"""
    cmd = ["mypy", "self_evolving_agent"]
    print(f"[type] {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="代码质量门禁")
    parser.add_argument("--lint", action="store_true", help="仅运行lint")
    parser.add_argument("--type", action="store_true", help="仅运行类型检查")
    parser.add_argument("--fix", action="store_true", help="自动修复lint问题")
    parser.add_argument("--format", action="store_true", help="仅检查格式")
    args = parser.parse_args()

    # --fix 模式：返回实际退出码（用于开发者主动修复）
    if args.fix:
        return run_ruff_check(fix=True)

    # --lint 模式：非阻塞，报告但返回0
    if args.lint:
        lint_code = run_ruff_check()
        if lint_code != 0:
            print(f"\n[警告] lint发现建议（非阻塞，门禁通过）")
        return 0

    # --format 模式：非阻塞，报告但返回0
    if args.format:
        fmt_code = run_ruff_format()
        if fmt_code != 0:
            print(f"\n[警告] 格式有差异（非阻塞，门禁通过）")
        return 0

    # --type 模式：非阻塞，报告但返回0
    if args.type:
        type_code = run_mypy()
        if type_code != 0:
            print(f"\n[警告] 类型检查有建议（非阻塞，门禁通过）")
        return 0

    # 默认运行全部（非阻塞）
    print("=" * 50)
    print("代码质量门禁检查")
    print("=" * 50)

    print("\n[1/3] Ruff Lint 检查")
    lint_code = run_ruff_check()
    if lint_code != 0:
        print(f"  [警告] lint发现建议（非阻塞）")

    print("\n[2/3] Ruff Format 检查")
    fmt_code = run_ruff_format()
    if fmt_code != 0:
        print(f"  [警告] 格式有差异（非阻塞）")

    print("\n[3/3] Mypy 类型检查")
    type_code = run_mypy()
    if type_code != 0:
        print(f"  [警告] 类型检查有建议（非阻塞）")

    print("\n" + "=" * 50)
    print("质量门禁完成")
    print(f"  lint:   {'PASS' if lint_code == 0 else 'WARN'}")
    print(f"  format: {'PASS' if fmt_code == 0 else 'WARN'}")
    print(f"  type:   {'PASS' if type_code == 0 else 'WARN'}")
    print("=" * 50)

    # 门禁策略：lint/format/type均为非阻塞
    # 真正的阻塞条件留给CI配置决定
    return 0


if __name__ == "__main__":
    sys.exit(main())
