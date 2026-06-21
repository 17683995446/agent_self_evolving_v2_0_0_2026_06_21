"""
阶段125: LLM协同推理层

第一性原理:
1. LLM擅长语义理解（自然语言↔结构化），不擅长精确推理
2. 引擎擅长结构化推理（因果、决策、记忆），不擅长语义
3. 协同 = LLM负责感知/表达，引擎负责推理/记忆
4. 分工边界：LLM处理模糊性，引擎处理确定性

提供:
- LLMReasoningCoordinator: LLM-引擎协同协调器
- ReasoningTask: 推理任务
- ReasoningResult: 推理结果
- SemanticBridge: 语义桥接（自然语言↔结构化）
- 协同模式: LLM_LEAD / ENGINE_LEAD / HYBRID
"""

import json
import time
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum


# ============================================================
# 数据结构
# ============================================================

class ReasoningMode(Enum):
    """推理模式"""
    LLM_LEAD = "llm_lead"          # LLM主导，引擎辅助
    ENGINE_LEAD = "engine_lead"    # 引擎主导，LLM辅助
    HYBRID = "hybrid"              # 混合模式


class TaskType(Enum):
    """任务类型"""
    ANALYSIS = "analysis"          # 分析任务
    DECISION = "decision"          # 决策任务
    CREATION = "creation"          # 创作任务
    CAUSAL = "causal"              # 因果任务
    REFLECTION = "reflection"      # 反思任务
    GENERAL = "general"            # 通用任务


@dataclass
class ReasoningTask:
    """推理任务"""
    task_id: str
    task_type: TaskType
    query: str                              # 自然语言查询
    context: Dict[str, Any] = field(default_factory=dict)
    mode: ReasoningMode = ReasoningMode.HYBRID
    timestamp: float = field(default_factory=time.time)


@dataclass
class ReasoningResult:
    """推理结果"""
    task_id: str
    success: bool
    answer: str                             # 自然语言回答
    structured_data: Dict[str, Any] = field(default_factory=dict)  # 结构化数据
    confidence: float = 0.5
    sources: List[str] = field(default_factory=list)  # 结果来源
    latency_ms: float = 0.0
    error: Optional[str] = None


@dataclass
class SemanticMapping:
    """语义映射（自然语言↔结构化）"""
    natural_text: str
    structured: Dict[str, Any]
    mapping_type: str                       # "to_struct" | "to_text"
    confidence: float = 0.5


# ============================================================
# 语义桥接
# ============================================================

class SemanticBridge:
    """
    语义桥接

    第一性原理：
    - 自然语言→结构化：LLM解析
    - 结构化→自然语言：LLM表达
    - 无LLM时使用规则降级
    """

    def __init__(self, llm_service=None):
        self._llm = llm_service
        self._lock = threading.RLock()
        self._mapping_cache: Dict[str, SemanticMapping] = {}

    def to_structured(self, text: str, schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """自然语言→结构化"""
        # 防御：None/空输入
        if not text:
            return {}

        # 缓存检查
        cache_key = f"struct:{text}:{schema}"
        with self._lock:
            if cache_key in self._mapping_cache:
                return self._mapping_cache[cache_key].structured

        # 尝试LLM解析
        if self._llm is not None:
            try:
                result = self._llm.parse_observation(text)
                if result:
                    mapping = SemanticMapping(
                        natural_text=text,
                        structured=result,
                        mapping_type="to_struct",
                        confidence=0.8,
                    )
                    with self._lock:
                        self._mapping_cache[cache_key] = mapping
                    return result
            except Exception:
                pass

        # 降级：规则解析
        result = self._rule_based_parse(text)
        mapping = SemanticMapping(
            natural_text=text,
            structured=result,
            mapping_type="to_struct",
            confidence=0.4,
        )
        with self._lock:
            self._mapping_cache[cache_key] = mapping
        return result

    def to_natural_text(self, structured: Dict[str, Any], template: Optional[str] = None) -> str:
        """结构化→自然语言"""
        # 防御：None/空输入
        if not structured:
            return ""

        # 尝试LLM表达
        if self._llm is not None:
            try:
                text = self._llm.generate_reflection(structured)
                if text:
                    return text
            except Exception:
                pass

        # 降级：模板表达
        return self._template_based_express(structured, template)

    def _rule_based_parse(self, text: str) -> Dict[str, Any]:
        """规则解析（降级）"""
        result: Dict[str, Any] = {"raw_text": text}

        # 提取数字
        import re
        numbers = re.findall(r'\d+\.?\d*', text)
        if numbers:
            result["numbers"] = [float(n) for n in numbers]

        # 提取百分比
        percents = re.findall(r'(\d+\.?\d*)%', text)
        if percents:
            result["percentages"] = [float(p) / 100 for p in percents]

        # 关键词检测
        keywords = {
            "error": ["error", "fail", "exception", "错误", "失败", "异常"],
            "warning": ["warning", "warn", "警告"],
            "success": ["success", "ok", "成功", "完成"],
            "high": ["high", "critical", "高", "严重"],
            "low": ["low", "low", "低"],
        }
        text_lower = text.lower()
        for category, words in keywords.items():
            for word in words:
                if word in text_lower:
                    result.setdefault("tags", []).append(category)
                    break

        result["summary"] = text[:200]
        return result

    def _template_based_express(self, structured: Dict[str, Any], template: Optional[str] = None) -> str:
        """模板表达（降级）"""
        if template:
            try:
                return template.format(**structured)
            except (KeyError, ValueError):
                pass

        # 默认模板
        parts = []
        for key, value in structured.items():
            if isinstance(value, (str, int, float, bool)):
                parts.append(f"{key}: {value}")
            elif isinstance(value, list) and len(value) < 10:
                parts.append(f"{key}: {', '.join(str(v) for v in value)}")

        if not parts:
            return json.dumps(structured, ensure_ascii=False, default=str)[:500]

        return "; ".join(parts)

    def clear_cache(self) -> None:
        """清除缓存"""
        with self._lock:
            self._mapping_cache.clear()

    def get_cache_size(self) -> int:
        """获取缓存大小"""
        with self._lock:
            return len(self._mapping_cache)


# ============================================================
# LLM-引擎协同协调器
# ============================================================

class LLMReasoningCoordinator:
    """
    LLM-引擎协同协调器

    第一性原理：
    - LLM主导：语义任务（分析、创作、反思）
    - 引擎主导：结构化任务（因果推理、决策、记忆检索）
    - 混合模式：LLM解析输入→引擎推理→LLM表达输出
    """

    def __init__(
        self,
        llm_service=None,
        engine=None,
        coordinator=None,
    ):
        self._llm = llm_service
        self._engine = engine
        self._coordinator = coordinator
        self._semantic_bridge = SemanticBridge(llm_service)
        self._lock = threading.RLock()
        self._task_history: List[ReasoningResult] = []
        self._max_history = 1000

        # 任务路由表：任务类型→处理模式
        self._routing: Dict[TaskType, ReasoningMode] = {
            TaskType.ANALYSIS: ReasoningMode.LLM_LEAD,
            TaskType.DECISION: ReasoningMode.ENGINE_LEAD,
            TaskType.CREATION: ReasoningMode.LLM_LEAD,
            TaskType.CAUSAL: ReasoningMode.ENGINE_LEAD,
            TaskType.REFLECTION: ReasoningMode.HYBRID,
            TaskType.GENERAL: ReasoningMode.HYBRID,
        }

    def set_routing(self, task_type: TaskType, mode: ReasoningMode) -> None:
        """设置任务路由"""
        with self._lock:
            self._routing[task_type] = mode

    def reason(self, task: ReasoningTask) -> ReasoningResult:
        """执行推理"""
        start = time.time()

        # 确定模式
        mode = task.mode
        if mode == ReasoningMode.HYBRID:
            mode = self._routing.get(task.task_type, ReasoningMode.HYBRID)

        try:
            if mode == ReasoningMode.LLM_LEAD:
                result = self._reason_llm_lead(task)
            elif mode == ReasoningMode.ENGINE_LEAD:
                result = self._reason_engine_lead(task)
            else:
                result = self._reason_hybrid(task)
        except Exception as e:
            result = ReasoningResult(
                task_id=task.task_id,
                success=False,
                answer="",
                error=str(e),
                latency_ms=(time.time() - start) * 1000,
            )

        result.latency_ms = (time.time() - start) * 1000
        self._record_result(result)
        return result

    def _reason_llm_lead(self, task: ReasoningTask) -> ReasoningResult:
        """LLM主导推理"""
        if self._llm is None:
            # 降级到引擎
            return self._reason_engine_lead(task)

        # LLM处理
        try:
            # 使用LLM的chat能力
            from self_evolving_agent.core.llm_service import LLMMessage
            messages = [
                LLMMessage(role="system", content=f"你是一个{task.task_type.value}专家。"),
                LLMMessage(role="user", content=task.query),
            ]
            response = self._llm.chat(messages)

            if response.success:
                # 引擎辅助：提取结构化数据
                structured = self._semantic_bridge.to_structured(task.query)
                return ReasoningResult(
                    task_id=task.task_id,
                    success=True,
                    answer=response.content,
                    structured_data=structured,
                    confidence=0.8,
                    sources=["llm", "semantic_bridge"],
                )
            else:
                return ReasoningResult(
                    task_id=task.task_id,
                    success=False,
                    answer="",
                    error=response.error or "LLM call failed",
                    sources=["llm"],
                )
        except Exception as e:
            return ReasoningResult(
                task_id=task.task_id,
                success=False,
                answer="",
                error=str(e),
                sources=["llm"],
            )

    def _reason_engine_lead(self, task: ReasoningTask) -> ReasoningResult:
        """引擎主导推理"""
        if self._engine is None and self._coordinator is None:
            # 降级到LLM
            return self._reason_llm_lead(task)

        # 引擎处理
        try:
            structured_result: Dict[str, Any] = {}

            # 根据任务类型调用引擎能力
            if task.task_type == TaskType.CAUSAL and self._engine:
                # 因果推理
                causal_engine = getattr(self._engine, "causal_engine", None)
                if causal_engine:
                    structured_result["causal_analysis"] = "causal_engine_available"
            elif task.task_type == TaskType.DECISION and self._engine:
                # 决策
                free_will_engine = getattr(self._engine, "free_will_engine", None)
                if free_will_engine:
                    structured_result["decision_analysis"] = "decision_engine_available"
            elif task.task_type == TaskType.REFLECTION and self._coordinator:
                # 反思
                reflection = self._coordinator.reflect()
                structured_result["reflection"] = reflection

            # LLM表达
            answer = self._semantic_bridge.to_natural_text(structured_result)

            return ReasoningResult(
                task_id=task.task_id,
                success=True,
                answer=answer,
                structured_data=structured_result,
                confidence=0.7,
                sources=["engine", "semantic_bridge"],
            )
        except Exception as e:
            return ReasoningResult(
                task_id=task.task_id,
                success=False,
                answer="",
                error=str(e),
                sources=["engine"],
            )

    def _reason_hybrid(self, task: ReasoningTask) -> ReasoningResult:
        """混合推理：LLM解析→引擎推理→LLM表达"""
        structured_result: Dict[str, Any] = {}
        sources: List[str] = []

        # 步骤1：LLM解析输入
        parsed = self._semantic_bridge.to_structured(task.query)
        structured_result["parsed_input"] = parsed
        sources.append("semantic_bridge")

        # 步骤2：引擎推理
        if self._coordinator is not None:
            try:
                # 使用coordinator的reflect获取引擎状态
                reflection = self._coordinator.reflect()
                structured_result["engine_reflection"] = reflection
                sources.append("engine")
            except Exception:
                pass

        # 步骤3：LLM表达输出
        if self._llm is not None:
            try:
                from self_evolving_agent.core.llm_service import LLMMessage
                context_str = json.dumps(structured_result, ensure_ascii=False, default=str)[:1000]
                messages = [
                    LLMMessage(
                        role="system",
                        content=f"你是一个{task.task_type.value}专家。基于以下结构化数据回答用户问题。",
                    ),
                    LLMMessage(role="user", content=f"问题: {task.query}\n\n数据: {context_str}"),
                ]
                response = self._llm.chat(messages)
                if response.success:
                    answer = response.content
                    sources.append("llm")
                else:
                    answer = self._semantic_bridge.to_natural_text(structured_result)
            except Exception:
                answer = self._semantic_bridge.to_natural_text(structured_result)
        else:
            answer = self._semantic_bridge.to_natural_text(structured_result)

        return ReasoningResult(
            task_id=task.task_id,
            success=True,
            answer=answer,
            structured_data=structured_result,
            confidence=0.75,
            sources=sources,
        )

    def _record_result(self, result: ReasoningResult) -> None:
        """记录结果"""
        with self._lock:
            self._task_history.append(result)
            if len(self._task_history) > self._max_history:
                self._task_history = self._task_history[-self._max_history:]

    def get_history(self, limit: int = 100) -> List[ReasoningResult]:
        """获取历史"""
        with self._lock:
            return list(self._task_history[-limit:])

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            total = len(self._task_history)
            success = sum(1 for r in self._task_history if r.success)
            avg_latency = (
                sum(r.latency_ms for r in self._task_history) / total
                if total > 0 else 0.0
            )
            return {
                "total_tasks": total,
                "successful_tasks": success,
                "success_rate": success / total if total > 0 else 0.0,
                "avg_latency_ms": avg_latency,
                "cache_size": self._semantic_bridge.get_cache_size(),
                "llm_available": self._llm is not None,
                "engine_available": self._engine is not None or self._coordinator is not None,
            }

    def clear_history(self) -> None:
        """清除历史"""
        with self._lock:
            self._task_history.clear()
            self._semantic_bridge.clear_cache()

    @property
    def semantic_bridge(self) -> SemanticBridge:
        """获取语义桥接"""
        return self._semantic_bridge


# ============================================================
# 便捷函数
# ============================================================

def create_reasoning_task(
    task_id: str,
    query: str,
    task_type: TaskType = TaskType.GENERAL,
    context: Optional[Dict[str, Any]] = None,
    mode: ReasoningMode = ReasoningMode.HYBRID,
) -> ReasoningTask:
    """创建推理任务"""
    return ReasoningTask(
        task_id=task_id,
        task_type=task_type,
        query=query,
        context=context or {},
        mode=mode,
    )


def create_llm_reasoning_coordinator(
    llm_service=None,
    engine=None,
    coordinator=None,
) -> LLMReasoningCoordinator:
    """创建LLM推理协调器"""
    return LLMReasoningCoordinator(
        llm_service=llm_service,
        engine=engine,
        coordinator=coordinator,
    )
