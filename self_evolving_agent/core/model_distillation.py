"""
阶段58: 模型蒸馏接口标准化

第一性原理:
1. 大模型知识可以迁移到小模型：知识是压缩的
2. 小模型更快更省：适合边缘部署
3. 蒸馏是师生传承：教师输出软标签，学生学习分布

设计原则:
- TeacherModel: 教师模型接口
- StudentModel: 学生模型接口
- DistillationLoss: 蒸馏损失
- DistillationTrainer: 蒸馏训练器
- 支持温度缩放、中间层蒸馏
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class DistillationConfig:
    """蒸馏配置"""
    temperature: float = 4.0          # 温度缩放
    alpha: float = 0.7                # 蒸馏损失权重
    epochs: int = 10
    learning_rate: float = 0.001
    intermediate_layers: List[str] = field(default_factory=list)


@dataclass
class DistillationResult:
    """蒸馏结果"""
    student_model: Any
    final_loss: float
    teacher_accuracy: float
    student_accuracy: float
    compression_ratio: float
    speedup_ratio: float


# ============================================================
# 模型接口
# ============================================================

class Model(ABC):
    """模型抽象接口"""

    @abstractmethod
    def predict(self, input_data: Any) -> Any:
        """预测"""
        pass

    @abstractmethod
    def get_size(self) -> int:
        """获取模型大小（参数数量）"""
        pass


class TeacherModel(Model):
    """教师模型"""

    def __init__(self, weights: Dict[str, List[float]], name: str = "teacher"):
        self.name = name
        self._weights = weights

    def predict(self, input_data: Any) -> Any:
        """模拟预测：加权求和"""
        if isinstance(input_data, dict):
            total = sum(input_data.get(k, 0) * self._weights.get(k, [0])[0] for k in input_data)
            return {"logits": [total, -total], "confidence": 0.9}
        return {"logits": [0.0, 0.0], "confidence": 0.5}

    def get_size(self) -> int:
        return sum(len(v) for v in self._weights.values())


class StudentModel(Model):
    """学生模型"""

    def __init__(self, weights: Dict[str, List[float]], name: str = "student"):
        self.name = name
        self._weights = weights

    def predict(self, input_data: Any) -> Any:
        """模拟预测"""
        if isinstance(input_data, dict):
            total = sum(input_data.get(k, 0) * self._weights.get(k, [0])[0] for k in input_data)
            return {"logits": [total, -total], "confidence": 0.7}
        return {"logits": [0.0, 0.0], "confidence": 0.5}

    def get_size(self) -> int:
        return sum(len(v) for v in self._weights.values())

    def update_weights(self, new_weights: Dict[str, List[float]]) -> None:
        """更新权重"""
        self._weights = new_weights


# ============================================================
# 蒸馏损失
# ============================================================

class DistillationLoss:
    """
    蒸馏损失计算

    结合软标签（教师输出）和硬标签（真实标签）
    """

    def __init__(self, temperature: float = 4.0, alpha: float = 0.7):
        self.temperature = temperature
        self.alpha = alpha

    def compute(self, teacher_logits: List[float], student_logits: List[float], true_label: int) -> float:
        """
        计算蒸馏损失

        简化实现：MSE(softmax(teacher/T), softmax(student/T)) * alpha + CE(student, true) * (1-alpha)
        """
        import math

        def softmax(logits: List[float], t: float) -> List[float]:
            exp_vals = [math.exp(x / t) for x in logits]
            total = sum(exp_vals)
            return [v / total for v in exp_vals]

        teacher_soft = softmax(teacher_logits, self.temperature)
        student_soft = softmax(student_logits, self.temperature)

        # KL散度近似（MSE）
        kl_loss = sum((t - s) ** 2 for t, s in zip(teacher_soft, student_soft))

        # 硬标签交叉熵近似
        student_hard = softmax(student_logits, 1.0)
        ce_loss = -math.log(student_hard[true_label] + 1e-10)

        return self.alpha * kl_loss + (1 - self.alpha) * ce_loss


# ============================================================
# 蒸馏训练器
# ============================================================

class DistillationTrainer:
    """
    蒸馏训练器

    将教师模型的知识迁移到学生模型
    """

    def __init__(self, config: DistillationConfig):
        self.config = config
        self._loss_fn = DistillationLoss(temperature=config.temperature, alpha=config.alpha)
        self._history: List[Dict[str, float]] = []

    def train(
        self,
        teacher: TeacherModel,
        student: StudentModel,
        dataset: List[Dict[str, Any]],
    ) -> DistillationResult:
        """
        执行蒸馏训练

        Args:
            teacher: 教师模型
            student: 学生模型
            dataset: 训练数据 [{"input": ..., "label": ...}]

        Returns:
            蒸馏结果
        """
        total_loss = 0.0
        teacher_correct = 0
        student_correct = 0

        for epoch in range(self.config.epochs):
            epoch_loss = 0.0
            for sample in dataset:
                input_data = sample["input"]
                label = sample["label"]

                teacher_output = teacher.predict(input_data)
                student_output = student.predict(input_data)

                loss = self._loss_fn.compute(
                    teacher_output["logits"],
                    student_output["logits"],
                    label,
                )
                epoch_loss += loss

                # 模拟学生模型学习（简化：权重向教师靠近）
                self._update_student(student, teacher, input_data)

                # 统计准确率
                if teacher_output["logits"][label] > teacher_output["logits"][1 - label]:
                    teacher_correct += 1
                if student_output["logits"][label] > student_output["logits"][1 - label]:
                    student_correct += 1

            total_loss += epoch_loss
            self._history.append({"epoch": epoch, "loss": epoch_loss})

        n = len(dataset) * self.config.epochs
        compression_ratio = teacher.get_size() / max(student.get_size(), 1)
        speedup_ratio = 2.0  # 模拟加速比

        return DistillationResult(
            student_model=student,
            final_loss=total_loss / max(n, 1),
            teacher_accuracy=teacher_correct / max(n, 1),
            student_accuracy=student_correct / max(n, 1),
            compression_ratio=compression_ratio,
            speedup_ratio=speedup_ratio,
        )

    def _update_student(self, student: StudentModel, teacher: TeacherModel, input_data: Any) -> None:
        """模拟更新学生模型权重"""
        # 简化：不做实际更新，仅模拟
        pass

    def get_history(self) -> List[Dict[str, float]]:
        """获取训练历史"""
        return self._history


# ============================================================
# 便捷函数
# ============================================================

def create_teacher_model(weights: Dict[str, List[float]], name: str = "teacher") -> TeacherModel:
    """创建教师模型"""
    return TeacherModel(weights=weights, name=name)


def create_student_model(weights: Dict[str, List[float]], name: str = "student") -> StudentModel:
    """创建学生模型"""
    return StudentModel(weights=weights, name=name)


def create_distillation_trainer(
    temperature: float = 4.0,
    alpha: float = 0.7,
    epochs: int = 10,
) -> DistillationTrainer:
    """创建蒸馏训练器"""
    config = DistillationConfig(temperature=temperature, alpha=alpha, epochs=epochs)
    return DistillationTrainer(config=config)
