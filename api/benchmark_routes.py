from flask import Blueprint, request, jsonify

from .shared import ensure_agent
from self_evolving_agent.core.error_response import api_error_response

benchmark_bp = Blueprint("benchmark", __name__)


@benchmark_bp.route("/api/benchmark/results", methods=["GET"])
def benchmark_results():
    """获取基准测试结果"""
    agent = ensure_agent()
    results = agent.get_benchmark_results()
    return jsonify({"results": [r.to_dict() for r in results], "count": len(results)})


@benchmark_bp.route("/api/benchmark/results", methods=["DELETE"])
def benchmark_clear_results():
    """清空基准测试结果"""
    agent = ensure_agent()
    agent.clear_benchmark_results()
    return jsonify({"cleared": True})


@benchmark_bp.route("/api/benchmark/summary", methods=["GET"])
def benchmark_summary():
    """获取基准测试摘要"""
    agent = ensure_agent()
    return jsonify(agent.get_benchmark_summary())


@benchmark_bp.route("/api/benchmark/suites", methods=["GET"])
def benchmark_list_suites():
    """列出所有基准测试套件"""
    agent = ensure_agent()
    return jsonify({"suites": agent.list_benchmark_suites()})


@benchmark_bp.route("/api/benchmark/suites/<suite_name>/run", methods=["POST"])
def benchmark_run_suite(suite_name):
    """运行指定基准测试套件"""
    agent = ensure_agent()
    results = agent.run_benchmark_suite(suite_name)
    return jsonify({"results": [r.to_dict() for r in results], "count": len(results)})


@benchmark_bp.route("/api/benchmark/run-all", methods=["POST"])
def benchmark_run_all():
    """运行所有基准测试套件"""
    agent = ensure_agent()
    results = agent.run_all_benchmarks()
    return jsonify({"results": [r.to_dict() for r in results], "count": len(results)})


@benchmark_bp.route("/api/benchmark/baseline", methods=["GET"])
def benchmark_get_baseline():
    """获取性能基线"""
    agent = ensure_agent()
    return jsonify(agent.get_performance_baseline())


@benchmark_bp.route("/api/benchmark/baseline", methods=["POST"])
def benchmark_set_baseline():
    """设置性能基线"""
    agent = ensure_agent()
    data = request.get_json() or {}
    name = data.get("name")
    max_avg_time = data.get("max_avg_time")
    min_ops_per_second = data.get("min_ops_per_second")

    if not name or max_avg_time is None or min_ops_per_second is None:
        resp, status = api_error_response("missing_field", "Missing required fields")
        return jsonify(resp), status

    agent.set_performance_baseline(name, max_avg_time, min_ops_per_second)
    return jsonify({"set": name})
