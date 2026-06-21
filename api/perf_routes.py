from flask import Blueprint, request, jsonify

from .shared import ensure_agent
from self_evolving_agent.core.error_response import api_error_response

perf_bp = Blueprint("perf", __name__)


# ---- 性能监控（阶段130）----

@perf_bp.route("/api/performance/report")
def performance_report():
    """获取性能报告"""
    agent = ensure_agent()
    return jsonify(agent.get_performance_report())


@perf_bp.route("/api/performance/cache/stats")
def cache_stats():
    """获取缓存统计"""
    agent = ensure_agent()
    return jsonify(agent.get_cache_stats())


@perf_bp.route("/api/performance/cache/invalidate", methods=["POST"])
def cache_invalidate():
    """使缓存失效"""
    agent = ensure_agent()
    data = request.get_json(silent=True) or {}
    key = data.get("key", "")
    agent.cache_invalidate(key)
    return jsonify({"invalidated": key})


@perf_bp.route("/api/performance/profiler")
def profiler_report():
    """获取性能分析报告"""
    agent = ensure_agent()
    return jsonify(agent.get_profiler_report())


@perf_bp.route("/api/performance/reset", methods=["POST"])
def performance_reset():
    """重置性能指标"""
    agent = ensure_agent()
    agent.reset_performance()
    return jsonify({"reset": True})


# ---- 分布式（阶段131）----

@perf_bp.route("/api/distributed/status")
def distributed_status():
    """获取分布式状态"""
    agent = ensure_agent()
    return jsonify(agent.get_cluster_status())


@perf_bp.route("/api/distributed/enable", methods=["POST"])
def distributed_enable():
    """启用分布式模式"""
    agent = ensure_agent()
    data = request.get_json(silent=True) or {}
    node_id = data.get("node_id")
    role = data.get("role", "worker")
    from self_evolving_agent.core.distributed import NodeRole
    try:
        role_enum = NodeRole(role)
    except ValueError:
        role_enum = NodeRole.WORKER
    agent.enable_distributed(node_id=node_id, role=role_enum)
    return jsonify(agent.get_cluster_status())


@perf_bp.route("/api/distributed/state", methods=["GET", "POST"])
def distributed_state():
    """获取/设置分布式状态"""
    agent = ensure_agent()
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        key = data.get("key", "")
        value = data.get("value")
        agent.set_distributed_state(key, value)
        return jsonify({"set": key})
    else:
        key = request.args.get("key", "")
        value = agent.get_distributed_state(key)
        return jsonify({"key": key, "value": value})
