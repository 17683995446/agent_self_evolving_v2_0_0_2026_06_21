"""
阶段19验证：标准数据交换格式
"""
import sys
sys.path.insert(0, '/workspace')

from datetime import datetime
from self_evolving_agent.core.schemas import (
    VectorData, StateVector, PredictionSchema, DriveGapsSchema,
    DriveWeightsSchema, TaskCandidateSchema, OptimizationResultSchema,
    SystemEventSchema, MemoryEntrySchema, ModuleConfigSchema,
    SchemaValidator, SchemaSerializer
)


def test_vector_data():
    """测试向量数据Schema"""
    print("=" * 60)
    print("测试: VectorData")
    print("=" * 60)

    v = VectorData(values=[1.0, 2.0, 3.0])
    print(f"创建: {v}")
    assert v.dimension == 3
    assert v.validate()

    # 无效数据
    v2 = VectorData(values=[1, "a", 3])
    assert not v2.validate()
    print("无效数据正确检测")

    print("\nVectorData测试通过!")
    return True


def test_prediction_schema():
    """测试预测Schema"""
    print("\n" + "=" * 60)
    print("测试: PredictionSchema")
    print("=" * 60)

    p = PredictionSchema(
        predicted_state={"x": 0.5, "y": 0.3},
        confidence=0.8,
        uncertainty=0.2,
    )
    print(f"创建: {p}")
    assert p.validate()
    assert p.confidence == 0.8

    # 无效数据
    p2 = PredictionSchema(
        predicted_state={"x": 0.5},
        confidence=1.5,  # 超出范围
        uncertainty=0.2,
    )
    assert not p2.validate()
    print("无效confidence正确检测")

    print("\nPredictionSchema测试通过!")
    return True


def test_drive_gaps():
    """测试驱力缺口Schema"""
    print("\n" + "=" * 60)
    print("测试: DriveGapsSchema")
    print("=" * 60)

    gaps = DriveGapsSchema(safe_gap=0.3, gain_gap=0.5, eff_gap=0.2)
    print(f"创建: {gaps}")
    assert gaps.validate()
    assert gaps.max_gap() == "gain"

    # 无效数据
    gaps2 = DriveGapsSchema(safe_gap=1.5, gain_gap=0.5, eff_gap=0.2)
    assert not gaps2.validate()
    print("无效gap正确检测")

    print("\nDriveGapsSchema测试通过!")
    return True


def test_drive_weights():
    """测试驱力权重Schema"""
    print("\n" + "=" * 60)
    print("测试: DriveWeightsSchema")
    print("=" * 60)

    w = DriveWeightsSchema(safe=0.3, gain=0.4, eff=0.3)
    print(f"创建: {w}")
    assert w.validate()

    # 和不等于1
    w2 = DriveWeightsSchema(safe=0.5, gain=0.5, eff=0.5)
    assert not w2.validate()
    print("权重和不为1正确检测")

    print("\nDriveWeightsSchema测试通过!")
    return True


def test_task_candidate():
    """测试候选任务Schema"""
    print("\n" + "=" * 60)
    print("测试: TaskCandidateSchema")
    print("=" * 60)

    task = TaskCandidateSchema(
        action="explore",
        params={"target": "area1"},
        expected_benefit=0.8,
        cost=0.2,
        success_probability=0.9,
    )
    print(f"创建: {task}")
    assert task.validate()

    score = task.score()
    print(f"得分: {score:.3f}")
    assert score > 0

    # 无效数据
    task2 = TaskCandidateSchema(
        action="",
        success_probability=1.5,
    )
    assert not task2.validate()
    print("无效任务正确检测")

    print("\nTaskCandidateSchema测试通过!")
    return True


def test_optimization_result():
    """测试优化结果Schema"""
    print("\n" + "=" * 60)
    print("测试: OptimizationResultSchema")
    print("=" * 60)

    result = OptimizationResultSchema(
        success=True,
        error_before=1.0,
        error_after=0.5,
        iterations=10,
    )
    print(f"创建: {result}")
    assert result.validate()
    assert result.improvement() == 0.5

    print("\nOptimizationResultSchema测试通过!")
    return True


def test_system_event():
    """测试系统事件Schema"""
    print("\n" + "=" * 60)
    print("测试: SystemEventSchema")
    print("=" * 60)

    event = SystemEventSchema(
        event_type="module_started",
        severity="info",
        source="predictor",
    )
    print(f"创建: {event}")
    assert event.validate()

    # 无效severity
    event2 = SystemEventSchema(
        event_type="test",
        severity="invalid",
    )
    assert not event2.validate()
    print("无效severity正确检测")

    print("\nSystemEventSchema测试通过!")
    return True


def test_memory_entry():
    """测试记忆条目Schema"""
    print("\n" + "=" * 60)
    print("测试: MemoryEntrySchema")
    print("=" * 60)

    entry = MemoryEntrySchema(key="test_key", data={"value": 42})
    print(f"创建: {entry}")
    assert entry.validate()
    assert entry.access_count == 0

    entry.touch()
    assert entry.access_count == 1
    print(f"访问后: access_count={entry.access_count}")

    print("\nMemoryEntrySchema测试通过!")
    return True


def test_schema_validator():
    """测试Schema验证器"""
    print("\n" + "=" * 60)
    print("测试: SchemaValidator")
    print("=" * 60)

    # 有效对象
    valid_obj = DriveGapsSchema(safe_gap=0.1, gain_gap=0.2, eff_gap=0.3)
    is_valid, errors = SchemaValidator.validate(valid_obj)
    print(f"有效对象: is_valid={is_valid}, errors={errors}")
    assert is_valid

    # 无效对象
    invalid_obj = DriveGapsSchema(safe_gap=1.5, gain_gap=0.2, eff_gap=0.3)
    is_valid, errors = SchemaValidator.validate(invalid_obj)
    print(f"无效对象: is_valid={is_valid}, errors={errors}")
    assert not is_valid

    # 批量验证
    objects = [
        DriveGapsSchema(0.1, 0.2, 0.3),
        DriveGapsSchema(0.1, 0.2, 0.3),
        DriveGapsSchema(1.5, 0.2, 0.3),
    ]
    results = SchemaValidator.validate_batch(objects)
    print(f"批量验证: {len(results)} 个对象")
    assert len(results) == 3

    print("\nSchemaValidator测试通过!")
    return True


def test_schema_serializer():
    """测试Schema序列化器"""
    print("\n" + "=" * 60)
    print("测试: SchemaSerializer")
    print("=" * 60)

    gaps = DriveGapsSchema(safe_gap=0.1, gain_gap=0.2, eff_gap=0.3)

    # 序列化
    data = SchemaSerializer.to_dict(gaps)
    print(f"序列化: {data}")
    assert isinstance(data, dict)
    assert "safe_gap" in data

    # 反序列化
    gaps2 = SchemaSerializer.from_dict(DriveGapsSchema, data)
    print(f"反序列化: {gaps2}")
    assert gaps2.safe_gap == 0.1
    assert gaps2.gain_gap == 0.2
    assert gaps2.eff_gap == 0.3

    print("\nSchemaSerializer测试通过!")
    return True


def test_module_config():
    """测试模块配置Schema"""
    print("\n" + "=" * 60)
    print("测试: ModuleConfigSchema")
    print("=" * 60)

    config = ModuleConfigSchema(
        module_id="predictor",
        enabled=True,
        parameters={"learning_rate": 0.01},
        dependencies=["memory"],
    )
    print(f"创建: {config}")
    assert config.validate()

    print("\nModuleConfigSchema测试通过!")
    return True


def run_all_tests():
    print("\n" + "=" * 60)
    print("阶段19: 标准数据交换格式 — 验证测试")
    print("=" * 60)

    tests = [
        ("VectorData", test_vector_data),
        ("PredictionSchema", test_prediction_schema),
        ("DriveGapsSchema", test_drive_gaps),
        ("DriveWeightsSchema", test_drive_weights),
        ("TaskCandidateSchema", test_task_candidate),
        ("OptimizationResultSchema", test_optimization_result),
        ("SystemEventSchema", test_system_event),
        ("MemoryEntrySchema", test_memory_entry),
        ("SchemaValidator", test_schema_validator),
        ("SchemaSerializer", test_schema_serializer),
        ("ModuleConfigSchema", test_module_config),
    ]

    passed = 0
    failed = 0
    for name, test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"\n测试 {name} 失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
