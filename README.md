# 自驱永续进化Agent系统

基于第一性原理设计的自驱永续进化预测修正Agent系统。

## 核心特性

- **预测编码**：多层预测模型 + 自由能最小化（误差驱动学习）
- **三大驱力**：安全（Safe）、收益（Gain）、能效（Eff）
- **15个第一性原理引擎**：预测编码、驱力、学习、探索、记忆、进化、安全、能效、社交、创造、因果、元认知、情感、意识、自由意志
- **LLM 集成**：硅基流动（SiliconFlow）Chat + Embedding API
- **RAG 检索增强**：向量数据库 + 余弦相似度搜索
- **统一架构**：SystemCoordinator（门面）+ UnifiedFirstPrinciplesEngine（编排）+ 4 个职责内聚的协调器

## 架构

```
SelfEvolvingAgent (薄包装层)
    └── SystemCoordinator (门面，声明式接口)
            └── UnifiedFirstPrinciplesEngine (容器 + 周期编排)
                    ├── PerceptionCoordinator  — 感知层：预测编码 + 学习 + 记忆
                    ├── MotivationCoordinator — 动机层：驱力 + 情感 + 进化
                    ├── DecisionCoordinator    — 决策层：元认知 + 意识 + 自由意志 + 安全 + 能效
                    └── ExplorationCoordinator — 探索层：探索 + 创造 + 社交 + 因果
```

### 目录结构

```
self_evolving_agent/
├── agent.py                      # 主入口（SystemCoordinator 薄包装层）
├── __init__.py                   # 包入口，暴露统一架构B接口
├── core/
│   ├── engines/                  # 引擎层（15个第一性原理引擎 + 协调器 + LLM/RAG）
│   ├── infra/                    # 基础设施层（消息总线、配置、日志、序列化等）
│   ├── devops/                   # 运维层（部署、容灾、限流、熔断、工作流等）
│   ├── mlops/                    # MLOps层（模型管理、A/B测试、CI、自动化测试等）
│   ├── data/                     # 数据层（数据管道、版本管理、特征工程等）
│   ├── system_coordinator.py     # 系统协调器（门面）
│   ├── unified_first_principles_engine.py  # 统一引擎（编排）
│   ├── engine_coordinators.py    # 4个职责内聚的协调器
│   ├── llm_service.py            # LLM服务（硅基流动）
│   ├── vector_store.py           # 向量数据库 + RAG
│   └── ...                       # 75个核心模块（扁平结构，向后兼容）
└── modules/                      # 架构A遗留实现（已废弃，保留向后兼容）
```

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 基本使用

```python
from self_evolving_agent import create_default_agent

# 创建默认 Agent（无 LLM）
agent = create_default_agent()

# 设置声明式目标
agent.set_goal("safe", 0.95)
agent.set_goal("gain", 0.8)
agent.set_goal("eff", 0.85)

# 观察环境
result = agent.observe({
    "module_id": "env",
    "predicted": {"value": 0.5},
    "actual": {"value": 0.55},
})

# 执行行动
action = agent.act("explore", context={
    "resources_used": {"cpu": 0.3},
    "output_value": 0.6,
})

# 反思
reflection = agent.reflect()
print(reflection["recommended_action"])
```

### 启用 LLM 能力

```python
from self_evolving_agent import create_default_agent_with_llm

# 使用硅基流动免费模型
agent = create_default_agent_with_llm("your-siliconflow-api-key")

# 自然语言观察
result = agent.observe({"text": "CPU使用率上升到85%，内存使用率60%"})

# 反思报告（自然语言）
reflection = agent.reflect()
print(reflection.get("reflection_text"))
```

### RAG 检索增强

```python
from self_evolving_agent import create_rag_service, create_llm_service

llm = create_llm_service(api_key="your-key")
rag = create_rag_service(llm_service=llm)

# 添加文档
rag.add_document("预测编码是大脑通过生成预测并比较实际输入来减小预测误差的过程。")

# 检索问答
result = rag.query("什么是预测编码？")
print(result["answer"])
print(result["retrieved_docs"])
```

### REST API 服务

```bash
# 启动 Flask API（30个端点）
export SILICONFLOW_API_KEY="your-key"
python main.py

# 或使用 Docker
docker-compose up -d
```

API 端点：
- 基础：`/api/status`, `/api/start`, `/api/stop`, `/api/observe`, `/api/act`, `/api/reflect`, `/api/dashboard`
- LLM：`/api/chat`, `/api/llm/parse`, `/api/llm/create`, `/api/llm/qa`, `/api/llm/code`, `/api/llm/memory/chat`
- RAG：`/api/rag/add`, `/api/rag/query`, `/api/rag/search`, `/api/rag/docs`

## 测试

```bash
# 运行全部测试（26个测试用例）
pytest tests/ -v
```

## 部署

```bash
# Docker 部署
docker-compose up -d

# 或手动部署
pip install -r requirements.txt
python main.py
```

详见 [DEPLOY.md](DEPLOY.md)。

## 技术栈

- **语言**：Python 3.10+
- **依赖**：numpy, flask, flask-cors, gunicorn, psutil
- **LLM**：硅基流动 SiliconFlow API（DeepSeek-V3 / Qwen2.5-7B-Instruct）
- **Embedding**：BAAI/bge-m3（1024维向量）
- **容器化**：Docker + docker-compose

## 设计原则

1. **第一性原理**：每个引擎基于不可再分的基本原理
2. **单一职责**：每个协调器只负责一个领域
3. **门面模式**：SystemCoordinator 统一接口，隐藏内部结构
4. **声明式优于命令式**：设置目标，而非步骤
5. **迪米特法则**：只与直接朋友通信
6. **向后兼容**：重构保留原有接口

## 版本

v2.0.0 — 统一架构 + God Engine 拆分 + 分层重组 + 门面模式
