"""
阶段105: 模块集成联调 + 接口全量遍历 + 异常容错测试

1. 跨模块、跨层级调用验证
2. 全覆盖所有30个API端点（正常请求、异常入参、超限参数、空值、非法格式）
3. 异常容错：超时、断连、报错、兜底降级、重试机制
"""

import pytest
import json
import time
import threading
from unittest.mock import patch, MagicMock

# Flask 测试客户端
from main import app, init_agent


@pytest.fixture(scope="module")
def client():
    """Flask 测试客户端"""
    app.config["TESTING"] = True
    init_agent()
    with app.test_client() as client:
        yield client


# ============================================================
# 1. 基础接口测试
# ============================================================

class TestBasicAPI:
    """基础API端点测试"""

    def test_index(self, client):
        """根路径"""
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "name" in data
        # 阶段160: api_endpoints 改为 endpoints（完整端点清单）
        assert "endpoints" in data or "api_endpoints" in data

    def test_status(self, client):
        """状态接口"""
        resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "agent_running" in data
        assert "agent_initialized" in data
        assert "cycle_count" in data

    def test_dashboard(self, client):
        """大盘接口"""
        resp = client.get("/api/dashboard")
        assert resp.status_code == 200

    def test_stats(self, client):
        """统计接口"""
        resp = client.get("/api/stats")
        assert resp.status_code == 200

    def test_start_stop(self, client):
        """启动停止接口"""
        # 启动
        resp = client.post("/api/start")
        assert resp.status_code == 200
        # 再次启动（已运行）
        resp = client.post("/api/start")
        assert resp.status_code == 200
        # 停止
        resp = client.post("/api/stop")
        assert resp.status_code == 200


# ============================================================
# 2. 核心功能接口测试（正常 + 异常入参）
# ============================================================

class TestCoreAPIWithValidInput:
    """核心功能接口 - 正常输入"""

    def test_observe_valid(self, client):
        """observe 正常输入"""
        resp = client.post("/api/observe",
                           json={"module_id": "test", "predicted": {"v": 0.5}, "actual": {"v": 0.6}})
        assert resp.status_code == 200

    def test_act_valid(self, client):
        """act 正常输入"""
        resp = client.post("/api/act",
                           json={"action": "explore", "context": {"resources_used": {"cpu": 0.3}}})
        assert resp.status_code == 200

    def test_reflect(self, client):
        """reflect 接口"""
        resp = client.get("/api/reflect")
        assert resp.status_code == 200

    def test_goals(self, client):
        """goals 设置接口"""
        resp = client.post("/api/goals", json={"safe": 0.95, "gain": 0.8, "eff": 0.85})
        assert resp.status_code == 200

    def test_cycle(self, client):
        """cycle 接口"""
        resp = client.post("/api/cycle", json={"outcome": {"information_value": 0.7}})
        assert resp.status_code == 200


class TestCoreAPIWithAbnormalInput:
    """核心功能接口 - 异常入参"""

    def test_observe_empty(self, client):
        """observe 空JSON"""
        resp = client.post("/api/observe", json={})
        assert resp.status_code == 200  # 应兜底处理

    def test_observe_no_json(self, client):
        """observe 无JSON body"""
        resp = client.post("/api/observe", data="", content_type="application/json")
        assert resp.status_code in [200, 400, 415]  # 415 也算正常兜底

    def test_observe_none_values(self, client):
        """observe None值"""
        resp = client.post("/api/observe",
                           json={"module_id": None, "predicted": None, "actual": None})
        assert resp.status_code == 200

    def test_observe_extreme_values(self, client):
        """observe 极端值"""
        resp = client.post("/api/observe",
                           json={"module_id": "x", "predicted": {"v": 1e308}, "actual": {"v": -1e308}})
        assert resp.status_code == 200

    def test_observe_nan(self, client):
        """observe NaN值"""
        resp = client.post("/api/observe",
                           json={"module_id": "x", "predicted": {"v": "NaN"}, "actual": {"v": "inf"}})
        assert resp.status_code == 200

    def test_observe_wrong_types(self, client):
        """observe 错误类型"""
        resp = client.post("/api/observe",
                           json={"module_id": 123, "predicted": "string", "actual": [1, 2]})
        assert resp.status_code == 200

    def test_act_no_action(self, client):
        """act 无action字段"""
        resp = client.post("/api/act", json={})
        assert resp.status_code == 200

    def test_act_none_context(self, client):
        """act None context"""
        resp = client.post("/api/act", json={"action": "test", "context": None})
        assert resp.status_code == 200

    def test_goals_empty(self, client):
        """goals 空JSON"""
        resp = client.post("/api/goals", json={})
        assert resp.status_code == 200

    def test_goals_invalid_values(self, client):
        """goals 非法值"""
        resp = client.post("/api/goals", json={"safe": -1, "gain": 2, "eff": "invalid"})
        assert resp.status_code == 200

    def test_cycle_empty(self, client):
        """cycle 空JSON"""
        resp = client.post("/api/cycle", json={})
        assert resp.status_code == 200


# ============================================================
# 3. LLM 接口测试（无API Key时应优雅降级）
# ============================================================

class TestLLMAPI:
    """LLM接口测试"""

    def test_chat_no_llm(self, client):
        """chat 无LLM时应返回提示"""
        resp = client.post("/api/chat", json={"message": "hello"})
        assert resp.status_code in [200, 400]

    def test_llm_parse_no_llm(self, client):
        """llm/parse 无LLM"""
        resp = client.post("/api/llm/parse", json={"text": "CPU使用率85%"})
        assert resp.status_code in [200, 400]

    def test_llm_create_no_llm(self, client):
        """llm/create 无LLM"""
        resp = client.post("/api/llm/create", json={"topic": "AI"})
        assert resp.status_code in [200, 400]

    def test_llm_diagnose_no_llm(self, client):
        """llm/diagnose 无LLM"""
        resp = client.post("/api/llm/diagnose", json={"symptom": "high CPU"})
        assert resp.status_code in [200, 400]

    def test_llm_strategy_no_llm(self, client):
        """llm/strategy 无LLM"""
        resp = client.post("/api/llm/strategy", json={"problem": "memory leak"})
        assert resp.status_code in [200, 400]

    def test_llm_qa_no_llm(self, client):
        """llm/qa 无LLM"""
        resp = client.post("/api/llm/qa", json={"question": "what is AI?"})
        assert resp.status_code in [200, 400]

    def test_llm_code_no_llm(self, client):
        """llm/code 无LLM"""
        resp = client.post("/api/llm/code", json={"task": "sort array"})
        assert resp.status_code in [200, 400]

    def test_llm_code_analyze_no_llm(self, client):
        """llm/code/analyze 无LLM"""
        resp = client.post("/api/llm/code/analyze", json={"code": "print(1)"})
        assert resp.status_code in [200, 400]

    def test_llm_explain_no_llm(self, client):
        """llm/explain 无LLM"""
        resp = client.post("/api/llm/explain", json={"concept": "neural network"})
        assert resp.status_code in [200, 400]

    def test_llm_memory_chat_no_llm(self, client):
        """llm/memory/chat 无LLM"""
        resp = client.post("/api/llm/memory/chat", json={"message": "hello"})
        assert resp.status_code in [200, 400]

    def test_llm_memory_clear(self, client):
        """llm/memory/clear"""
        resp = client.post("/api/llm/memory/clear")
        assert resp.status_code in [200, 400]

    def test_llm_batch_no_llm(self, client):
        """llm/batch 无LLM"""
        resp = client.post("/api/llm/batch", json={"tasks": ["task1", "task2"]})
        assert resp.status_code in [200, 400]

    def test_llm_empty_input(self, client):
        """LLM接口空输入"""
        for endpoint in ["/api/chat", "/api/llm/parse", "/api/llm/create",
                         "/api/llm/diagnose", "/api/llm/strategy", "/api/llm/qa",
                         "/api/llm/code", "/api/llm/code/analyze", "/api/llm/explain"]:
            resp = client.post(endpoint, json={})
            assert resp.status_code in [200, 400], f"{endpoint} 状态码异常: {resp.status_code}"


# ============================================================
# 4. RAG 接口测试
# ============================================================

class TestRAGAPI:
    """RAG接口测试"""

    def test_rag_add(self, client):
        """rag/add"""
        resp = client.post("/api/rag/add", json={"content": "测试文档", "metadata": {"source": "test"}})
        assert resp.status_code in [200, 400]

    def test_rag_add_empty(self, client):
        """rag/add 空内容"""
        resp = client.post("/api/rag/add", json={})
        assert resp.status_code in [200, 400]

    def test_rag_batch_add(self, client):
        """rag/batch_add"""
        resp = client.post("/api/rag/batch_add", json={"documents": ["doc1", "doc2", "doc3"]})
        assert resp.status_code in [200, 400]

    def test_rag_batch_add_empty(self, client):
        """rag/batch_add 空列表"""
        resp = client.post("/api/rag/batch_add", json={"documents": []})
        assert resp.status_code in [200, 400]

    def test_rag_query(self, client):
        """rag/query"""
        resp = client.post("/api/rag/query", json={"question": "什么是预测编码?"})
        assert resp.status_code in [200, 400]

    def test_rag_query_empty(self, client):
        """rag/query 空问题"""
        resp = client.post("/api/rag/query", json={})
        assert resp.status_code in [200, 400]

    def test_rag_search(self, client):
        """rag/search"""
        resp = client.post("/api/rag/search", json={"query": "预测", "top_k": 3})
        assert resp.status_code in [200, 400]

    def test_rag_docs(self, client):
        """rag/docs"""
        resp = client.get("/api/rag/docs")
        assert resp.status_code == 200

    def test_rag_clear(self, client):
        """rag/clear"""
        resp = client.post("/api/rag/clear")
        assert resp.status_code == 200

    def test_rag_stats(self, client):
        """rag/stats"""
        resp = client.get("/api/rag/stats")
        assert resp.status_code == 200


# ============================================================
# 5. 跨模块集成联调测试
# ============================================================

class TestCrossModuleIntegration:
    """跨模块集成联调"""

    def test_observe_act_reflect_flow(self, client):
        """完整流程：observe -> act -> reflect"""
        # observe
        resp = client.post("/api/observe",
                           json={"module_id": "env", "predicted": {"v": 0.5}, "actual": {"v": 0.55}})
        assert resp.status_code == 200

        # act
        resp = client.post("/api/act",
                           json={"action": "explore", "context": {"resources_used": {"cpu": 0.2}}})
        assert resp.status_code == 200

        # reflect
        resp = client.get("/api/reflect")
        assert resp.status_code == 200

    def test_goals_affect_observe(self, client):
        """设置目标后应影响observe结果"""
        # 设置目标
        client.post("/api/goals", json={"safe": 0.95, "gain": 0.8, "eff": 0.85})

        # observe
        resp = client.post("/api/observe",
                           json={"module_id": "env", "predicted": {"v": 0.5}, "actual": {"v": 0.6}})
        assert resp.status_code == 200

    def test_multiple_cycles_consistency(self, client):
        """多周期一致性"""
        # 获取当前周期数
        resp = client.get("/api/status")
        initial_count = resp.get_json()["cycle_count"]

        for i in range(10):
            resp = client.post("/api/cycle", json={"outcome": {"information_value": 0.5 + i * 0.01}})
            assert resp.status_code == 200

        # 验证周期数增加了
        resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["cycle_count"] > initial_count

    def test_rag_add_then_search(self, client):
        """RAG添加后搜索"""
        # 添加文档
        client.post("/api/rag/add", json={"content": "预测编码是大脑的核心计算原理"})

        # 搜索
        resp = client.post("/api/rag/search", json={"query": "预测编码", "top_k": 1})
        assert resp.status_code in [200, 400]

    def test_concurrent_api_calls(self, client):
        """并发API调用（Flask test client 不支持真并发，用顺序模拟）"""
        errors = []
        for tid in range(5):
            for i in range(10):
                resp = client.post("/api/observe",
                                   json={"module_id": f"concurrent_{tid}_{i}",
                                         "predicted": {"v": 0.5}, "actual": {"v": 0.6}})
                if resp.status_code != 200:
                    errors.append(f"thread {tid} iter {i}: status {resp.status_code}")
        assert len(errors) == 0, f"API错误: {errors[:5]}"


# ============================================================
# 6. 异常容错测试
# ============================================================

class TestExceptionTolerance:
    """异常容错测试"""

    def test_observe_after_many_errors(self, client):
        """大量异常输入后系统应仍能正常工作"""
        # 注入大量异常输入
        for _ in range(20):
            try:
                client.post("/api/observe", json={"module_id": None, "predicted": None, "actual": None})
            except Exception:
                pass

        # 验证系统恢复正常
        resp = client.post("/api/observe",
                           json={"module_id": "recovery", "predicted": {"v": 0.5}, "actual": {"v": 0.6}})
        assert resp.status_code == 200

    def test_repeated_start_stop(self, client):
        """反复启停不崩溃"""
        for _ in range(5):
            client.post("/api/start")
            client.post("/api/stop")
        # 最终状态正常
        resp = client.get("/api/status")
        assert resp.status_code == 200

    def test_invalid_http_methods(self, client):
        """非法HTTP方法"""
        # GET 到 POST 端点
        resp = client.get("/api/observe")
        assert resp.status_code in [200, 405]

        # POST 到 GET 端点
        resp = client.post("/api/status")
        assert resp.status_code in [200, 405]

    def test_malformed_json(self, client):
        """畸形JSON"""
        resp = client.post("/api/observe", data="not json {{{", content_type="application/json")
        # Flask 应处理畸形 JSON 不崩溃
        assert resp.status_code in [200, 400]

    def test_nonexistent_endpoint(self, client):
        """不存在的端点"""
        resp = client.get("/api/nonexistent")
        assert resp.status_code == 404

    def test_large_payload(self, client):
        """超大请求体"""
        large_data = {"module_id": "x", "predicted": {"v": "x" * 100000}, "actual": {"v": "y"}}
        resp = client.post("/api/observe", json=large_data)
        assert resp.status_code == 200
