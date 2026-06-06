import sys
sys.path.insert(0, '/workspace')

from self_evolving_agent.core.model_manager import ModelVersion, ModelMetrics, ModelManager

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
print(comparison)
