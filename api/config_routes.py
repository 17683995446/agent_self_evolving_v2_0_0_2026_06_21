from flask import Blueprint, request, jsonify

from .shared import ensure_agent
from self_evolving_agent.core.error_response import api_error_response

config_bp = Blueprint("config", __name__)


@config_bp.route("/api/config/<path:key>", methods=["GET"])
def config_get(key):
    """获取配置值"""
    agent = ensure_agent()
    value = agent.get_config(key)
    return jsonify({"key": key, "value": value, "exists": agent.has_config(key)})


@config_bp.route("/api/config/<path:key>", methods=["POST"])
def config_set(key):
    """设置配置值"""
    agent = ensure_agent()
    data = request.get_json() or {}
    if "value" not in data:
        resp, status = api_error_response("missing_field", "Missing 'value' field")
        return jsonify(resp), status
    ok, err = agent.set_config(key, data["value"])
    if not ok:
        resp, status = api_error_response("config_invalid", err)
        return jsonify(resp), status
    return jsonify({"key": key, "success": True})


@config_bp.route("/api/config/<path:key>", methods=["DELETE"])
def config_delete(key):
    """删除配置项"""
    agent = ensure_agent()
    ok, err = agent.delete_config(key)
    if not ok:
        resp, status = api_error_response("not_found", err)
        return jsonify(resp), status
    return jsonify({"key": key, "deleted": True})


@config_bp.route("/api/config", methods=["GET"])
def config_list():
    """获取所有配置"""
    agent = ensure_agent()
    return jsonify(agent.get_config_snapshot())


@config_bp.route("/api/config/update", methods=["POST"])
def config_update():
    """批量更新配置"""
    agent = ensure_agent()
    data = request.get_json() or {}
    ok, errors = agent.update_config(data)
    if not ok:
        resp, status = api_error_response("config_invalid", "Validation failed", context={"details": errors})
        return jsonify(resp), status
    return jsonify({"success": True, "updated": len(data)})


@config_bp.route("/api/config/history", methods=["GET"])
def config_history():
    """获取配置变更历史"""
    agent = ensure_agent()
    key = request.args.get("key")
    limit = int(request.args.get("limit", 100))
    return jsonify(agent.get_config_history(key=key, limit=limit))


@config_bp.route("/api/config/rollback/<change_id>", methods=["POST"])
def config_rollback(change_id):
    """回滚配置变更"""
    agent = ensure_agent()
    ok, err = agent.rollback_config(change_id)
    if not ok:
        return jsonify({"error": err}), 400
    return jsonify({"rolled_back": change_id, "success": True})


@config_bp.route("/api/config/watch", methods=["POST"])
def config_watch():
    """监视配置文件"""
    agent = ensure_agent()
    data = request.get_json() or {}
    file_path = data.get("file_path")
    namespace = data.get("namespace", "")
    if not file_path:
        return jsonify({"error": "Missing 'file_path'"}), 400
    ok = agent.watch_config_file(file_path, namespace=namespace)
    if not ok:
        return jsonify({"error": "File not found"}), 404
    return jsonify({"watching": file_path, "namespace": namespace})


@config_bp.route("/api/config/unwatch", methods=["POST"])
def config_unwatch():
    """停止监视配置文件"""
    agent = ensure_agent()
    data = request.get_json() or {}
    file_path = data.get("file_path")
    if not file_path:
        return jsonify({"error": "Missing 'file_path'"}), 400
    agent.unwatch_config_file(file_path)
    return jsonify({"unwatched": file_path})


@config_bp.route("/api/config/reload", methods=["POST"])
def config_reload():
    """通知所有处理器重新加载配置"""
    agent = ensure_agent()
    results = agent.reload_all_config()
    return jsonify({"results": {k: {"success": v[0], "error": v[1]} for k, v in results.items()}})


@config_bp.route("/api/config/stats", methods=["GET"])
def config_stats():
    """获取配置统计"""
    agent = ensure_agent()
    return jsonify(agent.get_config_stats())


@config_bp.route("/api/config/save", methods=["POST"])
def config_save():
    """保存配置到文件"""
    agent = ensure_agent()
    data = request.get_json() or {}
    file_path = data.get("file_path")
    if not file_path:
        return jsonify({"error": "Missing 'file_path'"}), 400
    ok, err = agent.save_config(file_path)
    if not ok:
        return jsonify({"error": err}), 500
    return jsonify({"saved": file_path})


@config_bp.route("/api/config/load", methods=["POST"])
def config_load():
    """从文件加载配置"""
    agent = ensure_agent()
    data = request.get_json() or {}
    file_path = data.get("file_path")
    if not file_path:
        return jsonify({"error": "Missing 'file_path'"}), 400
    ok, errors = agent.load_config(file_path)
    if not ok:
        return jsonify({"error": "Load failed", "details": errors}), 400
    return jsonify({"loaded": file_path})


@config_bp.route("/api/config/subscribe/<path:key>", methods=["POST"])
def config_subscribe(key):
    """订阅配置变更（记录订阅，实际回调通过API无法注册）"""
    # API订阅仅返回当前状态，实际订阅需通过SDK
    agent = ensure_agent()
    return jsonify({"key": key, "subscribed": True, "note": "Use SDK for actual callbacks"})
