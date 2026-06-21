from flask import Blueprint, jsonify, request

from .shared import get_coordinator
from self_evolving_agent.core.error_response import api_error_response

llm_bp = Blueprint("llm", __name__)


@llm_bp.route("/api/llm/parse", methods=["POST"])
def llm_parse():
    """自然语言解析接口"""
    if get_coordinator() is None or get_coordinator()._llm is None:
        resp, status = api_error_response("config_invalid", "LLM服务未初始化（需配置SILICONFLOW_API_KEY）")
        return jsonify(resp), status

    data = request.get_json() or {}
    text = data.get("text", "")

    if not text:
        resp, status = api_error_response("missing_field", "text字段必填")
        return jsonify(resp), status

    parsed = get_coordinator()._llm.parse_observation(text)
    return jsonify({"parsed": parsed})


@llm_bp.route("/api/llm/create", methods=["POST"])
def llm_create():
    """创意生成接口"""
    if get_coordinator() is None or get_coordinator()._llm is None:
        resp, status = api_error_response("config_invalid", "LLM服务未初始化（需配置SILICONFLOW_API_KEY）")
        return jsonify(resp), status

    data = request.get_json() or {}
    concepts = data.get("concepts", [])
    context = data.get("context")

    if not concepts:
        resp, status = api_error_response("missing_field", "concepts字段必填")
        return jsonify(resp), status

    ideas = get_coordinator()._llm.assist_creation(concepts, context)
    return jsonify({"ideas": ideas})


@llm_bp.route("/api/llm/diagnose", methods=["POST"])
def llm_diagnose():
    """异常诊断接口"""
    if get_coordinator() is None or get_coordinator()._llm is None:
        resp, status = api_error_response("config_invalid", "LLM服务未初始化（需配置SILICONFLOW_API_KEY）")
        return jsonify(resp), status

    data = request.get_json() or {}
    metrics = data.get("metrics", {})

    if not metrics:
        resp, status = api_error_response("missing_field", "metrics字段必填")
        return jsonify(resp), status

    diagnosis = get_coordinator()._llm.diagnose_anomaly(metrics)
    return jsonify({"diagnosis": diagnosis})


@llm_bp.route("/api/llm/strategy", methods=["POST"])
def llm_strategy():
    """策略生成接口"""
    if get_coordinator() is None or get_coordinator()._llm is None:
        resp, status = api_error_response("config_invalid", "LLM服务未初始化（需配置SILICONFLOW_API_KEY）")
        return jsonify(resp), status

    data = request.get_json() or {}
    context = data.get("context", {})
    objective = data.get("objective", "")

    if not objective:
        resp, status = api_error_response("missing_field", "objective字段必填")
        return jsonify(resp), status

    strategy = get_coordinator()._llm.generate_strategy(context, objective)
    return jsonify({"strategy": strategy})


@llm_bp.route("/api/llm/qa", methods=["POST"])
def llm_qa():
    """知识问答接口"""
    if get_coordinator() is None or get_coordinator()._llm is None:
        resp, status = api_error_response("config_invalid", "LLM服务未初始化（需配置SILICONFLOW_API_KEY）")
        return jsonify(resp), status

    data = request.get_json() or {}
    question = data.get("question", "")
    docs = data.get("docs")

    if not question:
        resp, status = api_error_response("missing_field", "question字段必填")
        return jsonify(resp), status

    answer = get_coordinator()._llm.knowledge_qa(question, docs)
    return jsonify({"answer": answer})


@llm_bp.route("/api/llm/code", methods=["POST"])
def llm_code():
    """代码生成接口"""
    if get_coordinator() is None or get_coordinator()._llm is None:
        resp, status = api_error_response("config_invalid", "LLM服务未初始化（需配置SILICONFLOW_API_KEY）")
        return jsonify(resp), status

    data = request.get_json() or {}
    description = data.get("description", "")
    language = data.get("language", "python")

    if not description:
        resp, status = api_error_response("missing_field", "description字段必填")
        return jsonify(resp), status

    code = get_coordinator()._llm.generate_code(description, language)
    return jsonify({"code": code, "language": language})


@llm_bp.route("/api/llm/code/analyze", methods=["POST"])
def llm_code_analyze():
    """代码分析接口"""
    if get_coordinator() is None or get_coordinator()._llm is None:
        resp, status = api_error_response("config_invalid", "LLM服务未初始化（需配置SILICONFLOW_API_KEY）")
        return jsonify(resp), status

    data = request.get_json() or {}
    code = data.get("code", "")

    if not code:
        resp, status = api_error_response("missing_field", "code字段必填")
        return jsonify(resp), status

    analysis = get_coordinator()._llm.analyze_code(code)
    return jsonify({"analysis": analysis})


@llm_bp.route("/api/llm/explain", methods=["POST"])
def llm_explain():
    """预测解释接口"""
    if get_coordinator() is None or get_coordinator()._llm is None:
        resp, status = api_error_response("config_invalid", "LLM服务未初始化（需配置SILICONFLOW_API_KEY）")
        return jsonify(resp), status

    data = request.get_json() or {}
    prediction = data.get("prediction", {})
    actual = data.get("actual", {})

    explanation = get_coordinator()._llm.explain_prediction(prediction, actual)
    return jsonify({"explanation": explanation})


@llm_bp.route("/api/llm/memory/chat", methods=["POST"])
def llm_memory_chat():
    """带记忆的多轮对话接口"""
    if get_coordinator() is None or get_coordinator()._llm is None:
        resp, status = api_error_response("config_invalid", "LLM服务未初始化（需配置SILICONFLOW_API_KEY）")
        return jsonify(resp), status

    data = request.get_json() or {}
    message = data.get("message", "")
    system_prompt = data.get("system_prompt")
    clear_history = data.get("clear_history", False)

    if not message:
        resp, status = api_error_response("missing_field", "message字段必填")
        return jsonify(resp), status

    response = get_coordinator()._llm.chat_with_memory(message, system_prompt, clear_history)
    return jsonify({
        "response": response,
        "history": get_coordinator()._llm.get_conversation_history(),
    })


@llm_bp.route("/api/llm/memory/clear", methods=["POST"])
def llm_memory_clear():
    """清空对话历史"""
    if get_coordinator() is None or get_coordinator()._llm is None:
        resp, status = api_error_response("config_invalid", "LLM服务未初始化（需配置SILICONFLOW_API_KEY）")
        return jsonify(resp), status

    get_coordinator()._llm.clear_conversation_history()
    return jsonify({"status": "cleared"})


@llm_bp.route("/api/llm/batch", methods=["POST"])
def llm_batch():
    """批量处理接口"""
    if get_coordinator() is None or get_coordinator()._llm is None:
        resp, status = api_error_response("config_invalid", "LLM服务未初始化（需配置SILICONFLOW_API_KEY）")
        return jsonify(resp), status

    data = request.get_json() or {}
    items = data.get("items", [])
    task = data.get("task", "")

    if not items or not task:
        resp, status = api_error_response("missing_field", "items和task字段必填")
        return jsonify(resp), status

    results = get_coordinator()._llm.batch_process(items, task)
    return jsonify({"results": results})
