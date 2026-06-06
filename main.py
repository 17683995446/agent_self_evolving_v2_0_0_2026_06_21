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

app = Flask(__name__)
CORS(app)

# 全局Agent实例
_agent: SelfEvolvingAgent = None
_coordinator = None
_dashboard = None
_agent_thread: threading.Thread = None
_agent_running = False


def init_agent():
    """初始化Agent"""
    global _agent, _coordinator, _dashboard

    print("[部署] 初始化自驱永续进化Agent系统...")
    _agent = create_default_agent()
    _agent.initialize({})

    # 初始化协调器
    _coordinator = create_coordinator("deployed_coordinator")

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
        "api_endpoints": [
            "/api/status",
            "/api/start",
            "/api/stop",
            "/api/observe",
            "/api/act",
            "/api/reflect",
            "/api/dashboard",
            "/api/stats",
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
    return jsonify(result)


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
