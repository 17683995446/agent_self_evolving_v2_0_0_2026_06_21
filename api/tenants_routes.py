from flask import Blueprint, request, jsonify

from .shared import ensure_agent
from self_evolving_agent.core.error_response import api_error_response

tenants_bp = Blueprint("tenants", __name__)


@tenants_bp.route("/api/tenants", methods=["GET"])
def tenants_list():
    """列出租户"""
    agent = ensure_agent()
    state = request.args.get("state")
    tenants = agent.list_tenants()
    if state:
        from self_evolving_agent.core.multi_tenant import TenantState
        try:
            state_enum = TenantState(state)
            tenants = [t for t in tenants if t.state == state_enum]
        except ValueError:
            resp, status = api_error_response("invalid_value", f"Invalid state: {state}")
            return jsonify(resp), status
    return jsonify({"tenants": [t.to_dict() for t in tenants], "count": len(tenants)})


@tenants_bp.route("/api/tenants", methods=["POST"])
def tenants_create():
    """创建租户"""
    agent = ensure_agent()
    data = request.get_json() or {}
    name = data.get("name")
    if not name:
        resp, status = api_error_response("missing_field", "Missing required field: name")
        return jsonify(resp), status

    from self_evolving_agent.core.multi_tenant import ResourceQuota
    quota = None
    quota_data = data.get("quota")
    if quota_data:
        quota = ResourceQuota.from_dict(quota_data)

    try:
        tenant = agent.create_tenant(
            name=name,
            quota=quota,
            metadata=data.get("metadata"),
            tenant_id=data.get("tenant_id"),
            activate=data.get("activate", True),
        )
        return jsonify(tenant.to_dict()), 201
    except ValueError as e:
        resp, status = api_error_response("resource_conflict", str(e))
        return jsonify(resp), status


@tenants_bp.route("/api/tenants/<tenant_id>", methods=["GET"])
def tenants_get(tenant_id):
    """获取租户详情"""
    agent = ensure_agent()
    summary = agent.get_tenant_summary(tenant_id)
    if summary is None:
        resp, status = api_error_response("not_found", "Tenant not found")
        return jsonify(resp), status
    return jsonify(summary)


@tenants_bp.route("/api/tenants/<tenant_id>", methods=["PUT"])
def tenants_update(tenant_id):
    """更新租户"""
    agent = ensure_agent()
    data = request.get_json() or {}

    from self_evolving_agent.core.multi_tenant import ResourceQuota
    quota = None
    quota_data = data.get("quota")
    if quota_data:
        quota = ResourceQuota.from_dict(quota_data)

    tenant = agent.update_tenant(
        tenant_id=tenant_id,
        name=data.get("name"),
        quota=quota,
        metadata=data.get("metadata"),
    )
    if tenant is None:
        return jsonify({"error": "Tenant not found"}), 404
    return jsonify(tenant.to_dict())


@tenants_bp.route("/api/tenants/<tenant_id>", methods=["DELETE"])
def tenants_delete(tenant_id):
    """删除租户"""
    agent = ensure_agent()
    if agent.delete_tenant(tenant_id):
        return jsonify({"deleted": tenant_id})
    return jsonify({"error": "Tenant not found"}), 404


@tenants_bp.route("/api/tenants/<tenant_id>/suspend", methods=["POST"])
def tenants_suspend(tenant_id):
    """暂停租户"""
    agent = ensure_agent()
    if agent.suspend_tenant(tenant_id):
        return jsonify({"suspended": tenant_id})
    return jsonify({"error": "Tenant not found"}), 404


@tenants_bp.route("/api/tenants/<tenant_id>/resume", methods=["POST"])
def tenants_resume(tenant_id):
    """恢复租户"""
    agent = ensure_agent()
    if agent.resume_tenant(tenant_id):
        return jsonify({"resumed": tenant_id})
    return jsonify({"error": "Tenant not found"}), 404


@tenants_bp.route("/api/tenants/<tenant_id>/terminate", methods=["POST"])
def tenants_terminate(tenant_id):
    """终止租户"""
    agent = ensure_agent()
    if agent.terminate_tenant(tenant_id):
        return jsonify({"terminated": tenant_id})
    return jsonify({"error": "Tenant not found"}), 404


@tenants_bp.route("/api/tenants/<tenant_id>/quota", methods=["GET"])
def tenants_check_quota(tenant_id):
    """检查租户配额"""
    agent = ensure_agent()
    resource = request.args.get("resource", "requests_per_minute")
    amount = int(request.args.get("amount", "1"))
    allowed, msg = agent.check_tenant_quota(tenant_id, resource, amount)
    return jsonify({"allowed": allowed, "message": msg, "resource": resource})


@tenants_bp.route("/api/tenants/<tenant_id>/usage", methods=["GET"])
def tenants_get_usage(tenant_id):
    """获取租户资源使用"""
    agent = ensure_agent()
    usage = agent.get_tenant_usage(tenant_id)
    if usage is None:
        return jsonify({"error": "Tenant not found"}), 404
    return jsonify(usage.to_dict())


@tenants_bp.route("/api/tenants/<tenant_id>/data", methods=["GET"])
def tenants_get_data(tenant_id):
    """获取租户数据"""
    agent = ensure_agent()
    key = request.args.get("key")
    if key:
        value = agent.get_tenant_data(tenant_id, key)
        return jsonify({"key": key, "value": value})
    # 返回所有数据
    iso = agent.tenants.get_isolation(tenant_id)
    if iso is None:
        return jsonify({"error": "Tenant not found"}), 404
    return jsonify({"data": iso.get_all_data(tenant_id)})


@tenants_bp.route("/api/tenants/<tenant_id>/data", methods=["POST"])
def tenants_set_data(tenant_id):
    """设置租户数据"""
    agent = ensure_agent()
    data = request.get_json() or {}
    key = data.get("key")
    value = data.get("value")
    if not key:
        return jsonify({"error": "Missing required field: key"}), 400
    if agent.set_tenant_data(tenant_id, key, value):
        return jsonify({"set": key, "tenant_id": tenant_id})
    return jsonify({"error": "Tenant not found"}), 404


@tenants_bp.route("/api/tenants/<tenant_id>/data/<key>", methods=["DELETE"])
def tenants_delete_data(tenant_id, key):
    """删除租户数据"""
    agent = ensure_agent()
    if agent.delete_tenant_data(tenant_id, key):
        return jsonify({"deleted": key})
    return jsonify({"error": "Tenant or key not found"}), 404


@tenants_bp.route("/api/tenants/<tenant_id>/execute", methods=["POST"])
def tenants_execute(tenant_id):
    """在租户作用域内执行操作（仅记录操作）"""
    agent = ensure_agent()
    data = request.get_json() or {}
    operation = data.get("operation", "noop")

    def _op():
        return {"operation": operation, "tenant_id": tenant_id, "executed": True}

    try:
        result = agent.execute_in_tenant(tenant_id, _op)
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 409


@tenants_bp.route("/api/tenants/stats", methods=["GET"])
def tenants_stats():
    """获取租户统计"""
    agent = ensure_agent()
    return jsonify(agent.get_tenant_stats())
