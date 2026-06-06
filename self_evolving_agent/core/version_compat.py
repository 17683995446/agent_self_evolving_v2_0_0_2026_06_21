"""
自驱永续进化Agent系统 — 版本兼容性检查
阶段21：版本兼容性检查

第一性原理：系统演化过程中，接口可能变化，但必须保证向后兼容或明确拒绝不兼容的调用

语义化版本控制（SemVer）：
- MAJOR：不兼容的API修改
- MINOR：向下兼容的功能新增
- PATCH：向下兼容的问题修正

兼容性规则：
- 相同MAJOR版本：兼容
- 不同MAJOR版本：不兼容
"""

import re
from typing import Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class CompatibilityLevel(Enum):
    """兼容性级别"""
    FULLY_COMPATIBLE = "fully_compatible"      # 完全兼容
    BACKWARD_COMPATIBLE = "backward_compatible" # 向后兼容（新功能）
    INCOMPATIBLE = "incompatible"               # 不兼容
    UNKNOWN = "unknown"                         # 未知


@dataclass(frozen=True)
class SemanticVersion:
    """
    语义化版本

    格式：MAJOR.MINOR.PATCH
    示例：1.2.3
    """
    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    @classmethod
    def parse(cls, version_str: str) -> "SemanticVersion":
        """解析版本字符串"""
        match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", version_str.strip())
        if not match:
            raise VersionParseError(f"Invalid version format: {version_str}")
        return cls(
            major=int(match.group(1)),
            minor=int(match.group(2)),
            patch=int(match.group(3)),
        )

    def __lt__(self, other: "SemanticVersion") -> bool:
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SemanticVersion):
            return False
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)

    def __hash__(self) -> int:
        return hash((self.major, self.minor, self.patch))


class VersionCompatibilityChecker:
    """
    版本兼容性检查器

    检查两个版本是否兼容
    """

    @staticmethod
    def check(required: SemanticVersion,
              provided: SemanticVersion) -> CompatibilityLevel:
        """
        检查版本兼容性

        规则：
        - required.major == provided.major：兼容
        - required.major != provided.major：不兼容
        - provided > required：向后兼容（新功能）
        """
        if required.major != provided.major:
            return CompatibilityLevel.INCOMPATIBLE

        if provided > required:
            return CompatibilityLevel.BACKWARD_COMPATIBLE

        return CompatibilityLevel.FULLY_COMPATIBLE

    @staticmethod
    def is_compatible(required: SemanticVersion,
                      provided: SemanticVersion) -> bool:
        """判断是否兼容"""
        level = VersionCompatibilityChecker.check(required, provided)
        return level in (CompatibilityLevel.FULLY_COMPATIBLE,
                        CompatibilityLevel.BACKWARD_COMPATIBLE)

    @staticmethod
    def get_upgrade_path(current: SemanticVersion,
                         target: SemanticVersion) -> list[str]:
        """
        获取升级路径建议

        当版本不兼容时，提供升级建议
        """
        if current.major == target.major:
            if current.minor == target.minor:
                return [f"Update patch: {current} -> {target}"]
            return [f"Update minor: {current} -> {target}"]
        else:
            return [
                f"WARNING: Major version change from {current} to {target}",
                "This may introduce breaking changes.",
                "Please review the migration guide.",
            ]


class InterfaceVersionManager:
    """
    接口版本管理器

    管理模块接口的版本信息
    """

    def __init__(self):
        self._interface_versions: dict[str, SemanticVersion] = {}
        self._compatibility_matrix: dict[tuple[str, str], bool] = {}

    def register_interface(self, interface_name: str,
                           version: SemanticVersion) -> None:
        """注册接口版本"""
        self._interface_versions[interface_name] = version

    def get_version(self, interface_name: str) -> Optional[SemanticVersion]:
        """获取接口版本"""
        return self._interface_versions.get(interface_name)

    def check_compatibility(self, interface_name: str,
                            required_version: SemanticVersion) -> bool:
        """
        检查接口兼容性

        Args:
            interface_name: 接口名称
            required_version: 要求的版本

        Returns:
            是否兼容
        """
        current = self._interface_versions.get(interface_name)
        if current is None:
            return False

        return VersionCompatibilityChecker.is_compatible(required_version, current)

    def require_version(self, interface_name: str,
                        required_version: str) -> None:
        """
        要求接口版本

        如果不兼容，抛出异常
        """
        required = SemanticVersion.parse(required_version)
        current = self._interface_versions.get(interface_name)

        if current is None:
            raise VersionCompatibilityError(
                f"Interface '{interface_name}' not found"
            )

        if not VersionCompatibilityChecker.is_compatible(required, current):
            raise VersionCompatibilityError(
                f"Interface '{interface_name}' version incompatible: "
                f"required {required}, but current is {current}"
            )

    def list_interfaces(self) -> dict[str, str]:
        """列出所有接口版本"""
        return {
            name: str(version)
            for name, version in self._interface_versions.items()
        }


class VersionCompatibilityError(Exception):
    """版本兼容性错误"""
    pass


class VersionParseError(Exception):
    """版本解析错误"""
    pass


# ============================================================================
# 便捷函数
# ============================================================================

def check_version(required: str, provided: str) -> CompatibilityLevel:
    """便捷函数：检查版本兼容性"""
    req = SemanticVersion.parse(required)
    prov = SemanticVersion.parse(provided)
    return VersionCompatibilityChecker.check(req, prov)


def is_compatible(required: str, provided: str) -> bool:
    """便捷函数：判断是否兼容"""
    req = SemanticVersion.parse(required)
    prov = SemanticVersion.parse(provided)
    return VersionCompatibilityChecker.is_compatible(req, prov)
