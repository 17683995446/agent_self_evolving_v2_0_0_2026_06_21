"""
阶段59验证: 自动化测试接口标准化
"""
import sys
import importlib.util

spec = importlib.util.spec_from_file_location("at", "/workspace/self_evolving_agent/core/auto_testing.py")
mod = importlib.util.module_from_spec(spec)
sys.modules["at"] = mod
spec.loader.exec_module(mod)

print("=" * 60)
print("阶段59验证: 自动化测试接口标准化")
print("=" * 60)

# 测试1: 测试用例通过
def test_case_pass():
    tc = mod.create_test_case("t1", lambda: None)
    result = tc.run()
    assert result.status == mod.TestStatus.PASSED
    assert result.test_id == "t1"
    print("  [test_case_pass] 测试通过 OK")

# 测试2: 测试用例失败
def test_case_fail():
    tc = mod.create_test_case("t2", lambda: (_ for _ in ()).throw(AssertionError("fail")))
    result = tc.run()
    assert result.status == mod.TestStatus.FAILED
    assert "fail" in result.error
    print("  [test_case_fail] 测试失败 OK")

# 测试3: 测试用例异常
def test_case_error():
    tc = mod.create_test_case("t3", lambda: 1 / 0)
    result = tc.run()
    assert result.status == mod.TestStatus.ERROR
    assert "division by zero" in result.error
    print("  [test_case_error] 测试异常 OK")

# 测试4: setup和teardown
def test_setup_teardown():
    state = {"setup": False, "teardown": False}
    def setup():
        state["setup"] = True
    def teardown():
        state["teardown"] = True
    def test_fn():
        assert state["setup"] is True

    tc = mod.create_test_case("t4", test_fn, setup=setup, teardown=teardown)
    result = tc.run()
    assert result.status == mod.TestStatus.PASSED
    assert state["teardown"] is True
    print("  [test_setup_teardown] setup/teardown OK")

# 测试5: 测试套件
def test_suite():
    suite = mod.create_test_suite("suite1")
    suite.add_test(mod.create_test_case("a", lambda: None))
    suite.add_test(mod.create_test_case("b", lambda: None))
    assert suite.get_stats()["total_tests"] == 2
    print("  [test_suite] 测试套件 OK")

# 测试6: 测试运行器和报告
def test_runner():
    suite = mod.create_test_suite("suite2")
    suite.add_test(mod.create_test_case("pass1", lambda: None))
    suite.add_test(mod.create_test_case("fail1", lambda: (_ for _ in ()).throw(AssertionError("no"))))
    suite.add_test(mod.create_test_case("pass2", lambda: None))

    runner = mod.create_test_runner()
    report = runner.run(suite)

    summary = report.get_summary()
    assert summary["total"] == 3
    assert summary["passed"] == 2
    assert summary["failed"] == 1
    assert summary["success_rate"] == 2 / 3
    assert len(report.get_failures()) == 1
    print("  [test_runner] 测试运行器 OK")

# 测试7: 并行执行
def test_parallel():
    suite = mod.create_test_suite("suite3")
    for i in range(5):
        suite.add_test(mod.create_test_case(f"p{i}", lambda: None))

    runner = mod.create_test_runner(parallel=True)
    report = runner.run(suite)
    assert report.get_summary()["passed"] == 5
    print("  [test_parallel] 并行执行 OK")

# 测试8: 参数化测试
def test_parameterized():
    def check_positive(x):
        assert x > 0

    params = [((1,), {}), ((2,), {}), ((3,), {})]
    tests = mod.parameterized_test("pos", check_positive, params)
    assert len(tests) == 3

    suite = mod.create_test_suite("suite4")
    suite.add_tests(tests)
    runner = mod.create_test_runner()
    report = runner.run(suite)
    assert report.get_summary()["passed"] == 3
    print("  [test_parameterized] 参数化测试 OK")

if __name__ == "__main__":
    test_case_pass()
    test_case_fail()
    test_case_error()
    test_setup_teardown()
    test_suite()
    test_runner()
    test_parallel()
    test_parameterized()
    print("=" * 60)
    print("阶段59验证通过 ✓")
    print("=" * 60)
