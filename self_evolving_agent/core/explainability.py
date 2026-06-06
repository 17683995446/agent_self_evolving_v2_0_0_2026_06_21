"""
阶段56: 模型解释性接口标准化

第一性原理:
1. 不可解释的模型不可信任：黑箱决策无法验证
2. 解释性必须本地化：每个预测都应有对应解释
3. 解释必须可量化：特征重要性、置信度、反事实

设计原则:
- Explanation: 解释结果
- FeatureImportance: 特征重要性
- Explainer: 解释器接口
- CounterfactualExplainer: 反事实解释
- 支持SHAP、LIME风格解释
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum


class ExplanationType(Enum):
    """解释类型"""
    FEATURE_IMPORTANCE = "feature_importance"
    COUNTERFACTUAL = "counterfactual"
    RULE_BASED = "rule_based"
    ATTENTION = "attention"


@dataclass
class FeatureImportance:
    """特征重要性"""
    feature_name: str
    importance: float
    direction: str = "positive"  # positive / negative


@dataclass
class Explanation:
    """解释结果"""
    prediction_id: str
    explanation_type: ExplanationType
    feature_importances: List[FeatureImportance] = field(default_factory=list)
    confidence: float = 0.0
    summary: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# 解释器接口
# ============================================================

class Explainer(ABC):
    """
    解释器抽象接口

    第一性原理：为模型预测提供可理解的解释
    """

    @abstractmethod
    def explain(self, input_data: Any, prediction: Any) -> Explanation:
        """解释预测结果"""
        pass

    @abstractmethod
    def explain_batch(self, inputs: List[Any], predictions: List[Any]) -> List[Explanation]:
        """批量解释"""
        pass


# ============================================================
# 基于特征重要性的解释器
# ============================================================

class FeatureImportanceExplainer(Explainer):
    """
    特征重要性解释器

    基于模型内部权重或近似方法计算特征重要性
    """

    def __init__(self, feature_names: List[str]):
        self.feature_names = feature_names

    def explain(self, input_data: Any, prediction: Any) -> Explanation:
        """
        计算特征重要性

        简单实现：使用输入值与预测值的关联度作为重要性
        """
        importances = []
        if isinstance(input_data, dict):
            for name in self.feature_names:
                value = input_data.get(name, 0)
                importance = abs(value) / (sum(abs(v) for v in input_data.values()) + 1e-10)
                direction = "positive" if value >= 0 else "negative"
                importances.append(FeatureImportance(name, importance, direction))
        elif isinstance(input_data, (list, tuple)):
            total = sum(abs(v) for v in input_data) + 1e-10
            for i, value in enumerate(input_data):
                name = self.feature_names[i] if i < len(self.feature_names) else f"feature_{i}"
                importance = abs(value) / total
                direction = "positive" if value >= 0 else "negative"
                importances.append(FeatureImportance(name, importance, direction))

        importances.sort(key=lambda x: x.importance, reverse=True)

        return Explanation(
            prediction_id=str(id(prediction)),
            explanation_type=ExplanationType.FEATURE_IMPORTANCE,
            feature_importances=importances,
            confidence=0.8,
            summary=f"Top feature: {importances[0].feature_name if importances else 'none'}",
        )

    def explain_batch(self, inputs: List[Any], predictions: List[Any]) -> List[Explanation]:
        return [self.explain(inp, pred) for inp, pred in zip(inputs, predictions)]


# ============================================================
# 反事实解释器
# ============================================================

class CounterfactualExplainer(Explainer):
    """
    反事实解释器

    回答"如果输入如何改变，预测结果会怎样？"
    """

    def __init__(self, model_fn: Callable[[Any], Any], feature_names: List[str]):
        self.model_fn = model_fn
        self.feature_names = feature_names

    def explain(self, input_data: Any, prediction: Any) -> Explanation:
        """
        生成反事实解释

        简单实现：找到改变最小特征即可改变预测的情况
        """
        importances = []
        if isinstance(input_data, dict):
            original_pred = self.model_fn(input_data)
            for name in self.feature_names:
                modified = dict(input_data)
                modified[name] = modified.get(name, 0) + 1.0
                new_pred = self.model_fn(modified)
                if new_pred != original_pred:
                    importances.append(FeatureImportance(name, 1.0, "counterfactual"))
                else:
                    importances.append(FeatureImportance(name, 0.0, "counterfactual"))

        return Explanation(
            prediction_id=str(id(prediction)),
            explanation_type=ExplanationType.COUNTERFACTUAL,
            feature_importances=importances,
            confidence=0.7,
            summary=f"Counterfactual: change {sum(1 for i in importances if i.importance > 0)} features to flip prediction",
        )

    def explain_batch(self, inputs: List[Any], predictions: List[Any]) -> List[Explanation]:
        return [self.explain(inp, pred) for inp, pred in zip(inputs, predictions)]


# ============================================================
# 解释管理器
# ============================================================

class ExplanationManager:
    """
    解释管理器

    管理多个解释器，提供统一的解释接口
    """

    def __init__(self):
        self._explainers: Dict[str, Explainer] = {}

    def register(self, name: str, explainer: Explainer) -> None:
        """注册解释器"""
        self._explainers[name] = explainer

    def explain(self, name: str, input_data: Any, prediction: Any) -> Optional[Explanation]:
        """使用指定解释器解释"""
        explainer = self._explainers.get(name)
        if explainer is None:
            return None
        return explainer.explain(input_data, prediction)

    def list_explainers(self) -> List[str]:
        """列出所有解释器"""
        return list(self._explainers.keys())


# ============================================================
# 便捷函数
# ============================================================

def create_feature_importance_explainer(feature_names: List[str]) -> FeatureImportanceExplainer:
    """创建特征重要性解释器"""
    return FeatureImportanceExplainer(feature_names=feature_names)


def create_counterfactual_explainer(model_fn: Callable[[Any], Any], feature_names: List[str]) -> CounterfactualExplainer:
    """创建反事实解释器"""
    return CounterfactualExplainer(model_fn=model_fn, feature_names=feature_names)


def create_explanation_manager() -> ExplanationManager:
    """创建解释管理器"""
    return ExplanationManager()
