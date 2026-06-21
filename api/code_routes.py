from flask import Blueprint, request, jsonify

from .shared import ensure_agent
from self_evolving_agent.core.error_response import api_error_response

code_bp = Blueprint("code", __name__)


@code_bp.route("/api/review/code", methods=["POST"])
def review_code_api():
    """审查代码"""
    agent = ensure_agent()
    data = request.get_json(silent=True) or {}
    code = data.get("code", "")
    report = agent.review_code(code)
    return jsonify(report.to_dict() if hasattr(report, "to_dict") else {"report": str(report)})


@code_bp.route("/api/review/file", methods=["POST"])
def review_file_api():
    """审查文件"""
    agent = ensure_agent()
    data = request.get_json(silent=True) or {}
    file_path = data.get("file_path", "")
    try:
        report = agent.review_file(file_path)
        if report.error:
            resp, status = api_error_response("unknown", report.error)
            return jsonify(resp), status
        return jsonify(report.to_dict())
    except Exception as e:
        resp, status = api_error_response("unknown", str(e))
        return jsonify(resp), status


@code_bp.route("/api/review/directory", methods=["POST"])
def review_directory_api():
    """审查目录"""
    agent = ensure_agent()
    data = request.get_json(silent=True) or {}
    dir_path = data.get("dir_path", "")
    try:
        reports = agent.review_directory(dir_path)
        return jsonify({
            "count": len(reports),
            "reports": [r.to_dict() if hasattr(r, "to_dict") else str(r) for r in reports],
        })
    except Exception as e:
        resp, status = api_error_response("unknown", str(e))
        return jsonify(resp), status


# ---- 文档生成（阶段129）----

@code_bp.route("/api/docs/generate", methods=["POST"])
def docs_generate():
    """从代码生成文档"""
    agent = ensure_agent()
    data = request.get_json(silent=True) or {}
    code = data.get("code", "")
    fmt = data.get("format", "markdown")
    from self_evolving_agent.core.doc_generator import DocFormat
    try:
        fmt_enum = DocFormat(fmt)
    except ValueError:
        fmt_enum = DocFormat.MARKDOWN
    report = agent.generate_docs(code, fmt_enum)
    return jsonify({
        "content": report.content,
        "format": report.format.value,
        "duration_ms": report.generation_duration_ms,
    })


@code_bp.route("/api/docs/generate_file", methods=["POST"])
def docs_generate_file():
    """从文件生成文档"""
    agent = ensure_agent()
    data = request.get_json(silent=True) or {}
    file_path = data.get("file_path", "")
    fmt = data.get("format", "markdown")
    from self_evolving_agent.core.doc_generator import DocFormat
    try:
        fmt_enum = DocFormat(fmt)
    except ValueError:
        fmt_enum = DocFormat.MARKDOWN
    try:
        report = agent.generate_file_docs(file_path, fmt_enum)
        if report.error:
            resp, status = api_error_response("unknown", report.error)
            return jsonify(resp), status
        return jsonify({
            "content": report.content,
            "format": report.format.value,
            "duration_ms": report.generation_duration_ms,
        })
    except Exception as e:
        resp, status = api_error_response("unknown", str(e))
        return jsonify(resp), status
