# 贡献指南

感谢您对自驱永续进化Agent系统的关注！本文档介绍如何参与项目开发。

## 开发环境

### 环境要求

- Python 3.10+
- pip / venv

### 搭建开发环境

```bash
# 克隆仓库
git clone <repository-url>
cd self-evolving-agent

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 安装依赖（含开发依赖）
pip install -e ".[dev]"
```

## 代码规范

### Lint与格式化

项目使用 [Ruff](https://docs.astral.sh/ruff/) 进行代码检查和格式化：

```bash
# 检查代码
ruff check .

# 自动修复
ruff check . --fix

# 格式化
ruff format .
```

### 类型检查

项目使用 [Mypy](https://mypy-lang.org/) 进行静态类型检查：

```bash
mypy self_evolving_agent/ --ignore-missing-imports
```

### 质量门禁

运行质量门禁脚本（非阻塞模式）：

```bash
python scripts/quality_gate.py --lint --type
```

## 测试

### 运行测试

```bash
# 运行全部测试
pytest

# 运行特定阶段测试
pytest tests/test_agent_facade_stage149.py -v

# 运行并显示覆盖率
pytest --cov=self_evolving_agent
```

### 测试规范

- 测试文件命名：`test_<topic>_stage<NNN>.py`
- 测试类命名：`Test<Feature>`
- 测试方法命名：`test_<behavior>`
- 共享fixture放在 `tests/conftest.py`
- 每个阶段应包含第一性原理验证测试

## 架构原则

1. **第一性原理**：每个模块基于不可再分的基本原理
2. **单一职责**：每个模块/类只负责一个领域
3. **门面模式**：通过统一接口隐藏内部结构
4. **向后兼容**：重构时保持原有接口不变
5. **声明式优于命令式**：设置目标，而非步骤

## 提交规范

### 提交信息格式

```
<type>: <description> (阶段NNN)

<详细说明>
```

类型：
- `feat`: 新功能
- `fix`: 修复bug
- `refactor`: 重构
- `test`: 测试
- `docs`: 文档
- `chore`: 杂项

### 示例

```
refactor: agent.py门面重构 — 按领域拆分为14个Mixin (阶段149)

将SelfEvolvingAgent的1478行巨型类按领域拆分为14个Mixin文件，
agent.py缩减到541行，保持100%向后兼容。
```

## 项目结构

```
self_evolving_agent/
├── agent.py              # 主Agent（核心生命周期 + Mixin组合）
├── agent_mixins/         # 14个领域Mixin（阶段149）
├── core/                 # 核心模块（75+模块）
├── modules/              # 遗留模块（向后兼容）
api/                      # REST API（15个Blueprint，阶段148）
tests/                    # 测试套件（2800+测试）
docs/                     # 文档
scripts/                  # 脚本
pyproject.toml            # 项目配置（阶段144）
```

## 版本发布

版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)：
- MAJOR: 不兼容的API修改
- MINOR: 向下兼容的功能新增
- PATCH: 向下兼容的问题修复

当前版本：v2.0.0
