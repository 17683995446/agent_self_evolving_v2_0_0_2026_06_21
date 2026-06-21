"""
阶段134: HTTP API扩展 — 专项测试

测试覆盖：
1. 环境接口API
2. 任务执行API
3. 代码审查API
4. 文档生成API
5. 性能监控API
6. 分布式API
7. 可观测性API
8. 生产部署API
9. 健康检查端点
10. 错误处理
11. 第一性原理验证
"""

import json
import pytest
import sys
import os

# 确保能导入main
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def app():
    """Flask应用fixture"""
    # 设置环境变量避免初始化LLM
    os.environ.setdefault("SKIP_LLM_INIT", "true")
    from main import app as flask_app
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    """Flask测试客户端"""
    return app.test_client()


# ============================================================
# 基础端点测试
# ============================================================

class TestBasicEndpoints:
    """基础端点测试"""

    def test_index(self, client):
        """测试首页"""
        response = client.get("/")
        assert response.status_code == 200

    def test_status(self, client):
        """测试状态"""
        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.get_json()
        assert data is not None


# ============================================================
# 环境接口API测试
# ============================================================

class TestEnvironmentAPI:
    """环境接口API测试"""

    def test_env_list(self, client):
        """测试列出环境"""
        response = client.get("/api/env/list")
        assert response.status_code == 200
        data = response.get_json()
        assert "environments" in data


# ============================================================
# 任务执行API测试
# ============================================================

class TestTaskAPI:
    """任务执行API测试"""

    def test_task_submit(self, client):
        """测试提交任务"""
        response = client.post("/api/task/submit", json={
            "goal": "read file /tmp/test.txt",
        })
        assert response.status_code == 200
        data = response.get_json()
        assert "task_id" in data
        assert "status" in data

    def test_task_status(self, client):
        """测试获取任务状态"""
        # 先提交任务
        submit_resp = client.post("/api/task/submit", json={"goal": "list dir /tmp"})
        task_id = submit_resp.get_json()["task_id"]
        # 获取状态
        response = client.get(f"/api/task/{task_id}/status")
        assert response.status_code == 200
        data = response.get_json()
        assert "status" in data

    def test_task_status_not_found(self, client):
        """测试获取不存在任务的状态"""
        response = client.get("/api/task/nonexistent/status")
        assert response.status_code == 404

    def test_task_result_not_found(self, client):
        """测试获取不存在任务的结果"""
        response = client.get("/api/task/nonexistent/result")
        assert response.status_code == 404

    def test_task_execute(self, client):
        """测试同步执行任务"""
        response = client.post("/api/task/execute", json={
            "goal": "observe simulated environment",
        })
        assert response.status_code == 200


# ============================================================
# 代码审查API测试
# ============================================================

class TestCodeReviewAPI:
    """代码审查API测试"""

    def test_review_code(self, client):
        """测试审查代码"""
        code = "def add(a, b):\n    return a + b\n"
        response = client.post("/api/review/code", json={"code": code})
        assert response.status_code == 200
        data = response.get_json()
        assert data is not None

    def test_review_code_with_issues(self, client):
        """测试审查有问题的代码"""
        code = "import os\n\ndef bad():\n    eval('1+1')\n    pass\n"
        response = client.post("/api/review/code", json={"code": code})
        assert response.status_code == 200

    def test_review_file_not_found(self, client):
        """测试审查不存在的文件"""
        response = client.post("/api/review/file", json={
            "file_path": "/nonexistent/file.py"
        })
        assert response.status_code == 500


# ============================================================
# 文档生成API测试
# ============================================================

class TestDocsAPI:
    """文档生成API测试"""

    def test_docs_generate_markdown(self, client):
        """测试生成Markdown文档"""
        code = 'def hello():\n    """Say hello"""\n    print("hello")\n'
        response = client.post("/api/docs/generate", json={
            "code": code,
            "format": "markdown",
        })
        assert response.status_code == 200
        data = response.get_json()
        assert "content" in data
        assert "format" in data
        assert data["format"] == "markdown"

    def test_docs_generate_html(self, client):
        """测试生成HTML文档"""
        code = 'def hello():\n    pass\n'
        response = client.post("/api/docs/generate", json={
            "code": code,
            "format": "html",
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data["format"] == "html"

    def test_docs_generate_invalid_format(self, client):
        """测试无效格式（应回退到markdown）"""
        code = "x = 1\n"
        response = client.post("/api/docs/generate", json={
            "code": code,
            "format": "invalid_format",
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data["format"] == "markdown"

    def test_docs_generate_file_not_found(self, client):
        """测试生成不存在文件的文档"""
        response = client.post("/api/docs/generate_file", json={
            "file_path": "/nonexistent/file.py"
        })
        assert response.status_code == 500


# ============================================================
# 性能监控API测试
# ============================================================

class TestPerformanceAPI:
    """性能监控API测试"""

    def test_performance_report(self, client):
        """测试获取性能报告"""
        response = client.get("/api/performance/report")
        assert response.status_code == 200
        data = response.get_json()
        assert "cache" in data
        assert "metrics" in data

    def test_cache_stats(self, client):
        """测试获取缓存统计"""
        response = client.get("/api/performance/cache/stats")
        assert response.status_code == 200
        data = response.get_json()
        assert "L1" in data

    def test_cache_invalidate(self, client):
        """测试使缓存失效"""
        response = client.post("/api/performance/cache/invalidate", json={
            "key": "test_key"
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data["invalidated"] == "test_key"

    def test_profiler_report(self, client):
        """测试获取性能分析报告"""
        response = client.get("/api/performance/profiler")
        assert response.status_code == 200

    def test_performance_reset(self, client):
        """测试重置性能指标"""
        response = client.post("/api/performance/reset")
        assert response.status_code == 200
        data = response.get_json()
        assert data["reset"] is True


# ============================================================
# 分布式API测试
# ============================================================

class TestDistributedAPI:
    """分布式API测试"""

    def test_distributed_status(self, client):
        """测试获取分布式状态"""
        response = client.get("/api/distributed/status")
        assert response.status_code == 200
        data = response.get_json()
        assert "distributed" in data

    def test_distributed_enable(self, client):
        """测试启用分布式"""
        response = client.post("/api/distributed/enable", json={
            "node_id": "test_node",
            "role": "worker",
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data["distributed"] is True

    def test_distributed_state_get(self, client):
        """测试获取分布式状态"""
        response = client.get("/api/distributed/state?key=test_key")
        assert response.status_code == 200

    def test_distributed_state_set(self, client):
        """测试设置分布式状态"""
        response = client.post("/api/distributed/state", json={
            "key": "test_key",
            "value": "test_value",
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data["set"] == "test_key"


# ============================================================
# 可观测性API测试
# ============================================================

class TestObservabilityAPI:
    """可观测性API测试"""

    def test_observability_dashboard(self, client):
        """测试获取可观测性仪表板"""
        response = client.get("/api/observability/dashboard")
        assert response.status_code == 200
        data = response.get_json()
        assert "service_name" in data

    def test_observability_logs(self, client):
        """测试获取日志"""
        response = client.get("/api/observability/logs")
        assert response.status_code == 200
        data = response.get_json()
        assert "logs" in data

    def test_observability_logs_with_level(self, client):
        """测试按级别获取日志"""
        response = client.get("/api/observability/logs?level=INFO&limit=10")
        assert response.status_code == 200

    def test_observability_health(self, client):
        """测试健康检查"""
        response = client.get("/api/observability/health")
        assert response.status_code == 200
        data = response.get_json()
        assert "overall_status" in data

    def test_observability_alerts(self, client):
        """测试获取活跃告警"""
        response = client.get("/api/observability/alerts")
        assert response.status_code == 200
        data = response.get_json()
        assert "alerts" in data

    def test_observability_trigger_alert(self, client):
        """测试触发告警"""
        response = client.post("/api/observability/alert", json={
            "name": "test_alert",
            "severity": "warning",
            "message": "test message",
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data["name"] == "test_alert"


# ============================================================
# 生产部署API测试
# ============================================================

class TestProductionAPI:
    """生产部署API测试"""

    def test_production_status(self, client):
        """测试获取生产状态"""
        response = client.get("/api/production/status")
        assert response.status_code == 200
        data = response.get_json()
        assert "lifecycle_state" in data

    def test_production_start_stop(self, client):
        """测试启动和停止生产模式"""
        # 启动
        response = client.post("/api/production/start")
        assert response.status_code == 200
        # 停止
        response = client.post("/api/production/stop")
        assert response.status_code == 200


# ============================================================
# 健康检查端点测试
# ============================================================

class TestHealthEndpoints:
    """健康检查端点测试"""

    def test_health_liveness(self, client):
        """测试存活探针"""
        response = client.get("/health/liveness")
        assert response.status_code in (200, 503)
        data = response.get_json()
        assert "status" in data

    def test_health_readiness(self, client):
        """测试就绪探针"""
        response = client.get("/health/readiness")
        assert response.status_code in (200, 503)
        data = response.get_json()
        assert "status" in data

    def test_health_full(self, client):
        """测试完整健康检查"""
        response = client.get("/health")
        assert response.status_code in (200, 503)
        data = response.get_json()
        assert "status" in data
        assert "checks" in data


# ============================================================
# 错误处理测试
# ============================================================

class TestErrorHandling:
    """错误处理测试"""

    def test_404_not_found(self, client):
        """测试404"""
        response = client.get("/api/nonexistent")
        assert response.status_code == 404

    def test_review_code_empty(self, client):
        """测试审查空代码"""
        response = client.post("/api/review/code", json={"code": ""})
        assert response.status_code == 200

    def test_docs_generate_empty_code(self, client):
        """测试生成空代码文档"""
        response = client.post("/api/docs/generate", json={"code": ""})
        assert response.status_code == 200

    def test_task_submit_empty_goal(self, client):
        """测试提交空目标任务"""
        response = client.post("/api/task/submit", json={"goal": ""})
        assert response.status_code == 200


# ============================================================
# 第一性原理验证
# ============================================================

class TestFirstPrinciples:
    """第一性原理验证"""

    def test_api_completeness_principle(self, client):
        """第一性原理：API完整性"""
        # 所有关键能力都有API端点
        endpoints = [
            "/api/env/list",
            "/api/performance/report",
            "/api/distributed/status",
            "/api/observability/dashboard",
            "/api/production/status",
            "/health",
        ]
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code in (200, 503), f"{endpoint} failed"

    def test_restful_design_principle(self, client):
        """第一性原理：RESTful设计"""
        # GET用于获取，POST用于创建/操作
        # 获取状态用GET
        assert client.get("/api/distributed/status").status_code == 200
        # 启用分布式用POST
        assert client.post("/api/distributed/enable", json={}).status_code == 200

    def test_health_probe_separation_principle(self, client):
        """第一性原理：健康探针分离"""
        # Liveness和Readiness分离
        live = client.get("/health/liveness")
        ready = client.get("/health/readiness")
        assert live.status_code in (200, 503)
        assert ready.status_code in (200, 503)

    def test_error_transparency_principle(self, client):
        """第一性原理：错误透明"""
        # 错误应返回有意义的HTTP状态码
        response = client.get("/api/task/nonexistent/result")
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data
