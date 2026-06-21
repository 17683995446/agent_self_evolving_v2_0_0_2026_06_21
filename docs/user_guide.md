# 用户指南

本指南帮助用户从零开始使用自驱永续进化Agent系统。

## 目录

1. [安装](#安装)
2. [首次配置](#首次配置)
3. [快速开始](#快速开始)
4. [CLI 命令行工具](#cli-命令行工具)
5. [Python API](#python-api)
6. [REST API](#rest-api)
7. [LLM 集成](#llm-集成)
8. [RAG 检索增强](#rag-检索增强)
9. [高级功能](#高级功能)
10. [故障排查](#故障排查)

## 安装

### 前置条件

- Python 3.10+
- pip

### 安装步骤

```bash
# 1. 克隆项目（如果尚未克隆）
git clone <repository-url>
cd self-evolving-agent

# 2. 安装项目（推荐）
pip install -e .

# 或安装特定可选依赖
pip install -e ".[llm,dev]"
```

## 首次配置

### 使用初始化向导（推荐）

```bash
python cli.py init
```

向导会引导你完成：
1. 环境检查（Python 版本、依赖）
2. 配置文件创建（从 `.env.example` 复制）
3. Agent 验证
4. 下一步指引

### 手动配置

```bash
# 复制配置模板
cp .env.example .env

# 编辑 .env，按需设置变量
# 至少设置 SILICONFLOW_API_KEY 以启用 LLM 功能
```

完整环境变量说明见 [配置指南](configuration.md)。

## 快速开始

### 运行快速入门示例

```bash
python examples/quickstart.py
```

这会演示 Agent 的核心生命周期：创建 → 感知 → 行动 → 反思。

### 运行中级示例

```bash
python examples/intermediate.py
```

演示任务执行、代码审查和性能监控。

## CLI 命令行工具

### 基本命令

```bash
# 查看 Agent 状态
python cli.py status

# 运行一个周期
python cli.py cycle

# 启动/停止后台循环
python cli.py start
python cli.py stop
```

### 任务管理

```bash
# 同步执行任务
python cli.py task execute "分析代码质量"

# 提交异步任务
python cli.py task submit "优化性能"

# 查询任务状态
python cli.py task status <task_id>

# 查询任务结果
python cli.py task result <task_id>
```

### 代码审查

```bash
# 审查文件
python cli.py review file ./src/main.py

# 审查目录
python cli.py review dir ./src/

# 审查代码字符串
python cli.py review code "def foo(): pass"
```

### 文档生成

```bash
# 从文件生成文档
python cli.py docs file ./src/main.py --format markdown
```

### 性能监控

```bash
# 性能报告
python cli.py perf report

# 缓存统计
python cli.py perf cache
```

### 插件管理

```bash
# 列出插件
python cli.py plugin list

# 插件健康检查
python cli.py plugin health
```

### LLM 对话

```bash
# 需先配置 SILICONFLOW_API_KEY
python cli.py chat "你好，请介绍一下自己"
```

### 输出格式

```bash
# JSON 格式（便于脚本处理）
python cli.py --format json status

# 表格格式
python cli.py --format table status
```

### 交互模式

```bash
python cli.py repl
# 输入 help 查看命令，quit 退出
```

### 查看错误码

```bash
python cli.py errors
```

## Python API

### 创建 Agent

```python
from self_evolving_agent import create_default_agent

# 无 LLM 模式
agent = create_default_agent()
agent.initialize({"cycle_interval": 0.5})

# 启用 LLM
from self_evolving_agent import create_default_agent_with_llm
agent = create_default_agent_with_llm("your-api-key")
```

### 核心生命周期

```python
# 感知环境
result = agent.observe({
    "module_id": "env",
    "predicted": {"value": 0.5},
    "actual": {"value": 0.55},
})

# 执行行动
action = agent.act("explore", context={"resources_used": {"cpu": 0.3}})

# 反思
reflection = agent.reflect()

# 运行完整周期
cycle_result = agent.run_cycle({})
```

### 设置目标

```python
# 声明式目标设置
agent.set_goal("safe", 0.95)  # 安全目标
agent.set_goal("gain", 0.8)   # 收益目标
agent.set_goal("eff", 0.85)   # 能效目标
```

### 任务执行

```python
# 同步执行
result = agent.execute_task("分析系统状态")

# 异步提交
task_id = agent.submit_task("优化性能")

# 查询状态
status = agent.get_task_status(task_id)

# 获取结果
result = agent.get_task_result(task_id)
```

### 代码审查

```python
# 审查代码字符串
report = agent.review_code("def foo(): pass")

# 审查文件
report = agent.review_file("./src/main.py")

# 审查目录
reports = agent.review_directory("./src/")
```

### 文档生成

```python
from self_evolving_agent.core.doc_generator import DocFormat

# 生成 markdown 文档
report = agent.generate_file_docs("./src/main.py", DocFormat.MARKDOWN)

# 生成 HTML 文档
report = agent.generate_file_docs("./src/main.py", DocFormat.HTML)
```

### 性能监控

```python
# 性能报告
report = agent.get_performance_report()

# 缓存统计
stats = agent.get_cache_stats()

# 重置性能指标
agent.reset_performance()
```

## REST API

### 启动 API 服务

```bash
python main.py
# 默认端口 8080
```

### 查看端点文档

```bash
# 根端点 — 系统概览和端点清单
curl http://localhost:8080/

# 按 Blueprint 分组的端点
curl http://localhost:8080/api/docs/endpoints

# OpenAPI 3.0 Schema
curl http://localhost:8080/api/docs/openapi
```

### 常用端点

```bash
# 状态
curl http://localhost:8080/api/status

# 启动 Agent
curl -X POST http://localhost:8080/api/start

# 停止 Agent
curl -X POST http://localhost:8080/api/stop

# 感知
curl -X POST http://localhost:8080/api/observe \
  -H "Content-Type: application/json" \
  -d '{"module_id": "test", "predicted": {"value": 0.5}, "actual": {"value": 0.55}}'

# 行动
curl -X POST http://localhost:8080/api/act \
  -H "Content-Type: application/json" \
  -d '{"action": "explore", "context": {"resources_used": {"cpu": 0.3}}}'

# 反思
curl http://localhost:8080/api/reflect

# 健康检查
curl http://localhost:8080/health
```

### LLM 对话

```bash
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"text": "你好"}'
```

### RAG 查询

```bash
# 添加文档
curl -X POST http://localhost:8080/api/rag/add \
  -H "Content-Type: application/json" \
  -d '{"content": "预测编码是大脑通过生成预测来减小误差的过程。"}'

# 查询
curl -X POST http://localhost:8080/api/rag/query \
  -H "Content-Type: application/json" \
  -d '{"question": "什么是预测编码？"}'
```

## LLM 集成

### 配置

```bash
export SILICONFLOW_API_KEY="your-api-key"
```

从 https://siliconflow.cn 获取 API 密钥。

### 使用

```python
from self_evolving_agent import create_default_agent_with_llm

agent = create_default_agent_with_llm("your-api-key")

# 自然语言观察
result = agent.observe({"text": "CPU使用率上升到85%"})

# 反思（含自然语言报告）
reflection = agent.reflect()
print(reflection.get("reflection_text"))
```

### 更换模型

```bash
export SILICONFLOW_MODEL="deepseek-ai/DeepSeek-V2-Chat"
```

## RAG 检索增强

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

## 高级功能

### 多租户

```python
# 创建租户
tenant = agent.create_tenant("my-tenant")

# 设置配额
agent.check_tenant_quota(tenant.tenant_id)

# 在租户作用域执行
agent.execute_in_tenant(tenant.tenant_id, lambda: some_operation())
```

### 安全管理

```python
# 创建用户
user = agent.create_user("alice", "password")

# 认证
token = agent.authenticate("alice", "password")

# 检查权限
agent.check_permission(user.user_id, "read")
```

### 配置热更新

```python
# 设置配置
agent.set_config("key", "value")

# 获取配置
value = agent.get_config("key")

# 回滚配置
agent.rollback_config()
```

### 错误恢复

```python
# 带恢复的执行
result = agent.execute_with_recovery(risky_operation)

# 注册恢复策略
agent.register_recovery_strategy("network_error", recovery_handler)
```

### 性能基准

```python
# 运行基准测试
result = agent.run_benchmark("cpu_benchmark")

# 快速基准
result = agent.run_quick_benchmark()
```

## 故障排查

### 常见问题

**Q: `ModuleNotFoundError: No module named 'self_evolving_agent'`**
A: 运行 `pip install -e .` 安装项目。

**Q: `ModuleNotFoundError: No module named 'flask'`**
A: 运行 `pip install flask flask-cors` 或 `pip install -e .`。

**Q: LLM 服务未启用**
A: 设置 `SILICONFLOW_API_KEY` 环境变量。

**Q: 端口被占用**
A: 使用 `PORT=9090 python main.py` 指定其他端口。

**Q: 测试失败**
A: 部分并发测试可能 flaky，单独运行或使用 `--deselect` 排除。

### 查看错误码

```bash
python cli.py errors
```

### 获取帮助

- CLI 帮助：`python cli.py --help`
- 子命令帮助：`python cli.py <command> --help`
- API 文档：`http://localhost:8080/api/docs/openapi`
- 配置指南：[docs/configuration.md](configuration.md)

## 下一步

- 阅读 [README.md](../README.md) 了解项目概览
- 运行 [示例](../examples/README.md) 学习更多用法
- 查看 [变更日志](../CHANGELOG.md) 了解版本历史
- 阅读 [贡献指南](../CONTRIBUTING.md) 参与开发
