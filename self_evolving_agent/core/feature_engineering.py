"""
阶段44: 特征工程接口标准化

第一性原理:
1. 原始数据不等于特征。特征是对原始数据的结构化表达
2. 特征必须可计算、可比较、可存储
3. 特征工程是数据驱动的：从数据中提取、转换、选择

设计原则:
- FeatureExtractor: 特征提取接口
- FeatureTransformer: 特征转换接口（归一化、编码等）
- FeatureSelector: 特征选择接口
- FeatureVector: 统一特征向量格式
- 支持数值/类别/文本/时间序列特征
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
from enum import Enum
import statistics


class FeatureType(Enum):
    """特征类型"""
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    TEXT = "text"
    TIMESTAMP = "timestamp"
    BOOLEAN = "boolean"


@dataclass
class Feature:
    """单个特征"""
    name: str
    value: Any
    feature_type: FeatureType
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FeatureVector:
    """特征向量"""
    features: Dict[str, Feature] = field(default_factory=dict)
    label: Optional[Any] = None

    def get_value(self, name: str) -> Any:
        """获取特征值"""
        if name in self.features:
            return self.features[name].value
        return None

    def add(self, feature: Feature) -> None:
        """添加特征"""
        self.features[feature.name] = feature

    def to_dict(self) -> Dict[str, Any]:
        """转为字典"""
        return {
            name: f.value
            for name, f in self.features.items()
        }

    def names(self) -> List[str]:
        """获取所有特征名"""
        return list(self.features.keys())


# ============================================================
# 特征提取器
# ============================================================

class FeatureExtractor(ABC):
    """
    特征提取器

    第一性原理：从原始数据中提取有意义的特征
    """

    @abstractmethod
    def extract(self, raw_data: Any) -> FeatureVector:
        """从原始数据中提取特征"""
        pass

    @abstractmethod
    def get_feature_names(self) -> List[str]:
        """获取提取的特征名列表"""
        pass


class NumericFeatureExtractor(FeatureExtractor):
    """数值特征提取器"""

    def __init__(self, feature_name: str, extractor_fn: Optional[callable] = None):
        self.feature_name = feature_name
        self.extractor_fn = extractor_fn or (lambda x: x)

    def extract(self, raw_data: Any) -> FeatureVector:
        value = self.extractor_fn(raw_data)
        feature = Feature(
            name=self.feature_name,
            value=float(value) if value is not None else 0.0,
            feature_type=FeatureType.NUMERIC,
        )
        vector = FeatureVector()
        vector.add(feature)
        return vector

    def get_feature_names(self) -> List[str]:
        return [self.feature_name]


class CategoricalFeatureExtractor(FeatureExtractor):
    """类别特征提取器"""

    def __init__(self, feature_name: str, extractor_fn: Optional[callable] = None):
        self.feature_name = feature_name
        self.extractor_fn = extractor_fn or (lambda x: x)
        self._categories: set = set()
        self._fitted = False

    def extract(self, raw_data: Any) -> FeatureVector:
        value = self.extractor_fn(raw_data)
        feature = Feature(
            name=self.feature_name,
            value=str(value) if value is not None else "unknown",
            feature_type=FeatureType.CATEGORICAL,
        )
        vector = FeatureVector()
        vector.add(feature)
        return vector

    def get_feature_names(self) -> List[str]:
        return [self.feature_name]


# ============================================================
# 特征转换器
# ============================================================

class FeatureTransformer(ABC):
    """
    特征转换器

    第一性原理：特征必须标准化才能被模型有效使用
    """

    @abstractmethod
    def fit(self, feature_vectors: List[FeatureVector]) -> None:
        """从数据中学习转换参数"""
        pass

    @abstractmethod
    def transform(self, vector: FeatureVector) -> FeatureVector:
        """转换单个特征向量"""
        pass

    def fit_transform(self, feature_vectors: List[FeatureVector]) -> List[FeatureVector]:
        """先fit再transform"""
        self.fit(feature_vectors)
        return [self.transform(v) for v in feature_vectors]


class MinMaxScaler(FeatureTransformer):
    """最小最大归一化"""

    def __init__(self, feature_name: str, feature_range: Tuple[float, float] = (0.0, 1.0)):
        self.feature_name = feature_name
        self.feature_range = feature_range
        self._min: Optional[float] = None
        self._max: Optional[float] = None

    def fit(self, feature_vectors: List[FeatureVector]) -> None:
        values = [
            v.get_value(self.feature_name)
            for v in feature_vectors
            if v.get_value(self.feature_name) is not None
        ]
        if values:
            self._min = min(values)
            self._max = max(values)

    def transform(self, vector: FeatureVector) -> FeatureVector:
        value = vector.get_value(self.feature_name)
        if value is None or self._min is None or self._max is None:
            return vector

        if self._max == self._min:
            scaled = self.feature_range[0]
        else:
            scaled = (value - self._min) / (self._max - self._min)
            scaled = scaled * (self.feature_range[1] - self.feature_range[0]) + self.feature_range[0]

        new_vector = FeatureVector(label=vector.label)
        for name, feature in vector.features.items():
            if name == self.feature_name:
                new_vector.add(Feature(
                    name=name,
                    value=round(scaled, 6),
                    feature_type=FeatureType.NUMERIC,
                ))
            else:
                new_vector.add(feature)
        return new_vector


class StandardScaler(FeatureTransformer):
    """标准归一化（Z-score）"""

    def __init__(self, feature_name: str):
        self.feature_name = feature_name
        self._mean: Optional[float] = None
        self._std: Optional[float] = None

    def fit(self, feature_vectors: List[FeatureVector]) -> None:
        values = [
            v.get_value(self.feature_name)
            for v in feature_vectors
            if v.get_value(self.feature_name) is not None
        ]
        if values:
            self._mean = statistics.mean(values)
            if len(values) > 1:
                self._std = statistics.stdev(values)
            else:
                self._std = 1.0

    def transform(self, vector: FeatureVector) -> FeatureVector:
        value = vector.get_value(self.feature_name)
        if value is None or self._mean is None or self._std is None:
            return vector

        if self._std == 0:
            scaled = 0.0
        else:
            scaled = (value - self._mean) / self._std

        new_vector = FeatureVector(label=vector.label)
        for name, feature in vector.features.items():
            if name == self.feature_name:
                new_vector.add(Feature(
                    name=name,
                    value=round(scaled, 6),
                    feature_type=FeatureType.NUMERIC,
                ))
            else:
                new_vector.add(feature)
        return new_vector


class OneHotEncoder(FeatureTransformer):
    """One-Hot编码器"""

    def __init__(self, feature_name: str):
        self.feature_name = feature_name
        self._categories: List[str] = []

    def fit(self, feature_vectors: List[FeatureVector]) -> None:
        values = set()
        for v in feature_vectors:
            val = v.get_value(self.feature_name)
            if val is not None:
                values.add(str(val))
        self._categories = sorted(values)

    def transform(self, vector: FeatureVector) -> FeatureVector:
        value = vector.get_value(self.feature_name)
        value_str = str(value) if value is not None else "unknown"

        new_vector = FeatureVector(label=vector.label)
        for name, feature in vector.features.items():
            if name == self.feature_name:
                for cat in self._categories:
                    new_vector.add(Feature(
                        name=f"{name}_{cat}",
                        value=1.0 if value_str == cat else 0.0,
                        feature_type=FeatureType.NUMERIC,
                    ))
            else:
                new_vector.add(feature)
        return new_vector


# ============================================================
# 特征选择器
# ============================================================

class FeatureSelector(ABC):
    """
    特征选择器

    第一性原理：不是所有特征都有用，选择有价值的特征提高模型效率
    """

    @abstractmethod
    def select(self, feature_vectors: List[FeatureVector]) -> List[str]:
        """选择特征名列表"""
        pass


class VarianceThresholdSelector(FeatureSelector):
    """方差阈值选择器"""

    def __init__(self, threshold: float = 0.0):
        self.threshold = threshold

    def select(self, feature_vectors: List[FeatureVector]) -> List[str]:
        if not feature_vectors:
            return []

        feature_names = feature_vectors[0].names()
        selected = []

        for name in feature_names:
            values = [
                v.get_value(name)
                for v in feature_vectors
                if v.get_value(name) is not None
            ]
            if not values:
                continue

            if len(values) > 1:
                try:
                    var = statistics.variance(values)
                    if var > self.threshold:
                        selected.append(name)
                except statistics.StatisticsError:
                    pass
            else:
                selected.append(name)

        return selected


# ============================================================
# 特征工程管道
# ============================================================

class FeatureEngineeringPipeline:
    """
    特征工程管道

    组合提取 -> 转换 -> 选择
    """

    def __init__(self):
        self.extractors: List[FeatureExtractor] = []
        self.transformers: List[FeatureTransformer] = []
        self.selector: Optional[FeatureSelector] = None

    def add_extractor(self, extractor: FeatureExtractor) -> None:
        """添加提取器"""
        self.extractors.append(extractor)

    def add_transformer(self, transformer: FeatureTransformer) -> None:
        """添加转换器"""
        self.transformers.append(transformer)

    def set_selector(self, selector: FeatureSelector) -> None:
        """设置选择器"""
        self.selector = selector

    def process(self, raw_data_list: List[Any]) -> List[FeatureVector]:
        """处理原始数据"""
        # 提取
        vectors = []
        for raw in raw_data_list:
            vector = FeatureVector()
            for extractor in self.extractors:
                extracted = extractor.extract(raw)
                for name, feature in extracted.features.items():
                    vector.add(feature)
            vectors.append(vector)

        # 转换
        for transformer in self.transformers:
            transformer.fit(vectors)
            vectors = [transformer.transform(v) for v in vectors]

        # 选择
        if self.selector:
            selected_names = self.selector.select(vectors)
            vectors = [
                self._filter_features(v, selected_names)
                for v in vectors
            ]

        return vectors

    def _filter_features(self, vector: FeatureVector, names: List[str]) -> FeatureVector:
        """过滤特征"""
        new_vector = FeatureVector(label=vector.label)
        for name in names:
            if name in vector.features:
                new_vector.add(vector.features[name])
        return new_vector


# ============================================================
# 便捷函数
# ============================================================

def create_feature_vector(**kwargs) -> FeatureVector:
    """创建特征向量"""
    vector = FeatureVector()
    for name, value in kwargs.items():
        feature_type = FeatureType.NUMERIC if isinstance(value, (int, float)) else FeatureType.CATEGORICAL
        vector.add(Feature(name=name, value=value, feature_type=feature_type))
    return vector
