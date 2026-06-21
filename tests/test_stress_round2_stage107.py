"""
阶段107: 第二轮复杂场景验证

更长时间、更大规模、更错综复杂、更高难度、更混乱的场景。
基于第一轮发现的问题模式，设计更有针对性的破坏性测试。
"""

import logging
import sys
import os
import time
import json
import threading
import traceback
import random
import math
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stress_logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, f"stress_round2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("stress_round2")


class BugCollector:
    def __init__(self):
        self._lock = threading.Lock()
        self.bugs = []

    def record(self, category, desc, exc=None, ctx=None):
        with self._lock:
            self.bugs.append({
                "category": category, "description": desc,
                "exception": type(exc).__name__ if exc else None,
                "msg": str(exc) if exc else None,
                "context": str(ctx)[:300] if ctx else None,
                "ts": datetime.now().isoformat(),
            })
            logger.error("[BUG] %s: %s | %s", category, desc,
                         type(exc).__name__ if exc else "N/A")

    def summary(self):
        with self._lock:
            by_cat = {}
            for b in self.bugs:
                by_cat[b["category"]] = by_cat.get(b["category"], 0) + 1
            return {"total": len(self.bugs), "by_category": by_cat}


bc = BugCollector()


def safe(func, *args, cat="unknown", desc="", **kwargs):
    try:
        return func(*args, **kwargs)
    except Exception as e:
        bc.record(cat, desc or func.__name__, e, {"args": str(args)[:200]})
        return None


# ============================================================
# 场景1: 超大规模并发（50线程 x 200操作）
# ============================================================

def test_massive_concurrency():
    logger.info("=" * 60)
    logger.info("场景1: 超大规模并发（50线程 x 200操作 = 10000次）")
    logger.info("=" * 60)

    from self_evolving_agent import create_default_agent
    agent = create_default_agent()
    success = [0]
    fail = [0]
    lock = threading.Lock()

    def worker(tid):
        for i in range(200):
            try:
                ops = ["observe", "act", "reflect", "run_cycle", "get_state"]
                op = random.choice(ops)
                if op == "observe":
                    agent.observe({"module_id": f"t{tid}_{i}", "predicted": {"v": random.random()}, "actual": {"v": random.random()}})
                elif op == "act":
                    agent.act(f"action_{i}", context={"resources_used": {"cpu": random.uniform(0, 1)}})
                elif op == "reflect":
                    agent.reflect()
                elif op == "run_cycle":
                    agent.run_cycle({"outcome": {"information_value": random.uniform(0, 1)}})
                elif op == "get_state":
                    agent.get_state()
                with lock:
                    success[0] += 1
            except Exception as e:
                with lock:
                    fail[0] += 1
                bc.record("massive_concurrency", f"t{tid} op={op} i={i}", e)

    threads = [threading.Thread(target=worker, args=(t,), name=f"W{t}", daemon=True) for t in range(50)]
    start = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=120)
    elapsed = time.time() - start

    logger.info("超大规模并发完成: success=%d fail=%d 耗时=%.2fs 吞吐=%.0f ops/s",
                success[0], fail[0], elapsed, success[0] / elapsed)


# ============================================================
# 场景2: 混沌状态注入（随机破坏内部状态后验证恢复）
# ============================================================

def test_chaos_injection():
    logger.info("=" * 60)
    logger.info("场景2: 混沌状态注入")
    logger.info("=" * 60)

    from self_evolving_agent import create_default_agent
    agent = create_default_agent()

    # 正常运行
    for i in range(10):
        agent.observe({"module_id": f"pre_{i}", "predicted": {"v": 0.5}, "actual": {"v": 0.6}})

    # 注入混沌：各种畸形数据
    chaos_inputs = [
        {"module_id": [], "predicted": {}, "actual": {}},
        {"module_id": {}, "predicted": [], "actual": []},
        {"module_id": 3.14, "predicted": True, "actual": False},
        {"module_id": float('nan'), "predicted": float('inf'), "actual": float('nan')},
        {"module_id": "x", "predicted": {"v": [1, [2, [3, [4]]]]}, "actual": {"v": None}},
        {"module_id": "x" * 100000, "predicted": {"v": "x" * 100000}, "actual": {}},
        {"module_id": "\x00\x01\x02", "predicted": {"v": "\xff\xfe"}, "actual": {}},
        {"module_id": "x", "predicted": {"v": {"nested": {"deep": {"very": {"deep": "value"}}}}}, "actual": {}},
    ]

    for i, chaos in enumerate(chaos_inputs):
        safe(agent.observe, chaos, cat="chaos", desc=f"chaos_input_{i}")
        safe(agent.act, f"chaos_action_{i}", cat="chaos", desc=f"chaos_act_{i}")
        safe(agent.reflect, cat="chaos", desc=f"chaos_reflect_{i}")

    # 验证恢复
    result = safe(agent.observe, {"module_id": "recovery", "predicted": {"v": 0.5}, "actual": {"v": 0.6}},
                  cat="chaos", desc="recovery_after_chaos")
    if result is None:
        bc.record("chaos", "混沌注入后系统无法恢复")
    else:
        logger.info("混沌注入后系统恢复正常")


# ============================================================
# 场景3: 长期运行 + 周期性突变（2000周期）
# ============================================================

def test_long_term_with_shocks():
    logger.info("=" * 60)
    logger.info("场景3: 长期运行 + 周期性突变（2000周期）")
    logger.info("=" * 60)

    from self_evolving_agent import create_default_agent
    agent = create_default_agent()
    start = time.time()

    for i in range(2000):
        # 正常周期
        if i % 100 != 99:
            value = math.sin(i * 0.01) * 0.5 + 0.5 + random.gauss(0, 0.05)
            safe(agent.observe, {"module_id": f"env_{i}", "predicted": {"v": 0.5}, "actual": {"v": max(0, min(1, value))}},
                 cat="longterm", desc=f"observe_{i}")
        # 突变周期
        else:
            logger.info("[周期 %d] 注入突变", i)
            # 大幅偏离预测
            safe(agent.observe, {"module_id": f"shock_{i}", "predicted": {"v": 0.5}, "actual": {"v": random.choice([0.0, 1.0, 0.99, 0.01])}},
                 cat="longterm", desc=f"shock_observe_{i}")
            # 尝试行动
            safe(agent.act, "respond_to_shock", context={"resources_used": {"cpu": 0.8}, "output_value": 0.3},
                 cat="longterm", desc=f"shock_act_{i}")

        # 每200周期反思
        if i % 200 == 199:
            safe(agent.reflect, cat="longterm", desc=f"reflect_{i}")
            state = safe(agent.get_state, cat="longterm", desc=f"get_state_{i}")
            if state:
                logger.info("[周期 %d] cycle_count=%d", i, state.get("cycle_count", -1))

    elapsed = time.time() - start
    logger.info("长期运行完成: 2000周期, 耗时=%.2fs, 平均=%.4fs/周期", elapsed, elapsed / 2000)


# ============================================================
# 场景4: 子引擎极限压力测试
# ============================================================

def test_engine_extreme_stress():
    logger.info("=" * 60)
    logger.info("场景4: 子引擎极限压力测试")
    logger.info("=" * 60)

    from self_evolving_agent.core.unified_first_principles_engine import create_unified_engine
    engine = create_unified_engine()

    # 预测编码：1000次快速循环
    logger.info("[极限] predictive_coding: 1000次循环")
    for i in range(1000):
        safe(engine.predictive_coding.run_cycle, f"stress_{i}", {"v": random.random()}, {"v": random.random()},
             cat="extreme", desc=f"pc_{i}")

    # 驱力：反复更新状态
    logger.info("[极限] drive: 500次状态更新")
    for i in range(500):
        safe(engine.drive.update_state, safe_level=random.uniform(0, 1), gain_level=random.uniform(0, 1), eff_level=random.uniform(0, 1),
             cat="extreme", desc=f"drive_{i}")
    safe(engine.drive.compute_gaps, cat="extreme", desc="drive.compute_gaps_after_500")

    # 记忆：大量存储
    logger.info("[极限] memory: 500次存储")
    for i in range(500):
        safe(engine.memory.store, f"extreme_key_{i}", {"data": f"unique_content_{i}_{random.random()}"},
             cat="extreme", desc=f"memory_{i}")

    # 学习：大量学习信号
    logger.info("[极限] learning: 500次学习")
    for i in range(500):
        safe(engine.learning.learn_from_error, f"param_{i}", error_magnitude=random.uniform(0, 1), delta=-0.01, error_source=f"src_{i}",
             cat="extreme", desc=f"learning_{i}")

    # 能效：大量使用记录
    logger.info("[极限] efficiency: 500次使用记录")
    from self_evolving_agent.core.efficiency_first_principles import ResourceType
    engine.efficiency.set_budget("extreme_b", ResourceType.CPU, 1000.0)
    for i in range(500):
        safe(engine.efficiency.record_usage, f"extreme_usage_{i}", ResourceType.CPU, random.uniform(0, 2), random.uniform(0, 1),
             cat="extreme", desc=f"efficiency_{i}")

    # 因果：大量观测
    logger.info("[极限] causal: 500次观测")
    for i in range(500):
        safe(engine.causal.record_observation, {"var_a": random.random(), "var_b": random.random(), "var_c": random.random()},
             cat="extreme", desc=f"causal_{i}")

    # 意识：大量广播
    logger.info("[极限] consciousness: 100次广播")
    from self_evolving_agent.core.consciousness_first_principles import WorkspaceContent, ContentType
    for i in range(100):
        safe(engine.consciousness.broadcast, WorkspaceContent(
            content_id=f"extreme_c_{i}", content_type=random.choice(list(ContentType)),
            content={"i": i}, salience=random.uniform(0, 1)),
            cat="extreme", desc=f"consciousness_{i}")

    # 自由意志：大量决策
    logger.info("[极限] free_will: 100次决策")
    from self_evolving_agent.core.free_will_first_principles import ChoiceSet
    for i in range(100):
        choices = ChoiceSet(choice_id=f"extreme_d_{i}", options=[f"opt_{j}" for j in range(5)], context={})
        safe(engine.free_will.make_decision, choices, lambda o, c: random.random(),
             cat="extreme", desc=f"freewill_{i}")

    # 获取统计验证不崩溃
    safe(engine.get_full_stats, cat="extreme", desc="get_full_stats_after_extreme")
    logger.info("子引擎极限压力测试完成")


# ============================================================
# 场景5: 协调器编排极限测试
# ============================================================

def test_coordinator_extreme():
    logger.info("=" * 60)
    logger.info("场景5: 协调器编排极限测试（500次完整周期）")
    logger.info("=" * 60)

    from self_evolving_agent.core.unified_first_principles_engine import create_unified_engine
    engine = create_unified_engine()

    for i in range(500):
        context = {
            "available_actions": [f"action_{j}" for j in range(random.randint(1, 10))],
            "outcome": {
                "information_value": random.uniform(0, 1),
                "error_reduction": random.uniform(0, 0.5),
                "safe_improvement": random.uniform(0, 0.1) if random.random() > 0.7 else 0,
                "gain_improvement": random.uniform(0, 0.1) if random.random() > 0.8 else 0,
                "eff_improvement": random.uniform(0, 0.1) if random.random() > 0.9 else 0,
            },
            "resources_used": {
                "cpu": random.uniform(0.1, 0.8),
                "memory": random.uniform(0.1, 0.5),
            },
            "output_value": random.uniform(0.2, 0.9),
        }
        safe(engine.run_integration_cycle, context, cat="coordinator", desc=f"integration_{i}")

        if i % 100 == 99:
            logger.info("[周期 %d] 编排完成", i)

    logger.info("协调器编排极限测试完成: 500周期")


# ============================================================
# 场景6: 资源耗尽模拟
# ============================================================

def test_resource_exhaustion():
    logger.info("=" * 60)
    logger.info("场景6: 资源耗尽模拟")
    logger.info("=" * 60)

    from self_evolving_agent.core.memory_first_principles import MemoryFirstPrinciplesEngine
    from self_evolving_agent.core.efficiency_first_principles import EfficiencyFirstPrinciplesEngine, ResourceType

    # 记忆引擎：小容量 + 大量存储
    logger.info("[资源耗尽] memory: capacity=5, 存储100项")
    mem = MemoryFirstPrinciplesEngine("test", capacity=5, retention_threshold=0.0)
    for i in range(100):
        safe(mem.store, f"key_{i}", {"data": f"unique_long_content_for_testing_{i}"}, cat="resource", desc=f"mem_exhaust_{i}")
    stats = safe(mem.get_stats, cat="resource", desc="mem_stats_after_exhaust")
    if stats:
        logger.info("  memory: items=%d capacity=%d forgotten=%d", stats["items_count"], stats["capacity"], stats["forgotten_count"])

    # 能效引擎：预算耗尽
    logger.info("[资源耗尽] efficiency: budget=10, 消耗100")
    eff = EfficiencyFirstPrinciplesEngine("test")
    eff.set_budget("b1", ResourceType.CPU, 10.0)
    for i in range(100):
        safe(eff.record_usage, f"usage_{i}", ResourceType.CPU, 0.5, 0.3, cat="resource", desc=f"eff_exhaust_{i}")
    budget = eff._budgets.get("b1")
    if budget:
        logger.info("  efficiency: consumed=%.1f allocated=%.1f exhausted=%s", budget.consumed, budget.allocated, budget.is_exhausted)


# ============================================================
# 场景7: 混合操作流（模拟真实业务场景）
# ============================================================

def test_mixed_operation_flow():
    logger.info("=" * 60)
    logger.info("场景7: 混合操作流（模拟真实业务场景，500步）")
    logger.info("=" * 60)

    from self_evolving_agent import create_default_agent
    agent = create_default_agent()

    # 设置初始目标
    agent.set_goal("safe", 0.95)
    agent.set_goal("gain", 0.8)
    agent.set_goal("eff", 0.85)

    for step in range(500):
        # 模拟真实业务：80%正常操作，15%边界操作，5%异常操作
        r = random.random()
        if r < 0.8:
            # 正常操作
            agent.observe({"module_id": f"biz_{step}", "predicted": {"v": 0.5}, "actual": {"v": 0.5 + random.gauss(0, 0.1)}})
            if step % 5 == 0:
                agent.act("process", context={"resources_used": {"cpu": 0.3}})
            if step % 20 == 0:
                agent.reflect()
            if step % 50 == 0:
                agent.run_cycle({"outcome": {"information_value": 0.6}})
        elif r < 0.95:
            # 边界操作
            agent.observe({"module_id": f"edge_{step}", "predicted": {"v": 0.0}, "actual": {"v": 1.0}})
        else:
            # 异常操作（不崩溃即可）
            try:
                agent.observe({"module_id": None, "predicted": None, "actual": None})
            except Exception:
                pass

        if step % 100 == 99:
            state = agent.get_state()
            logger.info("[步骤 %d] cycle=%d", step, state.get("cycle_count", -1))

    logger.info("混合操作流完成: 500步")


# ============================================================
# 主入口
# ============================================================

def run_round2():
    logger.info("#" * 60)
    logger.info("# 第二轮复杂场景压力测试开始")
    logger.info("# 日志: %s", LOG_FILE)
    logger.info("#" * 60)

    start = time.time()
    tests = [
        ("超大规模并发", test_massive_concurrency),
        ("混沌状态注入", test_chaos_injection),
        ("长期运行+突变", test_long_term_with_shocks),
        ("子引擎极限压力", test_engine_extreme_stress),
        ("协调器编排极限", test_coordinator_extreme),
        ("资源耗尽模拟", test_resource_exhaustion),
        ("混合操作流", test_mixed_operation_flow),
    ]

    for name, func in tests:
        try:
            func()
        except Exception as e:
            bc.record("test_harness", f"测试场景崩溃: {name}", e)

    elapsed = time.time() - start
    summary = bc.summary()

    logger.info("#" * 60)
    logger.info("# 第二轮压力测试完成")
    logger.info("# 总耗时: %.2fs", elapsed)
    logger.info("# Bug统计: %s", json.dumps(summary, ensure_ascii=False, indent=2))
    logger.info("#" * 60)

    return {"elapsed": elapsed, "summary": summary, "bugs": bc.bugs, "log_file": LOG_FILE}


if __name__ == "__main__":
    result = run_round2()
    print("\n" + "=" * 60)
    print(f"第二轮压力测试完成: {result['summary']['total']} bugs")
    print(f"总耗时: {result['elapsed']:.2f}s")
    if result["bugs"]:
        print("\nBUG详情:")
        for i, bug in enumerate(result["bugs"], 1):
            print(f"  [{i}] {bug['category']}: {bug['description']} ({bug['exception']})")
