"""
阶段136: CLI工具 — 命令行接口

第一性原理:
1. 可操作性 — 系统必须提供人类可操作的命令行入口
2. 可脚本化 — CLI必须支持非交互式调用，便于自动化
3. 可发现性 — 命令和参数应有自解释的帮助信息
4. 一致性 — 命令结构、参数命名、输出格式应保持一致
5. 反馈性 — 操作结果应以清晰格式呈现

设计:
- 主命令: agent-cli
- 子命令: start/stop/status/cycle/observe/act/reflect/task/review/docs/perf/plugin/health/chat/repl
- 输出格式: json/table/text
- 交互模式: repl
"""

import argparse
import json
import os
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

# 确保能导入self_evolving_agent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 阶段175: 自动加载 .env 文件（在导入项目模块之前）
from self_evolving_agent.core.env_loader import load_env
load_env()

from self_evolving_agent import SelfEvolvingAgent, create_default_agent
from self_evolving_agent.core.system_coordinator import create_coordinator


# ============================================================
# 版本信息
# ============================================================

def _get_version() -> str:
    """从 pyproject.toml 读取版本号"""
    try:
        from importlib.metadata import version
        return version("self-evolving-agent")
    except Exception:
        return "2.0.0"


VERSION = _get_version()


# ============================================================
# CLI 帮助文本（epilog 示例）
# ============================================================

EPILOG = """
示例:
  # 启动 Agent
  agent-cli start

  # 查看 Agent 状态
  agent-cli status

  # 运行一个感知-行动-反思周期
  agent-cli cycle

  # 提交并执行任务
  agent-cli task execute "分析代码质量"
  agent-cli task submit "优化性能" --format json

  # 查看任务状态和结果
  agent-cli task status <task_id>
  agent-cli task result <task_id>

  # 代码审查
  agent-cli review file ./src/main.py
  agent-cli review dir ./src/

  # 生成文档
  agent-cli docs file ./src/main.py --format markdown

  # 性能监控
  agent-cli perf report
  agent-cli perf cache

  # 插件管理
  agent-cli plugin list
  agent-cli plugin health

  # 健康检查
  agent-cli health

  # LLM 对话（需配置 SILICONFLOW_API_KEY）
  agent-cli chat "你好，请介绍一下自己"

  # 交互模式
  agent-cli repl

  # JSON 格式输出（便于脚本处理）
  agent-cli --format json status
  agent-cli --format json cycle

环境变量:
  SILICONFLOW_API_KEY    硅基流动 API 密钥（启用 LLM 功能）
  PORT                   API 服务端口（默认 8080）
  HOST                   API 服务地址（默认 0.0.0.0）
  DEBUG                  调试模式（默认 false）

完整配置说明见 docs/configuration.md
"""


# ============================================================
# 输出格式化
# ============================================================

class OutputFormatter:
    """输出格式化器（阶段164: 接入 ColorOutput 颜色输出）"""

    def __init__(self, format: str = "text"):
        self.format = format
        # 阶段164: 接入颜色输出器
        from self_evolving_agent.core.output_enhanced import ColorOutput
        self._color = ColorOutput()

    def output(self, data: Any, title: str = "") -> None:
        """格式化输出"""
        if self.format == "json":
            self._output_json(data)
        elif self.format == "table":
            self._output_table(data, title)
        else:
            self._output_text(data, title)

    def _output_json(self, data: Any) -> None:
        """JSON格式输出"""
        if hasattr(data, "to_dict"):
            data = data.to_dict()
        elif hasattr(data, "__dict__"):
            data = data.__dict__
        print(json.dumps(data, indent=2, default=str, ensure_ascii=False))

    def _output_table(self, data: Any, title: str) -> None:
        """表格格式输出（阶段172: 接入 format_table 增强表格）"""
        from self_evolving_agent.core.output_enhanced import format_table

        if title:
            print(self._color.bold(f"\n{'=' * 60}"))
            print(self._color.bold(f"  {title}"))
            print(self._color.bold(f"{'=' * 60}"))

        # 阶段172: 使用 format_table 处理 dict 数据
        if isinstance(data, dict):
            # 简单 key-value 表格
            rows = [[str(k), str(v) if not isinstance(v, (dict, list)) else f"[{type(v).__name__}]"]
                    for k, v in data.items()]
            table_str = format_table(["Key", "Value"], rows)
            print(table_str)
            # 递归处理嵌套 dict/list
            for key, value in data.items():
                if isinstance(value, dict):
                    print(f"\n  {self._color.info(str(key))}:")
                    nested_rows = [[str(k), str(v) if not isinstance(v, (dict, list)) else f"[{type(v).__name__}]"]
                                   for k, v in value.items()]
                    print(format_table(["  Key", "  Value"], nested_rows))
                elif isinstance(value, list) and value:
                    print(f"\n  {self._color.info(str(key))} ({len(value)} items):")
                    for i, item in enumerate(value[:10]):
                        print(f"    [{i}] {item}")
                    if len(value) > 10:
                        print(f"    ... and {len(value) - 10} more")
        elif isinstance(data, list):
            # 列表数据: 尝试转为表格
            if data and isinstance(data[0], dict):
                # 列表中的 dict 转为多列表格
                headers = list(data[0].keys())
                rows = [[str(item.get(h, "")) for h in headers] for item in data]
                print(format_table(headers, rows))
            else:
                for i, item in enumerate(data):
                    print(f"  [{i}] {item}")
        else:
            print(f"  {data}")

        if title:
            print()

    def _output_text(self, data: Any, title: str) -> None:
        """文本格式输出"""
        if title:
            print(self._color.bold(f"\n--- {title} ---"))

        if hasattr(data, "to_dict"):
            data = data.to_dict()
        elif hasattr(data, "__dict__") and not isinstance(data, (str, int, float, bool, list, dict)):
            data = data.__dict__

        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, dict):
                    print(f"{self._color.info(key)}:")
                    for k2, v2 in value.items():
                        print(f"  {k2}: {v2}")
                elif isinstance(value, list):
                    print(f"{self._color.info(key)}: [{len(value)} items]")
                    for item in value[:5]:
                        print(f"  - {item}")
                    if len(value) > 5:
                        print(f"  ... and {len(value) - 5} more")
                else:
                    print(f"{self._color.info(key)}: {value}")
        elif isinstance(data, list):
            for item in data:
                print(f"  - {item}")
        else:
            print(data)

    def error(self, message: str) -> None:
        """输出错误（阶段164: 红色）"""
        print(self._color.error(f"Error: {message}"), file=sys.stderr)

    def success(self, message: str) -> None:
        """输出成功（阶段164: 绿色）"""
        if self.format == "json":
            print(json.dumps({"status": "ok", "message": message}))
        else:
            print(self._color.success(f"[OK] {message}"))

    def info(self, message: str) -> None:
        """输出信息（阶段164: 青色）"""
        print(self._color.info(f"[INFO] {message}"))

    def warning(self, message: str) -> None:
        """输出警告（阶段164: 黄色）"""
        print(self._color.warning(f"[WARN] {message}"))

    def progress(self, message: str):
        """阶段178: 创建进度提示器（上下文管理器）

        用法:
            with self.fmt.progress("正在执行任务..."):
                result = agent.execute_task(goal)
        非 TTY 环境自动降级（仅打印开始/结束消息）。
        """
        from self_evolving_agent.core.output_enhanced import ProgressIndicator
        return ProgressIndicator(message)


# ============================================================
# CLI上下文
# ============================================================

class CLIContext:
    """CLI上下文 — 管理Agent实例"""

    _agent: Optional[SelfEvolvingAgent] = None
    _coordinator = None

    @classmethod
    def get_agent(cls) -> SelfEvolvingAgent:
        """获取或创建Agent实例"""
        if cls._agent is None:
            cls._agent = create_default_agent()
            cls._agent.initialize({})
        return cls._agent

    @classmethod
    def get_coordinator(cls):
        """获取或创建协调器"""
        if cls._coordinator is None:
            agent = cls.get_agent()
            cls._coordinator = agent.coordinator
        return cls._coordinator

    @classmethod
    def reset(cls) -> None:
        """重置上下文"""
        cls._agent = None
        cls._coordinator = None


# ============================================================
# 命令处理器
# ============================================================

class CommandHandler:
    """命令处理器"""

    def __init__(self, formatter: OutputFormatter):
        self.fmt = formatter

    # ---- 系统控制 ----

    def cmd_start(self, args) -> int:
        """启动Agent"""
        agent = CLIContext.get_agent()
        agent.start()
        self.fmt.success("Agent已启动")
        return 0

    def cmd_stop(self, args) -> int:
        """停止Agent"""
        agent = CLIContext.get_agent()
        agent.stop()
        self.fmt.success("Agent已停止")
        return 0

    def cmd_status(self, args) -> int:
        """显示状态"""
        agent = CLIContext.get_agent()
        state = agent.get_state()
        self.fmt.output(state, "Agent状态")
        return 0

    def cmd_cycle(self, args) -> int:
        """运行一个周期"""
        coord = CLIContext.get_coordinator()
        with self.fmt.progress("正在运行进化周期..."):
            result = coord.run_cycle({})
        self.fmt.output(result, "周期结果")
        return 0

    # ---- 初始化向导 ----

    def cmd_init(self, args) -> int:
        """初始化向导 — 引导新用户完成首次配置"""
        self.fmt.info("=== 自驱永续进化Agent系统 — 初始化向导 ===")
        print()

        # 步骤1: 检查环境
        self.fmt.info("[1/4] 检查运行环境...")
        import sys as _sys
        print(f"  Python: {_sys.version.split()[0]}")
        project_root = os.path.dirname(os.path.abspath(__file__))
        print(f"  项目路径: {project_root}")

        # 检查关键依赖（阶段181: 与 doctor 命令统一检查范围）
        missing_deps = []
        required_deps = [
            ("flask", "Flask"),
            ("flask_cors", "Flask-CORS"),
            ("numpy", "NumPy"),
            ("psutil", "psutil"),
            ("dotenv", "python-dotenv"),
        ]
        for module, name in required_deps:
            try:
                __import__(module)
                print(f"  {name}: 已安装")
            except ImportError:
                missing_deps.append(name)
                print(f"  {name}: 未安装")

        if missing_deps:
            print(f"\n  [警告] 缺少依赖: {', '.join(missing_deps)}")
            print(f"  请运行: pip install -e .")
        print()

        # 步骤2: 配置环境变量
        self.fmt.info("[2/4] 检查配置...")
        env_file = os.path.join(project_root, ".env")
        env_example = os.path.join(project_root, ".env.example")

        if os.path.exists(env_file):
            print("  .env 文件: 已存在")
        elif os.path.exists(env_example):
            print("  .env 文件: 不存在")
            print("  .env.example 模板: 已存在")
            if self._prompt_yes_no("  是否从模板创建 .env 文件?", default=True):
                import shutil
                shutil.copy(env_example, env_file)
                print("  [OK] 已创建 .env 文件")
        else:
            print("  [警告] 未找到 .env 或 .env.example")

        # 检查 API Key
        api_key = os.environ.get("SILICONFLOW_API_KEY", "")
        if api_key:
            print(f"  SILICONFLOW_API_KEY: 已设置 ({api_key[:4]}...{api_key[-4:]})")
        else:
            print("  SILICONFLOW_API_KEY: 未设置")
            print("  [提示] LLM 和 RAG 功能需要此密钥")
            print("         从 https://siliconflow.cn 获取")
            if self._prompt_yes_no("  是否现在设置 API Key?", default=False):
                key = input("  请输入 SILICONFLOW_API_KEY: ").strip()
                if key:
                    self._write_env_var(env_file, "SILICONFLOW_API_KEY", key)
                    os.environ["SILICONFLOW_API_KEY"] = key
                    print("  [OK] API Key 已保存到 .env")
        print()

        # 步骤3: 验证 Agent
        self.fmt.info("[3/4] 验证 Agent 初始化...")
        try:
            agent = CLIContext.get_agent()
            state = agent.get_state()
            print(f"  [OK] Agent 初始化成功")
            print(f"  生命周期阶段: {state.get('lifecycle', {}).get('stage', 'unknown')}")
        except Exception as e:
            print(f"  [错误] Agent 初始化失败: {e}")
            return 1
        print()

        # 步骤4: 下一步指引
        self.fmt.info("[4/4] 下一步指引...")
        print("  常用命令:")
        print("    agent-cli status    查看 Agent 状态")
        print("    agent-cli cycle     运行一个周期")
        print("    agent-cli start     启动后台循环")
        print("    agent-cli repl      进入交互模式")
        print("    agent-cli --help    查看所有命令")
        print()
        if not api_key:
            print("  提示: 设置 SILICONFLOW_API_KEY 后可使用 LLM 对话功能")
            print("        agent-cli chat \"你好\"")
        print()
        self.fmt.success("初始化向导完成")
        return 0

    def _prompt_yes_no(self, prompt: str, default: bool = True) -> bool:
        """是/否提示（非交互模式下返回默认值）"""
        if not sys.stdin.isatty():
            return default
        suffix = " [Y/n] " if default else " [y/N] "
        try:
            answer = input(prompt + suffix).strip().lower()
        except (EOFError, KeyboardInterrupt):
            return default
        if not answer:
            return default
        return answer in ("y", "yes", "是")

    def _write_env_var(self, env_file: str, key: str, value: str) -> None:
        """写入或更新 .env 文件中的变量"""
        lines = []
        found = False
        if os.path.exists(env_file):
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith(f"{key}="):
                        lines.append(f"{key}={value}\n")
                        found = True
                    else:
                        lines.append(line)
        if not found:
            lines.append(f"{key}={value}\n")
        with open(env_file, "w", encoding="utf-8") as f:
            f.writelines(lines)

    # ---- 错误码参考 ----

    def cmd_errors(self, args) -> int:
        """查看错误码参考文档"""
        from self_evolving_agent.core.error_response import generate_error_docs
        docs = generate_error_docs()
        print(docs)
        return 0

    # ---- 交互式帮助（阶段171）----

    def cmd_help(self, args) -> int:
        """交互式帮助 — 查看命令帮助"""
        command_name = args.command_name if hasattr(args, "command_name") else None
        color = self.fmt._color  # 使用 OutputFormatter 的颜色输出器

        if not command_name:
            # 不带参数: 显示所有命令的简要列表
            parser = build_parser()
            print(color.bold("自驱永续进化Agent系统 — 命令列表"))
            print()
            print("用法: agent-cli <command> [options]")
            print()

            # 获取所有子命令
            import argparse
            subparsers_action = None
            for action in parser._actions:
                if isinstance(action, argparse._SubParsersAction):
                    subparsers_action = action
                    break

            if subparsers_action:
                print(color.bold("可用命令:"))
                print()
                # 按字母排序
                for name in sorted(subparsers_action.choices.keys()):
                    subparser = subparsers_action.choices[name]
                    help_text = subparser.description or ""
                    # 取第一行作为简要说明
                    short_help = help_text.split("。")[0] if help_text else ""
                    if not short_help:
                        short_help = name
                    print(f"  {color.info(name):<15} {short_help}")
                print()
                print(f"查看具体命令帮助: {color.info('agent-cli help <command>')}")
                print(f"查看全局帮助:     {color.info('agent-cli --help')}")
            return 0
        else:
            # 带参数: 显示指定命令的详细帮助
            parser = build_parser()
            import argparse
            subparsers_action = None
            for action in parser._actions:
                if isinstance(action, argparse._SubParsersAction):
                    subparsers_action = action
                    break

            if subparsers_action and command_name in subparsers_action.choices:
                # 调用子命令的 --help
                subparser = subparsers_action.choices[command_name]
                print(color.bold(f"=== {command_name} 命令帮助 ==="))
                print()
                subparser.print_help()
                return 0
            else:
                self.fmt.error(f"未知命令: {command_name}")
                print(f"运行 '{color.info('agent-cli help')}' 查看所有命令")
                return 1

    # ---- 日志查看 ----

    def cmd_logs(self, args) -> int:
        """查看系统日志"""
        agent = CLIContext.get_agent()
        level = args.level if hasattr(args, "level") and args.level else None
        limit = args.limit if hasattr(args, "limit") and args.limit else 50

        try:
            logs = agent.get_logs(level=level, limit=limit)
        except Exception as e:
            self.fmt.error(f"获取日志失败: {e}")
            return 1

        if not logs:
            self.fmt.info("无日志记录")
            return 0

        # 格式化输出（阶段174: 修复属性引用 — 使用 self.fmt 而非 self）
        if self.fmt.format == "json":
            self.fmt._output_json(logs)
        else:
            print(f"日志记录（共 {len(logs)} 条，级别: {level or 'all'}）")
            print("=" * 60)
            for log_entry in logs:
                if isinstance(log_entry, dict):
                    timestamp = log_entry.get("timestamp", "")
                    log_level = log_entry.get("level", "")
                    source = log_entry.get("source", "")
                    message = log_entry.get("message", "")
                    print(f"[{timestamp}] [{log_level}] [{source}] {message}")
                else:
                    print(f"  {log_entry}")
            print("=" * 60)
            print(f"共 {len(logs)} 条日志")
        return 0

    # ---- 配置管理 ----

    def cmd_config(self, args) -> int:
        """配置管理 — 查看/设置/删除/列表/校验"""
        action = args.config_action
        if action == "get":
            return self._config_get(args)
        elif action == "set":
            return self._config_set(args)
        elif action == "delete":
            return self._config_delete(args)
        elif action == "list":
            return self._config_list(args)
        elif action == "validate":
            return self._config_validate(args)
        else:
            self.fmt.error(f"未知配置操作: {action}")
            return 1

    def _config_get(self, args) -> int:
        """获取配置值"""
        agent = CLIContext.get_agent()
        key = args.key
        value = agent.get_config(key)
        exists = agent.has_config(key)
        self.fmt.output({"key": key, "value": value, "exists": exists}, "配置值")
        return 0

    def _config_set(self, args) -> int:
        """设置配置值"""
        agent = CLIContext.get_agent()
        key = args.key
        value = args.value
        # 尝试解析为 JSON，失败则作为字符串
        try:
            import json as _json
            parsed = _json.loads(value)
        except (ValueError, TypeError):
            parsed = value
        ok, err = agent.set_config(key, parsed)
        if not ok:
            self.fmt.error(f"设置失败: {err}")
            return 1
        self.fmt.success(f"已设置 {key} = {parsed}")
        return 0

    def _config_delete(self, args) -> int:
        """删除配置项"""
        agent = CLIContext.get_agent()
        key = args.key
        ok, err = agent.delete_config(key)
        if not ok:
            self.fmt.error(f"删除失败: {err}")
            return 1
        self.fmt.success(f"已删除 {key}")
        return 0

    def _config_list(self, args) -> int:
        """列出所有配置"""
        agent = CLIContext.get_agent()
        snapshot = agent.get_config_snapshot()
        self.fmt.output(snapshot, "配置快照")
        return 0

    def _config_validate(self, args) -> int:
        """校验配置（阶段181: 接入 config_schema 进行类型/约束校验）"""
        agent = CLIContext.get_agent()
        snapshot = agent.get_config_snapshot()
        errors = []
        warnings = []

        # 阶段181: 接入 config_schema 进行结构化校验
        try:
            from self_evolving_agent.core.config_schema import create_system_config_schema
            schema = create_system_config_schema()
            schema_errors = schema.validate(snapshot)
            errors.extend(schema_errors)
        except Exception as e:
            warnings.append(f"config_schema 校验跳过: {e}")

        # 基本校验规则（保留原有检查）
        for key, value in snapshot.items():
            if value is None:
                warnings.append(f"{key}: 值为 None")
            if isinstance(value, str) and len(value) > 1000:
                warnings.append(f"{key}: 字符串值过长 ({len(value)} 字符)")

        # 检查必需配置
        if not os.environ.get("SILICONFLOW_API_KEY"):
            warnings.append("SILICONFLOW_API_KEY: 未设置（LLM 功能不可用）")

        # 阶段181: 环境变量类型校验
        port_str = os.environ.get("PORT", "8080")
        try:
            port = int(port_str)
            if not (1 <= port <= 65535):
                errors.append(f"PORT: 端口超出有效范围 (1-65535)，当前: {port}")
        except ValueError:
            errors.append(f"PORT: 不是有效数字，当前: {port_str}")

        log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
        valid_levels = {"DEBUG", "INFO", "WARNING", "WARN", "ERROR", "CRITICAL"}
        if log_level not in valid_levels:
            warnings.append(f"LOG_LEVEL: 不是有效级别，当前: {log_level}，有效值: {valid_levels}")

        print("=" * 50)
        print("配置校验结果")
        print("=" * 50)
        print(f"配置项总数: {len(snapshot)}")
        print(f"错误: {len(errors)}")
        print(f"警告: {len(warnings)}")
        print()

        if errors:
            self.fmt.error("错误:")
            for e in errors:
                print(f"  - {e}")
            print()

        if warnings:
            self.fmt.warning("警告:")
            for w in warnings:
                print(f"  - {w}")
            print()

        if not errors and not warnings:
            self.fmt.success("配置校验通过，无错误无警告")
        elif not errors:
            self.fmt.warning(f"有 {len(warnings)} 项警告，配置可用")
        else:
            self.fmt.error(f"有 {len(errors)} 项错误，请修复")

        return 1 if errors else 0

    # ---- 系统诊断 ----

    def cmd_doctor(self, args) -> int:
        """系统诊断 — 一键自检"""
        self.fmt.info("=== 系统诊断（doctor）===")
        print()
        checks_passed = 0
        checks_failed = 0
        checks_warning = 0

        # 检查1: Python 环境
        print("[1/6] Python 环境...")
        import sys as _sys
        print(f"  Python: {_sys.version.split()[0]}")
        if _sys.version_info >= (3, 10):
            self.fmt.success("  Python 版本符合要求 (3.10+)")
            checks_passed += 1
        else:
            self.fmt.error("  Python 版本过低，需要 3.10+")
            checks_failed += 1
        print()

        # 检查2: 核心依赖
        print("[2/6] 核心依赖...")
        deps = [
            ("flask", "Flask"),
            ("flask_cors", "Flask-CORS"),
            ("numpy", "NumPy"),
            ("psutil", "psutil"),
            ("dotenv", "python-dotenv"),
        ]
        for module, name in deps:
            try:
                __import__(module)
                print(f"  {name}: 已安装")
                checks_passed += 1
            except ImportError:
                self.fmt.error(f"  {name}: 未安装")
                checks_failed += 1
        print()

        # 检查3: 项目模块导入
        print("[3/6] 项目模块导入...")
        modules = [
            ("self_evolving_agent", "self_evolving_agent"),
            ("self_evolving_agent.agent", "Agent门面"),
            ("self_evolving_agent.core.system_coordinator", "系统协调器"),
            ("self_evolving_agent.core.error_codes", "错误码体系"),
            ("self_evolving_agent.core.error_response", "错误响应构建器"),
            ("self_evolving_agent.core.output_enhanced", "输出增强"),
        ]
        for module, name in modules:
            try:
                __import__(module)
                print(f"  {name}: OK")
                checks_passed += 1
            except ImportError as e:
                self.fmt.error(f"  {name}: 导入失败 ({e})")
                checks_failed += 1
        print()

        # 检查4: 配置文件
        print("[4/6] 配置文件...")
        project_root = os.path.dirname(os.path.abspath(__file__))
        env_file = os.path.join(project_root, ".env")
        env_example = os.path.join(project_root, ".env.example")
        if os.path.exists(env_file):
            print(f"  .env: 存在")
            checks_passed += 1
        elif os.path.exists(env_example):
            self.fmt.warning("  .env: 不存在（.env.example 可用，运行 'cli.py init' 创建）")
            checks_warning += 1
        else:
            self.fmt.error("  .env 和 .env.example 都不存在")
            checks_failed += 1

        api_key = os.environ.get("SILICONFLOW_API_KEY", "")
        if api_key:
            self.fmt.success(f"  SILICONFLOW_API_KEY: 已设置")
            checks_passed += 1
        else:
            self.fmt.warning("  SILICONFLOW_API_KEY: 未设置（LLM 功能不可用）")
            checks_warning += 1
        print()

        # 检查5: Agent 初始化
        print("[5/6] Agent 初始化...")
        try:
            agent = CLIContext.get_agent()
            state = agent.get_state()
            stage = state.get("lifecycle", {}).get("stage", "unknown")
            self.fmt.success(f"  Agent 初始化成功（阶段: {stage}）")
            checks_passed += 1
        except Exception as e:
            self.fmt.error(f"  Agent 初始化失败: {e}")
            checks_failed += 1
        print()

        # 检查6: 健康检查
        print("[6/6] 健康检查...")
        try:
            coord = CLIContext.get_coordinator()
            if coord:
                health = agent.check_health() if hasattr(agent, "check_health") else None
                if health:
                    status = getattr(health, "status", "unknown")
                    print(f"  健康状态: {status}")
                    if status == "healthy":
                        self.fmt.success("  系统健康")
                        checks_passed += 1
                    else:
                        self.fmt.warning(f"  系统状态: {status}")
                        checks_warning += 1
                else:
                    self.fmt.warning("  健康检查不可用")
                    checks_warning += 1
            else:
                self.fmt.warning("  协调器未初始化")
                checks_warning += 1
        except Exception as e:
            self.fmt.error(f"  健康检查失败: {e}")
            checks_failed += 1
        print()

        # 汇总
        print("=" * 50)
        total = checks_passed + checks_failed + checks_warning
        print(f"诊断完成: {total} 项检查")
        print(f"  通过: {checks_passed}")
        print(f"  警告: {checks_warning}")
        print(f"  失败: {checks_failed}")
        print("=" * 50)

        if checks_failed > 0:
            self.fmt.error(f"有 {checks_failed} 项检查失败，请修复后重试")
            return 1
        elif checks_warning > 0:
            self.fmt.warning(f"有 {checks_warning} 项警告，系统可运行但建议处理")
            return 0
        else:
            self.fmt.success("所有检查通过")
            return 0

    # ---- 感知/行动/反思 ----

    def cmd_observe(self, args) -> int:
        """感知环境"""
        coord = CLIContext.get_coordinator()
        data = {}
        if args.module_id:
            data["module_id"] = args.module_id
        if args.predicted:
            data["predicted"] = args.predicted
        if args.actual:
            data["actual"] = args.actual

        result = coord.observe(data)
        self.fmt.output(result, "感知结果")
        return 0

    def cmd_act(self, args) -> int:
        """执行行动"""
        coord = CLIContext.get_coordinator()
        context = {}
        if args.context:
            try:
                context = json.loads(args.context)
            except json.JSONDecodeError:
                self.fmt.error("context必须是有效JSON")
                return 1

        result = coord.act(args.action, context)
        self.fmt.output(result, "行动结果")
        return 0

    def cmd_reflect(self, args) -> int:
        """运行反思"""
        coord = CLIContext.get_coordinator()
        result = coord.reflect()
        self.fmt.output(result, "反思结果")
        return 0

    # ---- 任务管理 ----

    def cmd_task(self, args) -> int:
        """任务管理"""
        agent = CLIContext.get_agent()

        if args.task_action == "submit":
            if not args.goal:
                self.fmt.error("请提供任务目标: task submit <goal>")
                return 1
            task_id = agent.submit_task(goal=args.goal)
            self.fmt.output({"task_id": task_id, "goal": args.goal}, "任务已提交")
            return 0

        elif args.task_action == "status":
            if not args.task_id:
                self.fmt.error("请提供任务ID: task status <id>")
                return 1
            status = agent.get_task_status(args.task_id)
            if status is None:
                self.fmt.error(f"任务不存在: {args.task_id}")
                return 1
            self.fmt.output({"task_id": args.task_id, "status": status.value}, "任务状态")
            return 0

        elif args.task_action == "result":
            if not args.task_id:
                self.fmt.error("请提供任务ID: task result <id>")
                return 1
            result = agent.get_task_result(args.task_id)
            if result is None:
                self.fmt.error(f"任务结果不存在: {args.task_id}")
                return 1
            self.fmt.output(result, "任务结果")
            return 0

        elif args.task_action == "execute":
            if not args.goal:
                self.fmt.error("请提供任务目标: task execute <goal>")
                return 1
            with self.fmt.progress("正在执行任务..."):
                result = agent.execute_task(args.goal)
            self.fmt.output(result, "执行结果")
            return 0

        else:
            self.fmt.error(f"未知子命令: {args.task_action}")
            return 1

    # ---- 代码审查 ----

    def cmd_review(self, args) -> int:
        """代码审查"""
        agent = CLIContext.get_agent()

        if args.review_action == "code":
            if not args.target:
                self.fmt.error("请提供代码: review code <code>")
                return 1
            with self.fmt.progress("正在审查代码..."):
                report = agent.review_code(args.target)
            self.fmt.output(report, "审查报告")
            return 0

        elif args.review_action == "file":
            if not args.target:
                self.fmt.error("请提供文件路径: review file <path>")
                return 1
            with self.fmt.progress(f"正在审查文件: {args.target}..."):
                report = agent.review_file(args.target)
            self.fmt.output(report, "审查报告")
            return 0

        elif args.review_action == "dir":
            if not args.target:
                self.fmt.error("请提供目录路径: review dir <path>")
                return 1
            with self.fmt.progress(f"正在审查目录: {args.target}..."):
                reports = agent.review_directory(args.target)
            self.fmt.output({"count": len(reports), "reports": reports}, "目录审查报告")
            return 0

        else:
            self.fmt.error(f"未知子命令: {args.review_action}")
            return 1

    # ---- 文档生成 ----

    def cmd_docs(self, args) -> int:
        """文档生成"""
        agent = CLIContext.get_agent()
        from self_evolving_agent.core.doc_generator import DocFormat

        fmt = DocFormat(args.format) if args.format in ["markdown", "html", "rst"] else DocFormat.MARKDOWN

        if args.docs_action == "generate":
            if not args.target:
                self.fmt.error("请提供代码: docs generate <code>")
                return 1
            with self.fmt.progress("正在生成文档..."):
                report = agent.generate_docs(args.target, fmt)
            self.fmt.output(report, "文档报告")
            return 0

        elif args.docs_action == "file":
            if not args.target:
                self.fmt.error("请提供文件路径: docs file <path>")
                return 1
            with self.fmt.progress(f"正在生成文件文档: {args.target}..."):
                report = agent.generate_file_docs(args.target, fmt)
            self.fmt.output(report, "文档报告")
            return 0

        else:
            self.fmt.error(f"未知子命令: {args.docs_action}")
            return 1

    # ---- 性能监控 ----

    def cmd_perf(self, args) -> int:
        """性能监控"""
        agent = CLIContext.get_agent()

        if args.perf_action == "report":
            report = agent.get_performance_report()
            self.fmt.output(report, "性能报告")
            return 0

        elif args.perf_action == "cache":
            stats = agent.get_cache_stats()
            self.fmt.output(stats, "缓存统计")
            return 0

        elif args.perf_action == "reset":
            agent.reset_performance()
            self.fmt.success("性能指标已重置")
            return 0

        elif args.perf_action == "profiler":
            report = agent.get_profiler_report()
            self.fmt.output(report, "性能分析报告")
            return 0

        else:
            self.fmt.error(f"未知子命令: {args.perf_action}")
            return 1

    # ---- 插件管理 ----

    def cmd_plugin(self, args) -> int:
        """插件管理"""
        agent = CLIContext.get_agent()

        if args.plugin_action == "list":
            plugins = agent.list_plugins()
            self.fmt.output(plugins, "插件列表")
            return 0

        elif args.plugin_action == "health":
            results = agent.get_all_plugin_health()
            output = {name: r.to_dict() for name, r in results.items()}
            self.fmt.output(output, "插件健康状态")
            return 0

        elif args.plugin_action == "unload":
            if not args.name:
                self.fmt.error("请提供插件名: plugin unload <name>")
                return 1
            success = agent.unload_plugin(args.name)
            if success:
                self.fmt.success(f"插件已卸载: {args.name}")
            else:
                self.fmt.error(f"卸载失败: {args.name}")
            return 0 if success else 1

        elif args.plugin_action == "reload":
            if not args.name:
                self.fmt.error("请提供插件名: plugin reload <name>")
                return 1
            success = agent.reload_plugin(args.name)
            if success:
                self.fmt.success(f"插件已重载: {args.name}")
            else:
                self.fmt.error(f"重载失败: {args.name}")
            return 0 if success else 1

        elif args.plugin_action == "stats":
            stats = agent.get_plugin_stats()
            self.fmt.output(stats, "插件统计")
            return 0

        elif args.plugin_action == "manifest":
            if not args.name:
                self.fmt.error("请提供插件名: plugin manifest <name>")
                return 1
            manifest = agent.get_plugin_manifest(args.name)
            if manifest is None:
                self.fmt.error(f"清单不存在: {args.name}")
                return 1
            self.fmt.output(manifest.to_dict(), "插件清单")
            return 0

        elif args.plugin_action == "discover":
            # 阶段170: 插件发现
            directory = args.name  # 复用 name 参数作为目录路径
            if not directory:
                # 默认搜索 plugins/ 目录
                project_root = os.path.dirname(os.path.abspath(__file__))
                directory = os.path.join(project_root, "plugins")
            if not os.path.isdir(directory):
                self.fmt.error(f"目录不存在: {directory}")
                return 1
            self.fmt.info(f"扫描目录: {directory}")
            try:
                with self.fmt.progress(f"正在扫描插件目录: {directory}..."):
                    # 调用 Agent 的 discover_plugins 方法
                    if hasattr(agent, "discover_plugins"):
                        discovered = agent.discover_plugins(directory)
                    else:
                        # 回退: 手动扫描 .py 文件
                        discovered = []
                        for fname in os.listdir(directory):
                            if fname.endswith(".py") and not fname.startswith("_"):
                                discovered.append(fname[:-3])
                if discovered:
                    self.fmt.success(f"发现 {len(discovered)} 个插件:")
                    for name in discovered:
                        print(f"  - {name}")
                else:
                    self.fmt.info("未发现插件")
                return 0
            except Exception as e:
                self.fmt.error(f"发现插件失败: {e}")
                return 1

        else:
            self.fmt.error(f"未知子命令: {args.plugin_action}")
            return 1

    # ---- 健康检查 ----

    def cmd_health(self, args) -> int:
        """健康检查"""
        agent = CLIContext.get_agent()
        result = agent.production_health_check()
        self.fmt.output({"status": result.status, "checks": result.checks}, "健康检查")
        return 0 if result.status == "healthy" else 1

    # ---- LLM对话 ----

    def cmd_chat(self, args) -> int:
        """LLM对话"""
        agent = CLIContext.get_agent()
        if not agent.coordinator._llm:
            self.fmt.error("LLM服务未初始化（需要配置API Key）")
            return 1

        message = args.message
        if not message:
            self.fmt.error("请提供消息: chat <message>")
            return 1

        response = agent.coordinator._llm.quick_chat(message)
        print(response)
        return 0

    # ---- 交互模式 ----

    def cmd_repl(self, args) -> int:
        """交互模式（阶段169: readline增强 — 历史记录、Tab补全）"""
        self.fmt.info("进入交互模式（输入 'help' 查看命令，'quit' 退出）")
        print()

        # 阶段169: readline 集成
        readline_available = False
        history_file = None
        try:
            import readline
            import atexit
            readline_available = True

            # 命令历史持久化
            project_root = os.path.dirname(os.path.abspath(__file__))
            history_file = os.path.join(project_root, ".cli_history")
            try:
                readline.read_history_file(history_file)
            except (FileNotFoundError, OSError):
                pass
            readline.set_history_length(1000)  # 最多保存1000条
            atexit.register(readline.write_history_file, history_file)

            # Tab 补全
            COMMANDS = [
                "start", "stop", "status", "cycle", "observe", "act", "reflect",
                "task", "review", "docs", "perf", "plugin", "health", "chat",
                "repl", "init", "errors", "doctor", "config", "logs",
                "help", "quit", "exit", "q",
            ]

            def completer(text, state):
                """Tab 补全器"""
                matches = [cmd for cmd in COMMANDS if cmd.startswith(text)]
                if state < len(matches):
                    return matches[state]
                return None

            readline.set_completer(completer)
            readline.parse_and_bind("tab: complete")
            self.fmt.success("已启用命令历史和Tab补全")
        except ImportError:
            self.fmt.warning("readline 不可用，命令历史和补全未启用")
        print()

        # 构建parser
        parser = build_parser()

        while True:
            try:
                line = input("agent> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if not line:
                continue
            if line in ("quit", "exit", "q"):
                break
            if line == "help":
                parser.print_help()
                continue
            # 阶段169: help <command> 交互式帮助
            if line.startswith("help "):
                cmd_name = line[5:].strip()
                if cmd_name:
                    result = subprocess.run(
                        [sys.executable, os.path.join(os.path.dirname(__file__), "cli.py"),
                         cmd_name, "--help"],
                        capture_output=True, text=True
                    )
                    print(result.stdout)
                    continue

            # 解析并执行
            parts = line.split()
            try:
                parsed_args = parser.parse_args(parts)
                exit_code = dispatch(parsed_args, self.fmt)
                if exit_code != 0:
                    self.fmt.info(f"命令返回码: {exit_code}")
            except SystemExit:
                # argparse在参数错误时抛出SystemExit
                continue
            except Exception as e:
                self.fmt.error(str(e))

        self.fmt.info("退出交互模式")
        return 0


# ============================================================
# 参数解析器构建
# ============================================================

def build_parser() -> argparse.ArgumentParser:
    """构建参数解析器"""
    parser = argparse.ArgumentParser(
        prog="agent-cli",
        description="自驱永续进化Agent系统 — 命令行工具",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"agent-cli {VERSION}",
        help="显示版本号并退出",
    )
    parser.add_argument(
        "-f", "--format",
        choices=["text", "json", "table"],
        default="text",
        help="输出格式（默认: text）",
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # start
    sp = subparsers.add_parser("start", help="启动Agent后台循环",
                               description="启动Agent后台循环。Agent将开始自主运行感知-行动-反思周期。")
    sp.set_defaults(handler="cmd_start")

    # stop
    sp = subparsers.add_parser("stop", help="停止Agent后台循环",
                               description="停止Agent后台循环。Agent将停止自主运行。")
    sp.set_defaults(handler="cmd_stop")

    # status
    sp = subparsers.add_parser("status", help="显示Agent当前状态（生命周期、配置、统计）",
                               description="显示Agent当前状态，包括生命周期阶段、配置信息、运行统计等。")
    sp.set_defaults(handler="cmd_status")

    # cycle
    sp = subparsers.add_parser("cycle", help="运行一个感知-行动-反思完整周期",
                               description="运行一个完整的感知-行动-反思周期，返回周期执行结果。")
    sp.set_defaults(handler="cmd_cycle")

    # observe
    sp = subparsers.add_parser("observe", help="感知环境（输入模块状态，返回感知结果）",
                               description="感知环境：输入模块的预测状态和实际状态，返回感知结果（含预测误差）。")
    sp.add_argument("--module-id", default=None, help="模块ID（标识被感知的模块）")
    sp.add_argument("--predicted", default=None, help="预测状态(JSON字符串)")
    sp.add_argument("--actual", default=None, help="实际状态(JSON字符串)")
    sp.set_defaults(handler="cmd_observe")

    # act
    sp = subparsers.add_parser("act", help="执行指定行动",
                               description="执行指定行动（如探索、利用、反思），返回行动结果。")
    sp.add_argument("action", nargs="?", default="default",
                    help="行动名称（如 explore/exploit/reflect，默认: default）")
    sp.add_argument("--context", default=None, help="行动上下文(JSON字符串)")
    sp.set_defaults(handler="cmd_act")

    # reflect
    sp = subparsers.add_parser("reflect", help="运行反思（总结经验、更新策略）",
                               description="运行反思：总结当前经验，更新内部策略和模型。")
    sp.set_defaults(handler="cmd_reflect")

    # task
    sp = subparsers.add_parser("task", help="任务管理（提交/执行/查询状态/查询结果）",
                               description="任务管理：提交异步任务、同步执行任务、查询任务状态和结果。")
    sp.add_argument("task_action", choices=["submit", "status", "result", "execute"],
                    help="submit=提交异步任务, execute=同步执行, status=查询状态, result=查询结果")
    sp.add_argument("goal", nargs="?", default=None, help="任务目标（submit/execute 时必填）")
    sp.add_argument("task_id", nargs="?", default=None, help="任务ID（status/result 时必填）")
    sp.set_defaults(handler="cmd_task")

    # review
    sp = subparsers.add_parser("review", help="代码审查（静态分析、指标计算、问题检测）",
                               description="代码审查：对代码进行静态分析，计算代码指标，检测潜在问题。")
    sp.add_argument("review_action", choices=["code", "file", "dir"],
                    help="code=审查代码字符串, file=审查单个文件, dir=审查整个目录")
    sp.add_argument("target", nargs="?", default=None, help="代码字符串/文件路径/目录路径")
    sp.set_defaults(handler="cmd_review")

    # docs
    sp = subparsers.add_parser("docs", help="文档生成（从代码自动生成文档）",
                               description="文档生成：从代码自动生成 markdown/html/rst 格式的文档。")
    sp.add_argument("docs_action", choices=["generate", "file"],
                    help="generate=从代码字符串生成, file=从文件生成")
    sp.add_argument("target", nargs="?", default=None, help="代码字符串/文件路径")
    sp.add_argument("--format", default="markdown", choices=["markdown", "html", "rst"],
                    help="文档格式（默认: markdown）")
    sp.set_defaults(handler="cmd_docs")

    # perf
    sp = subparsers.add_parser("perf", help="性能监控（报告/缓存/分析）",
                               description="性能监控：查看性能报告、缓存统计、性能分析报告，或重置性能指标。")
    sp.add_argument("perf_action", choices=["report", "cache", "reset", "profiler"],
                    help="report=性能报告, cache=缓存统计, reset=重置指标, profiler=分析报告")
    sp.set_defaults(handler="cmd_perf")

    # plugin
    sp = subparsers.add_parser("plugin", help="插件管理（列表/健康/卸载/重载/统计/清单/发现）",
                               description="插件管理：列出插件、检查健康、卸载/重载插件、查看统计和清单、发现新插件。")
    sp.add_argument("plugin_action",
                    choices=["list", "health", "unload", "reload", "stats", "manifest", "discover"],
                    help="list=列出插件, health=健康检查, unload=卸载, reload=重载, stats=统计, manifest=清单, discover=发现插件")
    sp.add_argument("name", nargs="?", default=None,
                    help="插件名（unload/reload/manifest 时必填）；目录路径（discover 时可选，默认 plugins/）")
    sp.set_defaults(handler="cmd_plugin")

    # health
    sp = subparsers.add_parser("health", help="系统健康检查（生产就绪探针）",
                               description="系统健康检查：执行生产就绪探针，返回各子系统健康状态。")
    sp.set_defaults(handler="cmd_health")

    # chat
    sp = subparsers.add_parser("chat", help="LLM对话（需配置 SILICONFLOW_API_KEY）",
                               description="LLM对话：与集成的 LLM 服务对话。需先配置环境变量 SILICONFLOW_API_KEY。")
    sp.add_argument("message", nargs="?", default=None, help="消息内容")
    sp.set_defaults(handler="cmd_chat")

    # repl
    sp = subparsers.add_parser("repl", help="进入交互模式（输入help查看命令，quit退出）",
                               description="进入交互式 REPL 模式，可连续执行多个命令。输入 help 查看可用命令，quit 退出。")
    sp.set_defaults(handler="cmd_repl")

    # init
    sp = subparsers.add_parser("init", help="初始化向导（引导新用户完成首次配置）",
                               description="初始化向导：检查环境、配置 .env、验证 Agent、提供下一步指引。"
                                           "新用户首次使用时推荐运行此命令。")
    sp.set_defaults(handler="cmd_init")

    # errors
    sp = subparsers.add_parser("errors", help="查看错误码参考文档",
                               description="列出所有错误码及其分类、严重级别、描述和建议操作。")
    sp.set_defaults(handler="cmd_errors")

    # doctor
    sp = subparsers.add_parser("doctor", help="系统诊断 — 一键自检（6项检查）",
                               description="系统诊断：检查 Python 环境、核心依赖、项目模块、配置文件、Agent 初始化、健康状态。"
                                           "用于排查问题和验证部署。")
    sp.set_defaults(handler="cmd_doctor")

    # config
    sp = subparsers.add_parser("config", help="配置管理（查看/设置/删除/列表/校验）",
                               description="配置管理：查看、设置、删除配置项，列出所有配置，或校验配置有效性。")
    sp.add_argument("config_action", choices=["get", "set", "delete", "list", "validate"],
                    help="get=获取配置, set=设置配置, delete=删除配置, list=列出全部, validate=校验配置")
    sp.add_argument("key", nargs="?", default=None, help="配置键名（get/set/delete 时必填）")
    sp.add_argument("value", nargs="?", default=None, help="配置值（set 时必填，支持JSON）")
    sp.set_defaults(handler="cmd_config")

    # logs
    sp = subparsers.add_parser("logs", help="查看系统日志",
                               description="查看系统日志，支持按级别过滤和限制条数。")
    sp.add_argument("--level", default=None,
                    choices=["debug", "info", "warning", "error", "critical"],
                    help="日志级别过滤（默认: all）")
    sp.add_argument("--limit", type=int, default=50,
                    help="最大条数（默认: 50）")
    sp.set_defaults(handler="cmd_logs")

    # help（阶段171: 交互式帮助系统）
    sp = subparsers.add_parser("help", help="查看命令帮助（如: help status）",
                               description="交互式帮助：不带参数显示所有命令，带参数显示指定命令的详细帮助。"
                                           "示例: agent-cli help status")
    sp.add_argument("command_name", nargs="?", default=None,
                    help="要查看帮助的命令名（如 status/task/config）")
    sp.set_defaults(handler="cmd_help")

    return parser


# ============================================================
# 命令分发
# ============================================================

def dispatch(args, formatter: OutputFormatter) -> int:
    """分发命令到处理器"""
    handler_name = getattr(args, "handler", None)
    if handler_name is None:
        formatter.error("未指定命令")
        return 1

    handler = CommandHandler(formatter)
    method = getattr(handler, handler_name, None)
    if method is None:
        formatter.error(f"未知命令处理器: {handler_name}")
        return 1

    try:
        return method(args)
    except Exception as e:
        # 阶段157: 接入错误码体系，提供结构化错误信息
        try:
            from self_evolving_agent.core.error_response import cli_error_message
            # 如果是 AgentException，提取错误码
            if hasattr(e, "error") and hasattr(e.error, "error_code"):
                msg = cli_error_message(
                    "unknown",
                    detail=e.error.message,
                )
                # 替换错误码为实际错误码
                msg = msg.replace("[SYS_001]", f"[{e.error.error_code.code}]")
                print(msg, file=sys.stderr)
            else:
                msg = cli_error_message("unknown", detail=str(e))
                print(msg, file=sys.stderr)
        except ImportError:
            # 回退到简单错误输出
            formatter.error(str(e))
        return 1


# ============================================================
# 主入口
# ============================================================

def main(argv: Optional[List[str]] = None) -> int:
    """主入口"""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    formatter = OutputFormatter(args.format)
    return dispatch(args, formatter)


if __name__ == "__main__":
    sys.exit(main())
