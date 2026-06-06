# 自驱永续进化Agent系统 — 部署指南

## 快速开始

### 方式一：直接运行（推荐开发环境）

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动服务
python main.py

# 3. 访问API
open http://localhost:8080
```

### 方式二：Docker部署（推荐生产环境）

```bash
# 1. 构建镜像
docker-compose build

# 2. 启动容器
docker-compose up -d

# 3. 查看日志
docker-compose logs -f

# 4. 停止服务
docker-compose down
```

### 方式三：部署脚本

```bash
chmod +x deploy.sh
./deploy.sh
```

## API接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 系统信息 |
| `/api/status` | GET | 运行状态 |
| `/api/start` | POST | 启动Agent |
| `/api/stop` | POST | 停止Agent |
| `/api/observe` | POST | 观察环境 |
| `/api/act` | POST | 执行行动 |
| `/api/reflect` | GET | 反思状态 |
| `/api/dashboard` | GET | 监控大盘 |
| `/api/stats` | GET | 完整统计 |
| `/api/goals` | POST | 设置目标 |
| `/api/cycle` | POST | 运行周期 |

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `PORT` | 8080 | 服务端口 |
| `HOST` | 0.0.0.0 | 绑定地址 |
| `DEBUG` | false | 调试模式 |

## 系统架构

```
┌─────────────────────────────────────────┐
│           REST API (Flask)              │
├─────────────────────────────────────────┤
│         SystemCoordinator               │
│  (声明式接口 / 协调 / 仲裁)              │
├─────────────────────────────────────────┤
│      UnifiedFirstPrinciplesEngine       │
│  (15个第一性原理引擎整合)                 │
├─────────────────────────────────────────┤
│  预测编码 │ 驱力 │ 学习 │ 探索 │ 记忆   │
│  进化 │ 安全 │ 能效 │ 社交 │ 创造      │
│  因果 │ 元认知 │ 情感 │ 意识 │ 自由意志 │
└─────────────────────────────────────────┘
```

## 健康检查

```bash
curl http://localhost:8080/api/status
```
