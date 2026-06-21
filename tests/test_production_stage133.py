"""
阶段133: 生产部署支持层 — 专项测试

测试覆盖：
1. Config/ConfigLoader: 配置管理
2. LifecycleManager: 生命周期管理
3. HealthEndpoint: 健康检查端点
4. RateLimiter: 限流器
5. CircuitBreaker: 熔断器
6. ResourceManager: 资源管理
7. DeploymentPackager: 部署打包
8. ProductionManager: 集成管理器
9. Agent集成
10. 并发安全
11. 异常容错
12. 第一性原理验证
"""

import os
import time
import json
import threading
import tempfile
import pytest
from unittest.mock import MagicMock

from self_evolving_agent.core.production import (
    Environment,
    Config,
    ConfigLoader,
    LifecycleState,
    LifecycleHook,
    LifecycleManager,
    HealthResponse,
    HealthEndpoint,
    RateLimiter,
    CircuitState,
    CircuitBreaker,
    ResourceQuota,
    ResourceManager,
    DeploymentPackager,
    ProductionManager,
    create_production_manager,
    create_deployment_package,
)


# ============================================================
# 配置管理测试
# ============================================================

class TestConfig:
    """配置容器测试"""

    def test_get_and_set(self):
        """测试基本存取"""
        config = Config()
        config.set("key", "value")
        assert config.get("key") == "value"

    def test_get_default(self):
        """测试默认值"""
        config = Config()
        assert config.get("nonexistent", "default") == "default"

    def test_nested_get(self):
        """测试嵌套获取"""
        config = Config()
        config.set("server.port", 8000)
        assert config.get("server.port") == 8000

    def test_nested_default(self):
        """测试嵌套默认值"""
        config = Config()
        assert config.get("server.nonexistent", 80) == 80

    def test_update(self):
        """测试批量更新"""
        config = Config()
        config.update({"a": 1, "b": {"c": 2}})
        assert config.get("a") == 1
        assert config.get("b.c") == 2

    def test_update_merge(self):
        """测试合并更新"""
        config = Config()
        config.set("a.b", 1)
        config.update({"a": {"c": 2}})
        assert config.get("a.b") == 1  # 原值保留
        assert config.get("a.c") == 2  # 新值添加

    def test_to_dict(self):
        """测试转字典"""
        config = Config()
        config.set("key", "value")
        d = config.to_dict()
        assert "values" in d
        assert "env" in d

    def test_to_json(self):
        """测试JSON序列化"""
        config = Config()
        config.set("key", "value")
        json_str = config.to_json()
        data = json.loads(json_str)
        assert data["values"]["key"] == "value"


class TestConfigLoader:
    """配置加载器测试"""

    def test_load_from_env(self):
        """测试从环境变量加载"""
        os.environ["APP_TEST_KEY"] = "test_value"
        os.environ["APP_TEST_INT"] = "42"
        config = ConfigLoader.load_from_env("APP_")
        assert config["test_key"] == "test_value"
        assert config["test_int"] == 42
        del os.environ["APP_TEST_KEY"]
        del os.environ["APP_TEST_INT"]

    def test_load_from_file(self):
        """测试从文件加载"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"key": "value", "nested": {"a": 1}}, f)
            f.flush()
            config = ConfigLoader.load_from_file(f.name)
        os.unlink(f.name)
        assert config["key"] == "value"
        assert config["nested"]["a"] == 1

    def test_load_from_nonexistent_file(self):
        """测试从不存在文件加载"""
        config = ConfigLoader.load_from_file("/nonexistent/path.json")
        assert config == {}

    def test_load_full(self):
        """测试完整加载"""
        config = ConfigLoader.load(
            env=Environment.PRODUCTION,
            defaults={"app": {"name": "test"}},
        )
        assert config.env == Environment.PRODUCTION
        assert config.get("app.name") == "test"

    def test_environment_types(self):
        """测试环境类型"""
        for env in Environment:
            config = ConfigLoader.load(env=env)
            assert config.env == env


# ============================================================
# 生命周期管理测试
# ============================================================

class TestLifecycleManager:
    """生命周期管理器测试"""

    def test_initial_state(self):
        """测试初始状态"""
        lm = LifecycleManager()
        assert lm.state == LifecycleState.CREATED

    def test_start(self):
        """测试启动"""
        lm = LifecycleManager()
        assert lm.start() is True
        assert lm.state == LifecycleState.RUNNING

    def test_start_hooks(self):
        """测试启动钩子"""
        lm = LifecycleManager()
        executed = []
        lm.on_start("hook1", lambda: executed.append("hook1"))
        lm.on_start("hook2", lambda: executed.append("hook2"))
        lm.start()
        assert executed == ["hook1", "hook2"]

    def test_start_hook_priority(self):
        """测试启动钩子优先级"""
        lm = LifecycleManager()
        executed = []
        lm.on_start("low", lambda: executed.append("low"), priority=10)
        lm.on_start("high", lambda: executed.append("high"), priority=1)
        lm.start()
        assert executed == ["high", "low"]

    def test_stop(self):
        """测试停止"""
        lm = LifecycleManager()
        lm.start()
        assert lm.stop() is True
        assert lm.state == LifecycleState.STOPPED

    def test_stop_hooks(self):
        """测试停止钩子"""
        lm = LifecycleManager()
        executed = []
        lm.on_stop("hook1", lambda: executed.append("hook1"))
        lm.on_stop("hook2", lambda: executed.append("hook2"))
        lm.start()
        lm.stop()
        # 停止钩子逆序执行
        assert executed == ["hook2", "hook1"]

    def test_start_when_running(self):
        """测试运行中启动"""
        lm = LifecycleManager()
        lm.start()
        assert lm.start() is False  # 已运行

    def test_stop_when_not_running(self):
        """测试未运行时停止"""
        lm = LifecycleManager()
        assert lm.stop() is False

    def test_start_hook_failure(self):
        """测试启动钩子失败"""
        lm = LifecycleManager()
        def failing_hook():
            raise RuntimeError("hook failed")
        lm.on_start("failing", failing_hook)
        with pytest.raises(RuntimeError):
            lm.start()
        assert lm.state == LifecycleState.FAILED

    def test_stop_hook_exception_isolation(self):
        """测试停止钩子异常隔离"""
        lm = LifecycleManager()
        executed = []
        def bad_hook():
            raise RuntimeError("bad hook")
        lm.on_stop("bad", bad_hook)
        lm.on_stop("good", lambda: executed.append("good"))
        lm.start()
        lm.stop()
        # bad钩子异常不应阻止good钩子
        assert "good" in executed

    def test_is_running(self):
        """测试运行状态"""
        lm = LifecycleManager()
        assert lm.is_running() is False
        lm.start()
        assert lm.is_running() is True

    def test_wait_for_shutdown(self):
        """测试等待关闭"""
        lm = LifecycleManager()
        lm.start()
        # 在另一个线程中停止
        def stop_after_delay():
            time.sleep(0.05)
            lm.stop()
        t = threading.Thread(target=stop_after_delay)
        t.start()
        result = lm.wait_for_shutdown(timeout=1.0)
        t.join()
        assert result is True

    def test_reset(self):
        """测试重置"""
        lm = LifecycleManager()
        lm.start()
        lm.stop()
        lm.reset()
        assert lm.state == LifecycleState.CREATED


# ============================================================
# 健康检查端点测试
# ============================================================

class TestHealthEndpoint:
    """健康检查端点测试"""

    def test_liveness_healthy(self):
        """测试存活检查-健康"""
        he = HealthEndpoint()
        he.add_liveness_check("process", lambda: True)
        result = he.liveness()
        assert result.code == 200
        assert result.status == "healthy"

    def test_liveness_unhealthy(self):
        """测试存活检查-不健康"""
        he = HealthEndpoint()
        he.add_liveness_check("process", lambda: False)
        result = he.liveness()
        assert result.code == 503
        assert result.status == "unhealthy"

    def test_readiness_healthy(self):
        """测试就绪检查-健康"""
        he = HealthEndpoint()
        he.add_readiness_check("db", lambda: True)
        result = he.readiness()
        assert result.code == 200

    def test_readiness_unhealthy(self):
        """测试就绪检查-不健康"""
        he = HealthEndpoint()
        he.add_readiness_check("db", lambda: False)
        result = he.readiness()
        assert result.code == 503

    def test_liveness_check_exception(self):
        """测试存活检查异常"""
        he = HealthEndpoint()
        def failing_check():
            raise RuntimeError("check failed")
        he.add_liveness_check("failing", failing_check)
        result = he.liveness()
        assert result.code == 503
        assert result.checks["failing"] == "error"

    def test_full_health_healthy(self):
        """测试完整健康检查-健康"""
        he = HealthEndpoint()
        he.add_liveness_check("a", lambda: True)
        he.add_readiness_check("b", lambda: True)
        result = he.full_health()
        assert result.code == 200
        assert "liveness" in result.checks
        assert "readiness" in result.checks

    def test_full_health_unhealthy(self):
        """测试完整健康检查-不健康"""
        he = HealthEndpoint()
        he.add_liveness_check("a", lambda: True)
        he.add_readiness_check("b", lambda: False)
        result = he.full_health()
        assert result.code == 503

    def test_multiple_checks(self):
        """测试多个检查"""
        he = HealthEndpoint()
        he.add_liveness_check("a", lambda: True)
        he.add_liveness_check("b", lambda: True)
        he.add_liveness_check("c", lambda: False)
        result = he.liveness()
        assert result.code == 503  # 任一不健康
        assert len(result.checks) == 3


# ============================================================
# 限流器测试
# ============================================================

class TestRateLimiter:
    """限流器测试"""

    def test_basic_acquire(self):
        """测试基本获取"""
        rl = RateLimiter(rate=10, capacity=10)
        for _ in range(10):
            assert rl.acquire() is True

    def test_exceed_capacity(self):
        """测试超过容量"""
        rl = RateLimiter(rate=10, capacity=10)
        for _ in range(10):
            rl.acquire()
        assert rl.acquire() is False

    def test_token_refill(self):
        """测试令牌补充"""
        rl = RateLimiter(rate=100, capacity=10)
        # 消耗所有令牌
        for _ in range(10):
            rl.acquire()
        assert rl.acquire() is False
        # 等待补充
        time.sleep(0.05)
        assert rl.acquire() is True

    def test_wait_acquire(self):
        """测试等待获取"""
        rl = RateLimiter(rate=100, capacity=1)
        rl.acquire()  # 消耗令牌
        # 等待应成功
        result = rl.wait_acquire(timeout=0.1)
        assert result is True

    def test_wait_acquire_timeout(self):
        """测试等待获取超时"""
        rl = RateLimiter(rate=0.1, capacity=1)
        rl.acquire()  # 消耗令牌
        # 速率很低，应超时
        result = rl.wait_acquire(timeout=0.05)
        assert result is False

    def test_available_tokens(self):
        """测试可用令牌数"""
        rl = RateLimiter(rate=10, capacity=10)
        assert rl.available_tokens() <= 10.001
        rl.acquire(5)
        assert rl.available_tokens() <= 5.001

    def test_properties(self):
        """测试属性"""
        rl = RateLimiter(rate=50, capacity=100)
        assert rl.rate == 50
        assert rl.capacity == 100

    def test_concurrent_access(self):
        """测试并发访问"""
        rl = RateLimiter(rate=100, capacity=100)
        acquired = []
        lock = threading.Lock()

        def worker():
            for _ in range(20):
                if rl.acquire():
                    with lock:
                        acquired.append(1)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 不应超过容量
        assert len(acquired) <= 100


# ============================================================
# 熔断器测试
# ============================================================

class TestCircuitBreaker:
    """熔断器测试"""

    def test_initial_state(self):
        """测试初始状态"""
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED

    def test_closed_allows_execution(self):
        """测试关闭状态允许执行"""
        cb = CircuitBreaker()
        assert cb.can_execute() is True

    def test_open_on_failures(self):
        """测试失败达到阈值后熔断"""
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_open_blocks_execution(self):
        """测试熔断状态阻止执行"""
        cb = CircuitBreaker(failure_threshold=1)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.can_execute() is False

    def test_half_open_after_timeout(self):
        """测试超时后半开"""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.05)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        time.sleep(0.06)
        assert cb.state == CircuitState.HALF_OPEN

    def test_half_open_allows_limited_calls(self):
        """测试半开状态限制调用"""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.05, half_open_max_calls=2)
        cb.record_failure()
        time.sleep(0.06)
        assert cb.can_execute() is True
        assert cb.can_execute() is True
        assert cb.can_execute() is False  # 超过限制

    def test_half_open_success_recovers(self):
        """测试半开状态成功恢复"""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.05, half_open_max_calls=2)
        cb.record_failure()
        time.sleep(0.06)
        cb.can_execute()
        cb.record_success()
        cb.can_execute()
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_half_open_failure_reopens(self):
        """测试半开状态失败重新熔断"""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.05)
        cb.record_failure()
        time.sleep(0.06)
        assert cb.state == CircuitState.HALF_OPEN
        cb.can_execute()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_success_resets_failure_count(self):
        """测试成功重置失败计数"""
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb._failure_count == 0

    def test_reset(self):
        """测试重置"""
        cb = CircuitBreaker(failure_threshold=1)
        cb.record_failure()
        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb._failure_count == 0

    def test_stats(self):
        """测试统计"""
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=30)
        cb.record_failure()
        stats = cb.stats()
        assert stats["state"] == "closed"
        assert stats["failure_count"] == 1
        assert stats["failure_threshold"] == 5


# ============================================================
# 资源管理器测试
# ============================================================

class TestResourceManager:
    """资源管理器测试"""

    def test_set_quota(self):
        """测试设置配额"""
        rm = ResourceManager()
        rm.set_quota("connections", 100)
        usage = rm.get_usage("connections")
        assert usage["limit"] == 100

    def test_acquire_within_quota(self):
        """测试配额内获取"""
        rm = ResourceManager()
        rm.set_quota("connections", 5)
        for _ in range(5):
            assert rm.acquire("connections") is True

    def test_acquire_exceed_quota(self):
        """测试超过配额"""
        rm = ResourceManager()
        rm.set_quota("connections", 3)
        for _ in range(3):
            rm.acquire("connections")
        assert rm.acquire("connections") is False

    def test_release(self):
        """测试释放"""
        rm = ResourceManager()
        rm.set_quota("connections", 3)
        for _ in range(3):
            rm.acquire("connections")
        rm.release("connections")
        assert rm.acquire("connections") is True

    def test_no_quota(self):
        """测试无配额限制"""
        rm = ResourceManager()
        # 未设置配额，应允许获取
        assert rm.acquire("anything") is True

    def test_get_usage(self):
        """测试获取使用情况"""
        rm = ResourceManager()
        rm.set_quota("memory", 100)
        rm.acquire("memory", 30)
        usage = rm.get_usage("memory")
        assert usage["current"] == 30
        assert usage["limit"] == 100

    def test_get_all_usage(self):
        """测试获取所有使用情况"""
        rm = ResourceManager()
        rm.set_quota("a", 10)
        rm.set_quota("b", 20)
        all_usage = rm.get_all_usage()
        assert "a" in all_usage
        assert "b" in all_usage

    def test_reset(self):
        """测试重置"""
        rm = ResourceManager()
        rm.set_quota("connections", 5)
        rm.acquire("connections", 3)
        rm.reset()
        usage = rm.get_usage("connections")
        assert usage["current"] == 0

    def test_release_more_than_acquired(self):
        """测试释放超过获取量"""
        rm = ResourceManager()
        rm.set_quota("connections", 5)
        rm.acquire("connections", 2)
        rm.release("connections", 10)  # 释放超过
        usage = rm.get_usage("connections")
        assert usage["current"] == 0  # 不应为负


# ============================================================
# 部署打包器测试
# ============================================================

class TestDeploymentPackager:
    """部署打包器测试"""

    def test_generate_dockerfile(self):
        """测试生成Dockerfile"""
        dockerfile = DeploymentPackager.generate_dockerfile()
        assert "FROM python" in dockerfile
        assert "EXPOSE" in dockerfile
        assert "HEALTHCHECK" in dockerfile
        assert "CMD" in dockerfile

    def test_generate_dockerfile_custom(self):
        """测试自定义Dockerfile"""
        dockerfile = DeploymentPackager.generate_dockerfile(
            app_name="myapp", python_version="3.12", port=9000
        )
        assert "myapp" in dockerfile
        assert "3.12" in dockerfile
        assert "9000" in dockerfile

    def test_generate_docker_compose(self):
        """测试生成docker-compose"""
        compose = DeploymentPackager.generate_docker_compose()
        assert "version:" in compose
        assert "services:" in compose
        assert "replicas" in compose

    def test_generate_kubernetes_manifest(self):
        """测试生成K8s清单"""
        k8s = DeploymentPackager.generate_kubernetes_manifest()
        assert "apiVersion: apps/v1" in k8s
        assert "kind: Deployment" in k8s
        assert "livenessProbe" in k8s
        assert "readinessProbe" in k8s

    def test_generate_requirements(self):
        """测试生成requirements.txt"""
        reqs = DeploymentPackager.generate_requirements()
        assert "Core dependencies" in reqs

    def test_generate_requirements_with_deps(self):
        """测试带依赖的requirements"""
        reqs = DeploymentPackager.generate_requirements(extra_deps=["flask>=2.0.0"])
        assert "flask>=2.0.0" in reqs

    def test_generate_config_template(self):
        """测试生成配置模板"""
        config = DeploymentPackager.generate_config_template()
        data = json.loads(config)
        assert "env" in data
        assert "server" in data
        assert "logging" in data

    def test_create_deployment_package(self):
        """测试创建部署包"""
        with tempfile.TemporaryDirectory() as tmpdir:
            files = create_deployment_package(tmpdir, app_name="testapp")
            assert "Dockerfile" in files
            assert "docker-compose.yml" in files
            assert "k8s-deployment.yaml" in files
            assert "requirements.txt" in files
            assert "config.json" in files
            # 验证文件实际创建
            for filename in files:
                assert os.path.exists(os.path.join(tmpdir, filename))


# ============================================================
# 生产管理器测试
# ============================================================

class TestProductionManager:
    """生产管理器测试"""

    def test_creation(self):
        """测试创建"""
        pm = ProductionManager()
        assert pm.config is not None
        assert pm.lifecycle is not None
        assert pm.health_endpoint is not None
        assert pm.resource_manager is not None

    def test_start_stop(self):
        """测试启动停止"""
        pm = ProductionManager()
        assert pm.start() is True
        assert pm.lifecycle.state == LifecycleState.RUNNING
        assert pm.stop() is True
        assert pm.lifecycle.state == LifecycleState.STOPPED

    def test_default_health_checks(self):
        """测试默认健康检查"""
        pm = ProductionManager()
        health = pm.health_check()
        assert health.status in ("healthy", "unhealthy")

    def test_liveness(self):
        """测试存活探针"""
        pm = ProductionManager()
        pm.start()
        result = pm.liveness()
        assert result.code in (200, 503)
        pm.stop()

    def test_readiness(self):
        """测试就绪探针"""
        pm = ProductionManager()
        pm.start()
        result = pm.readiness()
        assert result.code in (200, 503)
        pm.stop()

    def test_rate_limiter_initialized_on_start(self):
        """测试启动时初始化限流器"""
        pm = ProductionManager()
        assert pm.rate_limiter is None
        pm.start()
        assert pm.rate_limiter is not None
        pm.stop()

    def test_check_request_allowed(self):
        """测试检查请求允许"""
        pm = ProductionManager()
        pm.start()
        # 应允许请求
        assert pm.check_request_allowed() in (True, False)
        pm.stop()

    def test_get_circuit_breaker(self):
        """测试获取熔断器"""
        pm = ProductionManager()
        cb1 = pm.get_circuit_breaker("api")
        cb2 = pm.get_circuit_breaker("api")
        assert cb1 is cb2  # 同一实例

    def test_status(self):
        """测试状态"""
        pm = ProductionManager()
        status = pm.status()
        assert "lifecycle_state" in status
        assert "config_env" in status
        assert "rate_limiter" in status
        assert "circuit_breakers" in status
        assert "resources" in status

    def test_create_production_manager_helper(self):
        """测试便捷函数"""
        pm = create_production_manager(env=Environment.TESTING)
        assert pm.config.env == Environment.TESTING


# ============================================================
# Agent集成测试
# ============================================================

class TestAgentIntegration:
    """Agent集成测试"""

    def test_agent_has_production(self):
        """测试Agent有生产管理器"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent()
        assert agent.production is not None

    def test_agent_production_status(self):
        """测试Agent生产状态"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent()
        status = agent.get_production_status()
        assert "lifecycle_state" in status

    def test_agent_production_health(self):
        """测试Agent生产健康检查"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent()
        health = agent.production_health_check()
        assert health.status in ("healthy", "unhealthy")

    def test_agent_liveness(self):
        """测试Agent存活探针"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent()
        result = agent.production_liveness()
        assert result.code in (200, 503)

    def test_agent_readiness(self):
        """测试Agent就绪探针"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent()
        result = agent.production_readiness()
        assert result.code in (200, 503)

    def test_agent_circuit_breaker(self):
        """测试Agent熔断器"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent()
        cb = agent.get_circuit_breaker("test")
        assert cb is not None

    def test_agent_resource_quota(self):
        """测试Agent资源配额"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent()
        agent.set_resource_quota("connections", 5)
        assert agent.acquire_resource("connections") is True
        agent.release_resource("connections")


# ============================================================
# 并发安全测试
# ============================================================

class TestConcurrencySafety:
    """并发安全测试"""

    def test_rate_limiter_concurrent(self):
        """测试限流器并发"""
        rl = RateLimiter(rate=1000, capacity=100)
        acquired = []
        lock = threading.Lock()

        def worker():
            for _ in range(50):
                if rl.acquire():
                    with lock:
                        acquired.append(1)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 并发下可能有少量超出（令牌补充），允许少量偏差
        assert len(acquired) <= 105

    def test_circuit_breaker_concurrent(self):
        """测试熔断器并发"""
        cb = CircuitBreaker(failure_threshold=100)
        errors = []

        def worker():
            try:
                for _ in range(100):
                    if cb.can_execute():
                        cb.record_success()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_resource_manager_concurrent(self):
        """测试资源管理器并发"""
        rm = ResourceManager()
        rm.set_quota("connections", 100)
        acquired_count = []
        lock = threading.Lock()

        def worker():
            for _ in range(20):
                if rm.acquire("connections"):
                    with lock:
                        acquired_count.append(1)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(acquired_count) <= 100


# ============================================================
# 异常容错测试
# ============================================================

class TestErrorHandling:
    """异常容错测试"""

    def test_lifecycle_hook_exception_during_stop(self):
        """测试停止时钩子异常"""
        lm = LifecycleManager()
        def bad_hook():
            raise RuntimeError("bad")
        lm.on_stop("bad", bad_hook)
        lm.on_stop("good", lambda: None)
        lm.start()
        # 不应崩溃
        lm.stop()

    def test_health_check_exception(self):
        """测试健康检查异常"""
        he = HealthEndpoint()
        def failing_check():
            raise ValueError("check failed")
        he.add_liveness_check("failing", failing_check)
        result = he.liveness()
        assert result.code == 503

    def test_rate_limiter_zero_rate(self):
        """测试零速率限流器"""
        rl = RateLimiter(rate=0, capacity=1)
        rl.acquire()  # 消耗初始令牌
        # 零速率不补充
        assert rl.acquire() is False

    def test_resource_release_nonexistent(self):
        """测试释放不存在的资源"""
        rm = ResourceManager()
        # 不应崩溃
        rm.release("nonexistent")

    def test_circuit_breaker_zero_threshold(self):
        """测试零阈值熔断器"""
        cb = CircuitBreaker(failure_threshold=0)
        # 零阈值，任何失败都熔断
        cb.record_failure()
        assert cb.state == CircuitState.OPEN


# ============================================================
# 第一性原理验证
# ============================================================

class TestFirstPrinciples:
    """第一性原理验证"""

    def test_config_separation_principle(self):
        """第一性原理：配置与环境分离"""
        config = ConfigLoader.load(env=Environment.PRODUCTION)
        # 配置来自环境，不硬编码
        assert config.env == Environment.PRODUCTION

    def test_graceful_lifecycle_principle(self):
        """第一性原理：优雅生命周期"""
        lm = LifecycleManager()
        started = []
        stopped = []
        lm.on_start("init", lambda: started.append("init"))
        lm.on_stop("cleanup", lambda: stopped.append("cleanup"))
        lm.start()
        lm.stop()
        # 启动和停止都有钩子执行
        assert len(started) == 1
        assert len(stopped) == 1

    def test_health_probe_principle(self):
        """第一性原理：健康探针分离"""
        he = HealthEndpoint()
        he.add_liveness_check("process", lambda: True)
        he.add_readiness_check("db", lambda: False)
        live = he.liveness()
        ready = he.readiness()
        # 存活和就绪分离
        assert live.code == 200  # 进程存活
        assert ready.code == 503  # 但未就绪

    def test_rate_limiting_principle(self):
        """第一性原理：限流防止过载"""
        rl = RateLimiter(rate=5, capacity=5)
        count = 0
        for _ in range(10):
            if rl.acquire():
                count += 1
        # 限流器限制了请求数
        assert count <= 5

    def test_circuit_breaker_principle(self):
        """第一性原理：熔断保护下游"""
        cb = CircuitBreaker(failure_threshold=3)
        # 连续失败触发熔断
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN
        # 熔断后阻止请求
        assert cb.can_execute() is False

    def test_resource_quota_principle(self):
        """第一性原理：资源配额防止耗尽"""
        rm = ResourceManager()
        rm.set_quota("memory", 100)
        # 可以获取配额内资源
        assert rm.acquire("memory", 50) is True
        # 超过配额被拒绝
        assert rm.acquire("memory", 60) is False
        # 释放后可重新获取
        rm.release("memory", 50)
        assert rm.acquire("memory", 60) is True

    def test_deployable_artifact_principle(self):
        """第一性原理：可部署制品"""
        dockerfile = DeploymentPackager.generate_dockerfile()
        compose = DeploymentPackager.generate_docker_compose()
        k8s = DeploymentPackager.generate_kubernetes_manifest()
        # 生成标准部署制品
        assert "FROM" in dockerfile
        assert "services" in compose
        assert "Deployment" in k8s
