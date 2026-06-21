"""
阶段152测试：入口统一 — 规范化main/cli/run_six_hours入口

验证：
1. 所有入口点在pyproject.toml中注册
2. 所有入口点可正常导入和调用
3. 入口点命名一致
4. 第一性原理：一致性、可发现性、可操作性
"""

import os
import sys
import importlib
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# pyproject.toml入口点注册测试
# ============================================================

class TestEntryPointRegistration:
    """测试入口点在pyproject.toml中注册"""

    def test_pyproject_has_scripts(self):
        """pyproject.toml应有[project.scripts]"""
        content = (PROJECT_ROOT / "pyproject.toml").read_text()
        assert "[project.scripts]" in content

    def test_cli_entry_registered(self):
        """CLI入口应注册"""
        content = (PROJECT_ROOT / "pyproject.toml").read_text()
        assert "cli:main" in content or "cli.main" in content

    def test_api_entry_registered(self):
        """API入口应注册"""
        content = (PROJECT_ROOT / "pyproject.toml").read_text()
        assert "main:main" in content

    def test_run_entry_registered(self):
        """运行脚本入口应注册"""
        content = (PROJECT_ROOT / "pyproject.toml").read_text()
        assert "run_six_hours:main" in content


# ============================================================
# 入口点可导入性测试
# ============================================================

class TestEntryPointImportable:
    """测试所有入口点可导入"""

    def test_cli_importable(self):
        """cli.py应可导入"""
        import cli
        assert hasattr(cli, "main")
        assert callable(cli.main)

    def test_main_importable(self):
        """main.py应可导入"""
        import main
        assert hasattr(main, "main")
        assert callable(main.main)

    def test_run_six_hours_importable(self):
        """run_six_hours.py应可导入"""
        import run_six_hours
        assert hasattr(run_six_hours, "main")
        assert callable(run_six_hours.main)


# ============================================================
# 入口点一致性测试
# ============================================================

class TestEntryPointConsistency:
    """测试入口点一致性"""

    def test_all_entries_have_main(self):
        """所有入口模块都应有main函数"""
        import cli, main, run_six_hours
        for module in [cli, main, run_six_hours]:
            assert hasattr(module, "main"), f"{module.__name__}应有main函数"
            assert callable(module.main), f"{module.__name__}.main应可调用"

    def test_all_entries_have_docstring(self):
        """所有入口模块都应有文档字符串"""
        import cli, main, run_six_hours
        for module in [cli, main, run_six_hours]:
            assert module.__doc__ is not None, f"{module.__name__}应有模块文档字符串"

    def test_entry_naming_consistent(self):
        """入口点命名应一致（都以self-evolving-agent开头）"""
        content = (PROJECT_ROOT / "pyproject.toml").read_text()
        # 找到[project.scripts]部分
        scripts_start = content.find("[project.scripts]")
        scripts_end = content.find("\n[", scripts_start + 1)
        if scripts_end == -1:
            scripts_end = len(content)
        scripts_section = content[scripts_start:scripts_end]
        # 所有入口点应以self-evolving-agent开头
        lines = [l.strip() for l in scripts_section.splitlines()
                 if "=" in l and not l.strip().startswith("[") and not l.strip().startswith("#")]
        for line in lines:
            name = line.split("=")[0].strip()
            assert name.startswith("self-evolving-agent"), \
                f"入口点'{name}'应以self-evolving-agent开头"


# ============================================================
# 入口点功能测试
# ============================================================

class TestEntryPointFunctionality:
    """测试入口点功能"""

    def test_cli_help(self):
        """CLI应支持--help"""
        import subprocess
        result = subprocess.run(
            ["python", "cli.py", "--help"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        assert result.returncode == 0
        assert "usage" in result.stdout.lower() or "usage" in result.stderr.lower()

    def test_main_app_exists(self):
        """main.py应创建Flask app"""
        import main
        assert hasattr(main, "app")
        assert main.app is not None

    def test_run_six_hours_config(self):
        """run_six_hours应有运行时长配置"""
        import run_six_hours
        # 应有DURATION_HOURS常量
        assert hasattr(run_six_hours, "DURATION_HOURS") or \
               hasattr(run_six_hours, "DURATION")


# ============================================================
# 第一性原理测试
# ============================================================

class TestFirstPrinciples:
    """第一性原理验证"""

    def test_consistency_principle(self):
        """一致性原则：所有入口点在pyproject.toml注册"""
        content = (PROJECT_ROOT / "pyproject.toml").read_text()
        assert "cli:main" in content
        assert "main:main" in content
        assert "run_six_hours:main" in content

    def test_discoverability_principle(self):
        """可发现性原则：入口点有文档和帮助"""
        import cli, main, run_six_hours
        for module in [cli, main, run_six_hours]:
            assert module.__doc__ is not None

    def test_operability_principle(self):
        """可操作性原则：入口点可调用"""
        import cli, main, run_six_hours
        for module in [cli, main, run_six_hours]:
            assert callable(getattr(module, "main", None))

    def test_single_responsibility_principle(self):
        """单一职责：每个入口点负责不同功能"""
        import cli, main, run_six_hours
        # cli: 命令行工具
        assert "cli" in cli.__doc__.lower() or "命令" in cli.__doc__
        # main: API服务
        assert "api" in main.__doc__.lower() or "部署" in main.__doc__ or "入口" in main.__doc__
        # run_six_hours: 持续运行
        assert "六小时" in run_six_hours.__doc__ or "6" in run_six_hours.__doc__ or "持续" in run_six_hours.__doc__
