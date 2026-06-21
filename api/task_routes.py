from flask import Blueprint, jsonify, request

from .shared import ensure_agent
from self_evolving_agent.core.error_response import api_error_response

task_bp = Blueprint("task", __name__)


@task_bp.route("/api/task/submit", methods=["POST"])
def task_submit():
    """提交任务"""
    agent = ensure_agent()
    data = request.get_json(silent=True) or {}
    goal = data.get("goal", "")
    task_id = agent.submit_task(goal=goal)
    status = agent.get_task_status(task_id)
    return jsonify({
        "task_id": task_id,
        "status": status.value if hasattr(status, "value") else str(status),
    })


@task_bp.route("/api/task/<task_id>/status")
def task_status(task_id):
    """获取任务状态"""
    agent = ensure_agent()
    status = agent.get_task_status(task_id)
    if status is None:
        resp, status = api_error_response("not_found", "Task not found")
        return jsonify(resp), status
    return jsonify({"task_id": task_id, "status": status.value if hasattr(status, "value") else str(status)})


@task_bp.route("/api/task/<task_id>/result")
def task_result(task_id):
    """获取任务结果"""
    agent = ensure_agent()
    result = agent.get_task_result(task_id)
    if result is None:
        resp, status = api_error_response("not_found", "Task not found or not completed")
        return jsonify(resp), status
    return jsonify(result.to_dict() if hasattr(result, "to_dict") else {"result": str(result)})


@task_bp.route("/api/task/execute", methods=["POST"])
def task_execute():
    """同步执行任务"""
    agent = ensure_agent()
    data = request.get_json(silent=True) or {}
    goal = data.get("goal", "")
    result = agent.execute_task(goal=goal)
    return jsonify(result.to_dict() if hasattr(result, "to_dict") else {"result": str(result)})
