"""
阶段148: main.py蓝图拆分测试

验证API端点从main.py拆分到api/包的Blueprint模块的正确性。
"""

import pytest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ============================================================
# Blueprint导入测试
# ============================================================

class TestBlueprintImports:
    """Blueprint导入测试"""

    def test_all_blueprints_importable(self):
        from api import (
            core_bp, llm_bp, rag_bp, env_bp, task_bp,
            code_bp, perf_bp, observability_bp, production_bp, plugins_bp,
            config_bp, security_bp, recovery_bp, benchmark_bp, tenants_bp,
        )
        bps = [core_bp, llm_bp, rag_bp, env_bp, task_bp, code_bp, perf_bp,
               observability_bp, production_bp, plugins_bp, config_bp,
               security_bp, recovery_bp, benchmark_bp, tenants_bp]
        assert len(bps) == 15

    def test_core_bp_endpoints(self):
        from api import core_bp
        assert len(core_bp.deferred_functions) >= 12

    def test_llm_bp_endpoints(self):
        from api import llm_bp
        assert len(llm_bp.deferred_functions) >= 11

    def test_rag_bp_endpoints(self):
        from api import rag_bp
        assert len(rag_bp.deferred_functions) >= 7

    def test_tenants_bp_endpoints(self):
        from api import tenants_bp
        assert len(tenants_bp.deferred_functions) >= 15

    def test_config_bp_endpoints(self):
        from api import config_bp
        assert len(config_bp.deferred_functions) >= 14


# ============================================================
# main.py薄入口测试
# ============================================================

class TestMainPyThinEntry:
    """main.py薄入口测试"""

    def test_main_importable(self):
        import main
        assert hasattr(main, "app")

    def test_main_has_app(self):
        import main
        assert main.app is not None

    def test_main_has_main_function(self):
        import main
        assert callable(main.main)

    def test_main_line_count_reduced(self):
        """main.py应大幅缩减（从1770行到<100行）"""
        main_path = PROJECT_ROOT / "main.py"
        line_count = len(main_path.read_text().splitlines())
        assert line_count < 100, f"main.py有{line_count}行，应<100行"

    def test_all_blueprints_registered(self):
        import main
        rules = list(main.app.url_map.iter_rules())
        # 排除/static
        api_rules = [r for r in rules if not str(r).startswith("/static")]
        assert len(api_rules) >= 100  # 至少100个API端点


# ============================================================
# 路由完整性测试
# ============================================================

class TestRouteCompleteness:
    """路由完整性测试"""

    @pytest.fixture(scope="class")
    def app(self):
        import main
        return main.app

    def test_root_route(self, app):
        rules = {str(r) for r in app.url_map.iter_rules()}
        assert "/" in rules

    def test_status_route(self, app):
        rules = {str(r) for r in app.url_map.iter_rules()}
        assert "/api/status" in rules

    def test_tenants_routes(self, app):
        rules = {str(r) for r in app.url_map.iter_rules()}
        assert "/api/tenants" in rules
        assert "/api/tenants/<tenant_id>" in rules

    def test_config_routes(self, app):
        rules = {str(r) for r in app.url_map.iter_rules()}
        assert "/api/config/<path:key>" in rules

    def test_security_routes(self, app):
        rules = {str(r) for r in app.url_map.iter_rules()}
        assert "/api/security/users" in rules
        assert "/api/security/authenticate" in rules

    def test_recovery_routes(self, app):
        rules = {str(r) for r in app.url_map.iter_rules()}
        assert "/api/recovery/execute" in rules
        assert "/api/recovery/health" in rules

    def test_benchmark_routes(self, app):
        rules = {str(r) for r in app.url_map.iter_rules()}
        assert "/api/benchmark/results" in rules
        assert "/api/benchmark/summary" in rules

    def test_llm_routes(self, app):
        rules = {str(r) for r in app.url_map.iter_rules()}
        assert "/api/llm/parse" in rules
        assert "/api/llm/batch" in rules

    def test_rag_routes(self, app):
        rules = {str(r) for r in app.url_map.iter_rules()}
        assert "/api/rag/query" in rules
        assert "/api/rag/stats" in rules

    def test_plugin_routes(self, app):
        rules = {str(r) for r in app.url_map.iter_rules()}
        assert "/api/plugins" in rules
        assert "/api/plugins/stats" in rules


# ============================================================
# API功能测试（通过test client）
# ============================================================

class TestAPIFunctionality:
    """API功能测试"""

    @pytest.fixture(scope="class")
    def client(self):
        import main
        main.app.config["TESTING"] = True
        with main.app.test_client() as client:
            yield client

    def test_root_endpoint(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "name" in data

    def test_status_endpoint(self, client):
        resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "agent_running" in data or "timestamp" in data

    def test_tenants_list_endpoint(self, client):
        resp = client.get("/api/tenants")
        assert resp.status_code == 200

    def test_tenants_stats_endpoint(self, client):
        resp = client.get("/api/tenants/stats")
        assert resp.status_code == 200

    def test_config_get_all(self, client):
        resp = client.get("/api/config")
        assert resp.status_code == 200

    def test_benchmark_results(self, client):
        resp = client.get("/api/benchmark/results")
        assert resp.status_code == 200

    def test_benchmark_summary(self, client):
        resp = client.get("/api/benchmark/summary")
        assert resp.status_code == 200


# ============================================================
# api/包结构测试
# ============================================================

class TestApiPackageStructure:
    """api/包结构测试"""

    def test_api_init_exists(self):
        assert (PROJECT_ROOT / "api" / "__init__.py").exists()

    def test_shared_module_exists(self):
        assert (PROJECT_ROOT / "api" / "shared.py").exists()

    def test_all_route_modules_exist(self):
        modules = [
            "core_routes", "llm_routes", "rag_routes", "env_routes",
            "task_routes", "code_routes", "perf_routes", "observability_routes",
            "production_routes", "plugins_routes", "config_routes",
            "security_routes", "recovery_routes", "benchmark_routes",
            "tenants_routes",
        ]
        for mod in modules:
            path = PROJECT_ROOT / "api" / f"{mod}.py"
            assert path.exists(), f"缺少: api/{mod}.py"

    def test_shared_exports_init_agent(self):
        from api import init_agent
        assert callable(init_agent)

    def test_shared_exports_ensure_agent(self):
        from api import ensure_agent
        assert callable(ensure_agent)

    def test_shared_exports_custom_json_provider(self):
        from api import CustomJSONProvider
        assert CustomJSONProvider is not None


# ============================================================
# 第一性原理验证
# ============================================================

class TestFirstPrinciples:
    """第一性原理验证"""

    def test_single_responsibility_principle(self):
        """第一性原理: 单一职责 — 每个Blueprint只负责一个业务域"""
        from api import core_bp, llm_bp, rag_bp
        assert core_bp.name == "core"
        assert llm_bp.name == "llm"
        assert rag_bp.name == "rag"

    def test_separation_of_concerns_principle(self):
        """第一性原理: 关注点分离 — 入口与路由分离"""
        import main
        # main.py不应包含路由定义
        main_content = (PROJECT_ROOT / "main.py").read_text()
        assert "@app.route" not in main_content
        assert "register_blueprint" in main_content

    def test_modularity_principle(self):
        """第一性原理: 模块化 — 每个域可独立导入"""
        from api.core_routes import core_bp
        from api.tenants_routes import tenants_bp
        from api.security_routes import security_bp
        assert core_bp is not None
        assert tenants_bp is not None
        assert security_bp is not None

    def test_backward_compatibility_principle(self):
        """第一性原理: 向后兼容 — 所有URL路径保持不变"""
        import main
        rules = {str(r) for r in main.app.url_map.iter_rules()}
        # 验证关键路径仍然存在
        required_paths = [
            "/api/status", "/api/tenants", "/api/config",
            "/api/security/users", "/api/benchmark/results",
        ]
        for path in required_paths:
            assert path in rules, f"缺少路径: {path}"
