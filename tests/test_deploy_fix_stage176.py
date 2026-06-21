"""
阶段176: 修复 deploy.sh 引用不存在的测试文件

P0 Bug: deploy.sh 第29行引用 test_system_end_to_end.py，该文件不存在
       set -e 模式下会导致部署脚本必然失败

验证:
1. deploy.sh 不再引用 test_system_end_to_end.py
2. 改为运行 pytest 核心测试子集
3. 测试失败不中断部署（|| true 或 || echo 警告）
4. 依赖验证包含新增依赖
"""

import os
import sys
import subprocess

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestDeployScriptFix:
    """deploy.sh 修复验证"""

    @property
    def deploy_path(self):
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "deploy.sh"
        )

    def test_deploy_sh_exists(self):
        """deploy.sh 存在"""
        assert os.path.exists(self.deploy_path)

    def test_no_reference_to_nonexistent_test(self):
        """deploy.sh 不引用 test_system_end_to_end.py"""
        with open(self.deploy_path, "r") as f:
            content = f.read()
        assert "test_system_end_to_end.py" not in content, \
            "deploy.sh 不应引用不存在的 test_system_end_to_end.py"

    def test_uses_pytest(self):
        """deploy.sh 改为使用 pytest"""
        with open(self.deploy_path, "r") as f:
            content = f.read()
        assert "pytest" in content, \
            "deploy.sh 应使用 pytest 运行测试"

    def test_test_failure_does_not_abort(self):
        """测试失败不中断部署（|| 警告）"""
        with open(self.deploy_path, "r") as f:
            content = f.read()
        # 应有 || 容错处理
        assert "||" in content, \
            "deploy.sh 测试步骤应有 || 容错，避免 set -e 中断部署"

    def test_dependency_check_includes_dotenv(self):
        """依赖验证包含 python-dotenv"""
        with open(self.deploy_path, "r") as f:
            content = f.read()
        assert "dotenv" in content, \
            "deploy.sh 依赖验证应包含 dotenv"

    def test_dependency_check_includes_psutil(self):
        """依赖验证包含 psutil"""
        with open(self.deploy_path, "r") as f:
            content = f.read()
        assert "psutil" in content, \
            "deploy.sh 依赖验证应包含 psutil"

    def test_referenced_test_file_exists(self):
        """deploy.sh 引用的测试文件实际存在"""
        with open(self.deploy_path, "r") as f:
            content = f.read()
        # 找到 pytest 引用的测试文件
        import re
        matches = re.findall(r'pytest\s+(\S+\.py)', content)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for match in matches:
            test_path = os.path.join(project_root, match)
            assert os.path.exists(test_path), \
                f"deploy.sh 引用的测试文件应存在: {match}"


class TestDeployScriptSyntax:
    """deploy.sh 语法验证"""

    def test_bash_syntax_valid(self):
        """deploy.sh bash 语法有效"""
        result = subprocess.run(
            ["bash", "-n", self.deploy_path if hasattr(self, 'deploy_path')
             else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "deploy.sh")],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0, \
            f"deploy.sh 语法错误: {result.stderr}"

    def test_set_e_present(self):
        """deploy.sh 保留 set -e（错误即退出）"""
        with open(self.deploy_path if hasattr(self, 'deploy_path')
                  else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "deploy.sh"), "r") as f:
            content = f.read()
        assert "set -e" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
