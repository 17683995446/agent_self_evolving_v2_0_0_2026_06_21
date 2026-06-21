"""
阶段101: 复杂场景压力测试框架

目标：在真实运行中发现系统bug
策略：
1. 全链路日志埋点（每个关键方法入口/出口/异常）
2. 复杂场景：并发、边界、异常、长期运行、状态混乱
3. 收集所有异常和警告，定位bug
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
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple

# 添加项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置根日志：输出到文件 + 控制台
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stress_logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, f"stress_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] [%(threadName)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("stress_test")


# ============================================================
# Bug 收集器
# ============================================================

class BugCollector:
    """收集测试中发现的bug"""

    def __init__(self):
        self._lock = threading.Lock()
        self.bugs: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []

    def record_bug(self, category: str, description: str, exception: Optional[Exception] = None,
                   context: Optional[Dict[str, Any]] = None) -> None:
        with self._lock:
            entry = {
                "category": category,
                "description": description,
                "exception_type": type(exception).__name__ if exception else None,
                "exception_msg": str(exception) if exception else None,
                "traceback": traceback.format_exc() if exception else None,
                "context": context or {},
                "timestamp": datetime.now().isoformat(),
            }
            self.bugs.append(entry)
            logger.error("[BUG] %s: %s | exc=%s", category, description,
                         entry["exception_type"])

    def record_error(self, source: str, msg: str) -> None:
        with self._lock:
            self.errors.append({"source": source, "msg": msg, "ts": datetime.now().isoformat()})

    def record_warning(self, source: str, msg: str) -> None:
        with self._lock:
            self.warnings.append({"source": source, "msg": msg, "ts": datetime.now().isoformat()})

    def summary(self) -> Dict[str, Any]:
        with self._lock:
            # 按类别聚合 bug
            by_category: Dict[str, int] = {}
            for b in self.bugs:
                by_category[b["category"]] = by_category.get(b["category"], 0) + 1
            return {
                "total_bugs": len(self.bugs),
                "total_errors": len(self.errors),
                "total_warnings": len(self.warnings),
                "bugs_by_category": by_category,
            }


bug_collector = BugCollector()


def safe_call(func, *args, category="unknown", description="", **kwargs):
    """安全调用：捕获异常并记录bug"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        bug_collector.record_bug(category, description or func.__name__, e,
                                 {"args": str(args)[:200], "kwargs": str(kwargs)[:200]})
        return None


# ============================================================
# 测试场景
# ============================================================

class StressTestScenarios:
    """复杂场景压力测试"""

    def __init__(self):
        from self_evolving_agent import create_default_agent, create_coordinator
        from self_evolving_agent.core.unified_first_principles_engine import create_unified_engine
        self.agent = create_default_agent()
        self.coordinator = create_coordinator("stress_coordinator")
        self.engine = create_unified_engine("stress_engine")

    # ------------------------------------------------------------
    # 场景1: 边界值与异常输入测试
    # ------------------------------------------------------------

    def test_boundary_inputs(self) -> None:
        """测试边界值和异常输入"""
        logger.info("=" * 60)
        logger.info("场景1: 边界值与异常输入测试")
        logger.info("=" * 60)

        # 各种异常输入
        abnormal_states = [
            ("空字典", {}),
            ("None值", {"module_id": None, "predicted": None, "actual": None}),
            ("空字符串", {"module_id": "", "predicted": "", "actual": ""}),
            ("极端大值", {"module_id": "x", "predicted": {"v": 1e308}, "actual": {"v": -1e308}}),
            ("NaN值", {"module_id": "x", "predicted": {"v": float('nan')}, "actual": {"v": float('inf')}}),
            ("负数", {"module_id": "x", "predicted": {"v": -999}, "actual": {"v": -1000}}),
            ("嵌套深对象", {"module_id": "x", "predicted": {"a": {"b": {"c": {"d": "deep"}}}}, "actual": {}}),
            ("列表而非字典", {"module_id": "x", "predicted": [1, 2, 3], "actual": [4, 5, 6]}),
            ("字符串而非字典", {"module_id": "x", "predicted": "string", "actual": "string2"}),
            ("数字而非字典", {"module_id": "x", "predicted": 42, "actual": 99}),
            ("布尔值", {"module_id": "x", "predicted": True, "actual": False}),
            ("超长字符串", {"module_id": "x" * 10000, "predicted": {"v": "x" * 10000}, "actual": {}}),
        ]

        for name, state in abnormal_states:
            logger.info("[边界测试] %s", name)
            # 测试 agent.observe
            result = safe_call(self.agent.observe, state,
                               category="boundary", description=f"agent.observe({name})")
            if result is not None:
                logger.debug("  -> observe 返回 keys=%s", list(result.keys()) if isinstance(result, dict) else type(result))

            # 测试 coordinator.observe
            result = safe_call(self.coordinator.observe, state,
                               category="boundary", description=f"coordinator.observe({name})")
            if result is not None:
                logger.debug("  -> coordinator.observe 返回 keys=%s", list(result.keys()) if isinstance(result, dict) else type(result))

            # 测试 engine.perceive_and_predict
            result = safe_call(
                self.engine.perceive_and_predict,
                state.get("module_id", "x") if isinstance(state, dict) else "x",
                state.get("predicted", {}) if isinstance(state, dict) else {},
                state.get("actual", {}) if isinstance(state, dict) else {},
                category="boundary", description=f"engine.perceive_and_predict({name})",
            )

    # ------------------------------------------------------------
    # 场景2: 并发压力测试
    # ------------------------------------------------------------

    def test_concurrent_stress(self) -> None:
        """并发压力测试：多线程同时操作"""
        logger.info("=" * 60)
        logger.info("场景2: 并发压力测试（20线程 x 50次操作）")
        logger.info("=" * 60)

        results = {"success": 0, "fail": 0}
        results_lock = threading.Lock()

        def worker(thread_id: int, ops: int) -> None:
            for i in range(ops):
                state = {
                    "module_id": f"thread_{thread_id}_op_{i}",
                    "predicted": {"value": random.uniform(0, 1)},
                    "actual": {"value": random.uniform(0, 1)},
                }
                # 随机选择操作
                op = random.choice(["observe", "act", "reflect", "run_cycle"])
                try:
                    if op == "observe":
                        self.agent.observe(state)
                    elif op == "act":
                        self.agent.act(f"action_{i}", context={"resources_used": {"cpu": 0.1}})
                    elif op == "reflect":
                        self.agent.reflect()
                    elif op == "run_cycle":
                        self.agent.run_cycle({"outcome": {"information_value": 0.6}})
                    with results_lock:
                        results["success"] += 1
                except Exception as e:
                    with results_lock:
                        results["fail"] += 1
                    bug_collector.record_bug("concurrent", f"thread_{thread_id} op={op}", e,
                                             {"thread": thread_id, "op": op, "iter": i})

        threads = []
        for t in range(20):
            th = threading.Thread(target=worker, args=(t, 50), name=f"Worker-{t}")
            threads.append(th)
            th.start()
        for th in threads:
            th.join(timeout=60)

        logger.info("并发测试结果: success=%d, fail=%d", results["success"], results["fail"])

    # ------------------------------------------------------------
    # 场景3: 长期运行稳定性测试
    # ------------------------------------------------------------

    def test_long_running_stability(self, cycles: int = 500) -> None:
        """长期运行稳定性测试"""
        logger.info("=" * 60)
        logger.info("场景3: 长期运行稳定性测试（%d周期）", cycles)
        logger.info("=" * 60)

        start_time = time.time()
        for i in range(cycles):
            try:
                # 模拟复杂环境：周期性 + 噪声 + 突变
                t = i * 0.1
                if i % 50 == 49:  # 每50周期注入突变
                    value = random.uniform(0, 1)
                    logger.info("[周期 %d] 注入突变 value=%.3f", i, value)
                else:
                    value = math.sin(t) * 0.5 + 0.5 + random.gauss(0, 0.1)

                state = {
                    "module_id": f"env_{i}",
                    "predicted": {"value": 0.5},
                    "actual": {"value": max(0.0, min(1.0, value))},
                }
                self.agent.observe(state)

                if i % 10 == 9:
                    self.agent.act("explore", context={
                        "resources_used": {"cpu": random.uniform(0.1, 0.5)},
                        "output_value": random.uniform(0.3, 0.9),
                    })

                if i % 25 == 24:
                    self.agent.reflect()

                if i % 100 == 99:
                    logger.info("[周期 %d] 累计运行 %d 周期，耗时 %.2fs",
                                i, i + 1, time.time() - start_time)
            except Exception as e:
                bug_collector.record_bug("long_running", f"cycle {i}", e, {"cycle": i})

        elapsed = time.time() - start_time
        logger.info("长期运行完成: %d 周期, 耗时 %.2fs, 平均 %.4fs/周期",
                    cycles, elapsed, elapsed / cycles)

    # ------------------------------------------------------------
    # 场景4: 引擎子模块逐一深度测试
    # ------------------------------------------------------------

    def test_sub_engines_deep(self) -> None:
        """逐一深度测试15个子引擎"""
        logger.info("=" * 60)
        logger.info("场景4: 15个子引擎深度测试")
        logger.info("=" * 60)

        engine = self.engine

        # 1. 预测编码引擎
        logger.info("[子引擎] predictive_coding")
        for _ in range(20):
            safe_call(engine.predictive_coding.run_cycle,
                      "test", {"v": random.random()}, {"v": random.random()},
                      category="sub_engine", description="predictive_coding.run_cycle")

        # 2. 驱力引擎
        logger.info("[子引擎] drive")
        safe_call(engine.drive.update_state, safe_level=0.5, gain_level=0.6, eff_level=0.7,
                  category="sub_engine", description="drive.update_state")
        safe_call(engine.drive.update_state, safe_level=-1, gain_level=2, eff_level=None,
                  category="sub_engine", description="drive.update_state(abnormal)")
        gaps = safe_call(engine.drive.compute_gaps, category="sub_engine", description="drive.compute_gaps")
        dom = safe_call(engine.drive.get_dominant_gap, category="sub_engine", description="drive.get_dominant_gap")
        req = safe_call(engine.drive.is_action_required, category="sub_engine", description="drive.is_action_required")
        logger.debug("  drive: gaps=%s dominant=%s action_required=%s",
                     len(gaps) if gaps else None,
                     dom.drive_type.value if dom else None,
                     req)

        # 3. 学习引擎
        logger.info("[子引擎] learning")
        for _ in range(10):
            safe_call(engine.learning.learn_from_error,
                      "param_x", error_magnitude=random.uniform(0, 1), delta=-0.1, error_source="test",
                      category="sub_engine", description="learning.learn_from_error")
        safe_call(engine.learning.learn_from_error,
                  "", error_magnitude=-1, delta=None, error_source=None,
                  category="sub_engine", description="learning.learn_from_error(abnormal)")

        # 4. 记忆引擎
        logger.info("[子引擎] memory")
        for i in range(20):
            safe_call(engine.memory.store, f"key_{i}", {"data": i},
                      context={"tag": "test"}, category="sub_engine", description="memory.store")
        safe_call(engine.memory.store, "", None, context=None,
                  category="sub_engine", description="memory.store(abnormal)")
        safe_call(engine.memory.store, None, {"x": 1}, category="sub_engine", description="memory.store(None key)")

        # 5. 进化引擎
        logger.info("[子引擎] evolution")
        from self_evolving_agent.core.evolution_first_principles import GoalType
        for gt in GoalType:
            safe_call(engine.evolution.update_progress, gt, random.uniform(0, 1),
                      category="sub_engine", description=f"evolution.update_progress({gt})")
        safe_call(engine.evolution.update_progress, gt, -1, category="sub_engine", description="evolution.update_progress(negative)")
        safe_call(engine.evolution.update_progress, gt, 2, category="sub_engine", description="evolution.update_progress(>1)")
        drift = safe_call(engine.evolution.check_drift, category="sub_engine", description="evolution.check_drift")
        logger.debug("  evolution drift=%s", drift.value if drift else None)

        # 6. 安全引擎
        logger.info("[子引擎] safety")
        safe_call(engine.safety.evaluate_operation, {"required_resources": {"cpu": 0.5}},
                  category="sub_engine", description="safety.evaluate_operation")
        safe_call(engine.safety.evaluate_operation, {},
                  category="sub_engine", description="safety.evaluate_operation(empty)")
        safe_call(engine.safety.evaluate_operation, None,
                  category="sub_engine", description="safety.evaluate_operation(None)")
        safe_call(engine.safety.analyze_stability, category="sub_engine", description="safety.analyze_stability")

        # 7. 能效引擎
        logger.info("[子引擎] efficiency")
        from self_evolving_agent.core.efficiency_first_principles import ResourceType
        for rt in ResourceType:
            safe_call(engine.efficiency.record_usage, "op1", rt, 0.5, 1.0,
                      category="sub_engine", description=f"efficiency.record_usage({rt})")
        safe_call(engine.efficiency.record_usage, "op1", ResourceType.CPU, -1, -1,
                  category="sub_engine", description="efficiency.record_usage(negative)")
        safe_call(engine.efficiency.evaluate_action_efficiency, "op1", {"cpu": 0.3}, 0.8,
                  category="sub_engine", description="efficiency.evaluate_action_efficiency")

        # 8. 情感引擎
        logger.info("[子引擎] emotion")
        safe_call(engine.emotion.process_event, "prediction_error", prediction_error=0.5, information_value=0.3,
                  category="sub_engine", description="emotion.process_event")
        safe_call(engine.emotion.process_event, "unknown_event",
                  category="sub_engine", description="emotion.process_event(unknown)")
        safe_call(engine.emotion.process_event, "",
                  category="sub_engine", description="emotion.process_event(empty)")
        safe_call(engine.emotion.get_attention_bias, category="sub_engine", description="emotion.get_attention_bias")

        # 9. 意识引擎
        logger.info("[子引擎] consciousness")
        from self_evolving_agent.core.consciousness_first_principles import WorkspaceContent, ContentType
        for ct in ContentType:
            wc = WorkspaceContent(content_id=f"c_{ct.value}", content_type=ct, content={"x": 1}, salience=0.5)
            safe_call(engine.consciousness.broadcast, wc,
                      category="sub_engine", description=f"consciousness.broadcast({ct})")
        safe_call(engine.consciousness.broadcast, None,
                  category="sub_engine", description="consciousness.broadcast(None)")
        contents = safe_call(engine.consciousness.get_conscious_contents,
                             category="sub_engine", description="consciousness.get_conscious_contents")
        logger.debug("  consciousness contents=%d", len(contents) if contents else 0)

        # 10. 自由意志引擎
        logger.info("[子引擎] free_will")
        from self_evolving_agent.core.free_will_first_principles import ChoiceSet
        choices = ChoiceSet(choice_id="test", options=["a", "b", "c"], context={})
        safe_call(engine.free_will.make_decision, choices, lambda o, c: 0.5,
                  category="sub_engine", description="free_will.make_decision")
        empty_choices = ChoiceSet(choice_id="test", options=[], context={})
        safe_call(engine.free_will.make_decision, empty_choices, lambda o, c: 0.5,
                  category="sub_engine", description="free_will.make_decision(empty options)")

        # 11. 元认知引擎
        logger.info("[子引擎] metacognition")
        safe_call(engine.metacognition.update_state, cognitive_load=0.5,
                  category="sub_engine", description="metacognition.update_state")
        safe_call(engine.metacognition.update_state, cognitive_load=-1,
                  category="sub_engine", description="metacognition.update_state(negative)")
        safe_call(engine.metacognition.update_state, cognitive_load=2,
                  category="sub_engine", description="metacognition.update_state(>1)")
        safe_call(engine.metacognition.select_strategy, {"complexity": 0.5, "urgency": 0.5},
                  category="sub_engine", description="metacognition.select_strategy")
        safe_call(engine.metacognition.select_strategy, {},
                  category="sub_engine", description="metacognition.select_strategy(empty)")
        safe_call(engine.metacognition.get_recommended_action,
                  category="sub_engine", description="metacognition.get_recommended_action")

        # 12. 探索引擎
        logger.info("[子引擎] exploration")
        safe_call(engine.exploration.get_stats, category="sub_engine", description="exploration.get_stats")

        # 13. 创造引擎
        logger.info("[子引擎] creativity")
        safe_call(engine.creativity.get_stats, category="sub_engine", description="creativity.get_stats")

        # 14. 社交引擎
        logger.info("[子引擎] social")
        safe_call(engine.social.get_stats, category="sub_engine", description="social.get_stats")

        # 15. 因果引擎
        logger.info("[子引擎] causal")
        safe_call(engine.causal.record_observation, {"outcome": "test", "value": 0.5},
                  category="sub_engine", description="causal.record_observation")
        safe_call(engine.causal.record_observation, None,
                  category="sub_engine", description="causal.record_observation(None)")
        safe_call(engine.causal.record_observation, {},
                  category="sub_engine", description="causal.record_observation(empty)")

    # ------------------------------------------------------------
    # 场景5: 协调器编排测试
    # ------------------------------------------------------------

    def test_coordinator_orchestration(self) -> None:
        """测试4个协调器的编排"""
        logger.info("=" * 60)
        logger.info("场景5: 协调器编排测试")
        logger.info("=" * 60)

        engine = self.engine

        # 感知协调器
        logger.info("[协调器] PerceptionCoordinator")
        for i in range(10):
            safe_call(engine.perception_coordinator.perceive_and_predict,
                      f"mod_{i}", {"v": 0.5}, {"v": 0.6},
                      category="coordinator", description="perception.perceive_and_predict")
        safe_call(engine.perception_coordinator.store_outcome, "k1", {"information_value": 0.8},
                  category="coordinator", description="perception.store_outcome")
        safe_call(engine.perception_coordinator.store_outcome, "k2", {"information_value": 0.1},
                  category="coordinator", description="perception.store_outcome(low value)")
        safe_call(engine.perception_coordinator.get_stats,
                  category="coordinator", description="perception.get_stats")

        # 动机协调器
        logger.info("[协调器] MotivationCoordinator")
        safe_call(engine.motivation_coordinator.evaluate_drives,
                  category="coordinator", description="motivation.evaluate_drives")
        safe_call(engine.motivation_coordinator.process_prediction_error, 0.5, 0.3,
                  category="coordinator", description="motivation.process_prediction_error")
        safe_call(engine.motivation_coordinator.process_prediction_error, -1, -1,
                  category="coordinator", description="motivation.process_prediction_error(negative)")
        safe_call(engine.motivation_coordinator.update_evolution, {"safe_improvement": 0.1},
                  category="coordinator", description="motivation.update_evolution")
        safe_call(engine.motivation_coordinator.update_evolution, {},
                  category="coordinator", description="motivation.update_evolution(empty)")
        safe_call(engine.motivation_coordinator.update_evolution, None,
                  category="coordinator", description="motivation.update_evolution(None)")

        # 决策协调器
        logger.info("[协调器] DecisionCoordinator")
        from self_evolving_agent.core.free_will_first_principles import ChoiceSet
        from self_evolving_agent.core.drive_first_principles import DriveGap, DriveType
        choices = ChoiceSet(choice_id="dec_test", options=["a", "b", "c"], context={})
        safe_call(engine.decision_coordinator.make_decision, choices, engine.motivation_coordinator,
                  category="coordinator", description="decision.make_decision")
        # 测试空选项
        empty_choices = ChoiceSet(choice_id="dec_empty", options=[], context={})
        safe_call(engine.decision_coordinator.make_decision, empty_choices, engine.motivation_coordinator,
                  category="coordinator", description="decision.make_decision(empty)")
        # 测试广播驱力缺口
        safe_call(engine.decision_coordinator.broadcast_drive_gap, None,
                  category="coordinator", description="decision.broadcast_drive_gap(None)")
        # 测试资源记录
        safe_call(engine.decision_coordinator.record_resource_usage, "op1", {"cpu": 0.3}, 0.5,
                  category="coordinator", description="decision.record_resource_usage")
        safe_call(engine.decision_coordinator.record_resource_usage, "op1", {"invalid_type": 0.3}, 0.5,
                  category="coordinator", description="decision.record_resource_usage(invalid type)")
        safe_call(engine.decision_coordinator.analyze_stability,
                  category="coordinator", description="decision.analyze_stability")

        # 探索协调器
        logger.info("[协调器] ExplorationCoordinator")
        safe_call(engine.exploration_coordinator.record_outcome, {"value": 0.5},
                  category="coordinator", description="exploration.record_outcome")
        safe_call(engine.exploration_coordinator.record_outcome, None,
                  category="coordinator", description="exploration.record_outcome(None)")
        safe_call(engine.exploration_coordinator.record_outcome, {},
                  category="coordinator", description="exploration.record_outcome(empty)")

    # ------------------------------------------------------------
    # 场景6: 完整集成周期压力测试
    # ------------------------------------------------------------

    def test_integration_cycle_stress(self) -> None:
        """完整集成周期压力测试"""
        logger.info("=" * 60)
        logger.info("场景6: 完整集成周期压力测试（100周期）")
        logger.info("=" * 60)

        for i in range(100):
            context = {
                "available_actions": ["wait", "explore", "exploit", "create", "learn"],
                "outcome": {
                    "information_value": random.uniform(0, 1),
                    "error_reduction": random.uniform(0, 0.5),
                    "safe_improvement": random.uniform(0, 0.1) if i % 3 == 0 else 0,
                    "gain_improvement": random.uniform(0, 0.1) if i % 4 == 0 else 0,
                    "eff_improvement": random.uniform(0, 0.1) if i % 5 == 0 else 0,
                },
                "resources_used": {
                    "cpu": random.uniform(0.1, 0.5),
                    "memory": random.uniform(0.1, 0.3),
                },
                "output_value": random.uniform(0.3, 0.9),
            }
            safe_call(self.engine.run_integration_cycle, context,
                      category="integration", description=f"run_integration_cycle {i}")

            if i % 20 == 19:
                stats = safe_call(self.engine.get_full_stats,
                                  category="integration", description="get_full_stats")
                if stats:
                    logger.info("[周期 %d] stats keys=%d", i, len(stats))

    # ------------------------------------------------------------
    # 场景7: 状态一致性测试
    # ------------------------------------------------------------

    def test_state_consistency(self) -> None:
        """状态一致性测试"""
        logger.info("=" * 60)
        logger.info("场景7: 状态一致性测试")
        logger.info("=" * 60)

        # 多次获取状态，验证一致性
        for i in range(20):
            state1 = safe_call(self.agent.get_state, category="consistency", description="get_state #1")
            state2 = safe_call(self.agent.get_state, category="consistency", description="get_state #2")

            if state1 and state2:
                # 验证关键字段存在
                for key in ["agent_id", "running", "cycle_count", "coordinator", "modules"]:
                    if key not in state1:
                        bug_collector.record_bug("consistency", f"get_state missing key: {key}")
                    if key not in state2:
                        bug_collector.record_bug("consistency", f"get_state #2 missing key: {key}")

                # 验证 coordinator 状态
                coord1 = state1.get("coordinator", {})
                coord2 = state2.get("coordinator", {})
                if coord1.get("coordinator_id") != coord2.get("coordinator_id"):
                    bug_collector.record_bug("consistency", "coordinator_id 不一致")

            # 注入操作
            self.agent.observe({"module_id": f"cons_{i}", "predicted": {"v": 0.5}, "actual": {"v": 0.6}})

        logger.info("状态一致性测试完成")

    # ------------------------------------------------------------
    # 场景8: 异常容错测试
    # ------------------------------------------------------------

    def test_fault_tolerance(self) -> None:
        """异常容错测试"""
        logger.info("=" * 60)
        logger.info("场景8: 异常容错测试")
        logger.info("=" * 60)

        # 测试在异常状态下系统是否能恢复
        # 1. 大量异常输入后系统是否仍能正常工作
        for _ in range(50):
            try:
                self.agent.observe({"module_id": None, "predicted": None, "actual": None})
            except Exception:
                pass

        # 2. 验证系统仍能正常工作
        result = safe_call(self.agent.observe,
                           {"module_id": "recovery", "predicted": {"v": 0.5}, "actual": {"v": 0.6}},
                           category="fault_tolerance", description="recovery observe")
        if result is None:
            bug_collector.record_bug("fault_tolerance", "异常输入后系统无法恢复")
        else:
            logger.info("异常容错测试: 系统恢复正常")

        # 3. 测试 coordinator 反复启停
        for _ in range(5):
            self.coordinator.start()
            self.coordinator.stop()
        logger.info("coordinator 反复启停测试完成")


# ============================================================
# 主测试入口
# ============================================================

def run_all_stress_tests() -> Dict[str, Any]:
    """运行所有压力测试"""
    logger.info("#" * 60)
    logger.info("# 复杂场景压力测试开始")
    logger.info("# 日志文件: %s", LOG_FILE)
    logger.info("#" * 60)

    scenarios = StressTestScenarios()
    start_time = time.time()

    test_methods = [
        ("边界值与异常输入", scenarios.test_boundary_inputs),
        ("并发压力", scenarios.test_concurrent_stress),
        ("长期运行稳定性", lambda: scenarios.test_long_running_stability(500)),
        ("子引擎深度测试", scenarios.test_sub_engines_deep),
        ("协调器编排", scenarios.test_coordinator_orchestration),
        ("集成周期压力", scenarios.test_integration_cycle_stress),
        ("状态一致性", scenarios.test_state_consistency),
        ("异常容错", scenarios.test_fault_tolerance),
    ]

    for name, test_func in test_methods:
        try:
            test_func()
        except Exception as e:
            bug_collector.record_bug("test_harness", f"测试场景本身崩溃: {name}", e)
            logger.error("测试场景崩溃: %s", name)

    elapsed = time.time() - start_time
    summary = bug_collector.summary()

    logger.info("#" * 60)
    logger.info("# 压力测试完成")
    logger.info("# 总耗时: %.2fs", elapsed)
    logger.info("# Bug统计: %s", json.dumps(summary, ensure_ascii=False, indent=2))
    logger.info("#" * 60)

    return {
        "elapsed": elapsed,
        "summary": summary,
        "bugs": bug_collector.bugs,
        "log_file": LOG_FILE,
    }


if __name__ == "__main__":
    result = run_all_stress_tests()
    # 输出 bug 详情
    print("\n" + "=" * 60)
    print("BUG 详情:")
    print("=" * 60)
    for i, bug in enumerate(result["bugs"], 1):
        print(f"\n[{i}] {bug['category']}: {bug['description']}")
        if bug["exception_type"]:
            print(f"    异常: {bug['exception_type']}: {bug['exception_msg']}")
