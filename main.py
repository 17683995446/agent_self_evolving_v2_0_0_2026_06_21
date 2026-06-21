"""自驱永续进化Agent系统 — 部署入口

阶段148重构: API端点已拆分至 api/ 包的15个Blueprint模块。
本文件仅保留app创建、Blueprint注册和main()入口。
阶段175: 入口处自动加载 .env 文件。
阶段179: 配置文件日志后端（带轮转）+ LOG_LEVEL 环境变量。
"""
import os
from flask import Flask, jsonify
from flask_cors import CORS

# 阶段175: 在所有其他导入之前加载 .env（确保环境变量对后续模块可见）
from self_evolving_agent.core.env_loader import load_env
load_env()

from api import (
    CustomJSONProvider, init_agent,
    core_bp, llm_bp, rag_bp, env_bp, task_bp, code_bp, perf_bp,
    observability_bp, production_bp, plugins_bp, config_bp,
    security_bp, recovery_bp, benchmark_bp, tenants_bp,
)
import api.shared as _shared  # noqa: E402


def _setup_logging():
    """阶段179: 配置文件日志后端 + LOG_LEVEL 环境变量

    第一性原理:
    1. 生产环境必须有持久化日志 — 仅 stdout 不够
    2. 日志级别应可配置 — LOG_LEVEL 环境变量控制
    3. 日志必须轮转 — 避免磁盘撑满
    """
    from self_evolving_agent.core.logging import LogManager, LogLevel, JsonFileBackend

    # 解析 LOG_LEVEL 环境变量
    level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
    level_map = {
        "DEBUG": LogLevel.DEBUG,
        "INFO": LogLevel.INFO,
        "WARNING": LogLevel.WARNING,
        "WARN": LogLevel.WARNING,
        "ERROR": LogLevel.ERROR,
        "CRITICAL": LogLevel.CRITICAL,
    }
    log_level = level_map.get(level_str, LogLevel.INFO)

    log_manager = LogManager()
    log_manager.set_default_level(log_level)

    # 配置文件日志后端（带轮转）
    log_dir = os.environ.get("LOG_DIR", "logs")
    log_file = os.path.join(log_dir, "agent.log")
    max_bytes = int(os.environ.get("LOG_MAX_BYTES", str(10 * 1024 * 1024)))
    backup_count = int(os.environ.get("LOG_BACKUP_COUNT", "5"))

    file_backend = JsonFileBackend(
        filepath=log_file,
        min_level=log_level,
        max_bytes=max_bytes,
        backup_count=backup_count,
        enable_rotation=True,
    )
    log_manager.add_backend(file_backend)
    print(f"[部署] 日志级别: {log_level.name}")
    print(f"[部署] 日志文件: {log_file}（轮转: {max_bytes}B x {backup_count}）")


# 向后兼容：旧测试通过 main._coordinator 等访问全局状态（已迁移至 api.shared）
def __getattr__(name):
    if name in ("_agent", "_coordinator", "_dashboard", "_rag",
                "_agent_thread", "_agent_running"):
        return getattr(_shared, name)
    raise AttributeError(f"module 'main' has no attribute {name!r}")

app = Flask(__name__)
app.json = CustomJSONProvider(app)
CORS(app)

_ALL_BLUEPRINTS = [
    core_bp, llm_bp, rag_bp, env_bp, task_bp, code_bp, perf_bp,
    observability_bp, production_bp, plugins_bp, config_bp,
    security_bp, recovery_bp, benchmark_bp, tenants_bp,
]
for _bp in _ALL_BLUEPRINTS:
    app.register_blueprint(_bp)

def main():
    """主入口"""
    _setup_logging()  # 阶段179: 配置文件日志
    init_agent()
    port = int(os.environ.get("PORT", 8080))
    host = os.environ.get("HOST", "0.0.0.0")
    debug = os.environ.get("DEBUG", "false").lower() == "true"
    print(f"[部署] 启动API服务: http://{host}:{port}")
    print(f"[部署] 调试模式: {debug}")
    print(f"[部署] 已注册Blueprint: {len(_ALL_BLUEPRINTS)}")
    app.run(host=host, port=port, debug=debug, threaded=True)

if __name__ == "__main__":
    main()
