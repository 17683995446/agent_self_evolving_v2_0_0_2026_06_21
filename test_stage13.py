"""
阶段13验证：梯度下降算法库化
"""
import sys
sys.path.insert(0, '/workspace')

import numpy as np
from self_evolving_agent.core.optimizers import (
    SGD, Momentum, RMSprop, Adam,
    StepDecay, ExponentialDecay, CosineAnnealing,
    ScheduledOptimizer, OptimizerFactory
)


def quadratic_loss(params):
    """二次损失函数 f(x,y) = x^2 + 2*y^2"""
    x = params["x"]
    y = params["y"]
    return np.sum(x**2 + 2*y**2)


def quadratic_grad(params):
    """二次损失函数的梯度"""
    return {
        "x": 2 * params["x"],
        "y": 4 * params["y"],
    }


def test_sgd():
    """测试SGD"""
    print("=" * 60)
    print("测试: SGD")
    print("=" * 60)

    opt = SGD(learning_rate=0.1)
    params = {"x": np.array([3.0]), "y": np.array([2.0])}

    print(f"初始: x={params['x'][0]:.3f}, y={params['y'][0]:.3f}, loss={quadratic_loss(params):.3f}")

    for i in range(20):
        grads = quadratic_grad(params)
        params = opt.step(params, grads)
        if i % 5 == 4:
            print(f"第{i+1}步: x={params['x'][0]:.3f}, y={params['y'][0]:.3f}, loss={quadratic_loss(params):.3f}")

    assert quadratic_loss(params) < 0.1
    print("\nSGD测试通过!")
    return True


def test_momentum():
    """测试Momentum"""
    print("\n" + "=" * 60)
    print("测试: Momentum")
    print("=" * 60)

    opt = Momentum(learning_rate=0.01, momentum=0.9)
    params = {"x": np.array([3.0]), "y": np.array([2.0])}

    print(f"初始: x={params['x'][0]:.3f}, y={params['y'][0]:.3f}, loss={quadratic_loss(params):.3f}")

    for i in range(100):
        grads = quadratic_grad(params)
        params = opt.step(params, grads)
        if i % 20 == 19:
            print(f"第{i+1}步: x={params['x'][0]:.3f}, y={params['y'][0]:.3f}, loss={quadratic_loss(params):.3f}")

    assert quadratic_loss(params) < 0.1
    print("\nMomentum测试通过!")
    return True


def test_adam():
    """测试Adam"""
    print("\n" + "=" * 60)
    print("测试: Adam")
    print("=" * 60)

    opt = Adam(learning_rate=0.1)
    params = {"x": np.array([3.0]), "y": np.array([2.0])}

    print(f"初始: x={params['x'][0]:.3f}, y={params['y'][0]:.3f}, loss={quadratic_loss(params):.3f}")

    for i in range(100):
        grads = quadratic_grad(params)
        params = opt.step(params, grads)
        if i % 20 == 19:
            print(f"第{i+1}步: x={params['x'][0]:.3f}, y={params['y'][0]:.3f}, loss={quadratic_loss(params):.3f}")

    assert quadratic_loss(params) < 0.1
    print("\nAdam测试通过!")
    return True


def test_rmsprop():
    """测试RMSprop"""
    print("\n" + "=" * 60)
    print("测试: RMSprop")
    print("=" * 60)

    opt = RMSprop(learning_rate=0.1)
    params = {"x": np.array([3.0]), "y": np.array([2.0])}

    print(f"初始: x={params['x'][0]:.3f}, y={params['y'][0]:.3f}, loss={quadratic_loss(params):.3f}")

    for i in range(20):
        grads = quadratic_grad(params)
        params = opt.step(params, grads)
        if i % 5 == 4:
            print(f"第{i+1}步: x={params['x'][0]:.3f}, y={params['y'][0]:.3f}, loss={quadratic_loss(params):.3f}")

    assert quadratic_loss(params) < 0.1
    print("\nRMSprop测试通过!")
    return True


def test_scheduler():
    """测试学习率调度器"""
    print("\n" + "=" * 60)
    print("测试: 学习率调度器")
    print("=" * 60)

    # 阶梯衰减
    step = StepDecay(step_size=10, gamma=0.1)
    lr10 = step.get_lr(0.1, 10)
    print(f"StepDecay: lr@0={step.get_lr(0.1, 0):.4f}, lr@10={lr10:.4f}, lr@20={step.get_lr(0.1, 20):.4f}")
    assert step.get_lr(0.1, 0) == 0.1
    assert abs(lr10 - 0.01) < 1e-10

    # 指数衰减
    exp = ExponentialDecay(gamma=0.01)
    print(f"ExponentialDecay: lr@0={exp.get_lr(0.1, 0):.4f}, lr@100={exp.get_lr(0.1, 100):.4f}")
    assert exp.get_lr(0.1, 0) == 0.1
    assert exp.get_lr(0.1, 100) < 0.1

    # 余弦退火
    cos = CosineAnnealing(max_iterations=100)
    print(f"CosineAnnealing: lr@0={cos.get_lr(0.1, 0):.4f}, lr@50={cos.get_lr(0.1, 50):.4f}, lr@100={cos.get_lr(0.1, 100):.4f}")
    assert cos.get_lr(0.1, 0) == 0.1
    assert cos.get_lr(0.1, 100) == 0.0

    print("\n学习率调度器测试通过!")
    return True


def test_scheduled_optimizer():
    """测试带调度器的优化器"""
    print("\n" + "=" * 60)
    print("测试: 带调度器的优化器")
    print("=" * 60)

    base_opt = SGD(learning_rate=0.1)
    scheduler = StepDecay(step_size=5, gamma=0.5)
    opt = ScheduledOptimizer(base_opt, scheduler)

    params = {"x": np.array([3.0]), "y": np.array([2.0])}

    for i in range(15):
        grads = quadratic_grad(params)
        params = opt.step(params, grads)
        if i % 5 == 0:
            state = opt.get_state()
            print(f"第{i}步: lr={state['current_lr']:.4f}, loss={quadratic_loss(params):.3f}")

    print("\n带调度器的优化器测试通过!")
    return True


def test_factory():
    """测试优化器工厂"""
    print("\n" + "=" * 60)
    print("测试: 优化器工厂")
    print("=" * 60)

    # 创建各种优化器
    sgd = OptimizerFactory.create("sgd", learning_rate=0.01)
    adam = OptimizerFactory.create("adam", learning_rate=0.001)
    momentum = OptimizerFactory.create("momentum", learning_rate=0.01, momentum=0.9)

    print(f"可用优化器: {OptimizerFactory.list_optimizers()}")
    print(f"SGD: {sgd.name}")
    print(f"Adam: {adam.name}")
    print(f"Momentum: {momentum.name}")

    # 带调度器的优化器（手动创建，工厂不支持scheduler参数传递）
    base_sgd = OptimizerFactory.create("sgd", learning_rate=0.1)
    step_scheduler = StepDecay(step_size=10, gamma=0.1)
    scheduled = ScheduledOptimizer(base_sgd, step_scheduler)
    print(f"Scheduled SGD: {scheduled.name}")

    print("\n优化器工厂测试通过!")
    return True


def run_all_tests():
    print("\n" + "=" * 60)
    print("阶段13: 梯度下降算法库化 — 验证测试")
    print("=" * 60)

    tests = [
        ("SGD", test_sgd),
        ("Momentum", test_momentum),
        ("Adam", test_adam),
        ("RMSprop", test_rmsprop),
        ("学习率调度器", test_scheduler),
        ("带调度器的优化器", test_scheduled_optimizer),
        ("优化器工厂", test_factory),
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
