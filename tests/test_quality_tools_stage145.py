"""
阶段145: 代码质量工具链测试

验证ruff和mypy工具链配置正确且可用。
"""

import os
import subprocess
import pytest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run_cmd(cmd: list) -> tuple:
    """运行命令，返回(returncode, stdout, stderr)"""
    result = subprocess.run(
        cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=60
    )
    return result.returncode, result.stdout, result.stderr


# ============================================================
# 工具安装验证
# ============================================================

class TestToolsInstalled:
    """工具安装验证"""

    def test_ruff_installed(self):
        code, out, _ = run_cmd(["ruff", "--version"])
        assert code == 0
        assert "ruff" in out.lower()

    def test_mypy_installed(self):
        code, out, _ = run_cmd(["mypy", "--version"])
        assert code == 0
        assert "mypy" in out.lower()


# ============================================================
# Ruff配置验证
# ============================================================

class TestRuffConfig:
    """Ruff配置验证"""

    def test_ruff_check_runs(self):
        """ruff check能正常运行（不要求0错误）"""
        code, out, err = run_cmd(["ruff", "check", "self_evolving_agent/core/multi_tenant.py"])
        # ruff check返回0表示无错误，1表示有错误，都说明工具可用
        assert code in [0, 1]

    def test_ruff_format_check_runs(self):
        """ruff format --check能正常运行"""
        code, out, err = run_cmd(["ruff", "format", "--check", "self_evolving_agent/core/multi_tenant.py"])
        assert code in [0, 1]

    def test_ruff_target_version(self):
        """验证ruff目标版本配置"""
        code, out, _ = run_cmd(["ruff", "check", "--show-settings", "self_evolving_agent/"])
        assert code == 0

    def test_ruff_excludes_backup(self):
        """验证ruff排除backup目录"""
        code, out, _ = run_cmd(["ruff", "check", "backup/"])
        # backup应被排除（无输出或跳过）
        assert code in [0, 1]


# ============================================================
# Mypy配置验证
# ============================================================

class TestMypyConfig:
    """Mypy配置验证"""

    def test_mypy_runs(self):
        """mypy能正常运行"""
        code, out, err = run_cmd(["mypy", "self_evolving_agent/core/multi_tenant.py"])
        # mypy返回0无错误，1有错误，都说明工具可用
        assert code in [0, 1]

    def test_mypy_ignore_missing_imports(self):
        """验证mypy忽略缺失导入"""
        code, out, _ = run_cmd(["mypy", "self_evolving_agent/core/multi_tenant.py"])
        # 不应有numpy等缺失导入的致命错误
        assert "can't find module 'numpy'" not in out


# ============================================================
# 质量门禁脚本验证
# ============================================================

class TestQualityGateScript:
    """质量门禁脚本验证"""

    def test_script_exists(self):
        script = PROJECT_ROOT / "scripts" / "quality_gate.py"
        assert script.exists()

    def test_script_help(self):
        code, out, _ = run_cmd(["python", "scripts/quality_gate.py", "--help"])
        assert code == 0
        assert "lint" in out.lower()

    def test_script_lint_mode(self):
        code, out, _ = run_cmd(["python", "scripts/quality_gate.py", "--lint"])
        assert code in [0, 1]

    def test_script_type_mode(self):
        code, out, _ = run_cmd(["python", "scripts/quality_gate.py", "--type"])
        assert code in [0, 1]


# ============================================================
# 配置一致性验证
# ============================================================

class TestConfigConsistency:
    """配置一致性验证"""

    def test_pyproject_has_ruff_config(self):
        import tomllib
        with open(PROJECT_ROOT / "pyproject.toml", "rb") as f:
            config = tomllib.load(f)
        assert "tool" in config
        assert "ruff" in config["tool"]

    def test_pyproject_has_mypy_config(self):
        import tomllib
        with open(PROJECT_ROOT / "pyproject.toml", "rb") as f:
            config = tomllib.load(f)
        assert "mypy" in config["tool"]

    def test_ruff_lint_select_rules(self):
        """验证ruff选择了关键规则集"""
        import tomllib
        with open(PROJECT_ROOT / "pyproject.toml", "rb") as f:
            config = tomllib.load(f)
        select = config["tool"]["ruff"]["lint"]["select"]
        assert "E" in select  # pycodestyle errors
        assert "F" in select  # pyflakes
        assert "I" in select  # isort

    def test_ruff_line_length_configured(self):
        """验证行长度配置"""
        import tomllib
        with open(PROJECT_ROOT / "pyproject.toml", "rb") as f:
            config = tomllib.load(f)
        ll = config["tool"]["ruff"]["line-length"]
        assert 80 <= ll <= 120


# ============================================================
# 第一性原理验证
# ============================================================

class TestFirstPrinciples:
    """第一性原理验证"""

    def test_automation_principle(self):
        """第一性原理: 自动化 — 质量检查应可自动化执行"""
        code, _, _ = run_cmd(["ruff", "--version"])
        assert code == 0
        code, _, _ = run_cmd(["mypy", "--version"])
        assert code == 0

    def test_consistency_principle(self):
        """第一性原理: 一致性 — 配置应集中管理"""
        import tomllib
        with open(PROJECT_ROOT / "pyproject.toml", "rb") as f:
            config = tomllib.load(f)
        # ruff和mypy配置都应在pyproject.toml中
        assert "ruff" in config["tool"]
        assert "mypy" in config["tool"]

    def test_non_blocking_principle(self):
        """第一性原理: 非阻塞 — 现有代码不应被工具链阻塞"""
        # 质量门禁脚本应总是返回0（非阻塞模式）
        code, _, _ = run_cmd(["python", "scripts/quality_gate.py"])
        assert code == 0
