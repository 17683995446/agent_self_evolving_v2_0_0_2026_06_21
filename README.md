# 自驱永续进化Agent系统

基于第一性原理设计的自驱永续进化预测修正Agent系统。

## 核心特性

- **预测编码**：多层预测模型 + 自由能最小化（误差驱动学习）
- **三大驱力**：安全（Safe）、收益（Gain）、能效（Eff）
- **15个第一性原理引擎**：预测编码、驱力、学习、探索、记忆、进化、安全、能效、社交、创造、因果、元认知、情感、意识、自由意志
- **LLM 集成**：硅基流动（SiliconFlow）Chat + Embedding API
- **RAG 检索增强**：向量数据库 + 余弦相似度搜索
- **统一架构**：SystemCoordinator（门面）+ UnifiedFirstPrinciplesEngine（编排）+ 4 个职责内聚的协调器
- **模块化API**：15个Flask Blueprint，128个REST端点
- **Mixin架构**：14个领域Mixin，单一职责，易于维护

## 架构

```
SelfEvolvingAgent (薄包装层 + 14个Mixin)
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
├── agent.py                      # 主Agent（核心生命周期 + Mixin组合）
├── agent_mixins/                 # 14个领域Mixin（阶段149）
│   ├── environment.py            # 环境管理
│   ├── persistence.py            # 持久化
│   ├── task.py                   # 任务执行
│   ├── code_docs.py              # 代码审查 + 文档生成
│   ├── performance.py            # 性能优化
│   ├── distributed.py            # 分布式支持
│   ├── observability.py          # 可观测性
│   ├── production.py             # 生产部署
│   ├── plugins.py                # 插件系统
│   ├── config.py                 # 配置热更新
│   ├── security.py               # 安全管理
│   ├── recovery.py               # 错误恢复
│   ├── benchmark.py              # 性能基准
│   └── tenants.py                # 多租户
├── core/                         # 核心模块（75+模块）
│   ├── engines/                  # 引擎层（15个第一性原理引擎 + 协调器）
│   ├── system_coordinator.py     # 系统协调器（门面）
│   ├── unified_first_principles_engine.py  # 统一引擎
│   └── ...
└── modules/                      # 遗留模块（向后兼容）

api/                              # REST API（15个Blueprint，阶段148）
├── shared.py                     # 共享状态和辅助函数
├── core_routes.py                # 核心API
├── llm_routes.py                 # LLM API
├── rag_routes.py                 # RAG API
└── ...                           # 12个其他领域Blueprint

tests/                            # 测试套件（2800+测试）
├── conftest.py                   # 共享fixtures
└── test_*.py                     # 按阶段组织的测试文件

pyproject.toml                    # 项目配置（PEP 517/518/621）
```

## 快速开始

### 安装依赖

```bash
# 使用pyproject.toml安装（推荐）
pip install -e .

# 或使用requirements.txt
pip install -r requirements.txt
```

#### 可选依赖

```bash
# 安装 LLM 功能依赖（启用 LLM 对话和 RAG）
pip install -e ".[llm]"

# 安装开发工具（pytest, ruff, mypy）
pip install -e ".[dev]"

# 安装文档构建工具（sphinx）
pip install -e ".[docs]"

# 同时安装所有可选依赖
pip install -e ".[llm,dev,docs]"
```

#### 环境配置

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env，按需设置变量（至少设置 SILICONFLOW_API_KEY 以启用 LLM）
# 完整配置说明见 docs/configuration.md
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

### CLI 命令行工具

系统提供 `agent-cli` 命令行工具（安装后可用，或通过 `python cli.py` 调用）：

```bash
# 初始化向导（新用户推荐首先运行）
python cli.py init

# 查看 Agent 状态
python cli.py status

# 运行一个感知-行动-反思周期
python cli.py cycle

# 任务管理
python cli.py task execute "分析代码质量"
python cli.py task submit "优化性能" --format json

# 代码审查
python cli.py review file ./src/main.py

# LLM 对话（需配置 SILICONFLOW_API_KEY）
python cli.py chat "你好"

# 查看所有命令
python cli.py --help

# 查看版本
python cli.py --version
```

完整 CLI 说明运行 `python cli.py --help` 查看。

### 示例

系统提供三个难度级别的示例：

```bash
# 快速入门（5分钟，推荐新用户首先运行）
python examples/quickstart.py

# 中级示例（任务执行、代码审查、性能监控）
python examples/intermediate.py

# 完整工作流（多租户、安全、配置、恢复、基准）
python examples/full_workflow.py
```

示例索引详见 [examples/README.md](examples/README.md)。

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
# 启动 Flask API（128个端点，15个Blueprint）
export SILICONFLOW_API_KEY="your-key"
python main.py

# 或使用 Docker
docker-compose up -d
```

API 端点（15个Blueprint）：
- **core**: `/api/status`, `/api/start`, `/api/stop`, `/api/observe`, `/api/act`, `/api/reflect`
- **llm**: `/api/chat`, `/api/llm/parse`, `/api/llm/create`, `/api/llm/qa`, `/api/llm/code`
- **rag**: `/api/rag/add`, `/api/rag/query`, `/api/rag/search`, `/api/rag/docs`
- **observability**: `/api/observability/dashboard`, `/api/observability/health`, `/api/observability/logs`
- **production**: `/api/production/status`, `/health`, `/health/liveness`, `/health/readiness`
- **plugins**: `/api/plugins/load`, `/api/plugins/unload`, `/api/plugins/health`
- **config**: `/api/config/get`, `/api/config/set`, `/api/config/history`
- **security**: `/api/security/users`, `/api/security/authenticate`, `/api/security/permissions`
- **tenants**: `/api/tenants/create`, `/api/tenants/list`, `/api/tenants/quota`
- 完整列表见15个Blueprint路由文件

## 测试

```bash
# 运行全部测试（2800+测试）
pytest

# 运行特定阶段测试
pytest tests/test_agent_facade_stage149.py -v

# 运行并显示覆盖率
pytest --cov=self_evolving_agent
```

## 代码质量

项目使用 Ruff（lint + format）和 Mypy（类型检查）保证代码质量：

```bash
# Lint检查
ruff check .

# 格式化
ruff format .

# 类型检查
mypy self_evolving_agent/ --ignore-missing-imports

# 质量门禁（非阻塞）
python scripts/quality_gate.py --lint --type
```

## 部署

```bash
# Docker 部署
docker-compose up -d

# 或手动部署
pip install -e .
python main.py
```

详见 [DEPLOY.md](DEPLOY.md)。

## 技术栈

- **语言**：Python 3.10+
- **依赖**：numpy, flask, flask-cors, gunicorn, psutil
- **LLM**：硅基流动 SiliconFlow API（DeepSeek-V3 / Qwen2.5-7B-Instruct）
- **Embedding**：BAAI/bge-m3（1024维向量）
- **容器化**：Docker + docker-compose
- **代码质量**：Ruff（lint + format）, Mypy（类型检查）
- **打包**：pyproject.toml（PEP 517/518/621）

## 设计原则

1. **第一性原理**：每个引擎基于不可再分的基本原理
2. **单一职责**：每个模块/Mixin/Blueprint只负责一个领域
3. **门面模式**：SystemCoordinator 统一接口，隐藏内部结构
4. **声明式优于命令式**：设置目标，而非步骤
5. **迪米特法则**：只与直接朋友通信
6. **向后兼容**：重构保留原有接口
7. **Mixin组合**：通过多继承组合领域能力（阶段149）

## 版本

v2.0.0 — 统一架构 + 秩序化重构 + 易用性提升（阶段96-163）

## FAQ — 常见问题

### Q: 启动时提示 "LLM服务未配置"？

A: 设置 `SILICONFLOW_API_KEY` 环境变量。从 https://siliconflow.cn 获取 API 密钥。

```bash
export SILICONFLOW_API_KEY="your-api-key"
```

或复制 `.env.example` 为 `.env` 并填写密钥。系统在无 LLM 模式下仍可运行核心循环。

### Q: 如何更换 LLM 模型？

A: 设置 `SILICONFLOW_MODEL` 环境变量：

```bash
export SILICONFLOW_MODEL="deepseek-ai/DeepSeek-V2-Chat"
```

### Q: Python 版本要求？

A: Python 3.10+（推荐 3.12+）。

### Q: 如何运行测试？

A: `pytest` 运行全部测试（2800+），或 `pytest tests/test_xxx.py` 运行特定测试。

### Q: 如何贡献代码？

A: 请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

### Q: 系统支持哪些 LLM？

A: 当前集成硅基流动（SiliconFlow），支持 Qwen、DeepSeek 等模型。可通过实现 `LLMService` 接口扩展其他 LLM。

## 故障排查

### 问题: `ModuleNotFoundError: No module named 'self_evolving_agent'`

**原因**: 未安装项目依赖。

**解决**:
```bash
pip install -e .
```

### 问题: `ImportError: No module named 'flask'`

**原因**: 缺少 Flask 依赖。

**解决**:
```bash
pip install flask flask-cors
# 或
pip install -e .
```

### 问题: LLM 对话返回错误

**原因**: API Key 无效或网络问题。

**解决**:
1. 检查 `SILICONFLOW_API_KEY` 是否正确设置
2. 检查网络连接
3. 查看错误码：运行 `python cli.py errors` 查看错误码参考

### 问题: API 服务无法启动

**原因**: 端口被占用。

**解决**:
```bash
# 使用其他端口
PORT=9090 python main.py
```

### 问题: 测试失败

**原因**: 可能是 flaky 并发测试。

**解决**: 单独运行失败的测试，或使用 `--deselect` 排除：
```bash
pytest --deselect tests/test_xxx.py::TestClass::test_method
```

## 许可证

[MIT License](LICENSE)

## 贡献

请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解贡献指南。

## 变更日志

详见 [CHANGELOG.md](CHANGELOG.md)。

## 文档索引

- [配置指南](docs/configuration.md) — 环境变量和配置说明
- [部署指南](DEPLOY.md) — 生产部署说明
- [贡献指南](CONTRIBUTING.md) — 开发规范和提交流程
- [变更日志](CHANGELOG.md) — 版本历史
- [示例索引](examples/README.md) — 示例文件说明
- [错误码参考](docs/error_codes.md) — 错误码文档（运行 `python cli.py errors` 查看）
