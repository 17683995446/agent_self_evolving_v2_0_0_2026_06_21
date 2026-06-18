#!/usr/bin/env python3
"""
自驱永续进化Agent系统 — 六小时持续运行脚本

功能:
1. 启动Agent并持续运行6小时
2. 每30秒记录系统状态到日志
3. 每5分钟保存一次快照
4. 6小时后自动生成运行报告
"""

import os
import sys
import time
import json
import signal
import threading
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from self_evolving_agent import create_default_agent
from self_evolving_agent.core.system_coordinator import create_coordinator

# 配置
DURATION_HOURS = 6
LOG_INTERVAL_SEC = 30
SNAPSHOT_INTERVAL_SEC = 300
REPORT_DIR = "run_reports"
LOG_DIR = "run_logs"

# 确保目录存在
os.makedirs(REPORT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# 全局状态
_running = True
_start_time = None
_log_file = None


def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(msg):
    line = f"[{get_timestamp()}] {msg}"
    print(line)
    if _log_file:
        _log_file.write(line + "\n")
        _log_file.flush()


def signal_handler(signum, frame):
    global _running
    log(f"收到信号 {signum}，准备优雅停止...")
    _running = False


signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


def run_agent_loop(agent, coordinator):
    """Agent主循环"""
    cycle = 0
    while _running:
        try:
            cycle += 1
            # 运行一个完整周期
            context = {
                "available_actions": ["explore", "exploit", "predict", "learn", "rest"],
                "outcome": {
                    "information_value": 0.5 + (cycle % 10) / 20.0,
                    "safe_improvement": 0.01,
                    "gain_improvement": 0.01,
                    "eff_improvement": 0.005,
                },
                "resources_used": {"cpu": 1.0, "time": 1.0},
                "output_value": float(cycle),
            }

            # 执行预测-修正循环
            coordinator._engine.perceive_and_predict(
                "main_sensor",
                {"cycle": cycle, "predicted_value": cycle * 1.1},
                {"cycle": cycle, "actual_value": cycle},
            )

            # 评估驱力
            coordinator._engine.evaluate_drives()

            # 学习与进化
            coordinator._engine.learn_and_evolve(context["outcome"])

            # 运行整合周期
            coordinator.run_cycle(context)

            # 情感处理
            coordinator._engine.emotion.process_event(
                "cycle_complete",
                prediction_error=0.1,
                information_value=context["outcome"]["information_value"],
                outcome="success" if cycle % 3 == 0 else "normal",
            )

            # 记忆存储（每10个周期）
            if cycle % 10 == 0:
                coordinator._engine.memory.store(
                    f"cycle_{cycle}",
                    {"cycle": cycle, "timestamp": time.time()},
                    context={"error_reduction_potential": 0.5},
                )

            # 创造（每20个周期）
            if cycle % 20 == 0:
                coordinator._engine.creativity.generate_novel_combination()

            # 因果记录
            coordinator._engine.causal.record_observation({
                "cycle": cycle,
                "information_value": context["outcome"]["information_value"],
            })

            time.sleep(1)  # 每秒一个周期

        except Exception as e:
            log(f"周期 {cycle} 错误: {e}")
            time.sleep(1)

    log(f"Agent循环结束，共执行 {cycle} 个周期")
    return cycle


def monitor_loop(agent, coordinator):
    """监控循环，每30秒记录状态"""
    log_count = 0
    while _running:
        try:
            log_count += 1
            elapsed = time.time() - _start_time
            remaining = (DURATION_HOURS * 3600) - elapsed

            stats = coordinator._engine.get_full_stats()

            log(f"--- 监控 #{log_count} ---")
            log(f"运行时间: {elapsed/60:.1f} 分钟 / {DURATION_HOURS} 小时")
            log(f"剩余时间: {remaining/60:.1f} 分钟")
            log(f"总周期: {stats['cycle_count']}")
            log(f"预测编码-预测数: {stats['predictive_coding']['predictions_count']}")
            log(f"预测编码-误差数: {stats['predictive_coding']['errors_count']}")
            log(f"学习-信号数: {stats['learning']['signals_count']}")
            log(f"学习-更新数: {stats['learning']['updates_count']}")
            log(f"记忆-条目数: {stats['memory']['items_count']}")
            log(f"进化-安全: {stats['evolution']['goals']['safe']['level']:.4f}")
            log(f"进化-收益: {stats['evolution']['goals']['gain']['level']:.4f}")
            log(f"进化-能效: {stats['evolution']['goals']['eff']['level']:.4f}")
            log(f"情感-主导: {stats['emotion']['dominant_emotion']}")
            log(f"意识-内容数: {stats['consciousness']['workspace_size']}")
            log(f"自由意志-决策数: {stats['free_will']['decisions_count']}")
            log(f"创造-概念数: {stats['creativity']['concepts_count']}")
            log(f"因果-链接数: {stats['causal']['causal_links']}")

            # 每5分钟保存快照
            if log_count % (SNAPSHOT_INTERVAL_SEC // LOG_INTERVAL_SEC) == 0:
                snapshot_file = os.path.join(
                    LOG_DIR,
                    f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
                with open(snapshot_file, 'w') as f:
                    json.dump(stats, f, indent=2, default=str)
                log(f"快照已保存: {snapshot_file}")

            # 等待30秒
            for _ in range(LOG_INTERVAL_SEC):
                if not _running:
                    break
                time.sleep(1)

        except Exception as e:
            log(f"监控错误: {e}")
            time.sleep(LOG_INTERVAL_SEC)


def generate_report(agent, coordinator, total_cycles):
    """生成最终运行报告"""
    stats = coordinator._engine.get_full_stats()
    elapsed = time.time() - _start_time

    report = {
        "report_title": "自驱永续进化Agent系统 — 六小时运行报告",
        "start_time": datetime.fromtimestamp(_start_time).isoformat(),
        "end_time": datetime.now().isoformat(),
        "duration_hours": DURATION_HOURS,
        "actual_duration_minutes": elapsed / 60,
        "total_cycles": total_cycles,
        "summary": {
            "predictions_made": stats['predictive_coding']['predictions_count'],
            "errors_computed": stats['predictive_coding']['errors_count'],
            "corrections_applied": stats['predictive_coding']['corrections_count'],
            "learning_signals": stats['learning']['signals_count'],
            "parameter_updates": stats['learning']['updates_count'],
            "memory_items_stored": stats['memory']['items_count'],
            "evolution_safe": stats['evolution']['goals']['safe']['level'],
            "evolution_gain": stats['evolution']['goals']['gain']['level'],
            "evolution_eff": stats['evolution']['goals']['eff']['level'],
            "decisions_made": stats['free_will']['decisions_count'],
            "concepts_created": stats['creativity']['concepts_count'],
            "emergent_concepts": stats['creativity']['emergent_concepts'],
            "causal_links_discovered": stats['causal']['causal_links'],
            "emotional_events": stats['emotion']['cycle_count'],
            "consciousness_broadcasts": stats['consciousness']['stream_length'],
        },
        "final_stats": stats,
    }

    report_file = os.path.join(
        REPORT_DIR,
        f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)

    log("=" * 60)
    log("六小时运行报告")
    log("=" * 60)
    log(f"总周期数: {total_cycles}")
    log(f"预测数: {report['summary']['predictions_made']}")
    log(f"误差数: {report['summary']['errors_computed']}")
    log(f"学习信号: {report['summary']['learning_signals']}")
    log(f"参数更新: {report['summary']['parameter_updates']}")
    log(f"记忆存储: {report['summary']['memory_items_stored']}")
    log(f"安全进化: {report['summary']['evolution_safe']:.4f}")
    log(f"收益进化: {report['summary']['evolution_gain']:.4f}")
    log(f"能效进化: {report['summary']['evolution_eff']:.4f}")
    log(f"决策数: {report['summary']['decisions_made']}")
    log(f"概念创造: {report['summary']['concepts_created']}")
    log(f"因果发现: {report['summary']['causal_links_discovered']}")
    log(f"报告文件: {report_file}")
    log("=" * 60)

    return report_file


def main():
    global _start_time, _log_file

    _start_time = time.time()
    end_time = _start_time + (DURATION_HOURS * 3600)

    log_file_path = os.path.join(
        LOG_DIR,
        f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )
    _log_file = open(log_file_path, 'w')

    log("=" * 60)
    log("自驱永续进化Agent系统 — 六小时持续运行")
    log("=" * 60)
    log(f"开始时间: {get_timestamp()}")
    log(f"预计结束: {datetime.fromtimestamp(end_time).strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"日志文件: {log_file_path}")
    log("=" * 60)

    # 初始化
    log("初始化Agent...")
    agent = create_default_agent()
    agent.initialize({})

    coordinator = create_coordinator("six_hour_runner")

    # 注册预测器和修正器
    coordinator._engine.predictive_coding.register_predictor(
        "main_sensor",
        lambda state: type('obj', (object,), {
            'prediction_id': f"pred_{int(time.time()*1000)}",
            'timestamp': time.time(),
            'predicted_state': {'value': state.get('predicted_value', 0)},
            'confidence': 0.8,
            'time_horizon': 1.0,
            'source': 'main_sensor',
        })()
    )
    coordinator._engine.predictive_coding.register_corrector(
        "main_sensor",
        lambda error: type('obj', (object,), {
            'correction_id': f"corr_{int(time.time()*1000)}",
            'error_id': getattr(error, 'error_id', 'unknown'),
            'timestamp': time.time(),
            'parameter_updates': {'weight': -0.01},
            'update_magnitude': 0.01,
            'target_module': 'main_sensor',
        })()
    )

    # 设置初始目标
    coordinator.set_goal("safe", 0.5)
    coordinator.set_goal("gain", 0.5)
    coordinator.set_goal("eff", 0.5)

    log("Agent初始化完成，启动运行循环...")

    # 启动Agent循环线程
    agent_thread = threading.Thread(
        target=run_agent_loop,
        args=(agent, coordinator),
        daemon=True,
    )
    agent_thread.start()

    # 启动监控循环（在主线程）
    monitor_loop(agent, coordinator)

    # 等待Agent线程结束
    agent_thread.join(timeout=10)

    # 生成报告
    total_cycles = agent._cycle_count if agent else 0
    report_file = generate_report(agent, coordinator, total_cycles)

    _log_file.close()

    log("六小时运行完成！")
    return report_file


if __name__ == "__main__":
    main()
