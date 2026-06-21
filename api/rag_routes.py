from flask import Blueprint, jsonify, request

from .shared import get_rag
from self_evolving_agent.core.error_response import api_error_response

rag_bp = Blueprint("rag", __name__)


@rag_bp.route("/api/rag/add", methods=["POST"])
def rag_add():
    """添加知识到RAG知识库"""
    if get_rag() is None:
        resp, status = api_error_response("config_invalid", "RAG服务未初始化（需配置SILICONFLOW_API_KEY）")
        return jsonify(resp), status

    data = request.get_json() or {}
    doc_id = data.get("doc_id", "")
    content = data.get("content", "")
    metadata = data.get("metadata")

    if not doc_id or not content:
        resp, status = api_error_response("missing_field", "doc_id和content字段必填")
        return jsonify(resp), status

    success = get_rag().add_knowledge(doc_id, content, metadata)
    return jsonify({"success": success, "doc_id": doc_id})


@rag_bp.route("/api/rag/batch_add", methods=["POST"])
def rag_batch_add():
    """批量添加知识"""
    if get_rag() is None:
        resp, status = api_error_response("config_invalid", "RAG服务未初始化（需配置SILICONFLOW_API_KEY）")
        return jsonify(resp), status

    data = request.get_json() or {}
    documents = data.get("documents", [])

    if not documents:
        resp, status = api_error_response("missing_field", "documents字段必填")
        return jsonify(resp), status

    # 转换为元组格式
    docs_tuples = []
    for doc in documents:
        docs_tuples.append((
            doc.get("doc_id", ""),
            doc.get("content", ""),
            doc.get("metadata")
        ))

    count = get_rag().add_knowledges(docs_tuples)
    return jsonify({"added_count": count})


@rag_bp.route("/api/rag/query", methods=["POST"])
def rag_query():
    """RAG知识库问答"""
    if get_rag() is None:
        resp, status = api_error_response("config_invalid", "RAG服务未初始化（需配置SILICONFLOW_API_KEY）")
        return jsonify(resp), status

    data = request.get_json() or {}
    question = data.get("question", "")
    top_k = data.get("top_k", 3)

    if not question:
        resp, status = api_error_response("missing_field", "question字段必填")
        return jsonify(resp), status

    result = get_rag().query(question, top_k=top_k)
    return jsonify(result)


@rag_bp.route("/api/rag/search", methods=["POST"])
def rag_search():
    """向量搜索"""
    if get_rag() is None:
        resp, status = api_error_response("config_invalid", "RAG服务未初始化（需配置SILICONFLOW_API_KEY）")
        return jsonify(resp), status

    data = request.get_json() or {}
    query = data.get("query", "")
    top_k = data.get("top_k", 5)

    if not query:
        resp, status = api_error_response("missing_field", "query字段必填")
        return jsonify(resp), status

    results = get_rag().vector_store.search(query, top_k=top_k)
    return jsonify({
        "results": [
            {
                "doc_id": r.doc.doc_id,
                "content": r.doc.content[:200] + "..." if len(r.doc.content) > 200 else r.doc.content,
                "score": r.score,
                "metadata": r.doc.metadata,
            }
            for r in results
        ]
    })


@rag_bp.route("/api/rag/docs")
def rag_docs():
    """列出知识库所有文档"""
    if get_rag() is None:
        return jsonify({"documents": [], "total": 0, "message": "RAG服务未初始化（需要配置LLM API Key）"})

    docs = get_rag().vector_store.list_documents()
    return jsonify({"documents": docs, "total": len(docs)})


@rag_bp.route("/api/rag/clear", methods=["POST"])
def rag_clear():
    """清空知识库"""
    if get_rag() is None:
        return jsonify({"status": "noop", "message": "RAG服务未初始化"})

    get_rag().vector_store.clear()
    return jsonify({"status": "cleared"})


@rag_bp.route("/api/rag/stats")
def rag_stats():
    """RAG服务统计"""
    if get_rag() is None:
        return jsonify({"initialized": False, "message": "RAG服务未初始化（需要配置LLM API Key）"})

    return jsonify(get_rag().get_stats())
