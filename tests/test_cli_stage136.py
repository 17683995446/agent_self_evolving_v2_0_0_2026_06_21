"""
阶段136: CLI工具 — 命令行接口 专项测试

测试覆盖：
1. 基础命令 — start/stop/status/cycle
2. 感知/行动/反思 — observe/act/reflect
3. 任务管理 — task submit/status/result/execute
4. 代码审查 — review code/file/dir
5. 文档生成 — docs generate/file
6. 性能监控 — perf report/cache/reset/profiler
7. 插件管理 — plugin list/health/unload/reload/stats
8. 健康检查 — health
9. 输出格式 — text/json/table
10. 错误处理 — 缺少参数/无效命令
11. 第一性原理验证
"""

import io
import json
import os
import sys
from contextlib import redirect_stdout, redirect_stderr

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cli


# ============================================================
# 测试辅助
# ============================================================

def run_cli(*args) -> tuple:
    """
    运行CLI命令，返回(exit_code, stdout, stderr)

    第一性原理：测试应可重复且无副作用
    """
    # 每次测试重置上下文
    cli.CLIContext.reset()

    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()

    try:
        with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
            exit_code = cli.main(list(args))
    except SystemExit as e:
        exit_code = e.code if e.code else 0

    return exit_code, stdout_buf.getvalue(), stderr_buf.getvalue()


# ============================================================
# 输出格式化测试
# ============================================================

class TestOutputFormatter:
    """输出格式化器测试"""

    def test_text_format(self):
        """测试文本格式"""
        fmt = cli.OutputFormatter("text")
        buf = io.StringIO()
        with redirect_stdout(buf):
            fmt.output({"key": "value"}, "Title")
        output = buf.getvalue()
        assert "Title" in output
        assert "key" in output
        assert "value" in output

    def test_json_format(self):
        """测试JSON格式"""
        fmt = cli.OutputFormatter("json")
        buf = io.StringIO()
        with redirect_stdout(buf):
            fmt.output({"key": "value"})
        output = buf.getvalue().strip()
        data = json.loads(output)
        assert data["key"] == "value"

    def test_table_format(self):
        """测试表格格式"""
        fmt = cli.OutputFormatter("table")
        buf = io.StringIO()
        with redirect_stdout(buf):
            fmt.output({"key": "value"}, "Title")
        output = buf.getvalue()
        assert "Title" in output
        assert "key" in output

    def test_error_output(self):
        """测试错误输出"""
        fmt = cli.OutputFormatter("text")
        buf = io.StringIO()
        with redirect_stderr(buf):
            fmt.error("test error")
        assert "Error: test error" in buf.getvalue()

    def test_success_output(self):
        """测试成功输出"""
        fmt = cli.OutputFormatter("text")
        buf = io.StringIO()
        with redirect_stdout(buf):
            fmt.success("done")
        assert "[OK]" in buf.getvalue()

    def test_json_success(self):
        """测试JSON格式成功输出"""
        fmt = cli.OutputFormatter("json")
        buf = io.StringIO()
        with redirect_stdout(buf):
            fmt.success("done")
        data = json.loads(buf.getvalue().strip())
        assert data["status"] == "ok"

    def test_list_output(self):
        """测试列表输出"""
        fmt = cli.OutputFormatter("text")
        buf = io.StringIO()
        with redirect_stdout(buf):
            fmt.output({"items": [1, 2, 3, 4, 5, 6, 7]})
        output = buf.getvalue()
        assert "items" in output

    def test_nested_dict_output(self):
        """测试嵌套字典输出"""
        fmt = cli.OutputFormatter("text")
        buf = io.StringIO()
        with redirect_stdout(buf):
            fmt.output({"outer": {"inner": "value"}})
        output = buf.getvalue()
        assert "outer" in output
        assert "inner" in output


# ============================================================
# 基础命令测试
# ============================================================

class TestBasicCommands:
    """基础命令测试"""

    def test_no_command_shows_help(self):
        """测试无命令显示帮助"""
        code, out, err = run_cli()
        assert code == 0
        assert "agent-cli" in out or "usage" in out.lower()

    def test_status(self):
        """测试状态命令"""
        code, out, err = run_cli("status")
        assert code == 0

    def test_status_json_format(self):
        """测试JSON格式状态"""
        code, out, err = run_cli("-f", "json", "status")
        assert code == 0
        # 应该能解析为JSON
        try:
            data = json.loads(out.strip())
            assert data is not None
        except json.JSONDecodeError:
            # 可能有多行，取最后一行
            lines = [l for l in out.strip().split("\n") if l.strip()]
            if lines:
                data = json.loads(lines[-1])

    def test_start(self):
        """测试启动命令"""
        code, out, err = run_cli("start")
        assert code == 0
        assert "OK" in out or "启动" in out

    def test_stop(self):
        """测试停止命令"""
        code, out, err = run_cli("stop")
        assert code == 0
        assert "OK" in out or "停止" in out

    def test_cycle(self):
        """测试周期命令"""
        code, out, err = run_cli("cycle")
        assert code == 0


# ============================================================
# 感知/行动/反思测试
# ============================================================

class TestObserveActReflect:
    """感知/行动/反思命令测试"""

    def test_observe(self):
        """测试感知命令"""
        code, out, err = run_cli("observe")
        assert code == 0

    def test_observe_with_module(self):
        """测试带模块ID的感知"""
        code, out, err = run_cli("observe", "--module-id", "test_module")
        assert code == 0

    def test_act(self):
        """测试行动命令"""
        code, out, err = run_cli("act", "test_action")
        assert code == 0

    def test_act_with_context(self):
        """测试带上下文的行动"""
        code, out, err = run_cli("act", "test_action", "--context", '{"key": "value"}')
        assert code == 0

    def test_act_invalid_context(self):
        """测试无效上下文"""
        code, out, err = run_cli("act", "test", "--context", "not_json")
        assert code == 1
        assert "Error" in err

    def test_reflect(self):
        """测试反思命令"""
        code, out, err = run_cli("reflect")
        assert code == 0


# ============================================================
# 任务管理测试
# ============================================================

class TestTaskCommands:
    """任务管理命令测试"""

    def test_task_submit(self):
        """测试提交任务"""
        code, out, err = run_cli("task", "submit", "test goal")
        assert code == 0
        assert "task_id" in out or "任务" in out

    def test_task_submit_no_goal(self):
        """测试无目标提交"""
        code, out, err = run_cli("task", "submit")
        assert code == 1
        assert "Error" in err

    def test_task_status_nonexistent(self):
        """测试查询不存在任务状态"""
        code, out, err = run_cli("task", "status", "nonexistent_id")
        assert code == 1

    def test_task_result_nonexistent(self):
        """测试查询不存在任务结果"""
        code, out, err = run_cli("task", "result", "nonexistent_id")
        assert code == 1

    def test_task_execute(self):
        """测试执行任务"""
        code, out, err = run_cli("task", "execute", "test goal")
        assert code == 0

    def test_task_status_after_submit(self):
        """测试提交后查询状态"""
        # 提交
        code, out, err = run_cli("-f", "json", "task", "submit", "test goal")
        assert code == 0
        # 解析task_id - JSON输出可能是多行的
        try:
            data = json.loads(out.strip())
        except json.JSONDecodeError:
            # 可能有多行，取最后一个JSON对象
            lines = out.strip().split("\n")
            json_text = ""
            brace_count = 0
            for line in reversed(lines):
                json_text = line + "\n" + json_text
                brace_count += line.count("{") - line.count("}")
                if brace_count == 0 and json_text.strip():
                    break
            data = json.loads(json_text.strip())
        task_id = data.get("task_id")
        assert task_id is not None

        # 查询状态（注意：CLIContext已重置，需要用同一个agent实例）
        # 由于每次run_cli都重置上下文，这里我们测试在同一进程中
        cli.CLIContext.reset()
        agent = cli.CLIContext.get_agent()
        tid = agent.submit_task(goal="test goal")
        status = agent.get_task_status(tid)
        assert status is not None


# ============================================================
# 代码审查测试
# ============================================================

class TestReviewCommands:
    """代码审查命令测试"""

    def test_review_code(self):
        """测试审查代码"""
        code = "def add(a, b):\n    return a + b\n"
        code_, out, err = run_cli("review", "code", code)
        assert code_ == 0

    def test_review_code_no_code(self):
        """测试无代码审查"""
        code_, out, err = run_cli("review", "code")
        assert code_ == 1

    def test_review_file(self):
        """测试审查文件"""
        # 使用自身文件
        code_, out, err = run_cli("review", "file", __file__)
        assert code_ == 0

    def test_review_file_not_found(self):
        """测试审查不存在文件"""
        code_, out, err = run_cli("review", "file", "/nonexistent/file.py")
        assert code_ == 0  # review_file返回带error的报告，不报错

    def test_review_dir(self):
        """测试审查目录"""
        code_, out, err = run_cli("review", "dir", os.path.dirname(__file__))
        assert code_ == 0


# ============================================================
# 文档生成测试
# ============================================================

class TestDocsCommands:
    """文档生成命令测试"""

    def test_docs_generate(self):
        """测试生成文档"""
        code_str = 'def hello():\n    """Say hello"""\n    print("hello")\n'
        code, out, err = run_cli("docs", "generate", code_str)
        assert code == 0

    def test_docs_generate_html(self):
        """测试生成HTML文档"""
        code_str = "def f(): pass\n"
        code, out, err = run_cli("docs", "generate", code_str, "--format", "html")
        assert code == 0

    def test_docs_file(self):
        """测试从文件生成文档"""
        code, out, err = run_cli("docs", "file", __file__)
        assert code == 0

    def test_docs_generate_no_code(self):
        """测试无代码生成文档"""
        code, out, err = run_cli("docs", "generate")
        assert code == 1


# ============================================================
# 性能监控测试
# ============================================================

class TestPerfCommands:
    """性能监控命令测试"""

    def test_perf_report(self):
        """测试性能报告"""
        code, out, err = run_cli("perf", "report")
        assert code == 0

    def test_perf_cache(self):
        """测试缓存统计"""
        code, out, err = run_cli("perf", "cache")
        assert code == 0

    def test_perf_reset(self):
        """测试重置性能"""
        code, out, err = run_cli("perf", "reset")
        assert code == 0
        assert "OK" in out or "重置" in out

    def test_perf_profiler(self):
        """测试性能分析"""
        code, out, err = run_cli("perf", "profiler")
        assert code == 0

    def test_perf_report_json(self):
        """测试JSON格式性能报告"""
        code, out, err = run_cli("-f", "json", "perf", "report")
        assert code == 0


# ============================================================
# 插件管理测试
# ============================================================

class TestPluginCommands:
    """插件管理命令测试"""

    def test_plugin_list(self):
        """测试列出插件"""
        code, out, err = run_cli("plugin", "list")
        assert code == 0

    def test_plugin_health(self):
        """测试插件健康"""
        code, out, err = run_cli("plugin", "health")
        assert code == 0

    def test_plugin_stats(self):
        """测试插件统计"""
        code, out, err = run_cli("plugin", "stats")
        assert code == 0

    def test_plugin_unload_nonexistent(self):
        """测试卸载不存在插件"""
        code, out, err = run_cli("plugin", "unload", "nonexistent")
        assert code == 1

    def test_plugin_reload_nonexistent(self):
        """测试重载不存在插件"""
        code, out, err = run_cli("plugin", "reload", "nonexistent")
        assert code == 1

    def test_plugin_manifest_nonexistent(self):
        """测试获取不存在插件清单"""
        code, out, err = run_cli("plugin", "manifest", "nonexistent")
        assert code == 1


# ============================================================
# 健康检查测试
# ============================================================

class TestHealthCommand:
    """健康检查命令测试"""

    def test_health(self):
        """测试健康检查"""
        code, out, err = run_cli("health")
        # 健康检查可能返回0或1，取决于系统状态
        assert code in (0, 1)

    def test_health_json(self):
        """测试JSON格式健康检查"""
        code, out, err = run_cli("-f", "json", "health")
        assert code in (0, 1)


# ============================================================
# 错误处理测试
# ============================================================

class TestErrorHandling:
    """错误处理测试"""

    def test_invalid_command(self):
        """测试无效命令"""
        code, out, err = run_cli("invalid_command")
        # argparse会返回2表示参数错误
        assert code in (1, 2)

    def test_task_no_subcommand(self):
        """测试任务无子命令"""
        code, out, err = run_cli("task")
        assert code in (1, 2)

    def test_review_no_subcommand(self):
        """测试审查无子命令"""
        code, out, err = run_cli("review")
        assert code in (1, 2)

    def test_perf_no_subcommand(self):
        """测试性能无子命令"""
        code, out, err = run_cli("perf")
        assert code in (1, 2)

    def test_plugin_no_subcommand(self):
        """测试插件无子命令"""
        code, out, err = run_cli("plugin")
        assert code in (1, 2)

    def test_invalid_format(self):
        """测试无效格式"""
        code, out, err = run_cli("-f", "xml", "status")
        assert code in (1, 2)


# ============================================================
# 参数解析测试
# ============================================================

class TestArgumentParsing:
    """参数解析测试"""

    def test_parser_creation(self):
        """测试解析器创建"""
        parser = cli.build_parser()
        assert parser is not None

    def test_format_flag(self):
        """测试格式标志"""
        code, out, err = run_cli("--format", "json", "status")
        assert code == 0

    def test_short_format_flag(self):
        """测试短格式标志"""
        code, out, err = run_cli("-f", "table", "status")
        assert code == 0

    def test_help_flag(self):
        """测试帮助标志"""
        code, out, err = run_cli("--help")
        assert code == 0
        assert "agent-cli" in out or "usage" in out.lower()

    def test_subcommand_help(self):
        """测试子命令帮助"""
        code, out, err = run_cli("task", "--help")
        assert code == 0
        assert "submit" in out or "task" in out.lower()


# ============================================================
# 命令分发测试
# ============================================================

class TestCommandDispatch:
    """命令分发测试"""

    def test_dispatch_with_handler(self):
        """测试有处理器的分发"""
        formatter = cli.OutputFormatter("text")
        args = type("Args", (), {
            "handler": "cmd_status",
            "format": "text",
        })()
        code = cli.dispatch(args, formatter)
        assert code == 0

    def test_dispatch_no_handler(self):
        """测试无处理器的分发"""
        formatter = cli.OutputFormatter("text")
        args = type("Args", (), {})()
        code = cli.dispatch(args, formatter)
        assert code == 1

    def test_dispatch_unknown_handler(self):
        """测试未知处理器"""
        formatter = cli.OutputFormatter("text")
        args = type("Args", (), {"handler": "nonexistent"})()
        code = cli.dispatch(args, formatter)
        assert code == 1

    def test_dispatch_with_exception(self):
        """测试处理器异常"""
        formatter = cli.OutputFormatter("text")
        args = type("Args", (), {
            "handler": "cmd_observe",
            "module_id": None,
            "predicted": None,
            "actual": None,
        })()
        # 不应该崩溃
        code = cli.dispatch(args, formatter)
        assert code in (0, 1)


# ============================================================
# CLI上下文测试
# ============================================================

class TestCLIContext:
    """CLI上下文测试"""

    def test_get_agent(self):
        """测试获取Agent"""
        cli.CLIContext.reset()
        agent = cli.CLIContext.get_agent()
        assert agent is not None

    def test_get_agent_cached(self):
        """测试Agent缓存"""
        cli.CLIContext.reset()
        agent1 = cli.CLIContext.get_agent()
        agent2 = cli.CLIContext.get_agent()
        assert agent1 is agent2

    def test_get_coordinator(self):
        """测试获取协调器"""
        cli.CLIContext.reset()
        coord = cli.CLIContext.get_coordinator()
        assert coord is not None

    def test_reset(self):
        """测试重置"""
        cli.CLIContext.get_agent()
        cli.CLIContext.reset()
        assert cli.CLIContext._agent is None


# ============================================================
# 第一性原理验证
# ============================================================

class TestFirstPrinciples:
    """第一性原理验证"""

    def test_operability_principle(self):
        """第一性原理：可操作性 — 每个核心功能都有CLI入口"""
        commands = ["status", "cycle", "observe", "reflect"]
        for cmd in commands:
            code, out, err = run_cli(cmd)
            assert code == 0, f"Command '{cmd}' failed"
        # act需要action参数
        assert run_cli("act", "default")[0] == 0

    def test_scriptability_principle(self):
        """第一性原理：可脚本化 — JSON输出可被程序解析"""
        code, out, err = run_cli("-f", "json", "status")
        assert code == 0
        # JSON输出应可解析（可能是多行JSON）
        try:
            json.loads(out.strip())
            found_json = True
        except json.JSONDecodeError:
            # 尝试找到JSON部分
            found_json = False
            lines = out.strip().split("\n")
            # 尝试从第一行{开始解析
            for start in range(len(lines)):
                if lines[start].strip().startswith("{"):
                    try:
                        json_text = "\n".join(lines[start:])
                        json.loads(json_text)
                        found_json = True
                        break
                    except json.JSONDecodeError:
                        continue
        assert found_json, "No valid JSON found in output"

    def test_discoverability_principle(self):
        """第一性原理：可发现性 — 帮助信息完整"""
        code, out, err = run_cli("--help")
        assert code == 0
        # 应包含所有主要命令
        for cmd in ["start", "stop", "status", "task", "review", "plugin"]:
            assert cmd in out, f"Command '{cmd}' not in help"

    def test_consistency_principle(self):
        """第一性原理：一致性 — 所有命令返回一致的退出码"""
        # 成功命令返回0
        assert run_cli("status")[0] == 0
        # 失败命令返回非0
        assert run_cli("task", "submit")[0] != 0

    def test_feedback_principle(self):
        """第一性原理：反馈性 — 操作结果有清晰输出"""
        code, out, err = run_cli("start")
        assert code == 0
        assert len(out) > 0  # 有输出

        code, out, err = run_cli("perf", "reset")
        assert code == 0
        assert "OK" in out or "重置" in out  # 有成功反馈

    def test_error_transparency_principle(self):
        """第一性原理：错误透明 — 错误信息清晰"""
        code, out, err = run_cli("task", "submit")
        assert code != 0
        assert "Error" in err or "error" in err.lower()

    def test_completeness_principle(self):
        """第一性原理：完整性 — 覆盖所有核心能力"""
        # 系统控制
        assert run_cli("start")[0] == 0
        assert run_cli("stop")[0] == 0
        assert run_cli("status")[0] == 0
        # 感知行动
        assert run_cli("observe")[0] == 0
        assert run_cli("act", "test")[0] == 0
        assert run_cli("reflect")[0] == 0
        # 任务
        assert run_cli("task", "submit", "goal")[0] == 0
        # 代码审查
        assert run_cli("review", "code", "x=1")[0] == 0
        # 文档
        assert run_cli("docs", "generate", "x=1")[0] == 0
        # 性能
        assert run_cli("perf", "report")[0] == 0
        # 插件
        assert run_cli("plugin", "list")[0] == 0
        # 健康
        assert run_cli("health")[0] in (0, 1)
