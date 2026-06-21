"""
阶段179: 日志轮转 + API文件日志 + LOG_LEVEL环境变量验证

验证:
1. JsonFileBackend 支持日志轮转（按大小切割，保留备份）
2. main.py 配置文件日志后端
3. LOG_LEVEL 环境变量控制日志级别
4. .env.example 文档化日志配置
"""

import os
import sys
import tempfile
import inspect

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestJsonFileBackendRotation:
    """JsonFileBackend 日志轮转验证"""

    def test_json_file_backend_has_rotation_params(self):
        """JsonFileBackend 支持轮转参数"""
        from self_evolving_agent.core.logging import JsonFileBackend, LogLevel
        # 检查 __init__ 签名包含轮转参数
        sig = inspect.signature(JsonFileBackend.__init__)
        params = sig.parameters
        assert "max_bytes" in params
        assert "backup_count" in params
        assert "enable_rotation" in params

    def test_json_file_backend_rotates_on_size(self):
        """日志文件超过 max_bytes 时自动轮转"""
        from self_evolving_agent.core.logging import JsonFileBackend, LogLevel, LogRecord
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            # 设置很小的 max_bytes 触发轮转
            backend = JsonFileBackend(
                filepath=log_file,
                min_level=LogLevel.DEBUG,
                max_bytes=100,  # 100字节就轮转
                backup_count=3,
                enable_rotation=True,
            )
            # 写入多条日志触发轮转
            for i in range(20):
                record = LogRecord(
                    message=f"测试日志消息 {i} " * 5,
                    level=LogLevel.INFO,
                    source="test",
                )
                backend.write(record)
            backend.flush()
            backend.close()

            # 应生成轮转备份文件
            files = os.listdir(tmpdir)
            # 至少有 test.log 和 test.log.1
            assert "test.log" in files
            assert "test.log.1" in files, f"应有轮转备份文件，实际: {files}"

    def test_json_file_backend_backup_count_limit(self):
        """轮转备份文件数量不超过 backup_count"""
        from self_evolving_agent.core.logging import JsonFileBackend, LogLevel, LogRecord
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            backend = JsonFileBackend(
                filepath=log_file,
                min_level=LogLevel.DEBUG,
                max_bytes=50,
                backup_count=2,
                enable_rotation=True,
            )
            # 写入大量日志触发多次轮转
            for i in range(50):
                record = LogRecord(
                    message=f"消息{i}" * 10,
                    level=LogLevel.INFO,
                    source="test",
                )
                backend.write(record)
            backend.flush()
            backend.close()

            files = os.listdir(tmpdir)
            # 备份文件不应超过 backup_count
            backup_files = [f for f in files if f.startswith("test.log.")]
            assert len(backup_files) <= 2, \
                f"备份文件数应<=2，实际: {backup_files}"

    def test_json_file_backend_no_rotation_when_disabled(self):
        """enable_rotation=False 时不轮转"""
        from self_evolving_agent.core.logging import JsonFileBackend, LogLevel, LogRecord
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            backend = JsonFileBackend(
                filepath=log_file,
                min_level=LogLevel.DEBUG,
                max_bytes=10,
                backup_count=3,
                enable_rotation=False,
            )
            for i in range(20):
                record = LogRecord(
                    message=f"消息{i}" * 10,
                    level=LogLevel.INFO,
                    source="test",
                )
                backend.write(record)
            backend.flush()
            backend.close()

            files = os.listdir(tmpdir)
            # 只有 test.log，无备份
            assert files == ["test.log"], f"不应有轮转备份，实际: {files}"

    def test_json_file_backend_creates_directory(self):
        """JsonFileBackend 自动创建日志目录"""
        from self_evolving_agent.core.logging import JsonFileBackend, LogLevel
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = os.path.join(tmpdir, "subdir", "logs")
            log_file = os.path.join(log_dir, "test.log")
            backend = JsonFileBackend(filepath=log_file, min_level=LogLevel.DEBUG)
            backend.close()
            assert os.path.exists(log_file)


class TestMainPyLoggingSetup:
    """main.py 日志配置验证"""

    def test_main_py_has_setup_logging(self):
        """main.py 有 _setup_logging 函数"""
        main_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "main.py"
        )
        with open(main_path, "r") as f:
            content = f.read()
        assert "_setup_logging" in content
        assert "def _setup_logging" in content

    def test_main_py_calls_setup_logging_in_main(self):
        """main() 函数调用 _setup_logging"""
        main_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "main.py"
        )
        with open(main_path, "r") as f:
            content = f.read()
        assert "_setup_logging()" in content

    def test_main_py_uses_json_file_backend(self):
        """main.py 使用 JsonFileBackend"""
        main_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "main.py"
        )
        with open(main_path, "r") as f:
            content = f.read()
        assert "JsonFileBackend" in content

    def test_main_py_supports_log_level_env(self):
        """main.py 支持 LOG_LEVEL 环境变量"""
        main_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "main.py"
        )
        with open(main_path, "r") as f:
            content = f.read()
        assert "LOG_LEVEL" in content

    def test_main_py_supports_log_dir_env(self):
        """main.py 支持 LOG_DIR 环境变量"""
        main_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "main.py"
        )
        with open(main_path, "r") as f:
            content = f.read()
        assert "LOG_DIR" in content

    def test_main_py_supports_rotation_params(self):
        """main.py 支持轮转参数环境变量"""
        main_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "main.py"
        )
        with open(main_path, "r") as f:
            content = f.read()
        assert "LOG_MAX_BYTES" in content
        assert "LOG_BACKUP_COUNT" in content


class TestSetupLoggingFunction:
    """_setup_logging 函数功能测试"""

    def test_setup_logging_creates_log_file(self):
        """_setup_logging 创建日志文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["LOG_DIR"] = tmpdir
            os.environ["LOG_LEVEL"] = "DEBUG"
            try:
                # 重新导入 main 以触发 _setup_logging
                import importlib
                import main
                importlib.reload(main)
                main._setup_logging()
                # 应创建日志文件
                log_file = os.path.join(tmpdir, "agent.log")
                assert os.path.exists(log_file), \
                    f"_setup_logging 应创建日志文件: {log_file}"
            finally:
                os.environ.pop("LOG_DIR", None)
                os.environ.pop("LOG_LEVEL", None)

    def test_setup_logging_respects_log_level(self):
        """_setup_logging 尊重 LOG_LEVEL 环境变量"""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["LOG_DIR"] = tmpdir
            os.environ["LOG_LEVEL"] = "ERROR"
            try:
                import importlib
                import main
                importlib.reload(main)
                main._setup_logging()
                # LogManager 的默认级别应为 ERROR
                from self_evolving_agent.core.logging import LogManager, LogLevel
                lm = LogManager()
                assert lm._default_level == LogLevel.ERROR
            finally:
                os.environ.pop("LOG_DIR", None)
                os.environ.pop("LOG_LEVEL", None)


class TestEnvExampleDocumentation:
    """ .env.example 文档验证"""

    def test_env_example_documents_log_level(self):
        """.env.example 文档化 LOG_LEVEL"""
        env_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            ".env.example"
        )
        with open(env_path, "r") as f:
            content = f.read()
        assert "LOG_LEVEL" in content

    def test_env_example_documents_log_dir(self):
        """.env.example 文档化 LOG_DIR"""
        env_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            ".env.example"
        )
        with open(env_path, "r") as f:
            content = f.read()
        assert "LOG_DIR" in content

    def test_env_example_documents_rotation_params(self):
        """.env.example 文档化轮转参数"""
        env_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            ".env.example"
        )
        with open(env_path, "r") as f:
            content = f.read()
        assert "LOG_MAX_BYTES" in content
        assert "LOG_BACKUP_COUNT" in content


class TestNoRegression:
    """验证不引入回归"""

    def test_flask_app_still_importable(self):
        """main 模块仍可导入"""
        import main
        assert hasattr(main, "app")
        assert hasattr(main, "main")

    def test_existing_logging_tests_still_pass(self):
        """现有日志功能不受影响"""
        from self_evolving_agent.core.logging import JsonFileBackend, LogLevel, LogRecord
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            backend = JsonFileBackend(filepath=log_file, min_level=LogLevel.INFO)
            record = LogRecord(message="test", level=LogLevel.INFO, source="test")
            backend.write(record)
            backend.flush()
            backend.close()
            assert os.path.exists(log_file)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
