"""
中级示例 — 任务执行与代码审查

演示 Agent 的实用功能：
- 同步执行任务
- 代码审查
- 性能监控

运行方式:
    python examples/intermediate.py

无需 LLM 配置即可运行。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SKIP_LLM_INIT", "true")


def demo_task_execution(agent):
    """演示任务执行"""
    print("--- 任务执行 ---")
    print("执行任务: '分析系统状态'")

    result = agent.execute_task("分析系统状态并生成报告")
    # TaskResult 对象，使用属性访问
    status = getattr(result, "status", None)
    status_str = status.value if hasattr(status, "value") else str(status)
    print(f"  任务状态: {status_str}")
    print(f"  是否成功: {getattr(result, 'success', 'N/A')}")
    print(f"  完成步骤: {getattr(result, 'steps_completed', 0)}/{getattr(result, 'steps_total', 0)}")
    print()
    return result


def demo_code_review(agent):
    """演示代码审查"""
    print("--- 代码审查 ---")
    sample_code = """
def calculate_sum(a, b):
    return a + b

def divide(a, b):
    return a / b
"""
    print(f"审查代码:\n{sample_code}")

    report = agent.review_code(sample_code)
    # ReviewReport 对象，使用属性访问
    issues = getattr(report, "issues", [])
    score = getattr(report, "score", "N/A")
    print(f"  审查完成")
    print(f"  问题数量: {len(issues)}")
    print(f"  代码评分: {score}")
    print()
    return report


def demo_performance(agent):
    """演示性能监控"""
    print("--- 性能监控 ---")
    report = agent.get_performance_report()
    print(f"  性能指标:")
    if isinstance(report, dict):
        for key, value in report.items():
            if isinstance(value, (int, float, str)):
                print(f"    {key}: {value}")
    else:
        # 对象形式
        for attr in ["total_operations", "avg_latency_ms", "cache_hit_rate"]:
            val = getattr(report, attr, None)
            if val is not None:
                print(f"    {attr}: {val}")
    print()
    return report


def main():
    """中级示例主函数"""
    print("=" * 50)
    print("  自驱永续进化Agent系统 — 中级示例")
    print("=" * 50)
    print()

    from self_evolving_agent import create_default_agent
    agent = create_default_agent()
    agent.initialize({"cycle_interval": 0.5})

    # 执行三个演示
    demo_task_execution(agent)
    demo_code_review(agent)
    demo_performance(agent)

    print("=" * 50)
    print("  中级示例完成！")
    print("=" * 50)
    print()
    print("下一步:")
    print("  - 完整工作流: python examples/full_workflow.py")
    print("  - API 工作流: python examples/api_workflow.py")
    print("  - 启用 LLM:   设置 SILICONFLOW_API_KEY 环境变量")
    print()


if __name__ == "__main__":
    main()
