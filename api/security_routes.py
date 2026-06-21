from flask import Blueprint, request, jsonify

from .shared import ensure_agent
from self_evolving_agent.core.error_response import api_error_response

security_bp = Blueprint("security", __name__)


@security_bp.route("/api/security/users", methods=["GET"])
def security_list_users():
    """列出所有用户"""
    agent = ensure_agent()
    users = agent.list_users()
    return jsonify({"users": [u.to_dict() for u in users]})


@security_bp.route("/api/security/users", methods=["POST"])
def security_create_user():
    """创建用户"""
    agent = ensure_agent()
    data = request.get_json() or {}
    username = data.get("username")
    roles = set(data.get("roles", ["viewer"]))
    password = data.get("password")
    api_key = data.get("api_key")

    if not username:
        resp, status = api_error_response("missing_field", "Missing 'username'")
        return jsonify(resp), status

    user = agent.create_user(username, roles, password=password, api_key=api_key)
    return jsonify({"user_id": user.user_id, "username": user.username}), 201


@security_bp.route("/api/security/users/<user_id>", methods=["DELETE"])
def security_delete_user(user_id):
    """删除用户"""
    agent = ensure_agent()
    if agent.delete_user(user_id):
        return jsonify({"deleted": user_id})
    resp, status = api_error_response("not_found", "User not found")
    return jsonify(resp), status


@security_bp.route("/api/security/users/<user_id>/roles", methods=["POST"])
def security_assign_role(user_id):
    """分配角色"""
    agent = ensure_agent()
    data = request.get_json() or {}
    role = data.get("role")
    if not role:
        resp, status = api_error_response("missing_field", "Missing 'role'")
        return jsonify(resp), status
    if agent.assign_role(user_id, role):
        return jsonify({"assigned": role, "user_id": user_id})
    return jsonify({"error": "User not found"}), 404


@security_bp.route("/api/security/authenticate", methods=["POST"])
def security_authenticate():
    """认证"""
    agent = ensure_agent()
    data = request.get_json() or {}
    method = data.get("method", "api_key")
    credentials = data.get("credentials", {})

    result = agent.authenticate(method, credentials)
    if result.success:
        return jsonify({"authenticated": True, "user_id": result.user.user_id, "username": result.user.username})
    return jsonify({"authenticated": False, "error": result.error}), 401


@security_bp.route("/api/security/users/<user_id>/api-key", methods=["POST"])
def security_create_api_key(user_id):
    """为用户创建API Key"""
    agent = ensure_agent()
    api_key = agent.create_api_key(user_id)
    if api_key:
        return jsonify({"api_key": api_key, "user_id": user_id})
    return jsonify({"error": "User not found"}), 404


@security_bp.route("/api/security/api-keys/<api_key>", methods=["DELETE"])
def security_revoke_api_key(api_key):
    """撤销API Key"""
    agent = ensure_agent()
    if agent.revoke_api_key(api_key):
        return jsonify({"revoked": api_key[:8] + "..."})
    return jsonify({"error": "API key not found"}), 404


@security_bp.route("/api/security/users/<user_id>/token", methods=["POST"])
def security_issue_token(user_id):
    """发放Bearer Token"""
    agent = ensure_agent()
    data = request.get_json() or {}
    expires_in = data.get("expires_in", 3600)
    token = agent.issue_token(user_id, expires_in=expires_in)
    if token:
        return jsonify({"token": token, "expires_in": expires_in})
    return jsonify({"error": "User not found"}), 404


@security_bp.route("/api/security/audit", methods=["GET"])
def security_audit_events():
    """获取审计事件"""
    agent = ensure_agent()
    event_type = request.args.get("event_type")
    user_id = request.args.get("user_id")
    limit = int(request.args.get("limit", 100))
    events = agent.get_audit_events(
        event_type=event_type,
        user_id=user_id,
        limit=limit,
    )
    return jsonify({"events": events, "count": len(events)})


@security_bp.route("/api/security/stats", methods=["GET"])
def security_stats():
    """获取安全统计"""
    agent = ensure_agent()
    return jsonify(agent.get_security_stats())


@security_bp.route("/api/security/rate-limit", methods=["POST"])
def security_check_rate_limit():
    """检查限流"""
    agent = ensure_agent()
    data = request.get_json() or {}
    identifier = data.get("identifier")
    if not identifier:
        return jsonify({"error": "Missing 'identifier'"}), 400
    allowed = agent.check_security_rate_limit(identifier)
    if allowed:
        return jsonify({"allowed": True})
    return jsonify({"allowed": False, "error": "Rate limit exceeded"}), 429
