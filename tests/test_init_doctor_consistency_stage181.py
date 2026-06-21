"""
阶段181: init/doctor依赖检查统一 + config_schema接入config validate

验证:
1. init 和 doctor 检查相同的依赖列表（flask/flask_cors/numpy/psutil/dotenv）
2. config validate 接入 config_schema
3. config validate 包含环境变量类型校验（PORT/LOG_LEVEL）
"""

import os
import sys
import inspect
import subprocess

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestInitDoctorDependencyConsistency:
    """init 和 doctor 依赖检查一致性"""

    def test_init_checks_flask_cors(self):
        """init 检查 flask_cors"""
        from cli import CommandHandler
        source = inspect.getsource(CommandHandler.cmd_init)
        assert "flask_cors" in source or "Flask-CORS" in source

    def test_init_checks_psutil(self):
        """init 检查 psutil"""
        from cli import CommandHandler
        source = inspect.getsource(CommandHandler.cmd_init)
        assert "psutil" in source

    def test_init_checks_dotenv(self):
        """init 检查 dotenv（阶段181新增）"""
        from cli import CommandHandler
        source = inspect.getsource(CommandHandler.cmd_init)
        assert "dotenv" in source

    def test_doctor_checks_dotenv(self):
        """doctor 检查 dotenv（阶段181新增）"""
        from cli import CommandHandler
        source = inspect.getsource(CommandHandler.cmd_doctor)
        assert "dotenv" in source

    def test_init_and_doctor_check_same_deps(self):
        """init 和 doctor 检查相同的依赖集合"""
        from cli import CommandHandler
        init_source = inspect.getsource(CommandHandler.cmd_init)
        doctor_source = inspect.getsource(CommandHandler.cmd_doctor)

        # 两者都应包含这5个依赖
        required_deps = ["flask", "flask_cors", "numpy", "psutil", "dotenv"]
        for dep in required_deps:
            assert dep in init_source, f"init 应检查 {dep}"
            assert dep in doctor_source, f"doctor 应检查 {dep}"


class TestConfigValidateSchemaIntegration:
    """config validate 接入 config_schema"""

    def test_config_validate_imports_schema(self):
        """_config_validate 导入 config_schema"""
        from cli import CommandHandler
        source = inspect.getsource(CommandHandler._config_validate)
        assert "config_schema" in source
        assert "create_system_config_schema" in source

    def test_config_validate_calls_schema_validate(self):
        """_config_validate 调用 schema.validate()"""
        from cli import CommandHandler
        source = inspect.getsource(CommandHandler._config_validate)
        assert "schema.validate" in source or "schema_errors" in source

    def test_config_validate_checks_port_range(self):
        """_config_validate 校验 PORT 范围"""
        from cli import CommandHandler
        source = inspect.getsource(CommandHandler._config_validate)
        assert "PORT" in source
        assert "65535" in source or "1 <= port" in source

    def test_config_validate_checks_log_level(self):
        """_config_validate 校验 LOG_LEVEL"""
        from cli import CommandHandler
        source = inspect.getsource(CommandHandler._config_validate)
        assert "LOG_LEVEL" in source
        assert "valid_levels" in source or "DEBUG" in source


class TestConfigValidateExecution:
    """config validate 实际执行验证"""

    def test_config_validate_runs_without_error(self):
        """config validate 命令可正常执行"""
        result = subprocess.run(
            [sys.executable, "cli.py", "config", "validate"],
            capture_output=True, text=True, timeout=30,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        # 应正常退出（0=无错误，1=有错误但命令本身正常执行）
        assert result.returncode in (0, 1), \
            f"config validate 应正常执行，returncode={result.returncode}, stderr={result.stderr}"
        # 不应因异常崩溃
        assert "Traceback" not in result.stderr, \
            f"config validate 不应崩溃: {result.stderr}"

    def test_config_validate_shows_results(self):
        """config validate 显示校验结果"""
        result = subprocess.run(
            [sys.executable, "cli.py", "config", "validate"],
            capture_output=True, text=True, timeout=30,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert "配置校验结果" in result.stdout or "错误" in result.stdout

    def test_config_validate_with_invalid_port(self):
        """无效 PORT 环境变量时 config validate 报错"""
        env = os.environ.copy()
        env["PORT"] = "not_a_number"
        result = subprocess.run(
            [sys.executable, "cli.py", "config", "validate"],
            capture_output=True, text=True, timeout=30,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            env=env
        )
        # 应检测到 PORT 错误
        assert "PORT" in result.stdout or result.returncode == 1

    def test_config_validate_with_invalid_log_level(self):
        """无效 LOG_LEVEL 环境变量时 config validate 警告"""
        env = os.environ.copy()
        env["LOG_LEVEL"] = "INVALID_LEVEL"
        result = subprocess.run(
            [sys.executable, "cli.py", "config", "validate"],
            capture_output=True, text=True, timeout=30,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            env=env
        )
        # 应检测到 LOG_LEVEL 警告
        assert "LOG_LEVEL" in result.stdout


class TestDoctorCommandExecution:
    """doctor 命令执行验证"""

    def test_doctor_checks_5_deps(self):
        """doctor 检查5个依赖"""
        from cli import CommandHandler
        source = inspect.getsource(CommandHandler.cmd_doctor)
        # 应有5个依赖项
        deps_count = source.count("(")  # 粗略计数
        # 更精确：检查 deps 列表中的项数
        assert source.count('("flask"') >= 1
        assert source.count('("flask_cors"') >= 1
        assert source.count('("numpy"') >= 1
        assert source.count('("psutil"') >= 1
        assert source.count('("dotenv"') >= 1

    def test_doctor_runs_without_crash(self):
        """doctor 命令不崩溃"""
        result = subprocess.run(
            [sys.executable, "cli.py", "doctor"],
            capture_output=True, text=True, timeout=30,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode in (0, 1), \
            f"doctor 应正常执行，returncode={result.returncode}"
        assert "Traceback" not in result.stderr


class TestNoRegression:
    """验证不引入回归"""

    def test_init_command_still_works(self):
        """init 命令仍正常"""
        result = subprocess.run(
            [sys.executable, "cli.py", "init", "--help"],
            capture_output=True, text=True, timeout=15,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0

    def test_doctor_command_still_works(self):
        """doctor 命令仍正常"""
        result = subprocess.run(
            [sys.executable, "cli.py", "doctor", "--help"],
            capture_output=True, text=True, timeout=15,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0

    def test_config_command_still_works(self):
        """config 命令仍正常"""
        result = subprocess.run(
            [sys.executable, "cli.py", "config", "--help"],
            capture_output=True, text=True, timeout=15,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
