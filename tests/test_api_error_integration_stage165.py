"""
阶段165测试：API错误响应接入

验证 API 路由实际使用 api_error_response（接入性测试）。
区别于阶段157的"模块存在性测试"。
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def app():
    """Flask app fixture"""
    from main import app, init_agent
    init_agent()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    """测试客户端"""
    return app.test_client()


class TestAPIErrorResponseIntegration:
    """验证 API 路由实际接入 api_error_response"""

    def test_tenants_routes_imports_error_response(self):
        """tenants_routes 应导入 api_error_response"""
        import api.tenants_routes as mod
        # 检查模块源码包含 api_error_response
        import inspect
        source = inspect.getsource(mod)
        assert "api_error_response" in source, "tenants_routes 未接入 api_error_response"

    def test_config_routes_imports_error_response(self):
        """config_routes 应导入 api_error_response"""
        import api.config_routes as mod
        import inspect
        source = inspect.getsource(mod)
        assert "api_error_response" in source, "config_routes 未接入 api_error_response"

    def test_plugins_routes_imports_error_response(self):
        """plugins_routes 应导入 api_error_response"""
        import api.plugins_routes as mod
        import inspect
        source = inspect.getsource(mod)
        assert "api_error_response" in source, "plugins_routes 未接入 api_error_response"

    def test_security_routes_imports_error_response(self):
        """security_routes 应导入 api_error_response"""
        import api.security_routes as mod
        import inspect
        source = inspect.getsource(mod)
        assert "api_error_response" in source, "security_routes 未接入 api_error_response"


class TestAPIErrorResponseStructure:
    """验证 API 错误响应包含结构化字段"""

    def test_missing_field_returns_error_code(self, client):
        """缺少必填字段应返回 error_code"""
        resp = client.post("/api/tenants", json={})
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error_code" in data, "错误响应应包含 error_code"
        assert data["error_code"].startswith("VAL_")

    def test_not_found_returns_error_code(self, client):
        """资源不存在应返回 error_code"""
        resp = client.get("/api/tenants/nonexistent_tenant_id")
        assert resp.status_code == 404
        data = resp.get_json()
        assert "error_code" in data, "错误响应应包含 error_code"

    def test_error_response_has_suggested_action(self, client):
        """错误响应应包含 suggested_action"""
        resp = client.post("/api/tenants", json={})
        data = resp.get_json()
        assert "suggested_action" in data, "错误响应应包含 suggested_action"

    def test_error_response_has_category(self, client):
        """错误响应应包含 category"""
        resp = client.post("/api/tenants", json={})
        data = resp.get_json()
        assert "category" in data, "错误响应应包含 category"

    def test_error_response_has_severity(self, client):
        """错误响应应包含 severity"""
        resp = client.post("/api/tenants", json={})
        data = resp.get_json()
        assert "severity" in data, "错误响应应包含 severity"

    def test_error_response_has_recoverable(self, client):
        """错误响应应包含 recoverable"""
        resp = client.post("/api/tenants", json={})
        data = resp.get_json()
        assert "recoverable" in data, "错误响应应包含 recoverable"


class TestConfigRouteErrorIntegration:
    """验证 config 路由错误响应接入"""

    def test_config_set_missing_value_returns_error_code(self, client):
        """config set 缺少 value 应返回 error_code"""
        resp = client.post("/api/config/test_key", json={})
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error_code" in data

    def test_config_delete_not_found_returns_error_code(self, client):
        """config delete 不存在的 key 应返回 error_code"""
        resp = client.delete("/api/config/nonexistent_key_12345")
        assert resp.status_code == 404
        data = resp.get_json()
        assert "error_code" in data


class TestPluginsRouteErrorIntegration:
    """验证 plugins 路由错误响应接入"""

    def test_plugin_status_not_found_returns_error_code(self, client):
        """plugin status 不存在应返回 error_code"""
        resp = client.get("/api/plugins/nonexistent_plugin/status")
        assert resp.status_code == 404
        data = resp.get_json()
        assert "error_code" in data


class TestSecurityRouteErrorIntegration:
    """验证 security 路由错误响应接入"""

    def test_security_create_user_missing_username(self, client):
        """创建用户缺少 username 应返回 error_code"""
        resp = client.post("/api/security/users", json={})
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error_code" in data

    def test_security_delete_user_not_found(self, client):
        """删除不存在用户应返回 error_code"""
        resp = client.delete("/api/security/users/nonexistent_user_id")
        assert resp.status_code == 404
        data = resp.get_json()
        assert "error_code" in data


class TestErrorResponseConsistency:
    """验证错误响应格式一致性"""

    def test_all_error_responses_have_error_code(self, client):
        """所有错误响应都应有 error_code"""
        # 触发多个不同路由的错误
        error_responses = []
        resp = client.post("/api/tenants", json={})
        error_responses.append(("tenants_create", resp.get_json()))
        resp = client.post("/api/config/test_key", json={})
        error_responses.append(("config_set", resp.get_json()))
        resp = client.get("/api/plugins/nonexistent/status")
        error_responses.append(("plugin_status", resp.get_json()))
        resp = client.post("/api/security/users", json={})
        error_responses.append(("security_create_user", resp.get_json()))

        for name, data in error_responses:
            assert "error_code" in data, f"{name} 的错误响应缺少 error_code"
