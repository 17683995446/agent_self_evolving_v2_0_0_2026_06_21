from flask import Blueprint, request, jsonify

from .shared import ensure_agent
from self_evolving_agent.core.error_response import api_error_response

recovery_bp = Blueprint("recovery", __name__)


@recovery_bp.route("/api/recovery/execute", methods=["POST"])
def recovery_execute():
    """带恢复策略执行操作"""
    agent = ensure_agent()
    data = request.get_json() or {}
    operation = data.get("operation")
    if not operation:
        resp, status = api_error_response("missing_field", "Missing 'operation'")
        return jsonify(resp), status
    # 注意：通过API无法传递可调用函数，此端点仅用于查询
    resp, status = api_error_response("interface_not_found", "Use SDK to execute functions with recovery")
    return jsonify(resp), status


@recovery_bp.route("/api/recovery/errors", methods=["GET"])
def recovery_errors():
    """获取错误历史"""
    agent = ensure_agent()
    component = request.args.get("component")
    limit = int(request.args.get("limit", 100))
    errors = agent.get_error_history(component=component, limit=limit)
    return jsonify({"errors": errors, "count": len(errors)})


@recovery_bp.route("/api/recovery/errors/count", methods=["GET"])
def recovery_error_count():
    """获取错误数"""
    agent = ensure_agent()
    component = request.args.get("component")
    count = agent.get_error_count(component)
    return jsonify({"count": count})


@recovery_bp.route("/api/recovery/errors", methods=["DELETE"])
def recovery_clear_errors():
    """清空错误历史"""
    agent = ensure_agent()
    agent.clear_errors()
    return jsonify({"cleared": True})


@recovery_bp.route("/api/recovery/health", methods=["GET"])
def recovery_health():
    """获取健康状态"""
    agent = ensure_agent()
    component = request.args.get("component")
    if component:
        health = agent.check_recovery_health(component)
    else:
        health = agent.get_system_health()
    return jsonify(health)


@recovery_bp.route("/api/recovery/health/<component>", methods=["POST"])
def recovery_check_component(component):
    """检查单个组件健康"""
    agent = ensure_agent()
    health = agent.check_recovery_health(component)
    return jsonify(health)


@recovery_bp.route("/api/recovery/stats", methods=["GET"])
def recovery_stats():
    """获取恢复统计"""
    agent = ensure_agent()
    return jsonify(agent.get_recovery_stats())


@recovery_bp.route("/api/recovery/strategies", methods=["GET"])
def recovery_strategies():
    """获取恢复策略列表"""
    agent = ensure_agent()
    stats = agent.get_recovery_stats()
    strategies = stats.get("strategies", {})
    return jsonify({"strategies": list(strategies.keys()), "stats": strategies})


@recovery_bp.route("/api/recovery/health-monitoring/start", methods=["POST"])
def recovery_start_monitoring():
    """启动健康监控"""
    agent = ensure_agent()
    agent.start_health_monitoring()
    return jsonify({"monitoring": True})


@recovery_bp.route("/api/recovery/health-monitoring/stop", methods=["POST"])
def recovery_stop_monitoring():
    """停止健康监控"""
    agent = ensure_agent()
    agent.stop_health_monitoring()
    return jsonify({"monitoring": False})
