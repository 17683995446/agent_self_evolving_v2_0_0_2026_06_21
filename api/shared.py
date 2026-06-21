"""
api.shared — API 蓝图共享模块

包含全局Agent状态、初始化函数和辅助函数。
所有Blueprint通过此模块访问Agent实例。
"""

import os
import sys
import time
import threading
from enum import Enum

from flask import Flask
from flask.json.provider import DefaultJSONProvider
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from self_evolving_agent import SelfEvolvingAgent, create_default_agent
from self_evolving_agent.core.system_coordinator import create_coordinator
from self_evolving_agent.core.dashboard import (
    create_dashboard, create_panel, create_widget, WidgetType, create_data_source,
)
from self_evolving_agent.core.llm_service import create_llm_service
from self_evolving_agent.core.vector_store import create_vector_store, create_rag_service


# ============================================================
# 自定义JSON提供者
# ============================================================

class CustomJSONProvider(DefaultJSONProvider):
    """处理Enum等不可序列化类型的JSON提供者"""

    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)


# ============================================================
# 全局状态
# ============================================================

_agent: SelfEvolvingAgent = None
_coordinator = None
_dashboard = None
_agent_thread: threading.Thread = None
_agent_running = False
_rag = None


# ============================================================
# 初始化
# ============================================================

def init_agent():
    """初始化Agent"""
    global _agent, _coordinator, _dashboard, _rag

    print("[部署] 初始化自驱永续进化Agent系统...")
    _agent = create_default_agent()
    _agent.initialize({})

    # 初始化LLM服务（如果配置了API Key）
    llm_service = None
    api_key = os.environ.get("SILICONFLOW_API_KEY")
    if api_key:
        model = os.environ.get("SILICONFLOW_MODEL", "Qwen/Qwen2.5-7B-Instruct")
        llm_service = create_llm_service(api_key=api_key, model=model)
        print(f"[部署] LLM服务已启用: {model}")
    else:
        print("[部署] LLM服务未配置（设置 SILICONFLOW_API_KEY 环境变量启用）")

    # 初始化协调器
    _coordinator = create_coordinator("deployed_coordinator", llm_service=llm_service)

    # 初始化RAG服务（向量数据库 + LLM）
    if llm_service:
        _rag = create_rag_service(llm_service=llm_service)
        print("[部署] RAG服务已启用")
    else:
        print("[部署] RAG服务未启用（需要LLM服务）")

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
                _agent._cycle_count += 1
                time.sleep(_agent._cycle_interval)
            else:
                time.sleep(0.1)
        except Exception as e:
            print(f"[部署] Agent循环错误: {e}")
            time.sleep(1)

    print("[部署] Agent后台循环停止")


# ============================================================
# 辅助函数
# ============================================================

def get_agent() -> SelfEvolvingAgent:
    """获取全局Agent实例（可能为None）"""
    return _agent


def ensure_agent() -> SelfEvolvingAgent:
    """确保Agent已初始化，返回Agent实例"""
    global _agent
    if _agent is None:
        init_agent()
    return _agent


def get_coordinator():
    """获取全局协调器"""
    return _coordinator


def get_dashboard():
    """获取全局仪表盘"""
    return _dashboard


def get_rag():
    """获取全局RAG服务"""
    return _rag


def is_agent_running() -> bool:
    """Agent是否在运行"""
    return _agent_running


def set_agent_running(running: bool) -> None:
    """设置Agent运行状态"""
    global _agent_running
    _agent_running = running


def get_agent_thread() -> threading.Thread:
    """获取Agent线程"""
    return _agent_thread


def set_agent_thread(thread: threading.Thread) -> None:
    """设置Agent线程"""
    global _agent_thread
    _agent_thread = thread
