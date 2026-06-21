from flask import Blueprint, request, jsonify

from .shared import ensure_agent
from self_evolving_agent.core.error_response import api_error_response

plugins_bp = Blueprint("plugins", __name__)


# ============================================================
# 阶段135: 插件系统API
# ============================================================

@plugins_bp.route("/api/plugins")
def plugins_list():
    """列出所有插件"""
    agent = ensure_agent()
    return jsonify({"plugins": agent.list_plugins()})


@plugins_bp.route("/api/plugins/<name>/status")
def plugin_status(name):
    """获取插件状态"""
    agent = ensure_agent()
    status = agent.get_plugin_status(name)
    if status is None:
        resp, status_code = api_error_response("not_found", "Plugin not found")
        return jsonify(resp), status_code
    return jsonify({"name": name, "status": status})


@plugins_bp.route("/api/plugins/<name>/health")
def plugin_health(name):
    """获取插件健康状态"""
    agent = ensure_agent()
    result = agent.get_plugin_health(name)
    return jsonify(result.to_dict())


@plugins_bp.route("/api/plugins/health")
def plugins_health_all():
    """获取所有插件健康状态"""
    agent = ensure_agent()
    results = agent.get_all_plugin_health()
    return jsonify({
        "plugins": {name: r.to_dict() for name, r in results.items()}
    })


@plugins_bp.route("/api/plugins/<name>/unload", methods=["POST"])
def plugin_unload(name):
    """卸载插件"""
    agent = ensure_agent()
    success = agent.unload_plugin(name)
    return jsonify({"unloaded": success, "name": name})


@plugins_bp.route("/api/plugins/<name>/reload", methods=["POST"])
def plugin_reload(name):
    """热重载插件"""
    agent = ensure_agent()
    success = agent.reload_plugin(name)
    return jsonify({"reloaded": success, "name": name})


@plugins_bp.route("/api/plugins/<name>/config", methods=["GET", "POST"])
def plugin_config(name):
    """获取/更新插件配置"""
    agent = ensure_agent()
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        valid, errors = agent.update_plugin_config(name, data)
        return jsonify({"valid": valid, "errors": errors})
    else:
        config = agent.get_plugin_config(name)
        if config is None:
            return jsonify({"error": "Plugin config not found"}), 404
        return jsonify({"config": config.to_dict(), "schema": config.schema})


@plugins_bp.route("/api/plugins/<name>/manifest")
def plugin_manifest(name):
    """获取插件清单"""
    agent = ensure_agent()
    manifest = agent.get_plugin_manifest(name)
    if manifest is None:
        return jsonify({"error": "Plugin manifest not found"}), 404
    return jsonify(manifest.to_dict())


@plugins_bp.route("/api/plugins/discover", methods=["POST"])
def plugins_discover():
    """发现并加载目录中的插件"""
    agent = ensure_agent()
    data = request.get_json(silent=True) or {}
    directory = data.get("directory", "")
    results = agent.discover_plugins(directory)
    return jsonify({"results": results})


@plugins_bp.route("/api/plugins/events/subscribe", methods=["POST"])
def plugins_event_subscribe():
    """订阅插件事件（注册回调）"""
    agent = ensure_agent()
    data = request.get_json(silent=True) or {}
    event_type = data.get("event_type", "")
    subscriber_name = data.get("subscriber_name", "api")
    # 注意：HTTP无法直接注册Python回调，这里仅记录订阅意图
    return jsonify({
        "event_type": event_type,
        "subscriber_name": subscriber_name,
        "message": "Subscription recorded (use SDK for callback registration)",
    })


@plugins_bp.route("/api/plugins/events/history")
def plugins_event_history():
    """获取插件事件历史"""
    agent = ensure_agent()
    event_type = request.args.get("event_type")
    limit = int(request.args.get("limit", 100))
    history = agent.plugin_manager.get_event_history(event_type, limit)
    return jsonify({"events": [e.to_dict() for e in history]})


@plugins_bp.route("/api/plugins/stats")
def plugins_stats():
    """获取插件系统统计"""
    agent = ensure_agent()
    return jsonify(agent.get_plugin_stats())
