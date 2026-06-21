# 示例索引

本目录包含不同难度级别的示例，帮助用户逐步了解系统功能。

## 示例分类

### 快速入门（推荐新用户首先运行）

| 文件 | 说明 | 运行方式 |
|------|------|----------|
| [quickstart.py](quickstart.py) | 最小可运行示例：创建Agent → 感知 → 行动 → 反思 | `python examples/quickstart.py` |

### 中级示例

| 文件 | 说明 | 运行方式 |
|------|------|----------|
| [intermediate.py](intermediate.py) | 任务执行、代码审查、性能监控 | `python examples/intermediate.py` |

### 高级示例

| 文件 | 说明 | 运行方式 |
|------|------|----------|
| [full_workflow.py](full_workflow.py) | 完整工作流：多租户、安全、配置、恢复、基准 | `python examples/full_workflow.py` |
| [api_workflow.py](api_workflow.py) | HTTP API 端到端示例（需先启动 `python main.py`） | `python examples/api_workflow.py` |

## 运行前提

1. 已安装依赖：`pip install -e .`
2. 快速入门和中级示例无需任何配置
3. 高级示例中的 API 工作流需先启动 API 服务

## 配置 LLM（可选）

如需启用 LLM 对话功能：

```bash
export SILICONFLOW_API_KEY="your-api-key"
```

从 https://siliconflow.cn 获取 API 密钥。

## 示例难度递进

```
quickstart.py  →  intermediate.py  →  full_workflow.py
   (5分钟)           (10分钟)             (20分钟)
                        ↓
                  api_workflow.py
                   (需启动API)
```
