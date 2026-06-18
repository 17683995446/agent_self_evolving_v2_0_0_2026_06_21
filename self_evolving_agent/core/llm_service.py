"""
LLM服务模块 — 硅基流动(SiliconFlow)集成

功能:
1. 提供统一的LLM调用接口
2. 支持多模型切换
3. 集成到SystemCoordinator
4. 为观察、反思、创造等接口提供自然语言能力

API文档: https://docs.siliconflow.cn/cn/api-reference/chat-completions/
Base URL: https://api.siliconflow.cn/v1
"""

import os
import json
import time
import threading
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field

# 使用标准库实现，不增加额外依赖
try:
    import urllib.request
    import urllib.error
    HAS_URLIB = True
except ImportError:
    HAS_URLIB = False


@dataclass
class LLMMessage:
    """LLM消息"""
    role: str  # system, user, assistant
    content: str


@dataclass
class LLMResponse:
    """LLM响应"""
    content: str
    reasoning_content: Optional[str] = None
    model: str = ""
    usage: Dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None


class SiliconFlowClient:
    """
    硅基流动API客户端
    
    支持模型:
    - Qwen/Qwen2.5-7B-Instruct (免费)
    - deepseek-ai/DeepSeek-V3
    - deepseek-ai/DeepSeek-R1
    - 更多见: https://cloud.siliconflow.cn/models
    """

    DEFAULT_BASE_URL = "https://api.siliconflow.cn/v1"
    DEFAULT_MODEL = "Qwen/Qwen2.5-7B-Instruct"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 60,
    ):
        self.api_key = api_key or os.environ.get("SILICONFLOW_API_KEY", "")
        self.base_url = (base_url or os.environ.get("SILICONFLOW_BASE_URL", "")).rstrip("/") or self.DEFAULT_BASE_URL
        self.model = model or os.environ.get("SILICONFLOW_MODEL", "") or self.DEFAULT_MODEL
        self.timeout = timeout
        self._stats = {
            "requests_total": 0,
            "requests_success": 0,
            "requests_failed": 0,
            "tokens_prompt": 0,
            "tokens_completion": 0,
            "total_latency_ms": 0,
        }
        self._lock = threading.Lock()

    def chat(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        stream: bool = False,
        enable_thinking: Optional[bool] = None,
    ) -> LLMResponse:
        """
        发送对话请求
        
        Args:
            messages: 消息列表
            model: 覆盖默认模型
            max_tokens: 最大生成token数
            temperature: 温度(0-2)
            stream: 是否流式输出
            enable_thinking: 是否启用思考模式
        """
        if not HAS_URLIB:
            return LLMResponse(
                content="",
                success=False,
                error="urllib not available"
            )

        start_time = time.time()
        model = model or self.model

        # 构建请求体
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
        }
        if enable_thinking is not None:
            payload["enable_thinking"] = enable_thinking

        # 构建请求
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            latency_ms = (time.time() - start_time) * 1000

            # 解析响应
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            content = message.get("content", "")
            reasoning_content = message.get("reasoning_content")

            usage = data.get("usage", {})

            with self._lock:
                self._stats["requests_total"] += 1
                self._stats["requests_success"] += 1
                self._stats["tokens_prompt"] += usage.get("prompt_tokens", 0)
                self._stats["tokens_completion"] += usage.get("completion_tokens", 0)
                self._stats["total_latency_ms"] += latency_ms

            return LLMResponse(
                content=content,
                reasoning_content=reasoning_content,
                model=data.get("model", model),
                usage=usage,
                latency_ms=latency_ms,
                success=True,
            )

        except urllib.error.HTTPError as e:
            latency_ms = (time.time() - start_time) * 1000
            error_body = e.read().decode("utf-8") if e.read else str(e)
            with self._lock:
                self._stats["requests_total"] += 1
                self._stats["requests_failed"] += 1
            return LLMResponse(
                content="",
                success=False,
                error=f"HTTP {e.code}: {error_body}",
                latency_ms=latency_ms,
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            with self._lock:
                self._stats["requests_total"] += 1
                self._stats["requests_failed"] += 1
            return LLMResponse(
                content="",
                success=False,
                error=str(e),
                latency_ms=latency_ms,
            )

    def quick_chat(self, user_message: str, system_prompt: Optional[str] = None) -> str:
        """快速对话，返回文本内容"""
        messages = []
        if system_prompt:
            messages.append(LLMMessage(role="system", content=system_prompt))
        messages.append(LLMMessage(role="user", content=user_message))

        resp = self.chat(messages)
        return resp.content if resp.success else f"[Error: {resp.error}]"

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            stats = dict(self._stats)
            if stats["requests_total"] > 0:
                stats["avg_latency_ms"] = stats["total_latency_ms"] / stats["requests_total"]
                stats["success_rate"] = stats["requests_success"] / stats["requests_total"]
            else:
                stats["avg_latency_ms"] = 0
                stats["success_rate"] = 0
            return stats


class LLMService:
    """
    Agent系统的LLM服务层
    
    为各引擎提供自然语言能力:
    - 观察解析: 自然语言 -> 结构化状态
    - 反思生成: 结构化状态 -> 自然语言报告
    - 创造辅助: 概念组合建议
    - 因果推断: 关系分析
    """

    def __init__(self, client: Optional[SiliconFlowClient] = None):
        self.client = client or SiliconFlowClient()
        self._system_prompts = {
            "observe": "你是一个环境感知解析器。将用户的自然语言描述转换为结构化的环境状态数据。只输出JSON格式。",
            "reflect": "你是一个智能系统的反思分析师。根据系统运行数据，生成通俗易懂的反思报告。",
            "create": "你是一个创意生成助手。基于给定的概念，提出新颖的组合和想法。",
            "causal": "你是一个因果分析专家。分析事件之间的因果关系，给出推断结论。",
            "emotion": "你是一个情感分析专家。分析文本或数据的情感倾向，给出情感标签和强度。",
        }

    # ============================================================
    # 观察解析
    # ============================================================

    def parse_observation(self, text: str) -> Dict[str, Any]:
        """
        将自然语言观察解析为结构化状态
        
        Example:
            "服务器CPU使用率90%，内存满了" -> {"cpu_usage": 0.9, "memory_usage": 1.0, "alert": "high_load"}
        """
        prompt = f"""将以下环境观察描述解析为结构化JSON数据。包含数值字段和状态字段。

观察描述: {text}

要求:
1. 输出必须是合法的JSON
2. 提取所有可量化的数值
3. 添加一个"summary"字段描述整体状态
4. 添加一个"urgency"字段(0-1)表示紧急程度

输出:"""

        response = self.client.quick_chat(prompt, self._system_prompts["observe"])
        return self._extract_json(response)

    # ============================================================
    # 反思生成
    # ============================================================

    def generate_reflection(self, stats: Dict[str, Any]) -> str:
        """
        根据系统统计数据生成反思报告
        """
        stats_text = json.dumps(stats, indent=2, ensure_ascii=False, default=str)
        prompt = f"""根据以下系统运行数据，生成一段通俗易懂的反思报告（200字以内）。

系统数据:
{stats_text}

要求:
1. 用大白话解释当前状态
2. 指出亮点和潜在问题
3. 给出下一步建议
4. 语气像一位经验丰富的系统管理员

反思报告:"""

        return self.client.quick_chat(prompt, self._system_prompts["reflect"])

    # ============================================================
    # 创造辅助
    # ============================================================

    def assist_creation(self, concepts: List[str], context: Optional[str] = None) -> List[str]:
        """
        辅助生成新概念组合
        
        Returns:
            新概念的文本描述列表
        """
        concepts_text = ", ".join(concepts)
        ctx = f"\n上下文: {context}" if context else ""
        prompt = f"""基于以下概念，提出3-5个新颖的组合或应用想法。

概念: {concepts_text}{ctx}

要求:
1. 每个想法用一句话描述
2. 想法要有创新性但可行
3. 直接列出想法，不要解释

新想法:"""

        response = self.client.quick_chat(prompt, self._system_prompts["create"])
        # 按行分割，过滤空行
        ideas = [line.strip("- ").strip() for line in response.split("\n") if line.strip() and not line.strip().startswith("```")]
        return ideas[:5]

    # ============================================================
    # 因果分析
    # ============================================================

    def analyze_causality(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析事件间的因果关系
        """
        events_text = json.dumps(events, indent=2, ensure_ascii=False, default=str)
        prompt = f"""分析以下事件序列中的因果关系。

事件:
{events_text}

要求:
1. 输出JSON格式
2. 包含 "causal_links" 列表，每个链接有 "cause", "effect", "strength"(0-1), "explanation"
3. 包含 "summary" 字段总结主要因果链

输出:"""

        response = self.client.quick_chat(prompt, self._system_prompts["causal"])
        return self._extract_json(response)

    # ============================================================
    # 情感分析
    # ============================================================

    def analyze_emotion(self, text: str) -> Dict[str, Any]:
        """
        分析文本情感
        """
        prompt = f"""分析以下文本的情感。

文本: {text}

要求输出JSON:
{{
  "emotion": "主要情感标签",
  "valence": 效价(-1到1),
  "arousal": 唤醒度(0到1),
  "confidence": 置信度(0到1)
}}

输出:"""

        response = self.client.quick_chat(prompt, self._system_prompts["emotion"])
        return self._extract_json(response)

    # ============================================================
    # 通用对话
    # ============================================================

    def chat(self, messages: List[LLMMessage], **kwargs) -> LLMResponse:
        """原始对话接口"""
        return self.client.chat(messages, **kwargs)

    def quick_chat(self, message: str, system_prompt: Optional[str] = None) -> str:
        """快速对话"""
        return self.client.quick_chat(message, system_prompt)

    # ============================================================
    # 工具方法
    # ============================================================

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """从文本中提取JSON"""
        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 尝试提取代码块
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end > start:
                try:
                    return json.loads(text[start:end].strip())
                except json.JSONDecodeError:
                    pass
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end > start:
                try:
                    return json.loads(text[start:end].strip())
                except json.JSONDecodeError:
                    pass

        # 尝试提取花括号内容（找最外层匹配的花括号）
        start = text.find("{")
        if start >= 0:
            # 找到与第一个 { 匹配的 }
            depth = 0
            end = -1
            for i, ch in enumerate(text[start:], start):
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        end = i
                        break
            if end > start:
                try:
                    return json.loads(text[start:end+1])
                except json.JSONDecodeError:
                    pass

        # 返回原始文本包装
        return {"raw_response": text, "parse_error": True}

    # ============================================================
    # 新增：预测解释
    # ============================================================

    def explain_prediction(self, prediction: Dict[str, Any], actual: Dict[str, Any]) -> str:
        """
        用自然语言解释预测结果和误差
        """
        pred_text = json.dumps(prediction, indent=2, ensure_ascii=False, default=str)
        actual_text = json.dumps(actual, indent=2, ensure_ascii=False, default=str)
        prompt = f"""解释以下预测结果与实际结果的差异。

预测:
{pred_text}

实际:
{actual_text}

要求:
1. 用一句话说明预测是否准确
2. 分析误差可能的原因
3. 给出改进建议
4. 总字数100字以内

解释:"""
        return self.client.quick_chat(prompt, "你是一个预测分析专家，擅长解释模型预测结果。")

    # ============================================================
    # 新增：异常诊断
    # ============================================================

    def diagnose_anomaly(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        诊断系统异常，返回根因分析和建议
        """
        metrics_text = json.dumps(metrics, indent=2, ensure_ascii=False, default=str)
        prompt = f"""诊断以下系统指标中的异常，输出JSON格式。

指标数据:
{metrics_text}

要求输出JSON:
{{
  "anomaly_detected": true/false,
  "anomaly_type": "异常类型",
  "root_cause": "根因分析",
  "severity": "low/medium/high/critical",
  "recommended_actions": ["建议1", "建议2"],
  "confidence": 0.0-1.0
}}

输出:"""
        response = self.client.quick_chat(prompt, "你是一个系统运维诊断专家，擅长从指标中发现异常并给出根因分析。")
        return self._extract_json(response)

    # ============================================================
    # 新增：策略生成
    # ============================================================

    def generate_strategy(self, context: Dict[str, Any], objective: str) -> Dict[str, Any]:
        """
        根据当前状态和目标生成行动策略
        """
        context_text = json.dumps(context, indent=2, ensure_ascii=False, default=str)
        prompt = f"""根据当前系统状态和目标，生成行动策略，输出JSON格式。

目标: {objective}

当前状态:
{context_text}

要求输出JSON:
{{
  "strategy_name": "策略名称",
  "steps": [
    {{"step": 1, "action": "具体行动", "expected_outcome": "预期结果", "priority": "high/medium/low"}}
  ],
  "risk_assessment": "风险评估",
  "success_probability": 0.0-1.0
}}

输出:"""
        response = self.client.quick_chat(prompt, "你是一个策略规划专家，擅长制定可执行的行动计划。")
        return self._extract_json(response)

    # ============================================================
    # 新增：知识问答
    # ============================================================

    def knowledge_qa(self, question: str, context_docs: Optional[List[str]] = None) -> str:
        """
        基于给定文档上下文回答问题
        """
        docs_text = ""
        if context_docs:
            docs_text = "\n\n参考文档:\n" + "\n---\n".join(context_docs)

        prompt = f"""基于以下参考文档回答问题。

问题: {question}{docs_text}

要求:
1. 如果文档中有答案，直接引用
2. 如果文档中没有，明确说明
3. 保持简洁，不超过150字

回答:"""
        return self.client.quick_chat(prompt, "你是一个知识库问答助手，擅长基于给定文档准确回答问题。")

    # ============================================================
    # 新增：代码生成/分析
    # ============================================================

    def generate_code(self, description: str, language: str = "python") -> str:
        """
        根据描述生成代码
        """
        prompt = f"""生成{language}代码实现以下功能。

功能描述: {description}

要求:
1. 代码必须可运行
2. 添加必要的注释
3. 处理边界情况
4. 只输出代码，不要解释

代码:"""
        return self.client.quick_chat(prompt, f"你是一个资深{language}开发专家，擅长编写高质量、可维护的代码。")

    def analyze_code(self, code: str) -> Dict[str, Any]:
        """
        分析代码质量和潜在问题
        """
        prompt = f"""分析以下代码的质量，输出JSON格式。

代码:
```
{code}
```

要求输出JSON:
{{
  "quality_score": 0-100,
  "issues": [
    {{"line": "行号或范围", "severity": "warning/error/info", "description": "问题描述", "suggestion": "修复建议"}}
  ],
  "strengths": ["优点1", "优点2"],
  "overall_assessment": "总体评价"
}}

输出:"""
        response = self.client.quick_chat(prompt, "你是一个代码审查专家，擅长发现代码中的问题和改进点。")
        return self._extract_json(response)

    # ============================================================
    # 新增：多轮对话记忆
    # ============================================================

    def __init__(self, client: Optional[SiliconFlowClient] = None):
        self.client = client or SiliconFlowClient()
        self._system_prompts = {
            "observe": "你是一个环境感知解析器。将用户的自然语言描述转换为结构化的环境状态数据。只输出JSON格式。",
            "reflect": "你是一个智能系统的反思分析师。根据系统运行数据，生成通俗易懂的反思报告。",
            "create": "你是一个创意生成助手。基于给定的概念，提出新颖的组合和想法。",
            "causal": "你是一个因果分析专家。分析事件之间的因果关系，给出推断结论。",
            "emotion": "你是一个情感分析专家。分析文本或数据的情感倾向，给出情感标签和强度。",
        }
        self._conversation_history: List[LLMMessage] = []
        self._max_history = 10

    def chat_with_memory(self, user_message: str, system_prompt: Optional[str] = None, clear_history: bool = False) -> str:
        """
        带记忆的多轮对话
        """
        if clear_history:
            self._conversation_history = []

        messages = []
        if system_prompt:
            messages.append(LLMMessage(role="system", content=system_prompt))

        # 添加历史记录
        messages.extend(self._conversation_history)

        # 添加当前消息
        user_msg = LLMMessage(role="user", content=user_message)
        messages.append(user_msg)

        # 调用LLM
        resp = self.client.chat(messages)
        if not resp.success:
            return f"[Error: {resp.error}]"

        # 保存到历史
        self._conversation_history.append(user_msg)
        self._conversation_history.append(LLMMessage(role="assistant", content=resp.content))

        # 限制历史长度
        if len(self._conversation_history) > self._max_history * 2:
            self._conversation_history = self._conversation_history[-self._max_history * 2:]

        return resp.content

    def get_conversation_history(self) -> List[Dict[str, str]]:
        """获取对话历史"""
        return [{"role": m.role, "content": m.content} for m in self._conversation_history]

    def clear_conversation_history(self) -> None:
        """清空对话历史"""
        self._conversation_history = []

    # ============================================================
    # 新增：批量处理
    # ============================================================

    def batch_process(self, items: List[str], task: str, max_workers: int = 3) -> List[str]:
        """
        批量处理文本任务
        
        Args:
            items: 待处理的文本列表
            task: 处理任务描述（如"翻译成英文"、"提取关键词"）
            max_workers: 最大并发数（实际为顺序处理，避免API限流）
        """
        results = []
        for i, item in enumerate(items):
            prompt = f"""对以下内容执行: {task}

内容:
{item}

结果:"""
            result = self.client.quick_chat(prompt, f"你是一个文本处理专家，擅长执行各种文本转换和分析任务。")
            results.append(result)
        return results

    def get_stats(self) -> Dict[str, Any]:
        """获取服务统计"""
        return self.client.get_stats()


# ============================================================================
# 快速创建
# ============================================================================

def create_llm_service(
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> LLMService:
    """创建LLM服务实例"""
    client = SiliconFlowClient(api_key=api_key, model=model)
    return LLMService(client)
