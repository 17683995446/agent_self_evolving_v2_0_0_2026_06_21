"""
快速入门示例 — 最小可运行示例

这是新用户首次使用的推荐起点。
演示 Agent 的核心生命周期：创建 → 初始化 → 感知 → 行动 → 反思

运行方式:
    python examples/quickstart.py

无需任何配置即可运行（无 LLM 模式）。
"""

import os
import sys

# 确保能导入项目模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SKIP_LLM_INIT", "true")


def main():
    """快速入门主函数"""
    print("=" * 50)
    print("  自驱永续进化Agent系统 — 快速入门")
    print("=" * 50)
    print()

    # 步骤1: 创建并初始化 Agent
    print("[1/5] 创建 Agent...")
    from self_evolving_agent import create_default_agent
    agent = create_default_agent()
    agent.initialize({"cycle_interval": 0.5})
    print("  [OK] Agent 创建成功")
    print()

    # 步骤2: 查看初始状态
    print("[2/5] 查看 Agent 状态...")
    state = agent.get_state()
    stage = state.get("lifecycle", {}).get("stage", "unknown")
    print(f"  生命周期阶段: {stage}")
    print()

    # 步骤3: 感知环境
    print("[3/5] 感知环境...")
    observation = agent.observe({
        "module_id": "demo",
        "predicted": {"value": 0.5},
        "actual": {"value": 0.55},
    })
    print(f"  [OK] 感知完成")
    print(f"  预测误差: {observation.get('prediction_error', 'N/A')}")
    print()

    # 步骤4: 执行行动
    print("[4/5] 执行行动...")
    action = agent.act("explore", context={"resources_used": {"cpu": 0.3}})
    print(f"  [OK] 行动完成")
    print(f"  行动类型: {action.get('action', 'N/A')}")
    print()

    # 步骤5: 反思
    print("[5/5] 运行反思...")
    reflection = agent.reflect()
    print(f"  [OK] 反思完成")
    print(f"  经验数量: {reflection.get('experiences_count', 'N/A')}")
    print()

    print("=" * 50)
    print("  快速入门完成！")
    print("=" * 50)
    print()
    print("下一步:")
    print("  - 运行完整工作流: python examples/full_workflow.py")
    print("  - 启动 API 服务:  python main.py")
    print("  - 使用 CLI 工具:   python cli.py --help")
    print("  - 查看配置指南:    docs/configuration.md")
    print()


if __name__ == "__main__":
    main()
