"""
阶段57: 持续集成接口标准化

第一性原理:
1. 代码变更必须自动验证：人工测试不可靠
2. 集成必须频繁：小步快跑，快速反馈
3. 构建必须可重复：相同输入产生相同输出

设计原则:
- Pipeline: CI流水线
- PipelineStage: 流水线阶段
- BuildArtifact: 构建产物
- CIEngine: CI引擎
- 支持阶段依赖、并行执行、失败重试
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum


class StageStatus(Enum):
    """阶段状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class PipelineStatus(Enum):
    """流水线状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class BuildArtifact:
    """构建产物"""
    artifact_id: str
    name: str
    path: str
    checksum: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StageResult:
    """阶段执行结果"""
    stage_id: str
    status: StageStatus
    output: str = ""
    error: str = ""
    elapsed_ms: float = 0.0
    artifacts: List[BuildArtifact] = field(default_factory=list)


# ============================================================
# 流水线阶段
# ============================================================

class PipelineStage:
    """
    流水线阶段

    CI流水线中的单个执行步骤
    """

    def __init__(
        self,
        stage_id: str,
        fn: Callable[..., Any],
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        dependencies: Optional[List[str]] = None,
        retries: int = 0,
        timeout_ms: float = 60000.0,
    ):
        self.stage_id = stage_id
        self.fn = fn
        self.args = args
        self.kwargs = kwargs or {}
        self.dependencies = dependencies or []
        self.retries = retries
        self.timeout_ms = timeout_ms

    def execute(self) -> StageResult:
        """执行阶段"""
        start = time.time()
        last_error = ""

        for attempt in range(self.retries + 1):
            try:
                result = self.fn(*self.args, **self.kwargs)
                elapsed = (time.time() - start) * 1000
                return StageResult(
                    stage_id=self.stage_id,
                    status=StageStatus.SUCCESS,
                    output=str(result) if result is not None else "",
                    elapsed_ms=elapsed,
                )
            except Exception as e:
                last_error = str(e)
                if attempt < self.retries:
                    time.sleep(0.1 * (2 ** attempt))
                    continue

        elapsed = (time.time() - start) * 1000
        return StageResult(
            stage_id=self.stage_id,
            status=StageStatus.FAILED,
            error=last_error,
            elapsed_ms=elapsed,
        )


# ============================================================
# 流水线
# ============================================================

class Pipeline:
    """
    CI流水线

    由多个阶段组成的有向无环图
    """

    def __init__(self, pipeline_id: str):
        self.pipeline_id = pipeline_id
        self._stages: Dict[str, PipelineStage] = {}
        self._results: Dict[str, StageResult] = {}
        self._status = PipelineStatus.PENDING
        self._lock = threading.Lock()

    def add_stage(self, stage: PipelineStage) -> None:
        """添加阶段"""
        self._stages[stage.stage_id] = stage

    def get_ready_stages(self) -> List[str]:
        """获取可执行的阶段"""
        ready = []
        with self._lock:
            for stage_id, stage in self._stages.items():
                if stage_id in self._results:
                    continue
                deps_satisfied = all(
                    dep in self._results and self._results[dep].status == StageStatus.SUCCESS
                    for dep in stage.dependencies
                )
                if deps_satisfied:
                    ready.append(stage_id)
        return ready

    def record_result(self, result: StageResult) -> None:
        """记录阶段结果"""
        with self._lock:
            self._results[result.stage_id] = result

    def is_complete(self) -> bool:
        """是否全部完成"""
        with self._lock:
            return len(self._results) == len(self._stages)

    def get_status(self) -> PipelineStatus:
        with self._lock:
            return self._status

    def set_status(self, status: PipelineStatus) -> None:
        with self._lock:
            self._status = status

    def get_results(self) -> Dict[str, StageResult]:
        with self._lock:
            return dict(self._results)

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "pipeline_id": self.pipeline_id,
                "total_stages": len(self._stages),
                "completed_stages": len(self._results),
                "status": self._status.value,
            }


# ============================================================
# CI引擎
# ============================================================

class CIEngine:
    """
    CI引擎

    执行流水线，管理构建产物
    """

    def __init__(self):
        self._pipelines: Dict[str, Pipeline] = {}
        self._artifacts: Dict[str, BuildArtifact] = {}
        self._lock = threading.Lock()

    def register_pipeline(self, pipeline: Pipeline) -> None:
        """注册流水线"""
        with self._lock:
            self._pipelines[pipeline.pipeline_id] = pipeline

    def run_pipeline(self, pipeline_id: str) -> Dict[str, StageResult]:
        """执行流水线"""
        pipeline = self._pipelines.get(pipeline_id)
        if pipeline is None:
            raise ValueError(f"Pipeline '{pipeline_id}' not found")

        pipeline.set_status(PipelineStatus.RUNNING)

        while not pipeline.is_complete():
            ready = pipeline.get_ready_stages()
            if not ready:
                break

            for stage_id in ready:
                stage = pipeline._stages[stage_id]
                result = stage.execute()
                pipeline.record_result(result)

            # 检查失败
            results = pipeline.get_results()
            if any(r.status == StageStatus.FAILED for r in results.values()):
                pipeline.set_status(PipelineStatus.FAILED)
                return pipeline.get_results()

        pipeline.set_status(PipelineStatus.SUCCESS)
        return pipeline.get_results()

    def store_artifact(self, artifact: BuildArtifact) -> None:
        """存储构建产物"""
        with self._lock:
            self._artifacts[artifact.artifact_id] = artifact

    def get_artifact(self, artifact_id: str) -> Optional[BuildArtifact]:
        """获取构建产物"""
        with self._lock:
            return self._artifacts.get(artifact_id)

    def list_artifacts(self) -> List[BuildArtifact]:
        """列出所有构建产物"""
        with self._lock:
            return list(self._artifacts.values())

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "total_pipelines": len(self._pipelines),
                "total_artifacts": len(self._artifacts),
            }


# ============================================================
# 便捷函数
# ============================================================

def create_pipeline(pipeline_id: str) -> Pipeline:
    """创建流水线"""
    return Pipeline(pipeline_id)


def create_stage(
    stage_id: str,
    fn: Callable[..., Any],
    *args,
    dependencies: Optional[List[str]] = None,
    retries: int = 0,
    **kwargs,
) -> PipelineStage:
    """创建流水线阶段"""
    return PipelineStage(
        stage_id=stage_id,
        fn=fn,
        args=args,
        kwargs=kwargs,
        dependencies=dependencies,
        retries=retries,
    )


def create_ci_engine() -> CIEngine:
    """创建CI引擎"""
    return CIEngine()
