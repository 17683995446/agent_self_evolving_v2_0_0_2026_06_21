from flask import Blueprint, request, jsonify

from .shared import ensure_agent
from self_evolving_agent.core.error_response import api_error_response

production_bp = Blueprint("production", __name__)


# ---- 生产部署（阶段133）----

@production_bp.route("/api/production/status")
def production_status():
    """获取生产状态"""
    agent = ensure_agent()
    return jsonify(agent.get_production_status())


@production_bp.route("/api/production/start", methods=["POST"])
def production_start():
    """启动生产模式"""
    agent = ensure_agent()
    result = agent.start_production()
    return jsonify({"started": result})


@production_bp.route("/api/production/stop", methods=["POST"])
def production_stop():
    """停止生产模式"""
    agent = ensure_agent()
    result = agent.stop_production()
    return jsonify({"stopped": result})


# ---- Kubernetes标准健康探针（根路径）----

@production_bp.route("/health")
def health_full():
    """完整健康检查（Kubernetes标准）"""
    agent = ensure_agent()
    resp = agent.production_health_check()
    return jsonify({
        "status": resp.status,
        "checks": resp.checks,
        "timestamp": resp.timestamp,
    }), resp.code


@production_bp.route("/health/liveness")
def health_liveness():
    """存活探针（Kubernetes liveness）"""
    agent = ensure_agent()
    resp = agent.production_liveness()
    return jsonify({
        "status": resp.status,
        "checks": resp.checks,
        "timestamp": resp.timestamp,
    }), resp.code


@production_bp.route("/health/readiness")
def health_readiness():
    """就绪探针（Kubernetes readiness）"""
    agent = ensure_agent()
    resp = agent.production_readiness()
    return jsonify({
        "status": resp.status,
        "checks": resp.checks,
        "timestamp": resp.timestamp,
    }), resp.code
