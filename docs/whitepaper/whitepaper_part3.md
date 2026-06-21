## 第三卷：核心算法与数学原理

---

## 第十六章：预测编码算法详解

### 16.1 预测编码的数学框架

预测编码的核心数学框架可以形式化为一个层级化的概率推断问题。

**符号定义**：
- $x^{(l)}$: 第$l$层的神经活动（或状态表示）
- $\mu^{(l)}$: 第$l$层的预测信号
- $\varepsilon^{(l)}$: 第$l$层的预测误差
- $\theta^{(l)}$: 第$l$层生成模型的参数
- $l = 1, 2, ..., L$: 层级索引，$L$为总层数

**生成模型**：

每一层的生成模型定义了如何从高层表示生成本层的预测：

$$\mu^{(l)} = f^{(l)}(x^{(l+1)}; \theta^{(l)})$$

其中$f^{(l)}$是第$l$层的生成函数，可以是线性变换、神经网络或其他函数。

**预测误差**：

预测误差是实际活动与预测之间的差异：

$$\varepsilon^{(l)} = x^{(l)} - \mu^{(l)}$$

**自由能**：

变分自由能是预测编码的目标函数：

$$F = \sum_{l=1}^{L} \left[ \frac{1}{2\sigma_l^2} \|\varepsilon^{(l)}\|^2 + \frac{1}{2} \log(2\pi\sigma_l^2) \right]$$

其中$\sigma_l^2$是第$l$层预测误差的方差，代表该层的不确定性。

**推断过程**：

预测编码通过最小化自由能来进行感知推断：

1. **状态更新**（自下而上+自上而下）：
   $$\dot{x}^{(l)} = -\frac{\partial F}{\partial x^{(l)}} = \varepsilon^{(l)} - \frac{\partial f^{(l-1)}}{\partial x^{(l)}} \varepsilon^{(l-1)}$$

2. **参数学习**（梯度下降）：
   $$\dot{\theta}^{(l)} = -\frac{\partial F}{\partial \theta^{(l)}} = -\frac{\partial f^{(l)}}{\partial \theta^{(l)}} \varepsilon^{(l)}$$

### 16.2 梯度下降实现

在实际工程中，我们使用数值梯度下降来实现参数更新。

**基本梯度下降**：

$$\theta_{t+1} = \theta_t - \eta \nabla_\theta F$$

其中$\eta$是学习率。

**带动量的梯度下降**：

$$v_{t+1} = \beta v_t + (1-\beta) \nabla_\theta F$$
$$\theta_{t+1} = \theta_t - \eta v_{t+1}$$

其中$\beta$是动量系数，通常取0.9。

**Adam优化器**：

Adam结合了动量和自适应学习率：

$$m_{t+1} = \beta_1 m_t + (1-\beta_1) \nabla_\theta F$$
$$v_{t+1} = \beta_2 v_t + (1-\beta_2) (\nabla_\theta F)^2$$
$$\hat{m}_{t+1} = \frac{m_{t+1}}{1-\beta_1^{t+1}}$$
$$\hat{v}_{t+1} = \frac{v_{t+1}}{1-\beta_2^{t+1}}$$
$$\theta_{t+1} = \theta_t - \eta \frac{\hat{m}_{t+1}}{\sqrt{\hat{v}_{t+1}} + \epsilon}$$

其中$\beta_1=0.9$, $\beta_2=0.999$, $\epsilon=10^{-8}$。

### 16.3 多层预测模型的具体实现

**底层模型（时序预测）**：

底层模型使用简单的时间序列模型：

```python
class LowLevelModel:
    def __init__(self, input_dim, hidden_dim):
        self.W = np.random.randn(input_dim, hidden_dim) * 0.01
        self.b = np.zeros(hidden_dim)

    def predict(self, x):
        return np.tanh(x @ self.W + self.b)

    def update(self, x, error, lr=0.001):
        grad_W = x.T @ error
        grad_b = np.sum(error, axis=0)
        self.W -= lr * grad_W
        self.b -= lr * grad_b
```

**中层模型（序列预测）**：

中层模型使用LSTM网络：

```python
class MidLevelModel:
    def __init__(self, input_dim, hidden_dim):
        self.lstm = LSTM(input_dim, hidden_dim)
        self.fc = Linear(hidden_dim, input_dim)

    def predict(self, sequence):
        hidden = self.lstm(sequence)
        return self.fc(hidden)

    def update(self, sequence, target, lr=0.001):
        prediction = self.predict(sequence)
        error = prediction - target
        # 反向传播更新参数
        self.backprop(error, lr)
```

**高层模型（趋势预测）**：

高层模型使用注意力机制：

```python
class HighLevelModel:
    def __init__(self, input_dim, hidden_dim):
        self.attention = MultiHeadAttention(input_dim, hidden_dim)
        self.fc = Linear(hidden_dim, input_dim)

    def predict(self, context):
        attended = self.attention(context)
        return self.fc(attended)
```

### 16.4 误差反向传播

误差从底层向高层反向传播：

```python
def backpropagate_error(low_error, models):
    errors = [low_error]
    current_error = low_error

    for model in models[1:]:
        # 计算当前层对上一层误差的贡献
        propagated = model.propagate_error(current_error)
        errors.append(propagated)
        current_error = propagated

    return errors
```

### 16.5 预测不确定性估计

预测不仅要有值，还要有不确定性估计。

**方差估计**：

```python
class UncertaintyEstimator:
    def __init__(self):
        self.error_history = RingBuffer(size=1000)

    def estimate_variance(self, feature_vector):
        # 基于历史误差估计方差
        similar_errors = self.find_similar_errors(feature_vector)
        if len(similar_errors) > 10:
            return np.var(similar_errors)
        else:
            return self.global_variance()

    def update(self, prediction, actual, feature_vector):
        error = (prediction - actual) ** 2
        self.error_history.append((feature_vector, error))
```

---

## 第十七章：驱力计算算法

### 17.1 安全驱力计算

**异常检测算法**：

使用孤立森林（Isolation Forest）检测异常：

```python
from sklearn.ensemble import IsolationForest

class AnomalyDetector:
    def __init__(self):
        self.model = IsolationForest(contamination=0.1)
        self.is_fitted = False

    def fit(self, X):
        self.model.fit(X)
        self.is_fitted = True

    def score(self, x):
        if not self.is_fitted:
            return 0.5
        # 返回异常分数（越小越异常）
        return -self.model.score_samples([x])[0]
```

**资源风险评估**：

```python
def assess_resource_risk(cpu_usage, memory_usage, disk_usage):
    # 使用Sigmoid函数将使用率映射到风险分数
    cpu_risk = 1 / (1 + np.exp(-10 * (cpu_usage - 0.8)))
    memory_risk = 1 / (1 + np.exp(-10 * (memory_usage - 0.8)))
    disk_risk = 1 / (1 + np.exp(-10 * (disk_usage - 0.9)))

    return max(cpu_risk, memory_risk, disk_risk)
```

**安全驱力综合计算**：

```python
def calculate_safe_reward(state, anomaly_detector):
    # 异常分数
    anomaly_score = anomaly_detector.score(state.vector)

    # 资源风险
    resource_risk = assess_resource_risk(
        state.cpu.usage,
        state.memory.usage,
        state.disk.usage
    )

    # 未知状态（新进程、新连接等）
    unknown_score = len(state.unknown_processes) / 10.0

    # 安全事件
    security_events = len(state.security_events)
    security_score = min(security_events / 5.0, 1.0)

    # 综合安全驱力
    safe_reward = 1.0 - (
        0.3 * anomaly_score +
        0.3 * resource_risk +
        0.2 * unknown_score +
        0.2 * security_score
    )

    return max(0.0, safe_reward)
```

### 17.2 收益驱力计算

**预测误差评估**：

```python
def calculate_prediction_error(predictions, actuals):
    errors = []
    for pred, actual in zip(predictions, actuals):
        error = np.mean((pred - actual) ** 2)
        errors.append(error)

    # 归一化到[0,1]
    max_error = max(errors) if errors else 1.0
    normalized_errors = [e / max_error for e in errors]

    return np.mean(normalized_errors)
```

**信息增量评估**：

```python
def calculate_information_gain(new_state, memory):
    # 计算新状态与历史状态的差异
    similarities = []
    for old_state in memory.recent_states:
        sim = cosine_similarity(new_state.vector, old_state.vector)
        similarities.append(sim)

    if not similarities:
        return 1.0  # 全新状态，信息增量最大

    max_similarity = max(similarities)
    information_gain = 1.0 - max_similarity

    return information_gain
```

**收益驱力综合计算**：

```python
def calculate_gain_reward(state, predictions, actuals, memory):
    # 预测误差（越小越好，所以用1-error）
    pred_error = calculate_prediction_error(predictions, actuals)
    error_component = 1.0 - pred_error

    # 信息增量
    info_gain = calculate_information_gain(state, memory)

    # 认知覆盖度（已覆盖维度/总维度）
    coverage = memory.coverage_ratio()

    # 规律发现数（归一化）
    patterns = min(memory.pattern_count / 100.0, 1.0)

    # 综合收益驱力
    gain_reward = (
        0.4 * error_component +
        0.3 * info_gain +
        0.2 * coverage +
        0.1 * patterns
    )

    return gain_reward
```

### 17.3 能效驱力计算

```python
def calculate_eff_reward(agent_metrics):
    # CPU消耗（归一化到[0,1]）
    cpu_usage = agent_metrics.cpu_usage / 20.0  # 上限20%
    cpu_component = 1.0 - min(cpu_usage, 1.0)

    # 内存消耗
    memory_usage = agent_metrics.memory_usage / (total_memory * 0.2)
    memory_component = 1.0 - min(memory_usage, 1.0)

    # 推理耗时
    inference_time = agent_metrics.inference_time / 1.0  # 目标<1秒
    time_component = 1.0 - min(inference_time, 1.0)

    # 计算冗余度
    redundancy = agent_metrics.redundancy_ratio
    redundancy_component = 1.0 - redundancy

    # 综合能效驱力
    eff_reward = (
        0.3 * cpu_component +
        0.3 * memory_component +
        0.2 * time_component +
        0.2 * redundancy_component
    )

    return eff_reward
```

### 17.4 动态权重调整算法

```python
def adjust_weights(state, base_weights):
    safe_w, gain_w, eff_w = base_weights

    # 紧急风险检测
    if state.anomaly_score > 0.8 or state.memory_usage > 0.9:
        # 紧急场景：安全权重最高
        return (0.8, 0.1, 0.1)

    # 资源紧张检测
    if state.cpu_usage > 0.8 or state.memory_usage > 0.8:
        # 资源紧张：能效权重最高
        return (0.2, 0.1, 0.7)

    # 稳态空闲检测
    if state.system_load < 0.2 and state.prediction_error < 0.1:
        # 稳态空闲：收益权重最高
        return (0.1, 0.7, 0.2)

    # 高误差检测
    if state.prediction_error > 0.5:
        # 高误差：收益权重较高
        return (0.1, 0.7, 0.2)

    # 默认返回基础权重
    return (safe_w, gain_w, eff_w)
```

### 17.5 全局奖励计算

```python
def calculate_total_reward(safe_reward, gain_reward, eff_reward, weights):
    w_safe, w_gain, w_eff = weights

    total_reward = (
        w_safe * safe_reward +
        w_gain * gain_reward +
        w_eff * eff_reward
    )

    return total_reward

def calculate_gaps(safe_reward, gain_reward, eff_reward):
    gap_safe = 1.0 - safe_reward
    gap_gain = 1.0 - gain_reward
    gap_eff = 1.0 - eff_reward

    return DriveGaps(gap_safe, gap_gain, gap_eff)
```

---

## 第十八章：任务生成与选择算法

### 18.1 任务生成算法

**基于缺口的任务生成**：

```python
def generate_tasks_from_gaps(gaps, task_templates):
    tasks = []

    if gaps.safe > 0.3:
        # 安全缺口大，生成安全类任务
        tasks.extend([
            Task("risk_prediction", priority=gaps.safe),
            Task("anomaly_detection", priority=gaps.safe * 0.8),
            Task("state_monitoring", priority=gaps.safe * 0.6),
        ])

    if gaps.gain > 0.3:
        # 收益缺口大，生成收益类任务
        tasks.extend([
            Task("unknown_exploration", priority=gaps.gain),
            Task("feature_testing", priority=gaps.gain * 0.7),
            Task("pattern_mining", priority=gaps.gain * 0.6),
        ])

    if gaps.eff > 0.3:
        # 能效缺口大，生成能效类任务
        tasks.extend([
            Task("model_pruning", priority=gaps.eff),
            Task("redundancy_cleanup", priority=gaps.eff * 0.8),
            Task("frequency_optimization", priority=gaps.eff * 0.6),
        ])

    return tasks
```

**基于预测的任务生成**：

```python
def generate_predictive_tasks(predictions, task_templates):
    tasks = []

    # 预测未来安全风险
    if predictions.future_anomaly_risk > 0.5:
        tasks.append(Task("preventive_security", priority=predictions.future_anomaly_risk))

    # 预测未来认知机会
    if predictions.future_information_gain > 0.5:
        tasks.append(Task("proactive_exploration", priority=predictions.future_information_gain))

    return tasks
```

### 18.2 任务评估算法

```python
def evaluate_task(task, state, history):
    # 预期收益
    expected_benefit = estimate_benefit(task, history)

    # 执行成本
    execution_cost = estimate_cost(task, state)

    # 成功概率
    success_rate = estimate_success_rate(task, history)

    # 信息价值
    info_value = estimate_information_value(task, state)

    # 紧急程度
    urgency = task.priority

    # 综合得分
    score = (
        (expected_benefit * success_rate * info_value) / (execution_cost + 0.001)
        + urgency * 0.5
    )

    return score

def estimate_benefit(task, history):
    # 基于历史同类任务的平均收益
    similar_tasks = history.find_similar(task)
    if similar_tasks:
        return np.mean([t.actual_benefit for t in similar_tasks])
    return 0.5  # 默认值

def estimate_cost(task, state):
    # 基于任务类型和当前资源状态估计成本
    base_cost = task.base_cost
    resource_factor = 1.0 / (1.0 - state.system_load + 0.1)
    return base_cost * resource_factor

def estimate_success_rate(task, history):
    similar_tasks = history.find_similar(task)
    if similar_tasks:
        successes = sum(1 for t in similar_tasks if t.success)
        return successes / len(similar_tasks)
    return 0.5

def estimate_information_value(task, state):
    # 探索性任务的信息价值更高
    if task.type in ["unknown_exploration", "feature_testing"]:
        return 1.0
    return 0.5
```

### 18.3 任务选择算法

```python
import random

def select_task(tasks, exploration_rate=0.3):
    if not tasks:
        return None

    # 评估所有任务
    scored_tasks = [(task, evaluate_task(task, state, history)) for task in tasks]
    scored_tasks.sort(key=lambda x: x[1], reverse=True)

    if random.random() < (1 - exploration_rate):
        # 利用：选择得分最高的任务
        return scored_tasks[0][0]
    else:
        # 探索：按信息价值加权随机选择
        weights = [estimate_information_value(t[0], state) for t in scored_tasks]
        total = sum(weights)
        probabilities = [w / total for w in weights]
        return random.choices([t[0] for t in scored_tasks], weights=probabilities)[0]
```

### 18.4 探索-利用平衡算法

```python
class ExplorationManager:
    def __init__(self, base_rate=0.3):
        self.base_rate = base_rate
        self.current_rate = base_rate
        self.exploration_history = []

    def adjust_rate(self, recent_rewards):
        # 如果近期收益低，增加探索
        if np.mean(recent_rewards) < 0.3:
            self.current_rate = min(0.5, self.current_rate + 0.05)
        # 如果近期收益高，减少探索
        elif np.mean(recent_rewards) > 0.7:
            self.current_rate = max(0.1, self.current_rate - 0.05)

    def should_explore(self):
        return random.random() < self.current_rate
```

---

## 第十九章：模型优化算法

### 19.1 在线梯度下降

```python
class OnlineGradientDescent:
    def __init__(self, model, lr=0.001):
        self.model = model
        self.lr = lr
        self.momentum = 0.9
        self.velocity = {name: np.zeros_like(param)
                         for name, param in model.params.items()}

    def update(self, gradient):
        for name in self.model.params:
            # 动量更新
            self.velocity[name] = (
                self.momentum * self.velocity[name]
                + (1 - self.momentum) * gradient[name]
            )
            # 参数更新
            self.model.params[name] -= self.lr * self.velocity[name]
```

### 19.2 自适应学习率

```python
class AdaptiveLearningRate:
    def __init__(self, base_lr=0.001):
        self.base_lr = base_lr
        self.current_lr = base_lr
        self.error_history = []

    def adjust(self, current_error):
        self.error_history.append(current_error)

        if len(self.error_history) < 10:
            return self.current_lr

        # 如果误差持续增大，降低学习率
        recent_errors = self.error_history[-10:]
        if np.mean(recent_errors[-5:]) > np.mean(recent_errors[:5]):
            self.current_lr *= 0.9

        # 如果误差持续减小，增加学习率
        elif np.mean(recent_errors[-5:]) < np.mean(recent_errors[:5]) * 0.9:
            self.current_lr *= 1.1

        # 限制学习率范围
        self.current_lr = np.clip(self.current_lr, 1e-6, 0.1)

        return self.current_lr
```

### 19.3 模型剪枝算法

```python
class ModelPruner:
    def __init__(self, model, target_sparsity=0.3):
        self.model = model
        self.target_sparsity = target_sparsity

    def prune(self):
        # 计算每个参数的重要性
        importance = self.compute_importance()

        # 确定阈值
        threshold = np.percentile(
            np.abs(importance),
            self.target_sparsity * 100
        )

        # 创建掩码
        mask = np.abs(importance) > threshold

        # 应用掩码
        self.model.apply_mask(mask)

        return mask

    def compute_importance(self):
        # 基于参数绝对值的重要性估计
        importance = {}
        for name, param in self.model.params.items():
            importance[name] = np.abs(param)
        return importance
```

### 19.4 特征选择算法

```python
class FeatureSelector:
    def __init__(self, model):
        self.model = model
        self.feature_importance = {}

    def compute_feature_importance(self, X, y):
        # 使用置换重要性
        baseline_error = self.model.evaluate(X, y)

        for feature_idx in range(X.shape[1]):
            # 置换该特征
            X_permuted = X.copy()
            np.random.shuffle(X_permuted[:, feature_idx])

            # 计算误差增加
            permuted_error = self.model.evaluate(X_permuted, y)
            importance = permuted_error - baseline_error

            self.feature_importance[feature_idx] = importance

        return self.feature_importance

    def select_features(self, threshold=0.01):
        selected = []
        for feature_idx, importance in self.feature_importance.items():
            if importance > threshold:
                selected.append(feature_idx)
        return selected
```

### 19.5 模型重构算法

```python
class ModelRestructurer:
    def __init__(self, model, memory):
        self.model = model
        self.memory = memory
        self.max_iterations = 3

    def restructure(self):
        # 保存快照
        snapshot = self.model.save_snapshot()

        for iteration in range(self.max_iterations):
            # 尝试新的结构
            new_structure = self.propose_structure()
            new_model = self.build_model(new_structure)

            # 快速验证
            validation_score = self.quick_validate(new_model)

            if validation_score > self.model.current_score:
                # A/B测试
                if self.ab_test(new_model):
                    # 新模型更好，替换
                    self.model = new_model
                    return True

        # 所有尝试都失败，回滚
        self.model.load_snapshot(snapshot)
        return False

    def propose_structure(self):
        # 基于当前误差模式提议新结构
        if self.model.error_pattern == "underfitting":
            # 欠拟合：增加复杂度
            return self.increase_complexity()
        elif self.model.error_pattern == "overfitting":
            # 过拟合：降低复杂度
            return self.decrease_complexity()
        else:
            # 尝试新的特征组合
            return self.new_feature_combination()

    def ab_test(self, new_model, duration=3600):
        # 并行运行新旧模型一段时间
        # 比较累积性能
        old_score = 0
        new_score = 0

        for _ in range(duration):
            state = get_current_state()

            old_pred = self.model.predict(state)
            new_pred = new_model.predict(state)
            actual = get_next_state()

            old_score -= np.mean((old_pred - actual) ** 2)
            new_score -= np.mean((new_pred - actual) ** 2)

        return new_score > old_score
```

---

## 第二十章：记忆与复盘算法

### 20.1 短期记忆管理

```python
class ShortTermMemory:
    def __init__(self, max_size=10000):
        self.buffer = RingBuffer(max_size)
        self.max_memory_usage = 0.05  # 最多使用5%内存

    def add(self, experience):
        # 检查内存使用
        if self.memory_usage() > self.max_memory_usage:
            self.compress()

        self.buffer.append(experience)

    def sample(self, batch_size):
        # 随机采样
        indices = np.random.choice(len(self.buffer), batch_size, replace=False)
        return [self.buffer[i] for i in indices]

    def compress(self):
        # 压缩旧数据
        # 保留高价值样本，删除低价值样本
        values = [self.assess_value(e) for e in self.buffer]
        threshold = np.percentile(values, 30)
        self.buffer = [e for e, v in zip(self.buffer, values) if v > threshold]
```

### 20.2 长期记忆管理

```python
class LongTermMemory:
    def __init__(self, db_path):
        self.db = sqlite3.connect(db_path)
        self.max_storage_gb = 10
        self.value_threshold = 0.5

    def store(self, experience):
        # 评估价值
        value = self.assess_value(experience)

        if value < self.value_threshold:
            return  # 低价值样本不保存

        # 保存到数据库
        self.db.execute(
            "INSERT INTO experiences VALUES (?, ?, ?, ?)",
            (experience.timestamp, experience.state,
             experience.action, experience.outcome)
        )
        self.db.commit()

        # 检查存储空间
        if self.storage_usage() > self.max_storage_gb:
            self.cleanup()

    def cleanup(self):
        # 只保留Top30%高价值样本
        self.db.execute("""
            DELETE FROM experiences
            WHERE id NOT IN (
                SELECT id FROM experiences
                ORDER BY value DESC
                LIMIT (SELECT COUNT(*) * 0.3 FROM experiences)
            )
        """)
        self.db.commit()

    def retrieve(self, query, k=100):
        # 基于相似度检索
        similarities = []
        for exp in self.db.execute("SELECT * FROM experiences"):
            sim = cosine_similarity(query, exp.state)
            similarities.append((exp, sim))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return [exp for exp, _ in similarities[:k]]
```

### 20.3 离线复盘算法

```python
class OfflineReview:
    def __init__(self, memory, model):
        self.memory = memory
        self.model = model
        self.batch_size = 32

    def review(self):
        # 加载批量样本
        batch = self.memory.sample_batch(self.batch_size * 10)

        # 批量训练
        for epoch in range(5):
            np.random.shuffle(batch)
            for i in range(0, len(batch), self.batch_size):
                mini_batch = batch[i:i+self.batch_size]
                self.train_on_batch(mini_batch)

        # 知识整理
        self.consolidate_knowledge()

        # 冗余清理
        self.cleanup_redundancy()

    def train_on_batch(self, batch):
        states = [e.state for e in batch]
        outcomes = [e.outcome for e in batch]

        predictions = self.model.predict_batch(states)
        errors = predictions - outcomes

        # 更新模型
        self.model.update_batch(states, errors)

    def consolidate_knowledge(self):
        # 从近期经验中提取规律
        recent = self.memory.get_recent(days=7)

        # 聚类分析
        clusters = self.cluster_experiences(recent)

        # 提取每个聚类的模式
        for cluster in clusters:
            pattern = self.extract_pattern(cluster)
            self.memory.store_pattern(pattern)

    def cleanup_redundancy(self):
        # 删除重复或相似的经验
        all_experiences = self.memory.get_all()

        # 计算相似度矩阵
        similarity_matrix = self.compute_similarities(all_experiences)

        # 标记冗余样本
        to_remove = []
        for i in range(len(all_experiences)):
            for j in range(i+1, len(all_experiences)):
                if similarity_matrix[i][j] > 0.95:
                    to_remove.append(j)

        # 删除冗余样本
        self.memory.remove_experiences(to_remove)
```

### 20.4 记忆价值评估

```python
def assess_memory_value(experience, model, memory):
    # 信息增益
    pred_before = model.predict(experience.state)
    # 假设用这个经验训练后
    model.update(experience.state, experience.outcome)
    pred_after = model.predict(experience.state)
    info_gain = np.abs(pred_after - pred_before)

    # 预测难度
    prediction_difficulty = np.abs(experience.outcome - pred_before)

    # 稀有度
    similarities = [cosine_similarity(experience.state, e.state)
                    for e in memory.recent]
    rarity = 1.0 - max(similarities) if similarities else 1.0

    # 代表性
    cluster_center = memory.get_cluster_center(experience)
    representativeness = cosine_similarity(experience.state, cluster_center)

    # 综合价值
    value = (
        0.3 * info_gain +
        0.3 * prediction_difficulty +
        0.2 * rarity +
        0.2 * representativeness
    )

    return value
```

---

## 第二十一章：时序预测算法

### 21.1 ARIMA模型

```python
from statsmodels.tsa.arima.model import ARIMA

class ARIMAModel:
    def __init__(self, order=(1, 1, 1)):
        self.order = order
        self.model = None
        self.fitted = None

    def fit(self, series):
        self.model = ARIMA(series, order=self.order)
        self.fitted = self.model.fit()

    def predict(self, steps=1):
        if self.fitted is None:
            return np.zeros(steps)
        return self.fitted.forecast(steps=steps)

    def update(self, new_value):
        # 增量更新
        if self.fitted is not None:
            self.fitted = self.fitted.append([new_value], refit=False)
```

### 21.2 指数平滑

```python
class ExponentialSmoothing:
    def __init__(self, alpha=0.3):
        self.alpha = alpha
        self.level = None

    def fit(self, series):
        self.level = series[0]
        for value in series[1:]:
            self.update(value)

    def predict(self, steps=1):
        return np.full(steps, self.level)

    def update(self, new_value):
        if self.level is None:
            self.level = new_value
        else:
            self.level = self.alpha * new_value + (1 - self.alpha) * self.level
```

### 21.3 LSTM时序预测

```python
import torch
import torch.nn as nn

class LSTMPredictor(nn.Module):
    def __init__(self, input_dim, hidden_dim, num_layers=2):
        super().__init__()
        self.lstm = nn.LSTM(
            input_dim, hidden_dim,
            num_layers, batch_first=True
        )
        self.fc = nn.Linear(hidden_dim, input_dim)

    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        # 只取最后一个时间步
        last_output = lstm_out[:, -1, :]
        prediction = self.fc(last_output)
        return prediction

    def predict_sequence(self, x, steps):
        predictions = []
        current = x

        for _ in range(steps):
            pred = self.forward(current)
            predictions.append(pred)
            # 将预测结果加入输入序列
            current = torch.cat([current[:, 1:, :], pred.unsqueeze(1)], dim=1)

        return torch.stack(predictions, dim=1)
```

### 21.4 注意力机制预测

```python
class AttentionPredictor(nn.Module):
    def __init__(self, input_dim, hidden_dim, num_heads=4):
        super().__init__()
        self.attention = nn.MultiheadAttention(
            hidden_dim, num_heads, batch_first=True
        )
        self.input_proj = nn.Linear(input_dim, hidden_dim)
        self.output_proj = nn.Linear(hidden_dim, input_dim)

    def forward(self, x):
        # x: (batch, seq_len, input_dim)
        x = self.input_proj(x)

        # 自注意力
        attn_out, _ = self.attention(x, x, x)

        # 取最后一个时间步
        last_output = attn_out[:, -1, :]

        prediction = self.output_proj(last_output)
        return prediction
```

---

## 第二十二章：异常检测算法

### 22.1 统计异常检测

```python
class StatisticalAnomalyDetector:
    def __init__(self, window_size=100):
        self.window_size = window_size
        self.history = RingBuffer(window_size)

    def fit(self, data):
        for value in data:
            self.history.append(value)

    def score(self, value):
        if len(self.history) < 10:
            return 0.5

        mean = np.mean(self.history)
        std = np.std(self.history)

        if std == 0:
            return 0.0 if value == mean else 1.0

        z_score = np.abs(value - mean) / std
        # 转换为[0,1]的异常分数
        anomaly_score = 1.0 / (1.0 + np.exp(-z_score + 3))

        return anomaly_score

    def update(self, value):
        self.history.append(value)
```

### 22.2 孤立森林

```python
from sklearn.ensemble import IsolationForest

class IsolationForestDetector:
    def __init__(self, contamination=0.1):
        self.model = IsolationForest(
            contamination=contamination,
            random_state=42
        )
        self.is_fitted = False

    def fit(self, X):
        self.model.fit(X)
        self.is_fitted = True

    def score(self, x):
        if not self.is_fitted:
            return 0.5
        # 返回异常分数（越大越异常）
        return -self.model.score_samples([x])[0]

    def predict(self, x):
        if not self.is_fitted:
            return 1  # 正常
        return self.model.predict([x])[0]
```

### 22.3 自编码器异常检测

```python
class AutoencoderDetector(nn.Module):
    def __init__(self, input_dim, hidden_dim):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU()
        )
        self.decoder = nn.Sequential(
            nn.Linear(hidden_dim // 2, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, input_dim)
        )

    def forward(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded

    def score(self, x):
        reconstruction = self.forward(x)
        error = torch.mean((x - reconstruction) ** 2)
        return error.item()
```

### 22.4 时序异常检测

```python
class TimeSeriesAnomalyDetector:
    def __init__(self, prediction_model, threshold=3.0):
        self.prediction_model = prediction_model
        self.threshold = threshold
        self.error_history = RingBuffer(1000)

    def detect(self, series):
        # 预测下一个值
        prediction = self.prediction_model.predict(series)
        actual = series[-1]

        # 计算预测误差
        error = np.abs(prediction - actual)

        # 基于历史误差分布判断异常
        if len(self.error_history) > 100:
            mean_error = np.mean(self.error_history)
            std_error = np.std(self.error_history)

            if std_error > 0:
                z_score = (error - mean_error) / std_error
                is_anomaly = z_score > self.threshold
            else:
                is_anomaly = error > mean_error * 2
        else:
            is_anomaly = False

        self.error_history.append(error)

        return {
            'is_anomaly': is_anomaly,
            'error': error,
            'prediction': prediction,
            'actual': actual
        }
```

---

## 第二十三章：资源控制算法

### 23.1 CPU限制算法

```python
import time
import psutil

class CPUController:
    def __init__(self, max_cpu_percent=20):
        self.max_cpu_percent = max_cpu_percent
        self.process = psutil.Process()

    def limit_cpu(self, task_func, *args, **kwargs):
        start_time = time.time()
        result = task_func(*args, **kwargs)
        end_time = time.time()

        # 计算实际CPU时间
        cpu_times = self.process.cpu_times()
        cpu_seconds = cpu_times.user + cpu_times.system

        # 计算应该等待的时间
        elapsed = end_time - start_time
        target_cpu_time = elapsed * (self.max_cpu_percent / 100)

        if cpu_seconds > target_cpu_time:
            sleep_time = cpu_seconds / (self.max_cpu_percent / 100) - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

        return result

    def adaptive_sleep(self):
        # 根据当前CPU使用率动态调整休眠时间
        current_cpu = self.process.cpu_percent()
        if current_cpu > self.max_cpu_percent:
            sleep_time = (current_cpu - self.max_cpu_percent) / 100
            time.sleep(sleep_time)
```

### 23.2 内存限制算法

```python
class MemoryController:
    def __init__(self, max_memory_percent=20):
        self.max_memory_percent = max_memory_percent
        self.total_memory = psutil.virtual_memory().total
        self.max_bytes = self.total_memory * (max_memory_percent / 100)

    def check_memory(self):
        current = psutil.Process().memory_info().rss
        return current / self.max_bytes

    def enforce_limit(self):
        usage_ratio = self.check_memory()
        if usage_ratio > 1.0:
            # 内存超限，触发清理
            self.emergency_cleanup()
        elif usage_ratio > 0.8:
            # 接近上限，主动清理
            self.proactive_cleanup()

    def emergency_cleanup(self):
        # 紧急清理：释放所有可释放的内存
        import gc
        gc.collect()

        # 清空短期记忆
        if hasattr(self, 'short_term_memory'):
            self.short_term_memory.clear()

    def proactive_cleanup(self):
        # 主动清理：删除低价值数据
        if hasattr(self, 'memory'):
            self.memory.cleanup_low_value(ratio=0.2)
```

### 23.3 自适应采样频率

```python
class AdaptiveSampler:
    def __init__(self, base_frequency=1.0):
        self.base_frequency = base_frequency
        self.current_frequency = base_frequency
        self.error_history = []

    def adjust_frequency(self, current_error):
        self.error_history.append(current_error)

        if len(self.error_history) < 10:
            return self.current_frequency

        # 如果误差大，增加采样频率
        recent_error = np.mean(self.error_history[-10:])
        if recent_error > 0.5:
            self.current_frequency = min(10.0, self.current_frequency * 1.2)
        # 如果误差小，降低采样频率以节省资源
        elif recent_error < 0.1:
            self.current_frequency = max(0.1, self.current_frequency * 0.8)

        return self.current_frequency
```

---

## 第二十四章：进化评估算法

### 24.1 预测精度进化评估

```python
class PrecisionEvolutionTracker:
    def __init__(self, window_size=1000):
        self.window_size = window_size
        self.error_history = RingBuffer(window_size)
        self.trend_history = []

    def add_error(self, error):
        self.error_history.append(error)

    def evaluate_trend(self):
        if len(self.error_history) < 100:
            return {'trend': 'insufficient_data', 'slope': 0}

        # 线性回归分析误差趋势
        x = np.arange(len(self.error_history))
        y = np.array(self.error_history)

        slope, intercept = np.polyfit(x, y, 1)

        if slope < -0.001:
            trend = 'improving'
        elif slope > 0.001:
            trend = 'degrading'
        else:
            trend = 'stable'

        return {
            'trend': trend,
            'slope': slope,
            'current_error': np.mean(self.error_history[-100:]),
            'historical_error': np.mean(self.error_history[:100])
        }

    def should_restructure(self):
        eval_result = self.evaluate_trend()

        # 如果误差持续增大，需要重构
        if eval_result['trend'] == 'degrading':
            return True

        # 如果误差长期稳定且较高，需要重构
        if (eval_result['trend'] == 'stable' and
            eval_result['current_error'] > 0.3):
            return True

        return False
```

### 24.2 认知广度进化评估

```python
class CoverageEvolutionTracker:
    def __init__(self):
        self.dimensions_covered = set()
        self.total_dimensions = 100  # 假设总维度
        self.coverage_history = []

    def update_coverage(self, new_dimensions):
        self.dimensions_covered.update(new_dimensions)
        coverage = len(self.dimensions_covered) / self.total_dimensions
        self.coverage_history.append(coverage)

    def evaluate_growth(self):
        if len(self.coverage_history) < 10:
            return {'growth_rate': 0, 'status': 'insufficient'}

        recent = np.mean(self.coverage_history[-10:])
        older = np.mean(self.coverage_history[:10])

        growth_rate = (recent - older) / max(older, 0.01)

        if growth_rate > 0.1:
            status = 'rapid_growth'
        elif growth_rate > 0.01:
            status = 'steady_growth'
        elif growth_rate > -0.01:
            status = 'plateau'
        else:
            status = 'declining'

        return {
            'growth_rate': growth_rate,
            'status': status,
            'current_coverage': self.coverage_history[-1]
        }
```

### 24.3 能效进化评估

```python
class EfficiencyEvolutionTracker:
    def __init__(self):
        self.cpu_history = []
        self.memory_history = []
        self.time_history = []

    def add_metrics(self, cpu, memory, inference_time):
        self.cpu_history.append(cpu)
        self.memory_history.append(memory)
        self.time_history.append(inference_time)

    def evaluate_efficiency(self):
        if len(self.cpu_history) < 100:
            return {'status': 'insufficient'}

        recent_cpu = np.mean(self.cpu_history[-100:])
        older_cpu = np.mean(self.cpu_history[:100])

        recent_memory = np.mean(self.memory_history[-100:])
        older_memory = np.mean(self.memory_history[:100])

        recent_time = np.mean(self.time_history[-100:])
        older_time = np.mean(self.time_history[:100])

        cpu_trend = (recent_cpu - older_cpu) / max(older_cpu, 0.01)
        memory_trend = (recent_memory - older_memory) / max(older_memory, 0.01)
        time_trend = (recent_time - older_time) / max(older_time, 0.01)

        # 趋势为负表示效率提升
        if cpu_trend < -0.05 and memory_trend < -0.05:
            status = 'improving'
        elif cpu_trend > 0.05 or memory_trend > 0.05:
            status = 'degrading'
        else:
            status = 'stable'

        return {
            'status': status,
            'cpu_trend': cpu_trend,
            'memory_trend': memory_trend,
            'time_trend': time_trend
        }
```

### 24.4 综合进化评估

```python
class EvolutionEvaluator:
    def __init__(self):
        self.precision_tracker = PrecisionEvolutionTracker()
        self.coverage_tracker = CoverageEvolutionTracker()
        self.efficiency_tracker = EfficiencyEvolutionTracker()

    def evaluate(self):
        precision = self.precision_tracker.evaluate_trend()
        coverage = self.coverage_tracker.evaluate_growth()
        efficiency = self.efficiency_tracker.evaluate_efficiency()

        # 综合评估
        scores = []

        if precision['trend'] == 'improving':
            scores.append(1.0)
        elif precision['trend'] == 'stable':
            scores.append(0.5)
        else:
            scores.append(0.0)

        if coverage['status'] in ['rapid_growth', 'steady_growth']:
            scores.append(1.0)
        elif coverage['status'] == 'plateau':
            scores.append(0.5)
        else:
            scores.append(0.0)

        if efficiency['status'] == 'improving':
            scores.append(1.0)
        elif efficiency['status'] == 'stable':
            scores.append(0.5)
        else:
            scores.append(0.0)

        overall_score = np.mean(scores)

        return {
            'overall_score': overall_score,
            'precision': precision,
            'coverage': coverage,
            'efficiency': efficiency,
            'should_restructure': precision['trend'] == 'degrading'
        }
```

---

