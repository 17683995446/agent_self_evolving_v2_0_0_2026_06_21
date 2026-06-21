"""环境管理Mixin — 阶段149从agent.py拆分"""

from typing import Any, Dict, Optional

from ..core.environment_interface import EnvironmentInterface, EnvironmentAction


class EnvironmentMixin:
    """环境管理接口（阶段124）"""

    def register_environment(
        self,
        env_id: str,
        environment: EnvironmentInterface,
        is_default: bool = False,
    ) -> None:
        """注册环境（阶段124新增）"""
        self._env_manager.register_environment(env_id, environment, is_default)

    def set_default_environment(self, env_id: str) -> bool:
        """设置默认环境（阶段124新增）"""
        env = self._env_manager.get_environment(env_id)
        if env is None:
            return False
        self._env_manager._default_env_id = env_id
        return True

    def execute_environment_action(
        self,
        action: EnvironmentAction,
        env_id: Optional[str] = None,
    ):
        """执行环境动作（阶段124新增）"""
        return self._env_manager.act(action, env_id)
