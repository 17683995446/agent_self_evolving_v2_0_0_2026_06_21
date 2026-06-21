"""
阶段157: 错误码体系接入入口层

提供统一的错误响应构建器，将 error_codes.py 体系接入 CLI 和 API 层。

第一性原理:
1. 错误是接口契约的一部分 — 入口层必须返回结构化错误信息
2. 一致性 — 所有入口（CLI/API）使用统一的错误格式
3. 可诊断性 — 错误响应包含错误码、建议操作，便于用户排查
4. 非侵入式 — 不改变现有业务逻辑，仅增强错误响应
"""

from typing import Any, Dict, Optional, Tuple

from self_evolving_agent.core.error_codes import (
    ErrorCode, AgentError, get_error_registry, create_error,
    ErrorCategory, ErrorSeverity,
    SYS_UNKNOWN_ERROR, SYS_MODULE_NOT_FOUND,
    VAL_INVALID_TYPE, VAL_MISSING_REQUIRED_FIELD, VAL_INVALID_VALUE,
    RES_RESOURCE_LEAK_DETECTED,
    CFG_KEY_NOT_FOUND, CFG_INVALID_VALUE,
    IFC_INTERFACE_NOT_FOUND,
    SEC_UNAUTHORIZED_ACCESS,
)


# ============================================================
# 错误码到 HTTP 状态码的映射
# ============================================================

_SEVERITY_TO_HTTP = {
    ErrorSeverity.DEBUG: 200,
    ErrorSeverity.INFO: 200,
    ErrorSeverity.WARNING: 200,
    ErrorSeverity.ERROR: 400,
    ErrorSeverity.CRITICAL: 500,
    ErrorSeverity.FATAL: 500,
}

_CATEGORY_TO_HTTP = {
    ErrorCategory.SYSTEM: 500,
    ErrorCategory.NETWORK: 503,
    ErrorCategory.VALIDATION: 400,
    ErrorCategory.RESOURCE: 409,
    ErrorCategory.LOGIC: 500,
    ErrorCategory.CONFIG: 400,
    ErrorCategory.INTERFACE: 400,
    ErrorCategory.SECURITY: 401,
}


def error_to_http_status(error: AgentError) -> int:
    """将 AgentError 映射到 HTTP 状态码"""
    # 优先按分类映射
    status = _CATEGORY_TO_HTTP.get(error.error_code.category)
    if status:
        return status
    # 回退到严重级别映射
    return _SEVERITY_TO_HTTP.get(error.error_code.severity, 500)


# ============================================================
# 常用错误码快捷映射
# ============================================================

# 场景 -> (错误码常量, HTTP状态码)
_ERROR_SCENARIOS = {
    "missing_field": (VAL_MISSING_REQUIRED_FIELD, 400),
    "invalid_value": (VAL_INVALID_VALUE, 400),
    "invalid_type": (VAL_INVALID_TYPE, 400),
    "not_found": (CFG_KEY_NOT_FOUND, 404),
    "config_invalid": (CFG_INVALID_VALUE, 400),
    "module_not_found": (SYS_MODULE_NOT_FOUND, 404),
    "interface_not_found": (IFC_INTERFACE_NOT_FOUND, 404),
    "unauthorized": (SEC_UNAUTHORIZED_ACCESS, 401),
    "resource_conflict": (RES_RESOURCE_LEAK_DETECTED, 409),
    "unknown": (SYS_UNKNOWN_ERROR, 500),
}


# ============================================================
# API 错误响应构建器
# ============================================================

def api_error_response(
    scenario: str,
    detail: str = "",
    source: str = "api",
    context: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], int]:
    """
    构建 API 错误响应（Flask 友好）

    Args:
        scenario: 错误场景（如 "missing_field", "not_found"）
        detail: 错误详情（人类可读）
        source: 错误来源模块
        context: 额外上下文

    Returns:
        (response_dict, http_status) — 可直接用于 jsonify(response), status

    示例:
        resp, status = api_error_response("missing_field", "name字段必填")
        return jsonify(resp), status
    """
    if scenario not in _ERROR_SCENARIOS:
        scenario = "unknown"

    error_code, http_status = _ERROR_SCENARIOS[scenario]
    ctx = context or {}
    if detail:
        ctx["detail"] = detail

    agent_error = create_error(
        code=error_code.code,
        source=source,
        **ctx,
    )

    response = {
        "error": detail or agent_error.message,
        "error_code": agent_error.error_code.code,
        "category": agent_error.error_code.category.value,
        "severity": agent_error.error_code.severity.value,
        "recoverable": agent_error.error_code.recoverable,
        "suggested_action": agent_error.error_code.suggested_action,
    }
    if detail:
        response["detail"] = detail

    return response, http_status


def api_exception_response(
    exception: Exception,
    source: str = "api",
    scenario: str = "unknown",
) -> Tuple[Dict[str, Any], int]:
    """
    将异常转换为 API 错误响应

    Args:
        exception: 捕获的异常
        source: 错误来源
        scenario: 错误场景

    Returns:
        (response_dict, http_status)
    """
    # 如果是 AgentException，提取错误信息
    if hasattr(exception, "error") and hasattr(exception.error, "error_code"):
        agent_error = exception.error
        response = {
            "error": agent_error.message,
            "error_code": agent_error.error_code.code,
            "category": agent_error.error_code.category.value,
            "severity": agent_error.error_code.severity.value,
            "recoverable": agent_error.error_code.recoverable,
            "suggested_action": agent_error.error_code.suggested_action,
        }
        return response, error_to_http_status(agent_error)

    # 普通异常
    return api_error_response(scenario, str(exception), source)


# ============================================================
# CLI 错误格式化器
# ============================================================

def cli_error_message(
    scenario: str,
    detail: str = "",
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    构建 CLI 友好的错误消息

    Args:
        scenario: 错误场景
        detail: 错误详情
        context: 额外上下文

    Returns:
        格式化的错误消息字符串

    示例:
        msg = cli_error_message("missing_field", "name字段必填")
        # "Error [VAL_002]: name字段必填
        #  建议操作: 检查输入参数，确保必填字段已提供"
    """
    if scenario not in _ERROR_SCENARIOS:
        scenario = "unknown"

    error_code, _ = _ERROR_SCENARIOS[scenario]
    ctx = context or {}
    if detail:
        ctx["detail"] = detail

    agent_error = create_error(
        code=error_code.code,
        source="cli",
        **ctx,
    )

    lines = [
        f"Error [{agent_error.error_code.code}]: {detail or agent_error.message}",
        f"  分类: {agent_error.error_code.category.value}",
        f"  严重级别: {agent_error.error_code.severity.value}",
    ]
    if agent_error.error_code.recoverable:
        lines.append(f"  可恢复: 是")
    lines.append(f"  建议操作: {agent_error.error_code.suggested_action}")

    return "\n".join(lines)


# ============================================================
# 错误码文档生成
# ============================================================

def generate_error_docs() -> str:
    """生成错误码参考文档（Markdown）"""
    registry = get_error_registry()
    return registry.to_documentation()
