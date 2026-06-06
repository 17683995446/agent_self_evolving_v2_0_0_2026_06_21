"""
阶段58验证: 模型蒸馏接口标准化
"""
import sys
import importlib.util

spec = importlib.util.spec_from_file_location("md", "/workspace/self_evolving_agent/core/model_distillation.py")
mod = importlib.util.module_from_spec(spec)
sys.modules["md"] = mod
spec.loader.exec_module(mod)

print("=" * 60)
print("阶段58验证: 模型蒸馏接口标准化")
print("=" * 60)

# 测试1: 创建教师和学生模型
def test_create_models():
    teacher = mod.create_teacher_model({"w1": [0.5, 0.3, 0.2], "w2": [0.1, 0.9]})
    student = mod.create_student_model({"w1": [0.4], "w2": [0.5]})
    assert teacher.get_size() == 5
    assert student.get_size() == 2
    print("  [test_create_models] 创建模型 OK")

# 测试2: 模型预测
def test_model_predict():
    teacher = mod.create_teacher_model({"a": [1.0], "b": [2.0]})
    result = teacher.predict({"a": 1, "b": 2})
    assert "logits" in result
    assert "confidence" in result
    print("  [test_model_predict] 模型预测 OK")

# 测试3: 蒸馏损失计算
def test_distillation_loss():
    loss_fn = mod.DistillationLoss(temperature=4.0, alpha=0.7)
    loss = loss_fn.compute(
        teacher_logits=[2.0, -2.0],
        student_logits=[1.0, -1.0],
        true_label=0,
    )
    assert loss >= 0
    print("  [test_distillation_loss] 蒸馏损失 OK")

# 测试4: 蒸馏训练
def test_distillation_train():
    teacher = mod.create_teacher_model({"f1": [1.0, 0.5], "f2": [0.3, 0.8]})
    student = mod.create_student_model({"f1": [0.5], "f2": [0.5]})
    trainer = mod.create_distillation_trainer(temperature=4.0, alpha=0.7, epochs=3)

    dataset = [
        {"input": {"f1": 1, "f2": 0}, "label": 0},
        {"input": {"f1": 0, "f2": 1}, "label": 1},
    ]

    result = trainer.train(teacher, student, dataset)
    assert result.compression_ratio == 2.0  # teacher=4, student=2
    assert result.speedup_ratio == 2.0
    assert len(trainer.get_history()) == 3
    print("  [test_distillation_train] 蒸馏训练 OK")

# 测试5: 压缩比
def test_compression_ratio():
    teacher = mod.create_teacher_model({"a": [1] * 100})
    student = mod.create_student_model({"a": [1] * 10})
    assert teacher.get_size() == 100
    assert student.get_size() == 10
    print("  [test_compression_ratio] 压缩比 OK")

# 测试6: 配置默认值
def test_config_defaults():
    config = mod.DistillationConfig()
    assert config.temperature == 4.0
    assert config.alpha == 0.7
    assert config.epochs == 10
    print("  [test_config_defaults] 配置默认值 OK")

if __name__ == "__main__":
    test_create_models()
    test_model_predict()
    test_distillation_loss()
    test_distillation_train()
    test_compression_ratio()
    test_config_defaults()
    print("=" * 60)
    print("阶段58验证通过 ✓")
    print("=" * 60)
