from flask import Blueprint, jsonify, request

from .shared import ensure_agent
from self_evolving_agent.core.error_response import api_error_response

env_bp = Blueprint("env", __name__)


@env_bp.route("/api/env/list")
def env_list():
    """列出所有已注册环境"""
    agent = ensure_agent()
    envs = agent.env_manager.get_environment_ids()
    return jsonify({"environments": envs})


@env_bp.route("/api/env/<env_id>/observe", methods=["POST"])
def env_observe(env_id):
    """环境感知"""
    agent = ensure_agent()
    data = request.get_json(silent=True) or {}
    result = agent.env_manager.observe(env_id, **data)
    return jsonify(result.to_dict() if hasattr(result, "to_dict") else result)


@env_bp.route("/api/env/<env_id>/act", methods=["POST"])
def env_act(env_id):
    """环境行动"""
    agent = ensure_agent()
    data = request.get_json(silent=True) or {}
    action = data.pop("action", None)
    result = agent.env_manager.act(env_id, action, **data)
    return jsonify(result.to_dict() if hasattr(result, "to_dict") else result)
