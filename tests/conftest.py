"""
测试共享配置 — 阶段150

集中管理测试共享的fixtures和配置，遵循DRY原则。
所有测试文件通过此conftest获取共享fixture，无需重复设置sys.path。
"""

import os
import sys
from pathlib import Path

import pytest

# ============================================================
# 全局路径设置（所有测试共享）
# ============================================================

_PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

# 环境变量默认值（避免LLM初始化）
os.environ.setdefault("SKIP_LLM_INIT", "true")


# ============================================================
# 共享Fixtures
# ============================================================

@pytest.fixture
def PROJECT_ROOT():
    """项目根目录路径"""
    return Path(__file__).parent.parent


@pytest.fixture
def agent():
    """默认配置的SelfEvolvingAgent实例"""
    from self_evolving_agent.agent import create_default_agent
    return create_default_agent()


@pytest.fixture
def flask_app():
    """Flask测试应用"""
    from main import app, init_agent
    init_agent()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(flask_app):
    """Flask测试客户端"""
    return flask_app.test_client()
