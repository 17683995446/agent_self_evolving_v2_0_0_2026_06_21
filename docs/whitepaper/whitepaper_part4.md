## 第四卷：工程实现与代码架构

---

## 第二十五章：技术栈选择

### 25.1 编程语言

**主语言：Python 3.10+**

选择Python的理由：
- 丰富的科学计算生态（NumPy, SciPy, Pandas）
- 成熟的机器学习框架（PyTorch, scikit-learn）
- 跨平台兼容性（Windows, Linux, macOS）
- 开发效率高，适合快速迭代
- 系统监控库完善（psutil等）

**辅助语言：C++（可选）**

对于性能关键的部分，可以使用C++扩展：
- 高频数据采集
- 核心预测算法
- 内存管理

### 25.2 核心依赖库

**数据处理**：
- NumPy: 数值计算基础
- Pandas: 结构化数据处理
- SciPy: 科学计算

**机器学习**：
- PyTorch: 深度学习框架
- scikit-learn: 传统机器学习算法
- statsmodels: 时间序列分析

**系统监控**：
- psutil: 系统资源监控
- pyinotify: Linux文件系统事件
- watchdog: 跨平台文件监控

**数据存储**：
- SQLite3: 本地结构化数据存储
- JSON: 配置文件和轻量数据
- pickle: Python对象序列化

**并发与异步**：
- threading: 多线程
- asyncio: 异步IO
- queue: 线程安全队列

**日志与监控**：
- logging: 标准日志
- prometheus_client: 指标暴露（可选）

### 25.3 开发工具

- 版本控制：Git
- 包管理：pip + requirements.txt
- 虚拟环境：venv
- 代码质量：flake8, black, mypy
- 测试：pytest

---

## 第二十六章：项目结构

### 26.1 目录结构

```
self_evolving_agent/
├── agent/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── agent.py              # Agent主类
│   │   ├── config.py             # 配置管理
│   │   └── constants.py          # 常量定义
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── perception/           # 环境感知模块
│   │   │   ├── __init__.py
│   │   │   ├── system_monitor.py
│   │   │   ├── log_collector.py
│   │   │   ├── file_watcher.py
│   │   │   └── state_vector.py
│   │   ├── drive/                # 驱力引擎模块
│   │   │   ├── __init__.py
│   │   │   ├── safe_drive.py
│   │   │   ├── gain_drive.py
│   │   │   ├── eff_drive.py
│   │   │   └── weight_adjuster.py
│   │   ├── task/                 # 自主目标生成模块
│   │   │   ├── __init__.py
│   │   │   ├── task_generator.py
│   │   │   ├── task_evaluator.py
│   │   │   ├── task_selector.py
│   │   │   └── task_pool.py
│   │   ├── prediction/           # 多层预测模型
│   │   │   ├── __init__.py
│   │   │   ├── low_level.py
│   │   │   ├── mid_level.py
│   │   │   ├── high_level.py
│   │   │   └── integrator.py
│   │   ├── error/                # 误差评估模块
│   │   │   ├── __init__.py
│   │   │   ├── error_calculator.py
│   │   │   ├── error_analyzer.py
│   │   │   └── feedback_generator.py
│   │   ├── optimization/         # 模型优化器
│   │   │   ├── __init__.py
│   │   │   ├── micro_optimizer.py
│   │   │   ├── restructurer.py
│   │   │   └── snapshot_manager.py
│   │   └── memory/               # 记忆与复盘模块
│   │       ├── __init__.py
│   │       ├── short_term.py
│   │       ├── long_term.py
│   │       ├── offline_review.py
│   │       └── value_assessor.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── ring_buffer.py
│   │   ├── math_utils.py
│   │   ├── logging_utils.py
│   │   └── file_utils.py
│   └── interfaces/
│       ├── __init__.py
│       └── api.py                # 外部接口
├── data/
│   ├── memory/                   # 长期记忆存储
│   ├── snapshots/                # 模型快照
│   ├── logs/                     # 运行日志
│   └── config/                   # 配置文件
├── tests/
│   ├── __init__.py
│   ├── test_perception.py
│   ├── test_drive.py
│   ├── test_task.py
│   ├── test_prediction.py
│   ├── test_error.py
│   ├── test_optimization.py
│   └── test_memory.py
├── scripts/
│   ├── install.sh
│   ├── start.sh
│   └── stop.sh
├── requirements.txt
├── setup.py
├── README.md
└── main.py                       # 入口文件
```

### 26.2 核心类设计

**Agent主类**：

```python
class SelfEvolvingAgent:
    def __init__(self, config):
        self.config = config
        self.perception = PerceptionModule(config)
        self.drive_engine = DriveEngine(config)
        self.task_generator = TaskGenerator(config)
        self.prediction_model = MultiLevelPredictor(config)
        self.error_evaluator = ErrorEvaluator(config)
        self.optimizer = DualModeOptimizer(config)
        self.memory = MemoryModule(config)

        self.running = False
        self.current_task = None

    def start(self):
        self.running = True
        self._run_main_loop()

    def stop(self):
        self.running = False

    def _run_main_loop(self):
        while self.running:
            # 1. 感知环境
            state = self.perception.sense()

            # 2. 计算驱力
            gaps = self.drive_engine.compute_gaps(state)

            # 3. 生成并选择任务
            tasks = self.task_generator.generate(gaps)
            task = self.task_generator.select(tasks)

            # 4. 生成预测
            prediction = self.prediction_model.predict(state)

            # 5. 执行任务
            self.current_task = task
            task.execute()

            # 6. 评估误差
            next_state = self.perception.sense()
            error = self.error_evaluator.evaluate(prediction, next_state)

            # 7. 优化模型
            self.optimizer.update(error)

            # 8. 保存记忆
            self.memory.save_experience(state, task, error)

            # 9. 检查离线复盘
            if self._should_review():
                self.memory.offline_review()

    def _should_review(self):
        # 检查是否满足离线复盘条件
        return (self.perception.is_idle() or
                self.memory.time_since_last_review() > 3600)
```

---

## 第二十七章：核心模块实现

### 27.1 环境感知模块实现

```python
import psutil
import time
from dataclasses import dataclass
from typing import List, Dict
from collections import deque

@dataclass
class CPUState:
    usage_percent: float
    per_cpu_percent: List[float]
    load_average: tuple
    user_time: float
    system_time: float

@dataclass
class MemoryState:
    total: int
    available: int
    used: int
    percent: float
    swap_total: int
    swap_used: int

@dataclass
class EnvironmentState:
    timestamp: float
    cpu: CPUState
    memory: MemoryState
    disk: 'DiskState'
    network: 'NetworkState'
    processes: 'ProcessState'
    logs: 'LogState'
    files: 'FileState'
    agent: 'AgentState'

class PerceptionModule:
    def __init__(self, config):
        self.config = config
        self.history = deque(maxlen=config.history_size)
        self.log_collector = LogCollector(config)
        self.file_watcher = FileWatcher(config)

    def sense(self) -> EnvironmentState:
        state = EnvironmentState(
            timestamp=time.time(),
            cpu=self._collect_cpu(),
            memory=self._collect_memory(),
            disk=self._collect_disk(),
            network=self._collect_network(),
            processes=self._collect_processes(),
            logs=self.log_collector.collect(),
            files=self.file_watcher.get_changes(),
            agent=self._collect_agent_state()
        )
        self.history.append(state)
        return state

    def _collect_cpu(self) -> CPUState:
        return CPUState(
            usage_percent=psutil.cpu_percent(interval=0.1),
            per_cpu_percent=psutil.cpu_percent(percpu=True),
            load_average=os.getloadavg(),
            user_time=psutil.cpu_times().user,
            system_time=psutil.cpu_times().system
        )

    def _collect_memory(self) -> MemoryState:
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return MemoryState(
            total=mem.total,
            available=mem.available,
            used=mem.used,
            percent=mem.percent / 100.0,
            swap_total=swap.total,
            swap_used=swap.used
        )

    def _collect_disk(self):
        # 实现磁盘状态采集
        pass

    def _collect_network(self):
        # 实现网络状态采集
        pass

    def _collect_processes(self):
        # 实现进程状态采集
        pass

    def _collect_agent_state(self):
        # 实现Agent自身状态采集
        pass

    def is_idle(self) -> bool:
        # 判断系统是否空闲
        if len(self.history) < 10:
            return False
        recent_cpu = [s.cpu.usage_percent for s in list(self.history)[-10:]]
        return np.mean(recent_cpu) < 5.0
```

### 27.2 驱力引擎实现

```python
class DriveEngine:
    def __init__(self, config):
        self.config = config
        self.safe_drive = SafeDrive(config)
        self.gain_drive = GainDrive(config)
        self.eff_drive = EffDrive(config)
        self.weight_adjuster = WeightAdjuster(config)

    def compute_gaps(self, state: EnvironmentState) -> DriveGaps:
        # 计算各驱力
        safe_reward = self.safe_drive.calculate(state)
        gain_reward = self.gain_drive.calculate(state)
        eff_reward = self.eff_drive.calculate(state)

        # 动态调整权重
        weights = self.weight_adjuster.adjust(state, self.config.base_weights)

        # 计算总奖励和缺口
        total_reward = (
            weights[0] * safe_reward +
            weights[1] * gain_reward +
            weights[2] * eff_reward
        )

        return DriveGaps(
            safe=1.0 - safe_reward,
            gain=1.0 - gain_reward,
            eff=1.0 - eff_reward,
            total=1.0 - total_reward,
            weights=weights
        )

class SafeDrive:
    def __init__(self, config):
        self.config = config
        self.anomaly_detector = IsolationForestDetector()

    def calculate(self, state: EnvironmentState) -> float:
        # 异常检测
        anomaly_score = self._detect_anomalies(state)

        # 资源风险评估
        resource_risk = self._assess_resource_risk(state)

        # 未知状态评估
        unknown_score = self._assess_unknown(state)

        # 安全事件评估
        security_score = self._assess_security(state)

        # 综合安全驱力
        safe_reward = 1.0 - (
            0.3 * anomaly_score +
            0.3 * resource_risk +
            0.2 * unknown_score +
            0.2 * security_score
        )

        return max(0.0, min(1.0, safe_reward))

    def _detect_anomalies(self, state):
        # 实现异常检测
        pass

    def _assess_resource_risk(self, state):
        # 实现资源风险评估
        pass

    def _assess_unknown(self, state):
        # 实现未知状态评估
        pass

    def _assess_security(self, state):
        # 实现安全事件评估
        pass
```

### 27.3 任务生成模块实现

```python
class TaskGenerator:
    def __init__(self, config):
        self.config = config
        self.task_pool = TaskPool(config)
        self.evaluator = TaskEvaluator(config)
        self.exploration_rate = config.exploration_rate

    def generate(self, gaps: DriveGaps) -> List[Task]:
        tasks = []

        # 基于缺口生成任务
        if gaps.safe > self.config.safe_threshold:
            tasks.extend(self._generate_safe_tasks(gaps.safe))

        if gaps.gain > self.config.gain_threshold:
            tasks.extend(self._generate_gain_tasks(gaps.gain))

        if gaps.eff > self.config.eff_threshold:
            tasks.extend(self._generate_eff_tasks(gaps.eff))

        # 添加探索任务
        if random.random() < 0.1:
            tasks.extend(self._generate_exploration_tasks())

        # 更新任务池
        self.task_pool.update(tasks)

        return self.task_pool.get_all()

    def select(self, tasks: List[Task]) -> Task:
        if not tasks:
            return self._default_task()

        # 评估所有任务
        scored_tasks = [(task, self.evaluator.evaluate(task)) for task in tasks]
        scored_tasks.sort(key=lambda x: x[1], reverse=True)

        # 探索-利用选择
        if random.random() < (1 - self.exploration_rate):
            return scored_tasks[0][0]  # 利用
        else:
            return self._exploration_select(scored_tasks)  # 探索

    def _generate_safe_tasks(self, gap):
        return [
            Task("risk_prediction", priority=gap),
            Task("anomaly_detection", priority=gap * 0.8),
            Task("state_monitoring", priority=gap * 0.6),
        ]

    def _generate_gain_tasks(self, gap):
        return [
            Task("unknown_exploration", priority=gap),
            Task("feature_testing", priority=gap * 0.7),
            Task("pattern_mining", priority=gap * 0.6),
        ]

    def _generate_eff_tasks(self, gap):
        return [
            Task("model_pruning", priority=gap),
            Task("redundancy_cleanup", priority=gap * 0.8),
            Task("frequency_optimization", priority=gap * 0.6),
        ]

    def _generate_exploration_tasks(self):
        # 随机生成探索性任务
        pass

    def _exploration_select(self, scored_tasks):
        # 按信息价值加权随机选择
        pass

    def _default_task(self):
        # 默认任务：继续监控
        return Task("state_monitoring", priority=0.5)
```

### 27.4 预测模型实现

```python
import torch
import torch.nn as nn

class MultiLevelPredictor:
    def __init__(self, config):
        self.config = config
        self.low_level = LowLevelModel(config)
        self.mid_level = MidLevelModel(config)
        self.high_level = HighLevelModel(config)
        self.integrator = PredictionIntegrator(config)

    def predict(self, state: EnvironmentState) -> Prediction:
        # 底层预测
        low_pred = self.low_level.predict(state)

        # 中层预测（基于底层）
        mid_pred = self.mid_level.predict(low_pred)

        # 高层预测（基于中层）
        high_pred = self.high_level.predict(mid_pred)

        # 整合预测
        integrated = self.integrator.integrate(low_pred, mid_pred, high_pred)

        return Prediction(
            low=low_pred,
            mid=mid_pred,
            high=high_pred,
            integrated=integrated
        )

    def update(self, error: ErrorSignal):
        # 更新各层模型
        self.low_level.update(error.low)
        self.mid_level.update(error.mid)
        self.high_level.update(error.high)

class LowLevelModel:
    def __init__(self, config):
        self.config = config
        self.model = self._build_model()
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001)

    def _build_model(self):
        return nn.Sequential(
            nn.Linear(self.config.state_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, self.config.state_dim)
        )

    def predict(self, state):
        x = torch.tensor(state.vector, dtype=torch.float32)
        with torch.no_grad():
            pred = self.model(x)
        return pred.numpy()

    def update(self, error):
        # 在线更新
        pass
```

### 27.5 误差评估实现

```python
class ErrorEvaluator:
    def __init__(self, config):
        self.config = config
        self.error_history = RingBuffer(config.error_history_size)

    def evaluate(self, prediction: Prediction, actual: EnvironmentState) -> ErrorSignal:
        # 计算各层误差
        low_error = self._compute_error(prediction.low, actual.vector)
        mid_error = self._compute_error(prediction.mid, actual.vector)
        high_error = self._compute_error(prediction.high, actual.vector)

        # 标准化误差
        low_error_norm = self._normalize(low_error)
        mid_error_norm = self._normalize(mid_error)
        high_error_norm = self._normalize(high_error)

        # 生成反馈
        feedback = self._generate_feedback(low_error_norm)

        return ErrorSignal(
            low=low_error_norm,
            mid=mid_error_norm,
            high=high_error_norm,
            total=np.mean([low_error_norm, mid_error_norm, high_error_norm]),
            feedback=feedback
        )

    def _compute_error(self, prediction, actual):
        return np.mean((prediction - actual) ** 2)

    def _normalize(self, error):
        # 基于历史误差标准化
        if len(self.error_history) < 100:
            return error
        max_error = max(self.error_history)
        return error / max(max_error, 1e-6)

    def _generate_feedback(self, error):
        if error < 0.1:
            return Feedback.POSITIVE
        elif error > 0.5:
            return Feedback.NEGATIVE
        else:
            return Feedback.NEUTRAL
```

### 27.6 模型优化器实现

```python
class DualModeOptimizer:
    def __init__(self, config):
        self.config = config
        self.micro_optimizer = MicroOptimizer(config)
        self.restructurer = Restructurer(config)
        self.snapshot_manager = SnapshotManager(config)
        self.mode = OptimizationMode.MICRO

    def update(self, error: ErrorSignal):
        if self.mode == OptimizationMode.MICRO:
            self.micro_optimizer.update(error)

            # 检查是否需要切换到重构模式
            if self._should_restructure(error):
                self._enter_restructure_mode()
        else:
            self.restructurer.update(error)

            # 重构完成或失败，回到微修正模式
            if self.restructurer.is_done():
                self._exit_restructure_mode()

    def _should_restructure(self, error):
        # 持续高误差或长期无提升
        recent_errors = self.micro_optimizer.get_recent_errors(100)
        if len(recent_errors) < 100:
            return False

        mean_error = np.mean(recent_errors)
        if mean_error > self.config.restructure_threshold:
            return True

        # 检查是否长期无提升
        if self._plateau_detected(recent_errors):
            return True

        return False

    def _plateau_detected(self, errors):
        # 线性回归检测趋势
        x = np.arange(len(errors))
        slope, _ = np.polyfit(x, errors, 1)
        return abs(slope) < 0.001  # 几乎无变化

    def _enter_restructure_mode(self):
        self.snapshot_manager.save_snapshot()
        self.mode = OptimizationMode.RESTRUCTURE
        self.restructurer.start()

    def _exit_restructure_mode(self):
        if self.restructurer.success:
            self.snapshot_manager.clear_snapshot()
        else:
            self.snapshot_manager.rollback()
        self.mode = OptimizationMode.MICRO
```

### 27.7 记忆模块实现

```python
import sqlite3
import json
from datetime import datetime

class MemoryModule:
    def __init__(self, config):
        self.config = config
        self.short_term = ShortTermMemory(config)
        self.long_term = LongTermMemory(config)
        self.offline_reviewer = OfflineReviewer(config)
        self.last_review_time = time.time()

    def save_experience(self, state, task, error):
        experience = Experience(
            timestamp=time.time(),
            state=state,
            task=task,
            error=error
        )

        # 保存到短期记忆
        self.short_term.add(experience)

        # 评估价值
        value = self._assess_value(experience)

        # 高价值经验保存到长期记忆
        if value > self.config.memory_threshold:
            self.long_term.store(experience)

    def offline_review(self):
        if not self._should_review():
            return

        self.offline_reviewer.review(self.short_term, self.long_term)
        self.last_review_time = time.time()

    def _should_review(self):
        elapsed = time.time() - self.last_review_time
        return elapsed > self.config.review_interval

    def _assess_value(self, experience):
        # 基于信息增益、预测难度、稀有度评估价值
        pass

class ShortTermMemory:
    def __init__(self, config):
        self.config = config
        self.buffer = RingBuffer(config.short_term_size)

    def add(self, experience):
        self.buffer.append(experience)

    def sample(self, batch_size):
        return random.sample(list(self.buffer), min(batch_size, len(self.buffer)))

class LongTermMemory:
    def __init__(self, config):
        self.config = config
        self.db_path = config.memory_db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS experiences (
                id INTEGER PRIMARY KEY,
                timestamp REAL,
                state TEXT,
                task TEXT,
                error REAL,
                value REAL
            )
        ''')
        conn.commit()
        conn.close()

    def store(self, experience):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            'INSERT INTO experiences (timestamp, state, task, error, value) VALUES (?, ?, ?, ?, ?)',
            (experience.timestamp,
             json.dumps(experience.state.to_dict()),
             experience.task.name,
             experience.error.total,
             experience.value)
        )
        conn.commit()
        conn.close()

    def retrieve(self, query, k=100):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            'SELECT * FROM experiences ORDER BY value DESC LIMIT ?',
            (k,)
        )
        results = cursor.fetchall()
        conn.close()
        return results
```

---

## 第二十八章：并发与线程设计

### 28.1 线程架构

系统采用多线程架构，不同模块运行在不同线程中：

```python
import threading
import queue

class AgentThreadManager:
    def __init__(self, agent):
        self.agent = agent
        self.threads = {}
        self.queues = {}

    def start(self):
        # 启动感知线程
        self.queues['perception'] = queue.Queue()
        self.threads['perception'] = threading.Thread(
            target=self._perception_loop,
            daemon=True
        )
        self.threads['perception'].start()

        # 启动预测线程
        self.queues['prediction'] = queue.Queue()
        self.threads['prediction'] = threading.Thread(
            target=self._prediction_loop,
            daemon=True
        )
        self.threads['prediction'].start()

        # 启动任务执行线程
        self.queues['execution'] = queue.Queue()
        self.threads['execution'] = threading.Thread(
            target=self._execution_loop,
            daemon=True
        )
        self.threads['execution'].start()

        # 启动优化线程
        self.queues['optimization'] = queue.Queue()
        self.threads['optimization'] = threading.Thread(
            target=self._optimization_loop,
            daemon=True
        )
        self.threads['optimization'].start()

        # 启动离线复盘线程
        self.threads['review'] = threading.Thread(
            target=self._review_loop,
            daemon=True
        )
        self.threads['review'].start()

    def _perception_loop(self):
        while self.agent.running:
            state = self.agent.perception.sense()
            self.queues['prediction'].put(state)
            time.sleep(1.0)  # 每秒感知一次

    def _prediction_loop(self):
        while self.agent.running:
            try:
                state = self.queues['prediction'].get(timeout=1.0)
                prediction = self.agent.prediction_model.predict(state)
                self.queues['execution'].put((state, prediction))
            except queue.Empty:
                continue

    def _execution_loop(self):
        while self.agent.running:
            try:
                state, prediction = self.queues['execution'].get(timeout=1.0)

                # 计算驱力
                gaps = self.agent.drive_engine.compute_gaps(state)

                # 生成并选择任务
                tasks = self.agent.task_generator.generate(gaps)
                task = self.agent.task_generator.select(tasks)

                # 执行任务
                task.execute()

                # 获取新状态
                next_state = self.agent.perception.sense()

                # 计算误差
                error = self.agent.error_evaluator.evaluate(prediction, next_state)

                # 发送给优化线程
                self.queues['optimization'].put(error)

            except queue.Empty:
                continue

    def _optimization_loop(self):
        while self.agent.running:
            try:
                error = self.queues['optimization'].get(timeout=1.0)
                self.agent.optimizer.update(error)
            except queue.Empty:
                continue

    def _review_loop(self):
        while self.agent.running:
            time.sleep(600)  # 每10分钟检查一次
            if self.agent.perception.is_idle():
                self.agent.memory.offline_review()
```

### 28.2 线程安全

```python
import threading

class ThreadSafeState:
    def __init__(self):
        self._lock = threading.RLock()
        self._state = None

    def get(self):
        with self._lock:
            return self._state

    def set(self, state):
        with self._lock:
            self._state = state

class ThreadSafeQueue:
    def __init__(self, maxsize=100):
        self._queue = queue.Queue(maxsize=maxsize)
        self._lock = threading.Lock()

    def put(self, item, block=True, timeout=None):
        with self._lock:
            if self._queue.full():
                self._queue.get()  # 丢弃最旧的消息
            self._queue.put(item, block, timeout)

    def get(self, block=True, timeout=None):
        return self._queue.get(block, timeout)
```

---

## 第二十九章：配置管理

### 29.1 配置文件

```json
{
    "agent": {
        "name": "SelfEvolvingAgent",
        "version": "1.0.0"
    },
    "resources": {
        "max_cpu_percent": 20,
        "max_memory_percent": 20,
        "max_disk_gb": 10
    },
    "drives": {
        "base_weights": {
            "safe": 0.4,
            "gain": 0.4,
            "eff": 0.2
        },
        "thresholds": {
            "safe": 0.3,
            "gain": 0.3,
            "eff": 0.3
        }
    },
    "tasks": {
        "exploration_rate": 0.3,
        "max_pool_size": 100,
        "default_task": "state_monitoring"
    },
    "prediction": {
        "low_level": {
            "hidden_dim": 64,
            "learning_rate": 0.001
        },
        "mid_level": {
            "hidden_dim": 128,
            "learning_rate": 0.001
        },
        "high_level": {
            "hidden_dim": 256,
            "learning_rate": 0.0005
        }
    },
    "optimization": {
        "restructure_threshold": 0.5,
        "max_restructure_iterations": 3,
        "micro_learning_rate": 0.001
    },
    "memory": {
        "short_term_size": 10000,
        "memory_threshold": 0.5,
        "review_interval": 3600,
        "max_storage_gb": 10
    },
    "safety": {
        "forbidden_paths": [
            "/sys",
            "/proc",
            "/dev",
            "/boot"
        ],
        "max_exploration_failures": 5,
        "snapshot_retention": 10
    }
}
```

### 29.2 配置加载

```python
import json
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class AgentConfig:
    name: str
    version: str
    max_cpu_percent: float
    max_memory_percent: float
    max_disk_gb: float
    base_weights: tuple
    thresholds: dict
    exploration_rate: float
    max_pool_size: int
    restructure_threshold: float
    max_restructure_iterations: int
    short_term_size: int
    memory_threshold: float
    review_interval: float
    forbidden_paths: List[str]
    max_exploration_failures: int

    @classmethod
    def from_file(cls, path: str):
        with open(path, 'r') as f:
            config = json.load(f)

        return cls(
            name=config['agent']['name'],
            version=config['agent']['version'],
            max_cpu_percent=config['resources']['max_cpu_percent'],
            max_memory_percent=config['resources']['max_memory_percent'],
            max_disk_gb=config['resources']['max_disk_gb'],
            base_weights=(
                config['drives']['base_weights']['safe'],
                config['drives']['base_weights']['gain'],
                config['drives']['base_weights']['eff']
            ),
            thresholds=config['drives']['thresholds'],
            exploration_rate=config['tasks']['exploration_rate'],
            max_pool_size=config['tasks']['max_pool_size'],
            restructure_threshold=config['optimization']['restructure_threshold'],
            max_restructure_iterations=config['optimization']['max_restructure_iterations'],
            short_term_size=config['memory']['short_term_size'],
            memory_threshold=config['memory']['memory_threshold'],
            review_interval=config['memory']['review_interval'],
            forbidden_paths=config['safety']['forbidden_paths'],
            max_exploration_failures=config['safety']['max_exploration_failures']
        )
```

---

## 第三十章：日志与监控

### 30.1 日志系统

```python
import logging
from datetime import datetime

class AgentLogger:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger('SelfEvolvingAgent')
        self.logger.setLevel(logging.DEBUG)

        # 文件处理器
        file_handler = logging.FileHandler('data/logs/agent.log')
        file_handler.setLevel(logging.DEBUG)

        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # 格式化
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def log_state(self, state):
        self.logger.debug(f"State: CPU={state.cpu.usage_percent:.1f}%, "
                         f"Memory={state.memory.percent:.1f}%")

    def log_drive(self, gaps):
        self.logger.info(f"Drive gaps: Safe={gaps.safe:.3f}, "
                        f"Gain={gaps.gain:.3f}, Eff={gaps.eff:.3f}")

    def log_task(self, task):
        self.logger.info(f"Selected task: {task.name} (priority={task.priority:.3f})")

    def log_error(self, error):
        self.logger.debug(f"Prediction error: {error.total:.3f}")

    def log_evolution(self, metrics):
        self.logger.info(f"Evolution metrics: {metrics}")
```

### 30.2 监控接口

```python
class AgentMonitor:
    def __init__(self, agent):
        self.agent = agent

    def get_status(self):
        return {
            'running': self.agent.running,
            'current_task': self.agent.current_task.name if self.agent.current_task else None,
            'drive_gaps': self.agent.drive_engine.last_gaps.to_dict(),
            'prediction_error': self.agent.error_evaluator.last_error.total,
            'memory_usage': self.agent.memory.usage(),
            'uptime': time.time() - self.agent.start_time
        }

    def get_metrics(self):
        return {
            'prediction_accuracy': self.agent.error_evaluator.accuracy_history(),
            'task_distribution': self.agent.task_generator.task_history(),
            'resource_usage': self.agent.perception.resource_history(),
            'evolution_score': self.agent.optimizer.evolution_score()
        }
```

---

## 第三十一章：部署与运行

### 31.1 安装脚本

```bash
#!/bin/bash
# install.sh

echo "Installing SelfEvolvingAgent..."

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 创建数据目录
mkdir -p data/memory
mkdir -p data/snapshots
mkdir -p data/logs
mkdir -p data/config

# 复制默认配置
if [ ! -f data/config/agent.json ]; then
    cp config/default.json data/config/agent.json
fi

echo "Installation complete!"
echo "Run 'python main.py' to start the agent."
```

### 31.2 入口文件

```python
#!/usr/bin/env python3
# main.py

import sys
import signal
from agent.core.agent import SelfEvolvingAgent
from agent.core.config import AgentConfig

def main():
    # 加载配置
    config = AgentConfig.from_file('data/config/agent.json')

    # 创建Agent
    agent = SelfEvolvingAgent(config)

    # 信号处理
    def signal_handler(sig, frame):
        print("\nShutting down agent...")
        agent.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 启动Agent
    print(f"Starting {config.name} v{config.version}...")
    agent.start()

if __name__ == '__main__':
    main()
```

### 31.3 系统服务配置

**Linux systemd服务**：

```ini
# /etc/systemd/system/self-evolving-agent.service
[Unit]
Description=Self Evolving Agent
After=network.target

[Service]
Type=simple
User=agent
WorkingDirectory=/opt/self-evolving-agent
ExecStart=/opt/self-evolving-agent/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Windows服务**：

```python
import win32serviceutil
import win32service
import win32event

class AgentService(win32serviceutil.ServiceFramework):
    _svc_name_ = "SelfEvolvingAgent"
    _svc_display_name_ = "Self Evolving Agent"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.agent = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        if self.agent:
            self.agent.stop()
        win32event.SetEvent(self.stop_event)

    def SvcDoRun(self):
        config = AgentConfig.from_file('data/config/agent.json')
        self.agent = SelfEvolvingAgent(config)
        self.agent.start()

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(AgentService)
```

---

