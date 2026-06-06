"""
阶段62验证: 混沌工程接口标准化
"""
import sys
import importlib.util

spec = importlib.util.spec_from_file_location("ce", "/workspace/self_evolving_agent/core/chaos_engineering.py")
mod = importlib.util.module_from_spec(spec)
sys.modules["ce"] = mod
spec.loader.exec_module(mod)

print("=" * 60)
print("阶段62验证: 混沌工程接口标准化")
print("=" * 60)

# 测试1: 延迟攻击
def test_latency_attack():
    engine = mod.create_chaos_engine()
    exp = mod.create_chaos_experiment("exp1", "系统在高延迟下保持可用")
    attack = mod.create_chaos_attack("a1", mod.AttackType.LATENCY, "svc1", config={"latency_ms": 50}, duration_sec=0.1)
    exp.add_attack(attack)

    result = engine.run_experiment(exp)
    assert result.status == mod.ExperimentStatus.COMPLETED
    assert result.attacks_executed == 1
    print("  [test_latency_attack] 延迟攻击 OK")

# 测试2: 错误注入攻击
def test_error_attack():
    engine = mod.create_chaos_engine()
    exp = mod.create_chaos_experiment("exp2", "系统能容忍50%错误率")
    attack = mod.create_chaos_attack("a2", mod.AttackType.ERROR, "svc2", config={"error_rate": 0.5}, duration_sec=0.1)
    exp.add_attack(attack)

    result = engine.run_experiment(exp)
    assert result.attacks_executed == 1
    assert len(result.observations) == 1
    print("  [test_error_attack] 错误注入攻击 OK")

# 测试3: 多攻击序列
def test_multi_attacks():
    engine = mod.create_chaos_engine()
    exp = mod.create_chaos_experiment("exp3", "系统能容忍多种故障")
    exp.add_attack(mod.create_chaos_attack("a1", mod.AttackType.LATENCY, "svc1", duration_sec=0.05))
    exp.add_attack(mod.create_chaos_attack("a2", mod.AttackType.KILL, "svc2", duration_sec=0.05))

    result = engine.run_experiment(exp)
    assert result.attacks_executed == 2
    print("  [test_multi_attacks] 多攻击序列 OK")

# 测试4: 实验状态
def test_experiment_status():
    exp = mod.create_chaos_experiment("exp4", "测试状态")
    assert exp.get_status() == mod.ExperimentStatus.PENDING
    print("  [test_experiment_status] 实验状态 OK")

# 测试5: 引擎统计
def test_engine_stats():
    engine = mod.create_chaos_engine()
    stats = engine.get_stats()
    assert "total_experiments" in stats
    assert len(stats["executors"]) == 3
    print("  [test_engine_stats] 引擎统计 OK")

# 测试6: 停止实验
def test_stop_experiment():
    engine = mod.create_chaos_engine()
    exp = mod.create_chaos_experiment("exp5", "测试停止")
    engine.run_experiment(exp)
    assert engine.stop_experiment("exp5") is True
    assert engine.stop_experiment("nonexistent") is False
    print("  [test_stop_experiment] 停止实验 OK")

if __name__ == "__main__":
    test_latency_attack()
    test_error_attack()
    test_multi_attacks()
    test_experiment_status()
    test_engine_stats()
    test_stop_experiment()
    print("=" * 60)
    print("阶段62验证通过 ✓")
    print("=" * 60)
