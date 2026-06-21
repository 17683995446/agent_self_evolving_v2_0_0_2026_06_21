"""
阶段160测试：API自动文档

验证:
1. 根端点返回完整端点清单
2. /api/docs/endpoints 返回按 Blueprint 分组的端点
3. /api/docs/openapi 返回 OpenAPI 3.0 schema
4. 端点数量正确
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


class TestRootEndpoint:
    """验证根端点增强"""

    def test_root_returns_endpoints(self, client):
        """根端点应返回完整端点清单"""
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "endpoints" in data
        assert isinstance(data["endpoints"], list)
        assert len(data["endpoints"]) > 0

    def test_root_has_endpoint_count(self, client):
        """根端点应有端点数量"""
        resp = client.get("/")
        data = resp.get_json()
        assert "endpoint_count" in data
        assert data["endpoint_count"] > 0

    def test_root_has_docs_links(self, client):
        """根端点应有文档链接"""
        resp = client.get("/")
        data = resp.get_json()
        assert "docs" in data
        assert "openapi" in data["docs"]
        assert "endpoints_grouped" in data["docs"]

    def test_root_version_updated(self, client):
        """根端点版本应为 2.0.0"""
        resp = client.get("/")
        data = resp.get_json()
        assert data["version"] == "2.0.0"

    def test_endpoints_have_methods(self, client):
        """端点应包含 HTTP 方法"""
        resp = client.get("/")
        data = resp.get_json()
        for ep in data["endpoints"]:
            assert "methods" in ep
            assert isinstance(ep["methods"], list)

    def test_endpoints_have_path(self, client):
        """端点应包含路径"""
        resp = client.get("/")
        data = resp.get_json()
        for ep in data["endpoints"]:
            assert "path" in ep
            assert ep["path"].startswith("/")


class TestEndpointsGrouped:
    """验证端点分组文档"""

    def test_endpoints_grouped_returns_200(self, client):
        """/api/docs/endpoints 应返回 200"""
        resp = client.get("/api/docs/endpoints")
        assert resp.status_code == 200

    def test_endpoints_grouped_has_groups(self, client):
        """端点分组应包含 groups 字段"""
        resp = client.get("/api/docs/endpoints")
        data = resp.get_json()
        assert "groups" in data
        assert isinstance(data["groups"], dict)

    def test_endpoints_grouped_has_blueprint_count(self, client):
        """端点分组应有 blueprint_count"""
        resp = client.get("/api/docs/endpoints")
        data = resp.get_json()
        assert "blueprint_count" in data
        assert data["blueprint_count"] >= 15  # 至少15个Blueprint

    def test_endpoints_grouped_has_total(self, client):
        """端点分组应有 total_endpoints"""
        resp = client.get("/api/docs/endpoints")
        data = resp.get_json()
        assert "total_endpoints" in data
        assert data["total_endpoints"] > 0

    def test_endpoints_grouped_has_core(self, client):
        """端点分组应包含 core Blueprint"""
        resp = client.get("/api/docs/endpoints")
        data = resp.get_json()
        assert "core" in data["groups"]

    def test_endpoints_grouped_has_production(self, client):
        """端点分组应包含 production Blueprint"""
        resp = client.get("/api/docs/endpoints")
        data = resp.get_json()
        assert "production" in data["groups"]


class TestOpenAPISchema:
    """验证 OpenAPI schema"""

    def test_openapi_returns_200(self, client):
        """/api/docs/openapi 应返回 200"""
        resp = client.get("/api/docs/openapi")
        assert resp.status_code == 200

    def test_openapi_has_version(self, client):
        """OpenAPI 应有版本号"""
        resp = client.get("/api/docs/openapi")
        data = resp.get_json()
        assert data["openapi"] == "3.0.0"

    def test_openapi_has_info(self, client):
        """OpenAPI 应有 info 字段"""
        resp = client.get("/api/docs/openapi")
        data = resp.get_json()
        assert "info" in data
        assert "title" in data["info"]
        assert "version" in data["info"]

    def test_openapi_has_paths(self, client):
        """OpenAPI 应有 paths 字段"""
        resp = client.get("/api/docs/openapi")
        data = resp.get_json()
        assert "paths" in data
        assert isinstance(data["paths"], dict)
        assert len(data["paths"]) > 0

    def test_openapi_has_tags(self, client):
        """OpenAPI 应有 tags 字段"""
        resp = client.get("/api/docs/openapi")
        data = resp.get_json()
        assert "tags" in data
        assert len(data["tags"]) >= 15

    def test_openapi_paths_have_methods(self, client):
        """OpenAPI paths 应有 HTTP 方法"""
        resp = client.get("/api/docs/openapi")
        data = resp.get_json()
        for path, methods in data["paths"].items():
            assert isinstance(methods, dict)
            assert len(methods) > 0

    def test_openapi_path_params_converted(self, client):
        """OpenAPI 应将 Flask 路径参数转换为 {param} 格式"""
        resp = client.get("/api/docs/openapi")
        data = resp.get_json()
        # 检查是否有路径参数被正确转换（不应有 < 或 >）
        for path in data["paths"]:
            assert "<" not in path
            assert ">" not in path


class TestEndpointConsistency:
    """验证端点一致性"""

    def test_root_count_matches_grouped(self, client):
        """根端点的 endpoint_count 应与分组总数一致"""
        resp_root = client.get("/")
        resp_grouped = client.get("/api/docs/endpoints")
        root_data = resp_root.get_json()
        grouped_data = resp_grouped.get_json()
        assert root_data["endpoint_count"] == grouped_data["total_endpoints"]

    def test_openapi_path_count_matches(self, client):
        """OpenAPI 的 paths 数量应与端点数一致"""
        resp_root = client.get("/")
        resp_openapi = client.get("/api/docs/openapi")
        root_data = resp_root.get_json()
        openapi_data = resp_openapi.get_json()
        # paths 数量应等于端点数（每个路径可能对应多个方法）
        assert len(openapi_data["paths"]) <= root_data["endpoint_count"]
