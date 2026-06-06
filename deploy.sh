#!/bin/bash
# 自驱永续进化Agent系统 — 部署脚本

set -e

echo "=========================================="
echo "自驱永续进化Agent系统 — 部署脚本"
echo "=========================================="

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "错误: Python3 未安装"
    exit 1
fi

# 检查pip
if ! command -v pip3 &> /dev/null; then
    echo "错误: pip3 未安装"
    exit 1
fi

echo "[1/5] 安装依赖..."
pip3 install -r requirements.txt

echo "[2/5] 验证安装..."
python3 -c "import numpy; import flask; print('依赖验证通过')"

echo "[3/5] 运行系统测试..."
python3 test_system_end_to_end.py

echo "[4/5] 启动服务..."
export PORT=${PORT:-8080}
export HOST=${HOST:-0.0.0.0}
export DEBUG=${DEBUG:-false}

echo "服务配置:"
echo "  PORT: $PORT"
echo "  HOST: $HOST"
echo "  DEBUG: $DEBUG"

echo "[5/5] 服务启动完成"
echo "=========================================="
echo "API地址: http://$HOST:$PORT"
echo "状态检查: http://$HOST:$PORT/api/status"
echo "=========================================="

# 启动服务
python3 main.py
