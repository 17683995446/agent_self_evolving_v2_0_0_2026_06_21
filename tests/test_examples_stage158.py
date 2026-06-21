"""
阶段158测试：最小可运行示例与示例分类

验证:
1. quickstart.py 存在且可运行
2. intermediate.py 存在且可运行
3. examples/README.md 存在且有索引
4. 示例分级清晰
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestQuickstartExample:
    """验证快速入门示例"""

    def test_quickstart_exists(self):
        """quickstart.py 应存在"""
        assert (PROJECT_ROOT / "examples" / "quickstart.py").is_file()

    def test_quickstart_runs(self):
        """quickstart.py 应能正常运行"""
        result = subprocess.run(
            [sys.executable, "examples/quickstart.py"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            env={**os.environ, "SKIP_LLM_INIT": "true"},
        )
        assert result.returncode == 0, f"quickstart 运行失败: {result.stderr}"
        assert "快速入门" in result.stdout

    def test_quickstart_has_5_steps(self):
        """quickstart 应有5个步骤"""
        result = subprocess.run(
            [sys.executable, "examples/quickstart.py"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            env={**os.environ, "SKIP_LLM_INIT": "true"},
        )
        assert "[1/5]" in result.stdout
        assert "[5/5]" in result.stdout

    def test_quickstart_shows_next_steps(self):
        """quickstart 应显示下一步指引"""
        result = subprocess.run(
            [sys.executable, "examples/quickstart.py"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            env={**os.environ, "SKIP_LLM_INIT": "true"},
        )
        assert "下一步" in result.stdout

    def test_quickstart_no_llm_required(self):
        """quickstart 不应需要 LLM 配置"""
        result = subprocess.run(
            [sys.executable, "examples/quickstart.py"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            env={**os.environ, "SKIP_LLM_INIT": "true", "SILICONFLOW_API_KEY": ""},
        )
        assert result.returncode == 0


class TestIntermediateExample:
    """验证中级示例"""

    def test_intermediate_exists(self):
        """intermediate.py 应存在"""
        assert (PROJECT_ROOT / "examples" / "intermediate.py").is_file()

    def test_intermediate_runs(self):
        """intermediate.py 应能正常运行"""
        result = subprocess.run(
            [sys.executable, "examples/intermediate.py"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            env={**os.environ, "SKIP_LLM_INIT": "true"},
        )
        assert result.returncode == 0, f"intermediate 运行失败: {result.stderr}"
        assert "中级示例" in result.stdout

    def test_intermediate_has_demos(self):
        """intermediate 应包含任务执行、代码审查、性能监控"""
        result = subprocess.run(
            [sys.executable, "examples/intermediate.py"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            env={**os.environ, "SKIP_LLM_INIT": "true"},
        )
        assert "任务执行" in result.stdout
        assert "代码审查" in result.stdout
        assert "性能监控" in result.stdout


class TestExamplesReadme:
    """验证示例索引文档"""

    def test_readme_exists(self):
        """examples/README.md 应存在"""
        assert (PROJECT_ROOT / "examples" / "README.md").is_file()

    def test_readme_has_classification(self):
        """README 应有难度分级"""
        content = (PROJECT_ROOT / "examples" / "README.md").read_text()
        assert "快速入门" in content
        assert "中级" in content
        assert "高级" in content

    def test_readme_lists_all_examples(self):
        """README 应列出所有示例"""
        content = (PROJECT_ROOT / "examples" / "README.md").read_text()
        assert "quickstart.py" in content
        assert "intermediate.py" in content
        assert "full_workflow.py" in content
        assert "api_workflow.py" in content

    def test_readme_has_run_instructions(self):
        """README 应有运行方式说明"""
        content = (PROJECT_ROOT / "examples" / "README.md").read_text()
        assert "python examples/" in content

    def test_readme_has_prerequisites(self):
        """README 应有运行前提说明"""
        content = (PROJECT_ROOT / "examples" / "README.md").read_text()
        assert "前提" in content or "依赖" in content


class TestExampleProgression:
    """验证示例难度递进"""

    def test_three_difficulty_levels(self):
        """应有三个难度级别"""
        examples_dir = PROJECT_ROOT / "examples"
        # 快速入门
        assert (examples_dir / "quickstart.py").is_file()
        # 中级
        assert (examples_dir / "intermediate.py").is_file()
        # 高级（已有）
        assert (examples_dir / "full_workflow.py").is_file()

    def test_quickstart_is_simplest(self):
        """quickstart 应是最简短的"""
        quickstart_lines = len((PROJECT_ROOT / "examples" / "quickstart.py").read_text().splitlines())
        intermediate_lines = len((PROJECT_ROOT / "examples" / "intermediate.py").read_text().splitlines())
        full_lines = len((PROJECT_ROOT / "examples" / "full_workflow.py").read_text().splitlines())
        # quickstart 应最短
        assert quickstart_lines < intermediate_lines
        assert quickstart_lines < full_lines
