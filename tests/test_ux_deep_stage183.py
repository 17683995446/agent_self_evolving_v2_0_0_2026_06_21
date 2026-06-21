"""
阶段183: 用户体验深度验证

综合验证阶段174-182的所有成果，重点验证"接入性"而非"模块存在性"。
使用 inspect.getsource() 检查源码是否实际调用相关函数。

覆盖:
- TestStage174: CLI Bug修复（cmd_logs/cmd_repl）
- TestStage175: .env自动加载
- TestStage176: deploy.sh修复
- TestStage177: API错误响应全面接入
- TestStage178: ProgressIndicator接入
- TestStage179: 日志轮转
- TestStage180: error_codes.md文档
- TestStage181: init/doctor一致性 + config_schema
- TestStage182: OpenAPI文档增强
- TestFirstPrinciples: 第一性原理验证
- TestUsabilityResults: 逐阶段成果验证
"""

import os
import sys
import inspect
import subprocess

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestStage174_CLIBugFix:
    """阶段174: CLI Bug修复验证"""

    def test_subprocess_imported(self):
        """cli.py 导入了 subprocess"""
        import cli
        assert hasattr(cli, "subprocess")

    def test_cmd_logs_uses_self_fmt(self):
        """cmd_logs 使用 self.fmt.format 而非 self.format"""
        from cli import CommandHandler
        source = inspect.getsource(CommandHandler.cmd_logs)
        assert "self.fmt.format" in source

    def test_cmd_logs_json_no_crash(self):
        """--format json logs 不崩溃"""
        result = subprocess.run(
            [sys.executable, "cli.py", "--format", "json", "logs", "--limit", "3"],
            capture_output=True, text=True, timeout=30,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert "AttributeError" not in result.stderr

    def test_repl_help_no_name_error(self):
        """REPL help <cmd> 不抛 NameError"""
        result = subprocess.run(
            [sys.executable, "cli.py", "repl"],
            input="help status\nquit\n",
            capture_output=True, text=True, timeout=30,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert "NameError" not in result.stderr


class TestStage175_EnvAutoLoad:
    """阶段175: .env自动加载验证"""

    def test_env_loader_module_exists(self):
        """env_loader 模块存在"""
        from self_evolving_agent.core import env_loader
        assert hasattr(env_loader, "load_env")

    def test_main_py_loads_env(self):
        """main.py 接入 load_env"""
        main_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py")
        with open(main_path) as f:
            content = f.read()
        assert "load_env()" in content

    def test_cli_py_loads_env(self):
        """cli.py 接入 load_env"""
        cli_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cli.py")
        with open(cli_path) as f:
            content = f.read()
        assert "load_env()" in content

    def test_dotenv_in_dependencies(self):
        """python-dotenv 在依赖中"""
        toml_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pyproject.toml")
        with open(toml_path) as f:
            content = f.read()
        assert "python-dotenv" in content


class TestStage176_DeployFix:
    """阶段176: deploy.sh修复验证"""

    def test_deploy_sh_no_nonexistent_test(self):
        """deploy.sh 不引用不存在的测试文件"""
        deploy_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "deploy.sh")
        with open(deploy_path) as f:
            content = f.read()
        assert "test_system_end_to_end.py" not in content

    def test_deploy_sh_uses_pytest(self):
        """deploy.sh 使用 pytest"""
        deploy_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "deploy.sh")
        with open(deploy_path) as f:
            content = f.read()
        assert "pytest" in content

    def test_deploy_sh_syntax_valid(self):
        """deploy.sh 语法有效"""
        deploy_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "deploy.sh")
        result = subprocess.run(["bash", "-n", deploy_path], capture_output=True, text=True)
        assert result.returncode == 0


class TestStage177_APIErrorFullIntegration:
    """阶段177: API错误响应全面接入验证"""

    def test_all_15_blueprints_import_api_error_response(self):
        """全部15个Blueprint导入api_error_response"""
        all_modules = [
            "api.core_routes", "api.llm_routes", "api.rag_routes",
            "api.env_routes", "api.task_routes", "api.code_routes",
            "api.perf_routes", "api.observability_routes",
            "api.production_routes", "api.plugins_routes",
            "api.config_routes", "api.security_routes",
            "api.recovery_routes", "api.benchmark_routes",
            "api.tenants_routes",
        ]
        import importlib
        for mod_path in all_modules:
            module = importlib.import_module(mod_path)
            source = inspect.getsource(module)
            assert "api_error_response" in source, \
                f"{mod_path} 应导入 api_error_response"


class TestStage178_ProgressIndicator:
    """阶段178: ProgressIndicator接入验证"""

    def test_output_formatter_has_progress(self):
        """OutputFormatter 有 progress 方法"""
        from cli import OutputFormatter
        assert hasattr(OutputFormatter, "progress")

    def test_cli_has_multiple_progress_calls(self):
        """CLI 有多处 progress 调用"""
        cli_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cli.py")
        with open(cli_path) as f:
            content = f.read()
        count = content.count("self.fmt.progress(")
        assert count >= 5, f"应有至少5处progress调用，实际{count}处"


class TestStage179_LogRotation:
    """阶段179: 日志轮转验证"""

    def test_json_file_backend_supports_rotation(self):
        """JsonFileBackend 支持轮转参数"""
        from self_evolving_agent.core.logging import JsonFileBackend
        sig = inspect.signature(JsonFileBackend.__init__)
        assert "max_bytes" in sig.parameters
        assert "backup_count" in sig.parameters

    def test_main_py_has_setup_logging(self):
        """main.py 有 _setup_logging"""
        main_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py")
        with open(main_path) as f:
            content = f.read()
        assert "_setup_logging" in content
        assert "LOG_LEVEL" in content

    def test_rotation_actually_works(self):
        """轮转实际生效"""
        import tempfile
        from self_evolving_agent.core.logging import JsonFileBackend, LogLevel, LogRecord
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            backend = JsonFileBackend(
                filepath=log_file, min_level=LogLevel.DEBUG,
                max_bytes=100, backup_count=2, enable_rotation=True)
            for i in range(20):
                backend.write(LogRecord(message=f"msg{i}" * 10, level=LogLevel.INFO, source="t"))
            backend.close()
            files = os.listdir(tmpdir)
            assert "test.log.1" in files, f"应有轮转备份: {files}"


class TestStage180_ErrorCodesDoc:
    """阶段180: error_codes.md文档验证"""

    def test_doc_exists(self):
        """docs/error_codes.md 存在"""
        doc_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "docs", "error_codes.md")
        assert os.path.exists(doc_path)

    def test_doc_has_error_codes(self):
        """文档包含错误码"""
        doc_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "docs", "error_codes.md")
        with open(doc_path) as f:
            content = f.read()
        assert "CFG_001" in content
        assert "VAL_002" in content
        assert "SYS_001" in content


class TestStage181_InitDoctorConsistency:
    """阶段181: init/doctor一致性验证"""

    def test_init_checks_dotenv(self):
        """init 检查 dotenv"""
        from cli import CommandHandler
        source = inspect.getsource(CommandHandler.cmd_init)
        assert "dotenv" in source

    def test_doctor_checks_dotenv(self):
        """doctor 检查 dotenv"""
        from cli import CommandHandler
        source = inspect.getsource(CommandHandler.cmd_doctor)
        assert "dotenv" in source

    def test_config_validate_uses_schema(self):
        """config validate 接入 config_schema"""
        from cli import CommandHandler
        source = inspect.getsource(CommandHandler._config_validate)
        assert "config_schema" in source
        assert "create_system_config_schema" in source

    def test_config_validate_checks_port(self):
        """config validate 校验 PORT"""
        from cli import CommandHandler
        source = inspect.getsource(CommandHandler._config_validate)
        assert "PORT" in source


class TestStage182_OpenAPIEnhanced:
    """阶段182: OpenAPI文档增强验证"""

    @pytest.fixture
    def openapi_spec(self):
        from main import app
        client = app.test_client()
        response = client.get("/api/docs/openapi")
        return response.get_json()

    def test_has_components_schemas(self, openapi_spec):
        """有components.schemas"""
        assert "components" in openapi_spec
        assert "ErrorResponse" in openapi_spec["components"]["schemas"]

    def test_has_servers(self, openapi_spec):
        """有servers"""
        assert "servers" in openapi_spec

    def test_error_response_has_error_code(self, openapi_spec):
        """错误响应Schema有error_code"""
        schema = openapi_spec["components"]["schemas"]["ErrorResponse"]
        assert "error_code" in schema["properties"]


class TestFirstPrinciples:
    """第一性原理验证"""

    def test_discoverability(self):
        """可发现性: 命令可通过 --help 发现"""
        result = subprocess.run(
            [sys.executable, "cli.py", "--help"],
            capture_output=True, text=True, timeout=15,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0
        assert "doctor" in result.stdout
        assert "config" in result.stdout
        assert "logs" in result.stdout

    def test_feedback(self):
        """反馈性: 耗时操作有进度反馈"""
        cli_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cli.py")
        with open(cli_path) as f:
            content = f.read()
        assert "self.fmt.progress" in content

    def test_consistency(self):
        """一致性: API错误响应格式统一"""
        import importlib
        all_modules = [
            "api.core_routes", "api.llm_routes", "api.rag_routes",
            "api.task_routes", "api.code_routes", "api.config_routes",
        ]
        for mod_path in all_modules:
            module = importlib.import_module(mod_path)
            source = inspect.getsource(module)
            assert "api_error_response" in source

    def test_graceful_degradation(self):
        """优雅降级: .env不存在时不崩溃"""
        from self_evolving_agent.core.env_loader import load_env
        result = load_env(env_path="/nonexistent/.env", verbose=False)
        assert result == {}

    def test_self_diagnosis(self):
        """自诊断: doctor命令可运行"""
        result = subprocess.run(
            [sys.executable, "cli.py", "doctor"],
            capture_output=True, text=True, timeout=30,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode in (0, 1)
        assert "Traceback" not in result.stderr


class TestUsabilityResults:
    """逐阶段成果验证"""

    def test_stage174_result(self):
        """阶段174成果: CLI无阻断性Bug"""
        # cmd_logs json格式可用
        result = subprocess.run(
            [sys.executable, "cli.py", "--format", "json", "logs", "--limit", "1"],
            capture_output=True, text=True, timeout=30,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert "AttributeError" not in result.stderr

    def test_stage175_result(self):
        """阶段175成果: .env自动加载"""
        from self_evolving_agent.core.env_loader import load_env, is_env_loaded
        assert callable(load_env)
        assert callable(is_env_loaded)

    def test_stage176_result(self):
        """阶段176成果: deploy.sh可执行"""
        deploy_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "deploy.sh")
        result = subprocess.run(["bash", "-n", deploy_path], capture_output=True, text=True)
        assert result.returncode == 0

    def test_stage177_result(self):
        """阶段177成果: API错误响应统一"""
        from self_evolving_agent.core.error_response import api_error_response
        resp, status = api_error_response("missing_field", "test")
        assert "error_code" in resp
        assert "suggested_action" in resp

    def test_stage178_result(self):
        """阶段178成果: 进度反馈"""
        from cli import OutputFormatter
        fmt = OutputFormatter()
        pi = fmt.progress("test")
        assert hasattr(pi, "__enter__")
        assert hasattr(pi, "__exit__")

    def test_stage179_result(self):
        """阶段179成果: 日志轮转"""
        from self_evolving_agent.core.logging import JsonFileBackend
        sig = inspect.signature(JsonFileBackend.__init__)
        assert "max_bytes" in sig.parameters
        assert "backup_count" in sig.parameters

    def test_stage180_result(self):
        """阶段180成果: 错误码文档"""
        doc_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "docs", "error_codes.md")
        assert os.path.exists(doc_path)

    def test_stage181_result(self):
        """阶段181成果: init/doctor一致"""
        from cli import CommandHandler
        init_src = inspect.getsource(CommandHandler.cmd_init)
        doctor_src = inspect.getsource(CommandHandler.cmd_doctor)
        for dep in ["flask", "flask_cors", "numpy", "psutil", "dotenv"]:
            assert dep in init_src, f"init应检查{dep}"
            assert dep in doctor_src, f"doctor应检查{dep}"

    def test_stage182_result(self):
        """阶段182成果: OpenAPI增强"""
        from main import app
        client = app.test_client()
        response = client.get("/api/docs/openapi")
        spec = response.get_json()
        assert "components" in spec
        assert "servers" in spec


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
