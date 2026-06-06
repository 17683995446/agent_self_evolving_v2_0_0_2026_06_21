"""
阶段22验证：接口文档自动生成
"""
import sys
sys.path.insert(0, '/workspace')

from self_evolving_agent.core.doc_generator import (
    InterfaceDocGenerator, SystemDocGenerator, InterfaceDoc
)
from self_evolving_agent.core.interfaces import BaseModule, AgentMessage, MessageType


class TestModule(BaseModule):
    """测试模块，用于文档生成"""

    def __init__(self):
        super().__init__("test_module")

    def predict(self, state: dict, horizon: int = 1) -> dict:
        """预测未来状态"""
        return {}

    def update(self, error: float) -> None:
        """更新模型"""
        pass

    def handle_message(self, message: AgentMessage):
        if message.msg_type == MessageType.STATE_UPDATE:
            return AgentMessage(msg_type=MessageType.PREDICTION, source="test")
        return None


def test_scan_module():
    """测试扫描模块"""
    print("=" * 60)
    print("测试: 扫描模块")
    print("=" * 60)

    generator = InterfaceDocGenerator()
    doc = generator.scan_module(TestModule)

    print(f"模块名: {doc.name}")
    print(f"模块路径: {doc.module_path}")
    print(f"描述: {doc.description}")
    print(f"方法数: {len(doc.methods)}")
    print(f"消息类型: {doc.message_types}")

    assert doc.name == "TestModule"
    assert len(doc.methods) >= 3  # predict, update, handle_message
    assert "STATE_UPDATE" in doc.message_types
    assert "PREDICTION" in doc.message_types

    print("\n扫描模块测试通过!")
    return True


def test_generate_markdown():
    """测试生成Markdown"""
    print("\n" + "=" * 60)
    print("测试: 生成Markdown")
    print("=" * 60)

    generator = InterfaceDocGenerator()
    generator.scan_module(TestModule)

    markdown = generator.generate_markdown("TestModule")
    print(f"生成的Markdown ({len(markdown)} 字符):")
    print(markdown[:500])
    print("...")

    assert "# TestModule" in markdown
    assert "predict" in markdown
    assert "update" in markdown

    print("\n生成Markdown测试通过!")
    return True


def test_generate_json():
    """测试生成JSON"""
    print("\n" + "=" * 60)
    print("测试: 生成JSON")
    print("=" * 60)

    generator = InterfaceDocGenerator()
    generator.scan_module(TestModule)

    json_doc = generator.generate_json("TestModule")
    print(f"生成的JSON ({len(json_doc)} 字符):")
    print(json_doc[:500])
    print("...")

    import json
    data = json.loads(json_doc)
    assert data["name"] == "TestModule"
    assert "methods" in data
    assert "generated_at" in data

    print("\n生成JSON测试通过!")
    return True


def test_list_interfaces():
    """测试列出接口"""
    print("\n" + "=" * 60)
    print("测试: 列出接口")
    print("=" * 60)

    generator = InterfaceDocGenerator()
    generator.scan_module(TestModule)

    interfaces = generator.list_interfaces()
    print(f"接口列表: {interfaces}")
    assert "TestModule" in interfaces

    print("\n列出接口测试通过!")
    return True


def test_system_doc_generator():
    """测试系统文档生成器"""
    print("\n" + "=" * 60)
    print("测试: 系统文档生成器")
    print("=" * 60)

    system_gen = SystemDocGenerator()
    system_gen.scan_all_modules([TestModule])

    doc = system_gen.generate_system_doc()
    print(f"系统文档 ({len(doc)} 字符):")
    print(doc[:500])
    print("...")

    assert "# 自驱永续进化Agent系统" in doc
    assert "TestModule" in doc

    print("\n系统文档生成器测试通过!")
    return True


def test_save_docs():
    """测试保存文档"""
    print("\n" + "=" * 60)
    print("测试: 保存文档")
    print("=" * 60)

    import os
    import tempfile

    system_gen = SystemDocGenerator()
    system_gen.scan_all_modules([TestModule])

    with tempfile.TemporaryDirectory() as tmpdir:
        system_gen.save_docs(tmpdir, format="markdown")

        # 检查文件
        files = os.listdir(tmpdir)
        print(f"生成的文件: {files}")
        assert "system_api.md" in files
        assert any("testmodule" in f.lower() for f in files)

        # 检查内容
        with open(os.path.join(tmpdir, "system_api.md"), "r") as f:
            content = f.read()
            assert "TestModule" in content

    print("\n保存文档测试通过!")
    return True


def test_get_doc():
    """测试获取文档对象"""
    print("\n" + "=" * 60)
    print("测试: 获取文档对象")
    print("=" * 60)

    generator = InterfaceDocGenerator()
    generator.scan_module(TestModule)

    doc = generator.get_doc("TestModule")
    assert doc is not None
    assert isinstance(doc, InterfaceDoc)
    assert doc.name == "TestModule"

    # 不存在的接口
    doc2 = generator.get_doc("NonExistent")
    assert doc2 is None

    print("\n获取文档对象测试通过!")
    return True


def run_all_tests():
    print("\n" + "=" * 60)
    print("阶段22: 接口文档自动生成 — 验证测试")
    print("=" * 60)

    tests = [
        ("扫描模块", test_scan_module),
        ("生成Markdown", test_generate_markdown),
        ("生成JSON", test_generate_json),
        ("列出接口", test_list_interfaces),
        ("系统文档生成器", test_system_doc_generator),
        ("保存文档", test_save_docs),
        ("获取文档对象", test_get_doc),
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
