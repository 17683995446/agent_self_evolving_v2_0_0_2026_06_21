"""
阶段44测试: 特征工程接口标准化
"""
import sys
sys.path.insert(0, '/workspace')

from self_evolving_agent.core.feature_engineering import (
    Feature, FeatureType, FeatureVector, FeatureExtractor,
    NumericFeatureExtractor, CategoricalFeatureExtractor,
    MinMaxScaler, StandardScaler, OneHotEncoder,
    VarianceThresholdSelector, FeatureEngineeringPipeline,
    create_feature_vector
)


def test_feature_vector():
    """测试特征向量"""
    vector = FeatureVector()
    vector.add(Feature(name="age", value=25, feature_type=FeatureType.NUMERIC))
    vector.add(Feature(name="city", value="beijing", feature_type=FeatureType.CATEGORICAL))

    assert vector.get_value("age") == 25
    assert vector.get_value("city") == "beijing"
    assert vector.names() == ["age", "city"]

    d = vector.to_dict()
    assert d["age"] == 25
    print("  [test_feature_vector] 特征向量 ✓")


def test_numeric_extractor():
    """测试数值特征提取"""
    extractor = NumericFeatureExtractor("score")
    vector = extractor.extract(95)

    assert vector.get_value("score") == 95.0
    assert vector.features["score"].feature_type == FeatureType.NUMERIC
    print("  [test_numeric_extractor] 数值特征提取 ✓")


def test_categorical_extractor():
    """测试类别特征提取"""
    extractor = CategoricalFeatureExtractor("color")
    vector = extractor.extract("red")

    assert vector.get_value("color") == "red"
    assert vector.features["color"].feature_type == FeatureType.CATEGORICAL
    print("  [test_categorical_extractor] 类别特征提取 ✓")


def test_minmax_scaler():
    """测试最小最大归一化"""
    vectors = [
        create_feature_vector(x=10),
        create_feature_vector(x=20),
        create_feature_vector(x=30),
    ]

    scaler = MinMaxScaler("x")
    scaler.fit(vectors)
    result = scaler.transform(vectors[1])

    assert result.get_value("x") == 0.5  # (20-10)/(30-10) = 0.5
    print("  [test_minmax_scaler] 最小最大归一化 ✓")


def test_standard_scaler():
    """测试标准归一化"""
    vectors = [
        create_feature_vector(x=10),
        create_feature_vector(x=20),
        create_feature_vector(x=30),
    ]

    scaler = StandardScaler("x")
    scaler.fit(vectors)
    result = scaler.transform(vectors[1])

    # mean=20, std=10, (20-20)/10 = 0
    assert result.get_value("x") == 0.0
    print("  [test_standard_scaler] 标准归一化 ✓")


def test_onehot_encoder():
    """测试One-Hot编码"""
    vectors = [
        create_feature_vector(color="red"),
        create_feature_vector(color="blue"),
        create_feature_vector(color="red"),
    ]

    encoder = OneHotEncoder("color")
    encoder.fit(vectors)
    result = encoder.transform(vectors[0])

    assert result.get_value("color_blue") == 0.0
    assert result.get_value("color_red") == 1.0
    assert "color" not in result.names()
    print("  [test_onehot_encoder] One-Hot编码 ✓")


def test_variance_selector():
    """测试方差选择器"""
    vectors = [
        create_feature_vector(a=1, b=1),
        create_feature_vector(a=2, b=1),
        create_feature_vector(a=3, b=1),
    ]

    selector = VarianceThresholdSelector(threshold=0.1)
    selected = selector.select(vectors)

    assert "a" in selected  # a有方差
    assert "b" not in selected  # b无方差
    print("  [test_variance_selector] 方差选择器 ✓")


def test_feature_pipeline():
    """测试特征工程管道"""
    pipeline = FeatureEngineeringPipeline()
    pipeline.add_extractor(NumericFeatureExtractor("age"))
    pipeline.add_extractor(CategoricalFeatureExtractor("gender"))
    pipeline.add_transformer(MinMaxScaler("age"))

    raw_data = [25, 30, 35]
    vectors = pipeline.process(raw_data)

    assert len(vectors) == 3
    assert vectors[0].get_value("age") == 0.0   # (25-25)/(35-25)
    assert vectors[1].get_value("age") == 0.5   # (30-25)/(35-25)
    assert vectors[2].get_value("age") == 1.0   # (35-25)/(35-25)
    print("  [test_feature_pipeline] 特征工程管道 ✓")


def test_create_feature_vector():
    """测试便捷创建函数"""
    vector = create_feature_vector(x=10, y="hello")

    assert vector.get_value("x") == 10
    assert vector.features["x"].feature_type == FeatureType.NUMERIC
    assert vector.get_value("y") == "hello"
    assert vector.features["y"].feature_type == FeatureType.CATEGORICAL
    print("  [test_create_feature_vector] 便捷创建 ✓")


def test_fit_transform():
    """测试fit_transform便捷方法"""
    vectors = [
        create_feature_vector(x=0),
        create_feature_vector(x=100),
    ]

    scaler = MinMaxScaler("x")
    results = scaler.fit_transform(vectors)

    assert results[0].get_value("x") == 0.0
    assert results[1].get_value("x") == 1.0
    print("  [test_fit_transform] fit_transform ✓")


if __name__ == "__main__":
    print("=" * 60)
    print("阶段44测试: 特征工程接口标准化")
    print("=" * 60)

    test_feature_vector()
    test_numeric_extractor()
    test_categorical_extractor()
    test_minmax_scaler()
    test_standard_scaler()
    test_onehot_encoder()
    test_variance_selector()
    test_feature_pipeline()
    test_create_feature_vector()
    test_fit_transform()

    print("=" * 60)
    print("全部10项测试通过 ✓")
    print("=" * 60)
