import threading
from datetime import datetime

from flask import Blueprint, jsonify, request, current_app

from .shared import (
    agent_loop,
    ensure_agent,
    get_agent,
    get_agent_thread,
    get_coordinator,
    get_dashboard,
    init_agent,
    is_agent_running,
    set_agent_running,
    set_agent_thread,
)
from self_evolving_agent.core.error_response import api_error_response

core_bp = Blueprint("core", __name__)


def _get_all_endpoints():
    """从当前 app 获取所有端点（阶段160: 自动文档）"""
    endpoints = []
    for rule in current_app.url_map.iter_rules():
        if rule.endpoint == "static":
            continue
        methods = sorted(m for m in rule.methods if m not in ("HEAD", "OPTIONS"))
        endpoints.append({
            "path": rule.rule,
            "methods": methods,
            "endpoint": rule.endpoint,
        })
    endpoints.sort(key=lambda e: e["path"])
    return endpoints


def _get_endpoint_groups():
    """按 Blueprint 分组端点（阶段160: 自动文档）"""
    groups = {}
    for rule in current_app.url_map.iter_rules():
        if rule.endpoint == "static":
            continue
        # 提取 blueprint 名（endpoint 格式: blueprint_name.function_name）
        bp_name = rule.endpoint.split(".")[0] if "." in rule.endpoint else "core"
        if bp_name not in groups:
            groups[bp_name] = []
        methods = sorted(m for m in rule.methods if m not in ("HEAD", "OPTIONS"))
        groups[bp_name].append({
            "path": rule.rule,
            "methods": methods,
            "function": rule.endpoint.split(".")[-1] if "." in rule.endpoint else rule.endpoint,
        })
    for bp in groups:
        groups[bp].sort(key=lambda e: e["path"])
    return groups


@core_bp.route("/")
def index():
    """根端点 — 系统概览和完整端点清单（阶段160增强）"""
    endpoints = _get_all_endpoints()
    return jsonify({
        "name": "自驱永续进化Agent系统",
        "version": "2.0.0",
        "status": "running" if is_agent_running() else "stopped",
        "llm_enabled": get_coordinator()._llm is not None if get_coordinator() else False,
        "endpoint_count": len(endpoints),
        "endpoints": endpoints,
        "docs": {
            "openapi": "/api/docs/openapi",
            "endpoints_grouped": "/api/docs/endpoints",
            "health": "/health",
        },
    })


@core_bp.route("/api/docs/endpoints")
def docs_endpoints():
    """端点文档 — 按 Blueprint 分组（阶段160: 自动文档）"""
    groups = _get_endpoint_groups()
    return jsonify({
        "total_endpoints": sum(len(v) for v in groups.values()),
        "blueprint_count": len(groups),
        "groups": groups,
    })


@core_bp.route("/api/docs/openapi")
def docs_openapi():
    """OpenAPI 3.0 Schema（阶段160: 自动文档，阶段182: 增强 Schema/参数/示例）"""
    import re as _re
    endpoints = _get_all_endpoints()
    paths = {}

    # 阶段182: 标准错误响应Schema（与 api_error_response 格式一致）
    error_response_schema = {
        "description": "错误响应",
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "error": {"type": "string", "description": "错误详情"},
                        "error_code": {"type": "string", "description": "错误码（如 VAL_002）"},
                        "category": {
                            "type": "string",
                            "enum": ["SYS", "NET", "VAL", "RES", "LOG", "CFG", "IFC", "SEC"],
                            "description": "错误分类",
                        },
                        "severity": {
                            "type": "string",
                            "enum": ["debug", "info", "warning", "error", "critical", "fatal"],
                        },
                        "recoverable": {"type": "boolean", "description": "是否可恢复"},
                        "suggested_action": {"type": "string", "description": "建议修复操作"},
                    },
                },
            },
        },
    }

    for ep in endpoints:
        path = ep["path"]
        # 将 Flask 路径参数 <name> 转为 OpenAPI 格式 {name}
        openapi_path = path
        path_params = []
        if "<" in path:
            openapi_path = _re.sub(r"<(?:[^:>]+:)?([^>]+)>", r"{\1}", path)
            # 阶段182: 提取路径参数
            for match in _re.finditer(r"<(?:[^:>]+:)?([^>]+)>", path):
                param_name = match.group(1)
                path_params.append({
                    "name": param_name,
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string"},
                    "description": f"路径参数: {param_name}",
                })

        if openapi_path not in paths:
            paths[openapi_path] = {}

        for method in ep["methods"]:
            method_lower = method.lower()
            if method_lower in ("get", "post", "put", "delete", "patch"):
                operation = {
                    "summary": ep["endpoint"].split(".")[-1] if "." in ep["endpoint"] else ep["endpoint"],
                    "operationId": ep["endpoint"].replace(".", "_"),
                    "tags": [ep["endpoint"].split(".")[0] if "." in ep["endpoint"] else "core"],
                    "responses": {
                        "200": {
                            "description": "成功",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object"},
                                },
                            },
                        },
                        "400": error_response_schema,
                        "404": error_response_schema,
                        "500": error_response_schema,
                    },
                }
                # 阶段182: 添加路径参数
                if path_params:
                    operation["parameters"] = path_params
                # 阶段182: POST/PUT 请求体Schema
                if method_lower in ("post", "put", "patch"):
                    operation["requestBody"] = {
                        "required": False,
                        "content": {
                            "application/json": {
                                "schema": {"type": "object"},
                                "example": {},
                            },
                        },
                    }
                paths[openapi_path][method_lower] = operation

    return jsonify({
        "openapi": "3.0.0",
        "info": {
            "title": "自驱永续进化Agent系统 API",
            "version": "2.0.0",
            "description": "基于第一性原理的自驱永续进化Agent系统 REST API\n\n阶段182: 增强文档，包含错误响应Schema、路径参数、请求体结构。",
            "contact": {
                "name": "SelfEvolvingAgent Team",
                "url": "https://github.com/example/self-evolving-agent",
            },
            "license": {"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
        },
        "servers": [
            {"url": "/", "description": "当前服务器"},
            {"url": "http://localhost:8080", "description": "本地开发服务器"},
        ],
        "paths": paths,
        "tags": [
            {"name": bp, "description": f"{bp} 模块端点"}
            for bp in _get_endpoint_groups().keys()
        ],
        "components": {
            "schemas": {
                "ErrorResponse": error_response_schema["content"]["application/json"]["schema"],
            },
        },
    })


@core_bp.route("/api/status")
def status():
    return jsonify({
        "agent_running": is_agent_running(),
        "agent_initialized": get_agent() is not None,
        "cycle_count": (get_coordinator()._cycle_count if get_coordinator() else 0) or (get_agent()._cycle_count if get_agent() else 0),
        "timestamp": datetime.now().isoformat(),
    })


@core_bp.route("/api/start", methods=["POST"])
def start_agent():
    if get_agent() is None:
        init_agent()

    if not is_agent_running():
        ensure_agent().start()
        set_agent_thread(threading.Thread(target=agent_loop, daemon=True))
        get_agent_thread().start()
        return jsonify({"status": "started", "message": "Agent已启动"})
    return jsonify({"status": "already_running", "message": "Agent已在运行"})


@core_bp.route("/api/stop", methods=["POST"])
def stop_agent():
    if get_agent():
        get_agent().stop()
    set_agent_running(False)
    return jsonify({"status": "stopped", "message": "Agent已停止"})


@core_bp.route("/api/observe", methods=["POST"])
def observe():
    if get_coordinator() is None:
        resp, status = api_error_response("config_invalid", "Agent未初始化")
        return jsonify(resp), status

    data = request.get_json() or {}
    try:
        result = get_coordinator().observe(data)
    except Exception as e:
        # 捕获所有异常，返回200以保证API健壮性
        return jsonify({"prediction": None, "error": None, "warning": str(e)})

    if not isinstance(result, dict):
        return jsonify({"prediction": None, "error": None, "warning": "Invalid result"})

    prediction = result.get("prediction")
    error = result.get("error")
    return jsonify({
        "prediction": prediction.__dict__ if prediction and hasattr(prediction, "__dict__") else None,
        "error": error.__dict__ if error and hasattr(error, "__dict__") else None,
    })


@core_bp.route("/api/act", methods=["POST"])
def act():
    if get_coordinator() is None:
        resp, status = api_error_response("config_invalid", "Agent未初始化")
        return jsonify(resp), status

    data = request.get_json() or {}
    action = data.get("action", "default")
    context = data.get("context", {})

    result = get_coordinator().act(action, context)
    return jsonify({
        "action_taken": result.get("action_taken"),
        "gaps_count": len(result.get("gaps", [])),
    })


@core_bp.route("/api/reflect")
def reflect():
    if get_coordinator() is None:
        resp, status = api_error_response("config_invalid", "Agent未初始化")
        return jsonify(resp), status

    result = get_coordinator().reflect()
    # 序列化
    result["consciousness_contents"] = [c for c in result.get("consciousness_contents", [])]
    # 如果有LLM生成的反思文本，单独返回
    if "reflection_text" in result:
        result["reflection_text"] = result["reflection_text"]
    return jsonify(result)


@core_bp.route("/api/chat", methods=["POST"])
def chat():
    """LLM对话接口"""
    if get_coordinator() is None or get_coordinator()._llm is None:
        resp, status = api_error_response("config_invalid", "LLM服务未初始化（需配置SILICONFLOW_API_KEY）")
        return jsonify(resp), status

    data = request.get_json() or {}
    message = data.get("message", "")
    system_prompt = data.get("system_prompt")

    if not message:
        resp, status = api_error_response("missing_field", "message字段必填")
        return jsonify(resp), status

    response = get_coordinator()._llm.quick_chat(message, system_prompt)
    return jsonify({
        "response": response,
        "llm_stats": get_coordinator()._llm.get_stats(),
    })


@core_bp.route("/api/dashboard")
def dashboard():
    if get_dashboard() is None:
        resp, status = api_error_response("config_invalid", "Dashboard未初始化")
        return jsonify(resp), status

    get_dashboard().refresh_all()
    return jsonify(get_dashboard().get_snapshot())


@core_bp.route("/api/stats")
def stats():
    if get_coordinator() is None:
        resp, status = api_error_response("config_invalid", "Agent未初始化")
        return jsonify(resp), status

    return jsonify(get_coordinator()._engine.get_full_stats())


@core_bp.route("/api/goals", methods=["POST"])
def set_goals():
    if get_coordinator() is None:
        resp, status = api_error_response("config_invalid", "Agent未初始化")
        return jsonify(resp), status

    data = request.get_json() or {}
    set_goals = {}
    errors = []
    for goal_type, level in data.items():
        try:
            level_float = float(level)
            get_coordinator().set_goal(goal_type, level_float)
            set_goals[goal_type] = level_float
        except (ValueError, TypeError) as e:
            errors.append({"goal": goal_type, "error": str(e)})

    return jsonify({"status": "goals_set", "goals": set_goals, "errors": errors})


@core_bp.route("/api/cycle", methods=["POST"])
def run_cycle():
    if get_coordinator() is None:
        resp, status = api_error_response("config_invalid", "Agent未初始化")
        return jsonify(resp), status

    data = request.get_json() or {}
    result = get_coordinator().run_cycle(data)
    return jsonify(result)
