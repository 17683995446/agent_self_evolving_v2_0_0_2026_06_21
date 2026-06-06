"""
阶段21验证：版本兼容性检查
"""
import sys
sys.path.insert(0, '/workspace')

from self_evolving_agent.core.version_compat import (
    SemanticVersion, VersionCompatibilityChecker, CompatibilityLevel,
    InterfaceVersionManager, VersionCompatibilityError, VersionParseError,
    check_version, is_compatible
)


def test_semantic_version():
    """测试语义化版本"""
    print("=" * 60)
    print("测试: SemanticVersion")
    print("=" * 60)

    v = SemanticVersion.parse("1.2.3")
    print(f"解析: {v}")
    assert v.major == 1
    assert v.minor == 2
    assert v.patch == 3

    # 比较
    v1 = SemanticVersion(1, 0, 0)
    v2 = SemanticVersion(1, 1, 0)
    v3 = SemanticVersion(2, 0, 0)
    assert v1 < v2
    assert v2 < v3
    assert v1 == SemanticVersion(1, 0, 0)
    print("比较测试通过")

    # 无效格式
    try:
        SemanticVersion.parse("invalid")
        assert False
    except VersionParseError:
        print("无效格式正确抛出异常")

    print("\nSemanticVersion测试通过!")
    return True


def test_compatibility_check():
    """测试兼容性检查"""
    print("\n" + "=" * 60)
    print("测试: 兼容性检查")
    print("=" * 60)

    # 相同版本
    level = check_version("1.0.0", "1.0.0")
    print(f"1.0.0 vs 1.0.0: {level.value}")
    assert level == CompatibilityLevel.FULLY_COMPATIBLE

    # 向后兼容（新功能）
    level = check_version("1.0.0", "1.1.0")
    print(f"1.0.0 vs 1.1.0: {level.value}")
    assert level == CompatibilityLevel.BACKWARD_COMPATIBLE

    # 向后兼容（patch）
    level = check_version("1.0.0", "1.0.5")
    print(f"1.0.0 vs 1.0.5: {level.value}")
    assert level == CompatibilityLevel.BACKWARD_COMPATIBLE

    # 不兼容
    level = check_version("1.0.0", "2.0.0")
    print(f"1.0.0 vs 2.0.0: {level.value}")
    assert level == CompatibilityLevel.INCOMPATIBLE

    # 反向检查
    level = check_version("2.0.0", "1.0.0")
    print(f"2.0.0 vs 1.0.0: {level.value}")
    assert level == CompatibilityLevel.INCOMPATIBLE

    print("\n兼容性检查测试通过!")
    return True


def test_is_compatible():
    """测试is_compatible便捷函数"""
    print("\n" + "=" * 60)
    print("测试: is_compatible")
    print("=" * 60)

    assert is_compatible("1.0.0", "1.0.0") == True
    assert is_compatible("1.0.0", "1.5.0") == True
    assert is_compatible("1.0.0", "2.0.0") == False
    assert is_compatible("2.0.0", "1.0.0") == False

    print("is_compatible测试通过")
    print("\nis_compatible测试通过!")
    return True


def test_upgrade_path():
    """测试升级路径"""
    print("\n" + "=" * 60)
    print("测试: 升级路径")
    print("=" * 60)

    # Patch升级
    path = VersionCompatibilityChecker.get_upgrade_path(
        SemanticVersion(1, 0, 0), SemanticVersion(1, 0, 5)
    )
    print(f"Patch升级: {path}")
    assert "patch" in path[0].lower()

    # Minor升级
    path = VersionCompatibilityChecker.get_upgrade_path(
        SemanticVersion(1, 0, 0), SemanticVersion(1, 2, 0)
    )
    print(f"Minor升级: {path}")
    assert "minor" in path[0].lower()

    # Major升级
    path = VersionCompatibilityChecker.get_upgrade_path(
        SemanticVersion(1, 0, 0), SemanticVersion(2, 0, 0)
    )
    print(f"Major升级: {path}")
    assert "WARNING" in path[0]

    print("\n升级路径测试通过!")
    return True


def test_interface_manager():
    """测试接口版本管理器"""
    print("\n" + "=" * 60)
    print("测试: 接口版本管理器")
    print("=" * 60)

    manager = InterfaceVersionManager()

    # 注册接口
    manager.register_interface("predictor", SemanticVersion(1, 2, 0))
    manager.register_interface("drive_engine", SemanticVersion(2, 0, 0))

    # 列出接口
    interfaces = manager.list_interfaces()
    print(f"注册接口: {interfaces}")
    assert len(interfaces) == 2

    # 检查兼容性
    assert manager.check_compatibility("predictor", SemanticVersion(1, 0, 0)) == True
    assert manager.check_compatibility("predictor", SemanticVersion(2, 0, 0)) == False
    assert manager.check_compatibility("nonexistent", SemanticVersion(1, 0, 0)) == False

    print("\n接口版本管理器测试通过!")
    return True


def test_require_version():
    """测试require_version"""
    print("\n" + "=" * 60)
    print("测试: require_version")
    print("=" * 60)

    manager = InterfaceVersionManager()
    manager.register_interface("predictor", SemanticVersion(1, 2, 0))

    # 兼容版本
    manager.require_version("predictor", "1.0.0")  # 不应抛出异常
    print("兼容版本通过")

    # 不兼容版本
    try:
        manager.require_version("predictor", "2.0.0")
        assert False, "应抛出异常"
    except VersionCompatibilityError as e:
        print(f"不兼容版本正确抛出异常: {e}")

    # 不存在的接口
    try:
        manager.require_version("nonexistent", "1.0.0")
        assert False, "应抛出异常"
    except VersionCompatibilityError as e:
        print(f"不存在接口正确抛出异常: {e}")

    print("\nrequire_version测试通过!")
    return True


def run_all_tests():
    print("\n" + "=" * 60)
    print("阶段21: 版本兼容性检查 — 验证测试")
    print("=" * 60)

    tests = [
        ("SemanticVersion", test_semantic_version),
        ("兼容性检查", test_compatibility_check),
        ("is_compatible", test_is_compatible),
        ("升级路径", test_upgrade_path),
        ("接口版本管理器", test_interface_manager),
        ("require_version", test_require_version),
    ]

    passed = 0
    failed = 0
    for name, test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"\n测试 {name} 失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
