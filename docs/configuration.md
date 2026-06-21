# 配置指南

本文档列出系统的所有环境变量及其用途。

## 快速开始

```bash
# 1. 复制配置模板
cp .env.example .env

# 2. 编辑 .env，至少设置 SILICONFLOW_API_KEY（如需 LLM 功能）
# 3. 启动服务
python main.py
```

## 环境变量清单

### 服务配置

| 变量名 | 默认值 | 说明 | 必需 |
|--------|--------|------|------|
| `PORT` | `8080` | Flask API 服务监听端口 | 否 |
| `HOST` | `0.0.0.0` | Flask API 服务监听地址 | 否 |
| `DEBUG` | `false` | Flask 调试模式（`true` 启用） | 否 |

### LLM 配置

| 变量名 | 默认值 | 说明 | 必需 |
|--------|--------|------|------|
| `SILICONFLOW_API_KEY` | （空） | 硅基流动 API 密钥，启用 LLM 对话功能 | 启用 LLM 时必需 |
| `SILICONFLOW_MODEL` | `Qwen/Qwen2.5-7B-Instruct` | LLM 对话模型名称 | 否 |
| `SILICONFLOW_BASE_URL` | `https://api.siliconflow.cn/v1` | 硅基流动 API 基础 URL | 否 |

### RAG 配置

| 变量名 | 默认值 | 说明 | 必需 |
|--------|--------|------|------|
| `SILICONFLOW_EMBEDDING_MODEL` | `BAAI/bge-m3` | Embedding 模型名称（用于 RAG 向量化） | 否 |

### 高级配置（前缀式批量加载）

系统支持以 `APP_` 为前缀的环境变量批量加载为配置项（遵循 12-Factor App 原则）。

- 格式：`APP_<KEY>=<value>`
- 前缀会被剥离，键名转为小写
- 值会尝试 JSON 解析，失败则保留为字符串

示例：

```bash
APP_MAX_CYCLES=100
APP_FEATURE_FLAGS={"rag": true, "llm": false}
```

## 运行模式

### 无 LLM 模式（默认）

不设置 `SILICONFLOW_API_KEY`，系统运行核心循环（感知-行动-反思），LLM 对话和 RAG 检索功能不启用。

```bash
python main.py
```

### 启用 LLM 模式

```bash
export SILICONFLOW_API_KEY="your-api-key"
python main.py
```

### 生产部署

```bash
PORT=80 HOST=0.0.0.0 DEBUG=false SILICONFLOW_API_KEY="your-key" python main.py
```

## 配置优先级

1. 环境变量（最高优先级）
2. `APP_` 前缀批量加载
3. 代码内默认值（最低优先级）

## 常见问题

**Q: 启动时提示 "LLM服务未配置"？**
A: 设置 `SILICONFLOW_API_KEY` 环境变量。从 https://siliconflow.cn 获取 API 密钥。

**Q: 如何更换 LLM 模型？**
A: 设置 `SILICONFLOW_MODEL` 环境变量，如 `deepseek-ai/DeepSeek-V2-Chat`。

**Q: 如何在 Docker 中使用？**
A: 在 docker run 时通过 `-e` 传递，或在 docker-compose.yml 的 `environment` 段声明。
