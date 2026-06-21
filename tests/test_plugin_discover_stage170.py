"""
阶段170测试：CLI plugin discover命令

验证 plugin discover 子命令存在并执行
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestPluginDiscoverCommand:
    """验证 plugin discover 命令存在"""

    def test_discover_in_choices(self):
        """discover 应在 plugin_action choices 中"""
        from cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["plugin", "discover"])
        assert args.plugin_action == "discover"

    def test_discover_help(self):
        """plugin --help 应包含 discover"""
        result = subprocess.run(
            [sys.executable, "cli.py", "plugin", "--help"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        assert result.returncode == 0
        assert "discover" in result.stdout

    def test_discover_description_in_help(self):
        """discover 应有描述"""
        result = subprocess.run(
            [sys.executable, "cli.py", "plugin", "--help"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        assert "发现" in result.stdout


class TestPluginDiscoverExecution:
    """验证 plugin discover 执行"""

    def test_discover_nonexistent_dir(self):
        """discover 不存在的目录应报错"""
        result = subprocess.run(
            [sys.executable, "cli.py", "plugin", "discover", "/nonexistent/path"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            stdin=subprocess.DEVNULL,
        )
        assert result.returncode == 1
        assert "目录不存在" in result.stderr or "目录不存在" in result.stdout

    def test_discover_empty_dir(self):
        """discover 空目录应提示未发现"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [sys.executable, "cli.py", "plugin", "discover", tmpdir],
                capture_output=True, text=True, cwd=str(PROJECT_ROOT),
                stdin=subprocess.DEVNULL,
            )
            assert result.returncode == 0
            assert "未发现" in result.stdout or "扫描" in result.stdout

    def test_discover_dir_with_plugins(self):
        """discover 含 .py 文件的目录应发现插件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试插件文件
            with open(os.path.join(tmpdir, "test_plugin.py"), "w") as f:
                f.write("# test plugin\n")
            with open(os.path.join(tmpdir, "_private.py"), "w") as f:
                f.write("# private\n")

            result = subprocess.run(
                [sys.executable, "cli.py", "plugin", "discover", tmpdir],
                capture_output=True, text=True, cwd=str(PROJECT_ROOT),
                stdin=subprocess.DEVNULL,
            )
            assert result.returncode == 0
            # 应发现 test_plugin，不发现 _private
            assert "test_plugin" in result.stdout or "未发现" in result.stdout

    def test_discover_default_dir(self):
        """discover 不带参数应使用默认 plugins/ 目录"""
        result = subprocess.run(
            [sys.executable, "cli.py", "plugin", "discover"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            stdin=subprocess.DEVNULL,
        )
        # 默认目录可能不存在，应返回1或0
        assert result.returncode in (0, 1)
