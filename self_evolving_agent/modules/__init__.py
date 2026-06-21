"""
modules 包 — 功能模块层

本包包含自驱永续进化Agent系统的功能模块实现：
- 预测器（predictor, temporal_predictor, predictive_coding）
- 驱力系统（drive_engine, drive_formulas, drive_weights）
- 记忆系统（memory）
- 优化器（optimizer）
- 评估器（evaluator, task_evaluation）
- 任务系统（task_system）
- 探索（exploration）
- 自由能（free_energy）

注意：大部分模块依赖 numpy。若 numpy 未安装，相关导入将被跳过。

推荐导入方式：
    from self_evolving_agent.modules import ShortTermMemory, LinearPredictor
"""

# memory 模块不依赖 numpy，可安全导入
from .memory import (
    MemoryEntry,
    ShortTermMemory,
    LongTermMemory,
    MemoryCoordinator,
)

# 以下模块依赖 numpy，使用 try/except 保护
try:
    from .predictor import (
        BasePredictor,
        LinearPredictor,
        MovingAveragePredictor,
        MultiLayerPredictor,
    )
except ImportError:
    pass

try:
    from .drive_engine import (
        SafeDriveCalculator,
        GainDriveCalculator,
        EffDriveCalculator,
        UnifiedDriveEngine,
    )
except ImportError:
    pass

try:
    from .drive_formulas import (
        DriveFormula,
        SafeDriveEngine,
        GainDriveEngine,
        EffDriveEngine,
        UnifiedDriveSystem,
    )
except ImportError:
    pass

try:
    from .drive_weights import (
        WeightConfig,
        DynamicWeightAdapter,
        WeightedDriveSystem,
    )
except ImportError:
    pass

try:
    from .evaluator import (
        PredictionErrorCalculator,
        DriveFeedbackGenerator,
        UnifiedEvaluator,
    )
except ImportError:
    pass

try:
    from .exploration import (
        AdaptiveExplorationRate,
        ExplorationStrategy,
    )
except ImportError:
    pass

try:
    from .free_energy import (
        EnergyTerm,
        ComplexityTerm,
        FreeEnergy,
        FreeEnergyCalculator,
    )
except ImportError:
    pass

try:
    from .optimizer import (
        GradientDescentOptimizer,
        StructuralRestructurer,
        OptimizationStrategy,
    )
except ImportError:
    pass

try:
    from .predictive_coding import (
        ConvergenceStatus,
        PredictiveCodingLayer,
        HierarchicalPredictiveCoder,
    )
except ImportError:
    pass

try:
    from .task_evaluation import (
        EvaluationComponents,
        FormulaTaskEvaluator,
        UCBTaskSelector,
    )
except ImportError:
    pass

try:
    from .task_system import (
        GapDrivenTaskFactory,
        BenefitCostEvaluator,
        ExplorationExploitationSelector,
        TaskSystem,
    )
except ImportError:
    pass

try:
    from .temporal_predictor import (
        SimpleGRUCell,
        TemporalPredictor,
        MultiHorizonPredictor,
    )
except ImportError:
    pass


__all__ = [
    # memory（始终可用）
    "MemoryEntry",
    "ShortTermMemory",
    "LongTermMemory",
    "MemoryCoordinator",
    # 以下在 numpy 可用时可用
    "BasePredictor",
    "LinearPredictor",
    "MovingAveragePredictor",
    "MultiLayerPredictor",
    "UnifiedDriveEngine",
    "UnifiedEvaluator",
    "FreeEnergyCalculator",
    "HierarchicalPredictiveCoder",
    "TaskSystem",
    "TemporalPredictor",
]
