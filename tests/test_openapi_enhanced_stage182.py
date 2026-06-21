"""
阶段182: OpenAPI文档增强验证

验证:
1. OpenAPI文档包含错误响应Schema（error_code/category/severity等）
2. 路径参数有描述
3. POST端点有请求体Schema
4. 包含servers信息
5. 包含components.schemas
6. 响应包含content/schema
"""

import os
import sys
import json

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestOpenAPIDocumentation:
    """OpenAPI文档增强验证"""

    @pytest.fixture
    def openapi_spec(self):
        """获取OpenAPI文档"""
        from main import app
        client = app.test_client()
        response = client.get("/api/docs/openapi")
        assert response.status_code == 200
        return response.get_json()

    def test_openapi_version(self, openapi_spec):
        """OpenAPI版本为3.0.0"""
        assert openapi_spec["openapi"] == "3.0.0"

    def test_has_servers(self, openapi_spec):
        """包含servers信息（阶段182新增）"""
        assert "servers" in openapi_spec
        assert len(openapi_spec["servers"]) >= 1

    def test_has_components_schemas(self, openapi_spec):
        """包含components.schemas（阶段182新增）"""
        assert "components" in openapi_spec
        assert "schemas" in openapi_spec["components"]
        assert "ErrorResponse" in openapi_spec["components"]["schemas"]

    def test_error_response_schema_has_error_code(self, openapi_spec):
        """错误响应Schema包含error_code字段"""
        error_schema = openapi_spec["components"]["schemas"]["ErrorResponse"]
        properties = error_schema["properties"]
        assert "error_code" in properties
        assert "category" in properties
        assert "severity" in properties
        assert "recoverable" in properties
        assert "suggested_action" in properties

    def test_error_response_schema_has_enums(self, openapi_spec):
        """错误响应Schema包含枚举值"""
        error_schema = openapi_spec["components"]["schemas"]["ErrorResponse"]
        category_prop = error_schema["properties"]["category"]
        assert "enum" in category_prop
        assert "VAL" in category_prop["enum"]
        assert "SYS" in category_prop["enum"]

    def test_has_contact_info(self, openapi_spec):
        """包含联系信息（阶段182新增）"""
        assert "contact" in openapi_spec["info"]

    def test_has_license_info(self, openapi_spec):
        """包含许可证信息（阶段182新增）"""
        assert "license" in openapi_spec["info"]


class TestPathParameters:
    """路径参数文档验证"""

    @pytest.fixture
    def openapi_spec(self):
        from main import app
        client = app.test_client()
        response = client.get("/api/docs/openapi")
        return response.get_json()

    def test_path_params_documented(self, openapi_spec):
        """含路径参数的端点有parameters文档"""
        paths = openapi_spec["paths"]
        found_path_param = False
        for path, methods in paths.items():
            if "{" in path:
                for method, operation in methods.items():
                    if "parameters" in operation:
                        for param in operation["parameters"]:
                            if param.get("in") == "path":
                                found_path_param = True
                                assert "name" in param
                                assert "schema" in param
        # 至少有一个路径参数被文档化
        assert found_path_param, "应有路径参数被文档化"

    def test_path_params_have_description(self, openapi_spec):
        """路径参数有描述"""
        paths = openapi_spec["paths"]
        for path, methods in paths.items():
            if "{" in path:
                for method, operation in methods.items():
                    if "parameters" in operation:
                        for param in operation["parameters"]:
                            if param.get("in") == "path":
                                assert "description" in param


class TestRequestBodySchema:
    """请求体Schema验证"""

    @pytest.fixture
    def openapi_spec(self):
        from main import app
        client = app.test_client()
        response = client.get("/api/docs/openapi")
        return response.get_json()

    def test_post_endpoints_have_request_body(self, openapi_spec):
        """POST端点有requestBody（阶段182新增）"""
        paths = openapi_spec["paths"]
        post_with_body = 0
        for path, methods in paths.items():
            if "post" in methods:
                operation = methods["post"]
                if "requestBody" in operation:
                    post_with_body += 1
                    assert "content" in operation["requestBody"]
                    assert "application/json" in operation["requestBody"]["content"]
        assert post_with_body > 0, "应有POST端点包含requestBody"

    def test_request_body_has_schema(self, openapi_spec):
        """请求体有schema"""
        paths = openapi_spec["paths"]
        for path, methods in paths.items():
            if "post" in methods:
                operation = methods["post"]
                if "requestBody" in operation:
                    content = operation["requestBody"]["content"]
                    assert "application/json" in content
                    assert "schema" in content["application/json"]


class TestResponseSchema:
    """响应Schema验证"""

    @pytest.fixture
    def openapi_spec(self):
        from main import app
        client = app.test_client()
        response = client.get("/api/docs/openapi")
        return response.get_json()

    def test_responses_have_content(self, openapi_spec):
        """200响应有content（阶段182新增）"""
        paths = openapi_spec["paths"]
        found_content = False
        for path, methods in paths.items():
            for method, operation in methods.items():
                responses = operation.get("responses", {})
                if "200" in responses:
                    resp_200 = responses["200"]
                    if "content" in resp_200:
                        found_content = True
                        assert "application/json" in resp_200["content"]
        assert found_content, "应有200响应包含content"

    def test_error_responses_have_schema(self, openapi_spec):
        """错误响应(400/404/500)有schema（阶段182新增）"""
        paths = openapi_spec["paths"]
        found_error_schema = False
        for path, methods in paths.items():
            for method, operation in methods.items():
                responses = operation.get("responses", {})
                for status in ("400", "404", "500"):
                    if status in responses:
                        resp = responses[status]
                        if "content" in resp:
                            found_error_schema = True
                            assert "application/json" in resp["content"]
        assert found_error_schema, "应有错误响应包含schema"

    def test_operations_have_tags(self, openapi_spec):
        """操作有tags（阶段182新增）"""
        paths = openapi_spec["paths"]
        for path, methods in paths.items():
            for method, operation in methods.items():
                assert "tags" in operation, f"{method} {path} 应有tags"


class TestOpenAPIValid:
    """OpenAPI文档有效性验证"""

    @pytest.fixture
    def openapi_spec(self):
        from main import app
        client = app.test_client()
        response = client.get("/api/docs/openapi")
        return response.get_json()

    def test_spec_is_valid_json(self, openapi_spec):
        """文档是有效JSON"""
        assert isinstance(openapi_spec, dict)

    def test_has_paths(self, openapi_spec):
        """文档有paths"""
        assert "paths" in openapi_spec
        assert len(openapi_spec["paths"]) > 0

    def test_has_info(self, openapi_spec):
        """文档有info"""
        assert "info" in openapi_spec
        assert "title" in openapi_spec["info"]
        assert "version" in openapi_spec["info"]

    def test_has_tags(self, openapi_spec):
        """文档有tags"""
        assert "tags" in openapi_spec
        assert len(openapi_spec["tags"]) > 0

    def test_endpoint_count_reasonable(self, openapi_spec):
        """端点数量合理（应>50）"""
        total_operations = 0
        for path, methods in openapi_spec["paths"].items():
            total_operations += len(methods)
        assert total_operations > 50, f"端点数应>50，实际: {total_operations}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
