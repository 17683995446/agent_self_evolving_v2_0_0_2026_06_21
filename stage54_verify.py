"""
阶段54验证: 联邦学习接口标准化
"""
import sys
import importlib.util

spec = importlib.util.spec_from_file_location("fl", "/workspace/self_evolving_agent/core/federated_learning.py")
mod = importlib.util.module_from_spec(spec)
sys.modules["fl"] = mod
spec.loader.exec_module(mod)

print("=" * 60)
print("阶段54验证: 联邦学习接口标准化")
print("=" * 60)

# 测试1: 客户端注册和训练
def test_client_train():
    client = mod.create_federated_client("c1")
    client.receive_global_model({"layer1": [0.0, 0.0, 0.0]})
    update = client.train(local_data_size=50)
    assert update.client_id == "c1"
    assert update.sample_count == 50
    assert "layer1" in update.weights
    print("  [test_client_train] 客户端训练 OK")

# 测试2: FedAvg聚合
def test_fedavg():
    server = mod.create_federated_server(mod.AggregationStrategyType.FEDAVG)
    c1 = mod.create_federated_client("c1")
    c2 = mod.create_federated_client("c2")
    server.register_client(c1)
    server.register_client(c2)

    result = server.run_round(min_clients=2)
    assert result["status"] == "completed"
    assert result["updates_received"] == 2
    print("  [test_fedavg] FedAvg聚合 OK")

# 测试3: 多轮训练
def test_multi_round():
    server = mod.create_federated_server(mod.AggregationStrategyType.FEDAVG)
    for i in range(3):
        server.register_client(mod.create_federated_client(f"c{i}"))

    for _ in range(3):
        server.run_round()

    stats = server.get_stats()
    assert stats["current_round"] == 3
    assert stats["completed_rounds"] == 3
    print("  [test_multi_round] 多轮训练 OK")

# 测试4: 全局模型更新
def test_global_model_update():
    server = mod.create_federated_server()
    c1 = mod.create_federated_client("c1")
    server.register_client(c1)

    initial = server.get_global_model()
    server.run_round()
    updated = server.get_global_model()

    assert initial != updated
    print("  [test_global_model_update] 全局模型更新 OK")

# 测试5: 客户端状态
def test_client_status():
    client = mod.create_federated_client("c1")
    assert client.get_status() == mod.ClientStatus.IDLE
    client.receive_global_model({"layer1": [0.0]})
    assert client.get_status() == mod.ClientStatus.IDLE
    print("  [test_client_status] 客户端状态 OK")

# 测试6: 加权平均策略
def test_weighted_average():
    strategy = mod.WeightedAverageStrategy(weights={"c1": 2.0, "c2": 1.0})
    server = mod.FederatedServer(strategy)
    c1 = mod.create_federated_client("c1")
    c2 = mod.create_federated_client("c2")
    server.register_client(c1)
    server.register_client(c2)
    result = server.run_round(min_clients=2)
    assert result["status"] == "completed"
    print("  [test_weighted_average] 加权平均策略 OK")

if __name__ == "__main__":
    test_client_train()
    test_fedavg()
    test_multi_round()
    test_global_model_update()
    test_client_status()
    test_weighted_average()
    print("=" * 60)
    print("阶段54验证通过 ✓")
    print("=" * 60)
