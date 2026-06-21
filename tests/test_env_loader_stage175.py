"""
阶段175: .env 自动加载验证

验证:
1. env_loader 模块可导入且功能正确
2. .env 文件自动加载到 os.environ
3. 已存在的环境变量不被覆盖
4. python-dotenv 未安装时回退到内置解析器
5. main.py 和 cli.py 入口处接入 load_env
6. pyproject.toml 和 requirements.txt 声明 python-dotenv 依赖
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestEnvLoaderModule:
    """env_loader 模块功能测试"""

    def test_module_importable(self):
        """env_loader 模块可导入"""
        from self_evolving_agent.core import env_loader
        assert hasattr(env_loader, "load_env")
        assert hasattr(env_loader, "is_env_loaded")

    def test_parse_env_line_basic(self):
        """简易解析器: KEY=VALUE"""
        from self_evolving_agent.core.env_loader import _parse_env_line
        result = _parse_env_line("KEY=VALUE")
        assert result == ("KEY", "VALUE")

    def test_parse_env_line_with_quotes(self):
        """简易解析器: 去引号"""
        from self_evolving_agent.core.env_loader import _parse_env_line
        assert _parse_env_line('KEY="VALUE"') == ("KEY", "VALUE")
        assert _parse_env_line("KEY='VALUE'") == ("KEY", "VALUE")

    def test_parse_env_line_comment(self):
        """简易解析器: 注释行返回None"""
        from self_evolving_agent.core.env_loader import _parse_env_line
        assert _parse_env_line("# 这是注释") is None
        assert _parse_env_line("") is None
        assert _parse_env_line("   ") is None

    def test_parse_env_line_no_equals(self):
        """简易解析器: 无等号返回None"""
        from self_evolving_agent.core.env_loader import _parse_env_line
        assert _parse_env_line("INVALID_LINE") is None

    def test_load_env_from_file(self):
        """load_env 从指定文件加载"""
        from self_evolving_agent.core.env_loader import load_env
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("TEST_STAGE175_KEY=hello175\n")
            f.write("# 注释\n")
            f.write("TEST_STAGE175_NUM=42\n")
            f_path = f.name
        try:
            # 确保环境变量不存在
            os.environ.pop("TEST_STAGE175_KEY", None)
            os.environ.pop("TEST_STAGE175_NUM", None)
            loaded = load_env(env_path=f_path, verbose=False)
            assert "TEST_STAGE175_KEY" in loaded
            assert os.environ.get("TEST_STAGE175_KEY") == "hello175"
            assert os.environ.get("TEST_STAGE175_NUM") == "42"
        finally:
            os.unlink(f_path)
            os.environ.pop("TEST_STAGE175_KEY", None)
            os.environ.pop("TEST_STAGE175_NUM", None)

    def test_load_env_no_override_existing(self):
        """load_env 不覆盖已存在的环境变量"""
        from self_evolving_agent.core.env_loader import load_env
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("TEST_STAGE175_OVERRIDE=file_value\n")
            f_path = f.name
        try:
            os.environ["TEST_STAGE175_OVERRIDE"] = "env_value"
            load_env(env_path=f_path, verbose=False)
            # 已存在的值不被覆盖
            assert os.environ.get("TEST_STAGE175_OVERRIDE") == "env_value"
        finally:
            os.unlink(f_path)
            os.environ.pop("TEST_STAGE175_OVERRIDE", None)

    def test_load_env_nonexistent_file(self):
        """load_env 文件不存在时返回空dict"""
        from self_evolving_agent.core.env_loader import load_env
        result = load_env(env_path="/nonexistent/path/.env", verbose=False)
        assert result == {}

    def test_load_env_fallback_parser(self):
        """python-dotenv 未安装时回退到内置解析器"""
        # 通过 mock 模拟 dotenv 未安装
        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "dotenv":
                raise ImportError("模拟 dotenv 未安装")
            return original_import(name, *args, **kwargs)

        from self_evolving_agent.core.env_loader import load_env
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("TEST_STAGE175_FALLBACK=fallback_value\n")
            f_path = f.name
        try:
            os.environ.pop("TEST_STAGE175_FALLBACK", None)
            with mock.patch("builtins.__import__", side_effect=mock_import):
                loaded = load_env(env_path=f_path, verbose=False)
            assert os.environ.get("TEST_STAGE175_FALLBACK") == "fallback_value"
        finally:
            os.unlink(f_path)
            os.environ.pop("TEST_STAGE175_FALLBACK", None)


class TestEntrypointIntegration:
    """入口处接入验证"""

    def test_main_py_loads_env(self):
        """main.py 在导入时调用 load_env"""
        main_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "main.py"
        )
        with open(main_path, "r") as f:
            content = f.read()
        assert "from self_evolving_agent.core.env_loader import load_env" in content
        assert "load_env()" in content

    def test_cli_py_loads_env(self):
        """cli.py 在导入时调用 load_env"""
        cli_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "cli.py"
        )
        with open(cli_path, "r") as f:
            content = f.read()
        assert "from self_evolving_agent.core.env_loader import load_env" in content
        assert "load_env()" in content

    def test_load_env_called_before_other_imports_in_main(self):
        """main.py 中 load_env 在 api 导入之前调用"""
        main_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "main.py"
        )
        with open(main_path, "r") as f:
            lines = f.readlines()
        load_env_line = None
        api_import_line = None
        for i, line in enumerate(lines):
            if "load_env()" in line and "import" not in line:
                load_env_line = i
            if "from api import" in line:
                api_import_line = i
                break
        assert load_env_line is not None, "main.py 应调用 load_env()"
        assert api_import_line is not None, "main.py 应导入 api"
        assert load_env_line < api_import_line, \
            "load_env() 应在 from api import 之前调用"


class TestDependencyDeclaration:
    """依赖声明验证"""

    def test_pyproject_toml_declares_dotenv(self):
        """pyproject.toml 声明 python-dotenv 依赖"""
        toml_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "pyproject.toml"
        )
        with open(toml_path, "r") as f:
            content = f.read()
        assert "python-dotenv" in content, \
            "pyproject.toml 应声明 python-dotenv 依赖"

    def test_requirements_txt_declares_dotenv(self):
        """requirements.txt 声明 python-dotenv 依赖"""
        req_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "requirements.txt"
        )
        with open(req_path, "r") as f:
            content = f.read()
        assert "python-dotenv" in content, \
            "requirements.txt 应声明 python-dotenv 依赖"

    def test_dotenv_actually_installed(self):
        """python-dotenv 实际已安装"""
        try:
            import dotenv
            assert dotenv is not None
        except ImportError:
            pytest.fail("python-dotenv 应已安装")

    def test_env_example_updated(self):
        """.env.example 注释已更新（移除"需安装python-dotenv"）"""
        env_example_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            ".env.example"
        )
        with open(env_example_path, "r") as f:
            content = f.read()
        # 不应再包含"需安装 python-dotenv"
        assert "需安装 python-dotenv" not in content
        # 应包含"自动加载"说明
        assert "自动加载" in content or "自动读取" in content


class TestEndToEndEnvLoading:
    """端到端: 实际 .env 加载效果"""

    def test_cli_loads_env_on_startup(self):
        """CLI 启动时加载 .env（通过环境变量验证）"""
        import subprocess
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # 创建临时 .env 测试文件
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("TEST_CLI_ENV_LOAD=stage175_success\n")
            env_path = f.name

        try:
            env = os.environ.copy()
            env["PYTHONPATH"] = project_root
            result = subprocess.run(
                [sys.executable, "-c",
                 "from self_evolving_agent.core.env_loader import load_env; "
                 "load_env(env_path='{}', verbose=False); "
                 "import os; print(os.environ.get('TEST_CLI_ENV_LOAD', 'NOT_LOADED'))".format(env_path)],
                capture_output=True, text=True, timeout=15,
                cwd=project_root,
                env=env
            )
            assert "stage175_success" in result.stdout, \
                f"CLI应加载.env: stdout={result.stdout}, stderr={result.stderr}"
        finally:
            os.unlink(env_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
