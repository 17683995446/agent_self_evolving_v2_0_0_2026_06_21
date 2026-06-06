"""
阶段45测试: 模型管理接口标准化
"""
import sys
sys.path.insert(0, '/workspace')

from self_evolving_agent.core.model_manager import (
    Model, ModelMetrics, ModelVersion, ModelStage, ModelStatus,
    ModelRegistry, ModelManager, create_model_manager
)


class DummyModel(Model):
    """测试模型"""

    def __init__(self, model_name="dummy"):
        self._name = model_name

    @property
    def name(self) -> str:
        return self._name

    def predict(self, input_data):
        return input_data * 2

    def evaluate(self, test_data, labels):
        return ModelMetrics(accuracy=0.9, loss=0.1)


def test_model_interface():
    """测试模型接口"""
    model = DummyModel("test_model")
    assert model.name == "test_model"
    assert model.predict(5) == 10
    metrics = model.evaluate(None, None)
    assert metrics.accuracy == 0.9
    print("  [test_model_interface] 模型接口 ✓")


def test_model_registry():
    """测试模型注册表"""
    registry = ModelRegistry()
    v1 = ModelVersion(version_id="v1", model_name="m1", created_at=1.0)
    v2 = ModelVersion(version_id="v2", model_name="m1", created_at=2.0)

    registry.register(v1)
    registry.register(v2)

    assert len(registry.get_versions("m1")) == 2
    assert registry.get_latest("m1").version_id == "v2"
    assert registry.get_version("m1", "v1").version_id == "v1"
    print("  [test_model_registry] 模型注册表 ✓")


def test_model_manager_register():
    """测试模型注册"""
    manager = ModelManager()
    model = DummyModel("my_model")

    version = manager.register_model(
        model,
        metrics=ModelMetrics(accuracy=0.85),
        metadata={"framework": "test"}
    )

    assert version.model_name == "my_model"
    assert version.metrics.accuracy == 0.85
    assert version.metadata["framework"] == "test"
    print("  [test_model_manager_register] 模型注册 ✓")


def test_model_deploy():
    """测试模型部署"""
    manager = ModelManager()
    model = DummyModel("deploy_test")

    version = manager.register_model(model)
    success = manager.deploy("deploy_test", version.version_id, alias="prod")

    assert success is True
    deployed = manager.get_deployed("prod")
    assert deployed is not None
    assert deployed.version_id == version.version_id
    print("  [test_model_deploy] 模型部署 ✓")


def test_model_undeploy():
    """测试取消部署"""
    manager = ModelManager()
    model = DummyModel("undeploy_test")

    version = manager.register_model(model)
    manager.deploy("undeploy_test", version.version_id)

    assert manager.undeploy("default") is True
    assert manager.get_deployed("default") is None
    assert manager.undeploy("default") is False
    print("  [test_model_undeploy] 取消部署 ✓")


def test_model_promote():
    """测试模型阶段提升"""
    manager = ModelManager()
    model = DummyModel("promote_test")

    version = manager.register_model(model)
    assert version.stage == ModelStage.DEVELOPMENT

    manager.promote("promote_test", version.version_id, ModelStage.PRODUCTION)
    updated = manager.registry.get_version("promote_test", version.version_id)
    assert updated.stage == ModelStage.PRODUCTION
    print("  [test_model_promote] 阶段提升 ✓")


def test_model_compare():
    """测试模型版本比较"""
    manager = ModelManager()

    v1 = ModelVersion(
        version_id="v1", model_name="cmp",
        created_at=1.0,
        metrics=ModelMetrics(accuracy=0.8, loss=0.2)
    )
    v2 = ModelVersion(
        version_id="v2", model_name="cmp",
        created_at=2.0,
        metrics=ModelMetrics(accuracy=0.9, loss=0.1)
    )

    manager.registry.register(v1)
    manager.registry.register(v2)

    comparison = manager.compare_versions("cmp", "v1", "v2")
    assert abs(comparison["accuracy"]["diff"] - 0.1) < 0.001
    assert comparison["accuracy"]["improved"] is True
    assert abs(comparison["loss"]["diff"] - (-0.1)) < 0.001
    assert comparison["loss"]["improved"] is True  # loss下降是改进
    print("  [test_model_compare] 版本比较 ✓")


def test_model_stats():
    """测试统计信息"""
    manager = ModelManager()

    manager.register_model(DummyModel("m1"))
    manager.register_model(DummyModel("m2"))
    manager.register_model(DummyModel("m1"))

    stats = manager.get_stats()
    assert stats["total_models"] == 2
    assert stats["total_versions"] == 3
    print("  [test_model_stats] 统计信息 ✓")


def test_model_metrics_to_dict():
    """测试指标序列化"""
    metrics = ModelMetrics(
        accuracy=0.9,
        custom={"auc": 0.95, "ap": 0.88}
    )

    d = metrics.to_dict()
    assert d["accuracy"] == 0.9
    assert d["auc"] == 0.95
    assert d["ap"] == 0.88
    assert "loss" not in d  # None的不包含
    print("  [test_model_metrics_to_dict] 指标序列化 ✓")


def test_latest_by_stage():
    """测试按阶段获取最新版本"""
    registry = ModelRegistry()

    v1 = ModelVersion(
        version_id="v1", model_name="stg",
        created_at=1.0, stage=ModelStage.STAGING
    )
    v2 = ModelVersion(
        version_id="v2", model_name="stg",
        created_at=2.0, stage=ModelStage.PRODUCTION
    )

    registry.register(v1)
    registry.register(v2)

    latest_prod = registry.get_latest("stg", stage=ModelStage.PRODUCTION)
    assert latest_prod.version_id == "v2"

    latest_all = registry.get_latest("stg")
    assert latest_all.version_id == "v2"
    print("  [test_latest_by_stage] 按阶段获取最新 ✓")


if __name__ == "__main__":
    print("=" * 60)
    print("阶段45测试: 模型管理接口标准化")
    print("=" * 60)

    test_model_interface()
    test_model_registry()
    test_model_manager_register()
    test_model_deploy()
    test_model_undeploy()
    test_model_promote()
    test_model_compare()
    test_model_stats()
    test_model_metrics_to_dict()
    test_latest_by_stage()

    print("=" * 60)
    print("全部10项测试通过 ✓")
    print("=" * 60)
