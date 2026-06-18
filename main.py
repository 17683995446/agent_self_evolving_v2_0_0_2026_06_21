"""
自驱永续进化Agent系统 — 部署入口

提供REST API和后台Agent进程的统一入口。
"""

import os
import sys
import json
import time
import threading
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from self_evolving_agent import SelfEvolvingAgent, create_default_agent
from self_evolving_agent.core.system_coordinator import create_coordinator
from self_evolving_agent.core.dashboard import create_dashboard, create_panel, create_widget, WidgetType, create_data_source
from self_evolving_agent.core.llm_service import create_llm_service
from self_evolving_agent.core.vector_store import create_vector_store, create_rag_service

app = Flask(__name__)
CORS(app)

# 全局Agent实例
_agent: SelfEvolvingAgent = None
_coordinator = None
_dashboard = None
_agent_thread: threading.Thread = None
_agent_running = False
_rag = None


def init_agent():
    """初始化Agent"""
    global _agent, _coordinator, _dashboard, _rag

    print("[部署] 初始化自驱永续进化Agent系统...")
    _agent = create_default_agent()
    _agent.initialize({})

    # 初始化LLM服务（如果配置了API Key）
    llm_service = None
    api_key = os.environ.get("SILICONFLOW_API_KEY")
    if api_key:
        model = os.environ.get("SILICONFLOW_MODEL", "Qwen/Qwen2.5-7B-Instruct")
        llm_service = create_llm_service(api_key=api_key, model=model)
        print(f"[部署] LLM服务已启用: {model}")
    else:
        print("[部署] LLM服务未配置（设置 SILICONFLOW_API_KEY 环境变量启用）")

    # 初始化协调器
    _coordinator = create_coordinator("deployed_coordinator", llm_service=llm_service)

    # 初始化RAG服务（向量数据库 + LLM）
    if llm_service:
        _rag = create_rag_service(llm_service=llm_service)
        print("[部署] RAG服务已启用")
    else:
        print("[部署] RAG服务未启用（需要LLM服务）")

    # 初始化监控大盘
    _dashboard = create_dashboard("system_dashboard", "系统监控大盘")
    panel = create_panel("core_metrics", "核心指标")
    panel.add_widget(create_widget("cycle_count", WidgetType.METRIC, "运行周期"))
    panel.add_widget(create_widget("drive_state", WidgetType.GAUGE, "驱力状态"))
    panel.add_widget(create_widget("prediction_error", WidgetType.CHART, "预测误差"))
    _dashboard.add_panel(panel)

    # 数据源
    ds = create_data_source("agent_metrics", "internal")
    ds.register_fetcher("cycle_count", lambda: _agent._cycle_count if _agent else 0)
    ds.register_fetcher("drive_state", lambda: _agent._drive_engine.get_drive_gaps() if _agent and _agent._drive_engine else {})
    _dashboard.add_data_source(ds)

    print("[部署] Agent初始化完成")


def agent_loop():
    """Agent后台主循环"""
    global _agent_running
    _agent_running = True
    print("[部署] Agent后台循环启动")

    while _agent_running:
        try:
            if _agent and _agent._running:
                # 运行一个周期
                _agent._cycle_count += 1
                time.sleep(_agent._cycle_interval)
            else:
                time.sleep(0.1)
        except Exception as e:
            print(f"[部署] Agent循环错误: {e}")
            time.sleep(1)

    print("[部署] Agent后台循环停止")


@app.route("/")
def index():
    return jsonify({
        "name": "自驱永续进化Agent系统",
        "version": "1.0.0",
        "status": "running" if _agent_running else "stopped",
        "llm_enabled": _coordinator._llm is not None if _coordinator else False,
        "api_endpoints": [
            "/api/status",
            "/api/start",
            "/api/stop",
            "/api/observe",
            "/api/act",
            "/api/reflect",
            "/api/dashboard",
            "/api/stats",
            "/api/goals",
            "/api/cycle",
            "/api/chat",
            "/api/llm/parse",
            "/api/llm/create",
            "/api/llm/diagnose",
            "/api/llm/strategy",
            "/api/llm/qa",
            "/api/llm/code",
            "/api/llm/code/analyze",
            "/api/llm/explain",
            "/api/llm/memory/chat",
            "/api/llm/memory/clear",
            "/api/llm/batch",
            "/api/rag/query",
            "/api/rag/add",
            "/api/rag/batch_add",
            "/api/rag/search",
            "/api/rag/docs",
            "/api/rag/clear",
            "/api/rag/stats",
        ]
    })


@app.route("/api/status")
def status():
    return jsonify({
        "agent_running": _agent_running,
        "agent_initialized": _agent is not None,
        "cycle_count": _agent._cycle_count if _agent else 0,
        "timestamp": datetime.now().isoformat(),
    })


@app.route("/api/start", methods=["POST"])
def start_agent():
    global _agent_thread
    if _agent is None:
        init_agent()

    if not _agent_running:
        _agent.start()
        _agent_thread = threading.Thread(target=agent_loop, daemon=True)
        _agent_thread.start()
        return jsonify({"status": "started", "message": "Agent已启动"})
    return jsonify({"status": "already_running", "message": "Agent已在运行"})


@app.route("/api/stop", methods=["POST"])
def stop_agent():
    global _agent_running
    if _agent:
        _agent.stop()
    _agent_running = False
    return jsonify({"status": "stopped", "message": "Agent已停止"})


@app.route("/api/observe", methods=["POST"])
def observe():
    if _coordinator is None:
        return jsonify({"error": "Agent未初始化"}), 400

    data = request.get_json() or {}
    result = _coordinator.observe(data)
    return jsonify({
        "prediction": result.get("prediction").__dict__ if result.get("prediction") else None,
        "error": result.get("error").__dict__ if result.get("error") else None,
    })


@app.route("/api/act", methods=["POST"])
def act():
    if _coordinator is None:
        return jsonify({"error": "Agent未初始化"}), 400

    data = request.get_json() or {}
    action = data.get("action", "default")
    context = data.get("context", {})

    result = _coordinator.act(action, context)
    return jsonify({
        "action_taken": result.get("action_taken"),
        "gaps_count": len(result.get("gaps", [])),
    })


@app.route("/api/reflect")
def reflect():
    if _coordinator is None:
        return jsonify({"error": "Agent未初始化"}), 400

    result = _coordinator.reflect()
    # 序列化
    result["consciousness_contents"] = [c for c in result.get("consciousness_contents", [])]
    # 如果有LLM生成的反思文本，单独返回
    if "reflection_text" in result:
        result["reflection_text"] = result["reflection_text"]
    return jsonify(result)


@app.route("/api/chat", methods=["POST"])
def chat():
    """LLM对话接口"""
    if _coordinator is None or _coordinator._llm is None:
        return jsonify({"error": "LLM服务未初始化"}), 400

    data = request.get_json() or {}
    message = data.get("message", "")
    system_prompt = data.get("system_prompt")

    if not message:
        return jsonify({"error": "message字段必填"}), 400

    response = _coordinator._llm.quick_chat(message, system_prompt)
    return jsonify({
        "response": response,
        "llm_stats": _coordinator._llm.get_stats(),
    })


@app.route("/api/llm/parse", methods=["POST"])
def llm_parse():
    """自然语言解析接口"""
    if _coordinator is None or _coordinator._llm is None:
        return jsonify({"error": "LLM服务未初始化"}), 400

    data = request.get_json() or {}
    text = data.get("text", "")

    if not text:
        return jsonify({"error": "text字段必填"}), 400

    parsed = _coordinator._llm.parse_observation(text)
    return jsonify({"parsed": parsed})


@app.route("/api/llm/create", methods=["POST"])
def llm_create():
    """创意生成接口"""
    if _coordinator is None or _coordinator._llm is None:
        return jsonify({"error": "LLM服务未初始化"}), 400

    data = request.get_json() or {}
    concepts = data.get("concepts", [])
    context = data.get("context")

    if not concepts:
        return jsonify({"error": "concepts字段必填"}), 400

    ideas = _coordinator._llm.assist_creation(concepts, context)
    return jsonify({"ideas": ideas})


@app.route("/api/dashboard")
def dashboard():
    if _dashboard is None:
        return jsonify({"error": "Dashboard未初始化"}), 400

    _dashboard.refresh_all()
    return jsonify(_dashboard.get_snapshot())


@app.route("/api/stats")
def stats():
    if _coordinator is None:
        return jsonify({"error": "Agent未初始化"}), 400

    return jsonify(_coordinator._engine.get_full_stats())


@app.route("/api/goals", methods=["POST"])
def set_goals():
    if _coordinator is None:
        return jsonify({"error": "Agent未初始化"}), 400

    data = request.get_json() or {}
    for goal_type, level in data.items():
        _coordinator.set_goal(goal_type, float(level))

    return jsonify({"status": "goals_set", "goals": data})


@app.route("/api/cycle", methods=["POST"])
def run_cycle():
    if _coordinator is None:
        return jsonify({"error": "Agent未初始化"}), 400

    data = request.get_json() or {}
    result = _coordinator.run_cycle(data)
    return jsonify(result)


@app.route("/api/llm/diagnose", methods=["POST"])
def llm_diagnose():
    """异常诊断接口"""
    if _coordinator is None or _coordinator._llm is None:
        return jsonify({"error": "LLM服务未初始化"}), 400

    data = request.get_json() or {}
    metrics = data.get("metrics", {})

    if not metrics:
        return jsonify({"error": "metrics字段必填"}), 400

    diagnosis = _coordinator._llm.diagnose_anomaly(metrics)
    return jsonify({"diagnosis": diagnosis})


@app.route("/api/llm/strategy", methods=["POST"])
def llm_strategy():
    """策略生成接口"""
    if _coordinator is None or _coordinator._llm is None:
        return jsonify({"error": "LLM服务未初始化"}), 400

    data = request.get_json() or {}
    context = data.get("context", {})
    objective = data.get("objective", "")

    if not objective:
        return jsonify({"error": "objective字段必填"}), 400

    strategy = _coordinator._llm.generate_strategy(context, objective)
    return jsonify({"strategy": strategy})


@app.route("/api/llm/qa", methods=["POST"])
def llm_qa():
    """知识问答接口"""
    if _coordinator is None or _coordinator._llm is None:
        return jsonify({"error": "LLM服务未初始化"}), 400

    data = request.get_json() or {}
    question = data.get("question", "")
    docs = data.get("docs")

    if not question:
        return jsonify({"error": "question字段必填"}), 400

    answer = _coordinator._llm.knowledge_qa(question, docs)
    return jsonify({"answer": answer})


@app.route("/api/llm/code", methods=["POST"])
def llm_code():
    """代码生成接口"""
    if _coordinator is None or _coordinator._llm is None:
        return jsonify({"error": "LLM服务未初始化"}), 400

    data = request.get_json() or {}
    description = data.get("description", "")
    language = data.get("language", "python")

    if not description:
        return jsonify({"error": "description字段必填"}), 400

    code = _coordinator._llm.generate_code(description, language)
    return jsonify({"code": code, "language": language})


@app.route("/api/llm/code/analyze", methods=["POST"])
def llm_code_analyze():
    """代码分析接口"""
    if _coordinator is None or _coordinator._llm is None:
        return jsonify({"error": "LLM服务未初始化"}), 400

    data = request.get_json() or {}
    code = data.get("code", "")

    if not code:
        return jsonify({"error": "code字段必填"}), 400

    analysis = _coordinator._llm.analyze_code(code)
    return jsonify({"analysis": analysis})


@app.route("/api/llm/explain", methods=["POST"])
def llm_explain():
    """预测解释接口"""
    if _coordinator is None or _coordinator._llm is None:
        return jsonify({"error": "LLM服务未初始化"}), 400

    data = request.get_json() or {}
    prediction = data.get("prediction", {})
    actual = data.get("actual", {})

    explanation = _coordinator._llm.explain_prediction(prediction, actual)
    return jsonify({"explanation": explanation})


@app.route("/api/llm/memory/chat", methods=["POST"])
def llm_memory_chat():
    """带记忆的多轮对话接口"""
    if _coordinator is None or _coordinator._llm is None:
        return jsonify({"error": "LLM服务未初始化"}), 400

    data = request.get_json() or {}
    message = data.get("message", "")
    system_prompt = data.get("system_prompt")
    clear_history = data.get("clear_history", False)

    if not message:
        return jsonify({"error": "message字段必填"}), 400

    response = _coordinator._llm.chat_with_memory(message, system_prompt, clear_history)
    return jsonify({
        "response": response,
        "history": _coordinator._llm.get_conversation_history(),
    })


@app.route("/api/llm/memory/clear", methods=["POST"])
def llm_memory_clear():
    """清空对话历史"""
    if _coordinator is None or _coordinator._llm is None:
        return jsonify({"error": "LLM服务未初始化"}), 400

    _coordinator._llm.clear_conversation_history()
    return jsonify({"status": "cleared"})


@app.route("/api/llm/batch", methods=["POST"])
def llm_batch():
    """批量处理接口"""
    if _coordinator is None or _coordinator._llm is None:
        return jsonify({"error": "LLM服务未初始化"}), 400

    data = request.get_json() or {}
    items = data.get("items", [])
    task = data.get("task", "")

    if not items or not task:
        return jsonify({"error": "items和task字段必填"}), 400

    results = _coordinator._llm.batch_process(items, task)
    return jsonify({"results": results})


@app.route("/api/rag/add", methods=["POST"])
def rag_add():
    """添加知识到RAG知识库"""
    if _rag is None:
        return jsonify({"error": "RAG服务未初始化"}), 400

    data = request.get_json() or {}
    doc_id = data.get("doc_id", "")
    content = data.get("content", "")
    metadata = data.get("metadata")

    if not doc_id or not content:
        return jsonify({"error": "doc_id和content字段必填"}), 400

    success = _rag.add_knowledge(doc_id, content, metadata)
    return jsonify({"success": success, "doc_id": doc_id})


@app.route("/api/rag/batch_add", methods=["POST"])
def rag_batch_add():
    """批量添加知识"""
    if _rag is None:
        return jsonify({"error": "RAG服务未初始化"}), 400

    data = request.get_json() or {}
    documents = data.get("documents", [])

    if not documents:
        return jsonify({"error": "documents字段必填"}), 400

    # 转换为元组格式
    docs_tuples = []
    for doc in documents:
        docs_tuples.append((
            doc.get("doc_id", ""),
            doc.get("content", ""),
            doc.get("metadata")
        ))

    count = _rag.add_knowledges(docs_tuples)
    return jsonify({"added_count": count})


@app.route("/api/rag/query", methods=["POST"])
def rag_query():
    """RAG知识库问答"""
    if _rag is None:
        return jsonify({"error": "RAG服务未初始化"}), 400

    data = request.get_json() or {}
    question = data.get("question", "")
    top_k = data.get("top_k", 3)

    if not question:
        return jsonify({"error": "question字段必填"}), 400

    result = _rag.query(question, top_k=top_k)
    return jsonify(result)


@app.route("/api/rag/search", methods=["POST"])
def rag_search():
    """向量搜索"""
    if _rag is None:
        return jsonify({"error": "RAG服务未初始化"}), 400

    data = request.get_json() or {}
    query = data.get("query", "")
    top_k = data.get("top_k", 5)

    if not query:
        return jsonify({"error": "query字段必填"}), 400

    results = _rag.vector_store.search(query, top_k=top_k)
    return jsonify({
        "results": [
            {
                "doc_id": r.doc.doc_id,
                "content": r.doc.content[:200] + "..." if len(r.doc.content) > 200 else r.doc.content,
                "score": r.score,
                "metadata": r.doc.metadata,
            }
            for r in results
        ]
    })


@app.route("/api/rag/docs")
def rag_docs():
    """列出知识库所有文档"""
    if _rag is None:
        return jsonify({"error": "RAG服务未初始化"}), 400

    docs = _rag.vector_store.list_documents()
    return jsonify({"documents": docs, "total": len(docs)})


@app.route("/api/rag/clear", methods=["POST"])
def rag_clear():
    """清空知识库"""
    if _rag is None:
        return jsonify({"error": "RAG服务未初始化"}), 400

    _rag.vector_store.clear()
    return jsonify({"status": "cleared"})


@app.route("/api/rag/stats")
def rag_stats():
    """RAG服务统计"""
    if _rag is None:
        return jsonify({"error": "RAG服务未初始化"}), 400

    return jsonify(_rag.get_stats())


def main():
    """主入口"""
    init_agent()

    port = int(os.environ.get("PORT", 8080))
    host = os.environ.get("HOST", "0.0.0.0")
    debug = os.environ.get("DEBUG", "false").lower() == "true"

    print(f"[部署] 启动API服务: http://{host}:{port}")
    print(f"[部署] 调试模式: {debug}")

    app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == "__main__":
    main()
