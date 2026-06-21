from flask import Blueprint, request, jsonify

from .shared import ensure_agent
from self_evolving_agent.core.error_response import api_error_response

observability_bp = Blueprint("observability", __name__)


# ---- 可观测性（阶段132）----

@observability_bp.route("/api/observability/dashboard")
def observability_dashboard():
    """获取可观测性仪表板"""
    agent = ensure_agent()
    return jsonify(agent.get_observability_dashboard())


@observability_bp.route("/api/observability/logs")
def observability_logs():
    """获取日志"""
    agent = ensure_agent()
    from self_evolving_agent.core.observability import LogLevel
    level_param = request.args.get("level")
    limit = int(request.args.get("limit", 100))
    level = None
    if level_param:
        try:
            level = LogLevel[level_param.upper()]
        except KeyError:
            pass
    logs = agent.get_logs(level=level, limit=limit)
    return jsonify({"logs": [l.to_dict() for l in logs]})


@observability_bp.route("/api/observability/health")
def observability_health():
    """健康检查"""
    agent = ensure_agent()
    result = agent.check_health()
    # 序列化HealthStatus枚举（checks中的值是__dict__，status字段为枚举需转为字符串）
    checks = {}
    for name, check_dict in result.get("checks", {}).items():
        status = check_dict.get("status")
        checks[name] = {
            "name": check_dict.get("name"),
            "status": status.value if hasattr(status, "value") else str(status),
            "message": check_dict.get("message", ""),
            "details": check_dict.get("details", {}),
            "timestamp": check_dict.get("timestamp", 0),
            "duration_ms": check_dict.get("duration_ms", 0),
        }
    return jsonify({
        "overall_status": result.get("overall_status"),
        "checks": checks,
    })


@observability_bp.route("/api/observability/alerts")
def observability_alerts():
    """获取活跃告警"""
    agent = ensure_agent()
    alerts = agent.get_active_alerts()
    return jsonify({"alerts": [a.to_dict() for a in alerts]})


@observability_bp.route("/api/observability/alert", methods=["POST"])
def observability_trigger_alert():
    """触发告警"""
    agent = ensure_agent()
    data = request.get_json(silent=True) or {}
    from self_evolving_agent.core.observability import AlertSeverity
    name = data.get("name", "manual")
    severity_str = data.get("severity", "warning")
    try:
        severity = AlertSeverity(severity_str)
    except ValueError:
        severity = AlertSeverity.WARNING
    message = data.get("message", "")
    alert = agent.trigger_alert(name, severity, message)
    return jsonify(alert.to_dict())
