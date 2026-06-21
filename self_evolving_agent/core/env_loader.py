"""
阶段175: .env 自动加载器

第一性原理:
1. 零配置启动 — 用户创建 .env 后，启动服务/CLI 即自动加载，无需手动 export
2. 优雅降级 — python-dotenv 未安装时，回退到内置简易解析器
3. 不覆盖已设值 — os.environ 已有的值优先（允许命令行覆盖文件配置）
4. 显式反馈 — 加载时打印来源（.env 路径），便于排障

用法:
    from self_evolving_agent.core.env_loader import load_env
    load_env()  # 在程序入口最早处调用
"""

import os
from pathlib import Path
from typing import Optional


def _parse_env_line(line: str) -> Optional[tuple]:
    """简易 .env 行解析器（python-dotenv 未安装时的回退）

    支持:
    - KEY=VALUE
    - KEY="VALUE" / KEY='VALUE'（去引号）
    - # 注释行
    - 空行跳过
    不支持: 多行值、转义字符（这些场景请安装 python-dotenv）
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    if "=" not in line:
        return None
    key, _, value = line.partition("=")
    key = key.strip()
    if not key:
        return None
    value = value.strip()
    # 去除外层引号
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1]
    return key, value


def load_env(env_path: Optional[str] = None, verbose: bool = True) -> dict:
    """加载 .env 文件到 os.environ

    Args:
        env_path: 指定 .env 文件路径；None 则自动查找（项目根目录）
        verbose: 是否打印加载信息

    Returns:
        本次实际加载的键值对（不覆盖已存在的环境变量）
    """
    # 确定查找路径
    if env_path is None:
        # 从调用栈推断项目根目录（向上查找 .env）
        cwd = Path.cwd()
        candidates = [cwd / ".env"]
        # 向上查找最多5层
        parent = cwd.parent
        for _ in range(5):
            candidates.append(parent / ".env")
            if parent == parent.parent:
                break
            parent = parent.parent
        # 也检查本模块所在项目根
        module_root = Path(__file__).resolve().parent.parent.parent
        candidates.append(module_root / ".env")

        env_file = None
        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                env_file = candidate
                break
    else:
        env_file = Path(env_path)
        if not env_file.exists():
            if verbose:
                print(f"[env] 指定的 .env 文件不存在: {env_file}")
            return {}

    if env_file is None:
        # 无 .env 文件，静默返回（正常场景）
        return {}

    loaded = {}

    # 优先使用 python-dotenv（功能完整）
    try:
        from dotenv import load_dotenv
        # load_dotenv 不会覆盖已存在的环境变量
        load_dotenv(env_file, override=False)
        # 读取文件内容记录本次加载的键
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                parsed = _parse_env_line(line)
                if parsed:
                    key, _ = parsed
                    loaded[key] = os.environ.get(key, "")
        if verbose:
            print(f"[env] 已加载 .env: {env_file}（python-dotenv，{len(loaded)} 项）")
    except ImportError:
        # 回退到内置解析器
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                parsed = _parse_env_line(line)
                if parsed is None:
                    continue
                key, value = parsed
                # 不覆盖已存在的环境变量
                if key not in os.environ:
                    os.environ[key] = value
                    loaded[key] = value
        if verbose:
            print(f"[env] 已加载 .env: {env_file}（内置解析器，{len(loaded)} 项）")

    return loaded


def is_env_loaded() -> bool:
    """检查 .env 是否存在且可加载"""
    cwd = Path.cwd()
    if (cwd / ".env").exists():
        return True
    module_root = Path(__file__).resolve().parent.parent.parent
    return (module_root / ".env").exists()
