"""
阶段162: 输出体验提升 — 颜色输出和进度提示

提供 ANSI 颜色码和简单的进度提示，无需第三方依赖。
在非 TTY 环境下自动降级为纯文本（不输出颜色码）。

第一性原理:
1. 可读性 — 颜色和格式帮助用户快速识别信息类型
2. 反馈性 — 长时间操作应有进度提示
3. 降级 — 非交互环境自动降级，不破坏脚本输出
4. 零依赖 — 使用 ANSI 转义码，无需安装 colorama/rich
"""

import sys
import time
from typing import Optional, TextIO


# ============================================================
# ANSI 颜色码
# ============================================================

class Colors:
    """ANSI 颜色码（零依赖）"""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # 前景色
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # 亮色
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_CYAN = "\033[96m"


# ============================================================
# 颜色输出器
# ============================================================

class ColorOutput:
    """
    颜色输出器

    在 TTY 环境下输出彩色文本，非 TTY 环境降级为纯文本。
    """

    def __init__(self, stream: Optional[TextIO] = None, force_color: Optional[bool] = None):
        """
        Args:
            stream: 输出流（默认 stdout）
            force_color: 强制启用/禁用颜色（None=自动检测）
        """
        self.stream = stream or sys.stdout
        if force_color is not None:
            self._use_color = force_color
        else:
            self._use_color = self._detect_color_support()

    def _detect_color_support(self) -> bool:
        """检测是否支持颜色输出"""
        # 检查是否是 TTY
        if not hasattr(self.stream, "isatty") or not self.stream.isatty():
            return False
        # 检查 NO_COLOR 环境变量（https://no-color.org/）
        import os
        if os.environ.get("NO_COLOR"):
            return False
        # 检查 TERM
        term = os.environ.get("TERM", "")
        if term == "dumb":
            return False
        return True

    def colorize(self, text: str, color: str) -> str:
        """添加颜色码（如果启用）"""
        if self._use_color:
            return f"{color}{text}{Colors.RESET}"
        return text

    def success(self, message: str) -> str:
        """成功消息（绿色）"""
        return self.colorize(message, Colors.GREEN)

    def error(self, message: str) -> str:
        """错误消息（红色）"""
        return self.colorize(message, Colors.RED)

    def warning(self, message: str) -> str:
        """警告消息（黄色）"""
        return self.colorize(message, Colors.YELLOW)

    def info(self, message: str) -> str:
        """信息消息（青色）"""
        return self.colorize(message, Colors.CYAN)

    def bold(self, message: str) -> str:
        """粗体"""
        return self.colorize(message, Colors.BOLD)

    def dim(self, message: str) -> str:
        """暗淡"""
        return self.colorize(message, Colors.DIM)

    def print(self, message: str, color: Optional[str] = None) -> None:
        """打印带颜色的消息"""
        if color:
            message = self.colorize(message, color)
        print(message, file=self.stream)

    def print_success(self, message: str) -> None:
        """打印成功消息"""
        self.print(f"[OK] {message}", Colors.GREEN)

    def print_error(self, message: str) -> None:
        """打印错误消息"""
        print(f"[ERROR] {message}", file=self.stream or sys.stderr, flush=True)
        if self._use_color:
            # 颜色码需要包裹整个消息
            pass

    def print_warning(self, message: str) -> None:
        """打印警告消息"""
        self.print(f"[WARN] {message}", Colors.YELLOW)

    def print_info(self, message: str) -> None:
        """打印信息消息"""
        self.print(f"[INFO] {message}", Colors.CYAN)


# ============================================================
# 进度提示器
# ============================================================

class ProgressIndicator:
    """
    简单的进度提示器

    用于长时间操作的进度反馈。
    在非 TTY 环境下自动降级（不输出进度）。
    """

    SPINNER_CHARS = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, message: str = "", stream: Optional[TextIO] = None):
        self.message = message
        self.stream = stream or sys.stderr
        self._active = False
        self._use_output = hasattr(self.stream, "isatty") and self.stream.isatty()
        self._spinner_idx = 0
        self._start_time = 0.0

    def start(self) -> None:
        """开始进度提示"""
        if not self._use_output:
            return
        self._active = True
        self._start_time = time.time()
        self._update()

    def update(self, message: Optional[str] = None) -> None:
        """更新进度消息"""
        if message:
            self.message = message
        if self._active:
            self._update()

    def _update(self) -> None:
        """更新显示"""
        if not self._use_output:
            return
        char = self.SPINNER_CHARS[self._spinner_idx % len(self.SPINNER_CHARS)]
        elapsed = time.time() - self._start_time if self._start_time else 0
        self.stream.write(f"\r{char} {self.message} ({elapsed:.1f}s)")
        self.stream.flush()
        self._spinner_idx += 1

    def tick(self) -> None:
        """推进 spinner（手动调用）"""
        if self._active:
            self._update()

    def stop(self, final_message: Optional[str] = None) -> None:
        """停止进度提示"""
        if not self._use_output:
            if final_message:
                print(final_message, file=self.stream)
            return
        self._active = False
        self.stream.write("\r" + " " * 80 + "\r")  # 清除行
        self.stream.flush()
        if final_message:
            print(final_message, file=self.stream)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.stop(f"[失败] {self.message}")
        else:
            self.stop(f"[完成] {self.message}")
        return False


# ============================================================
# 全局实例
# ============================================================

# 默认颜色输出器（自动检测）
color_output = ColorOutput()


def format_status(status: str) -> str:
    """格式化状态字符串"""
    status_lower = status.lower() if isinstance(status, str) else str(status).lower()
    if status_lower in ("running", "healthy", "ok", "success", "active", "passed"):
        return color_output.success(status)
    elif status_lower in ("stopped", "unhealthy", "error", "failed", "inactive"):
        return color_output.error(status)
    elif status_lower in ("warning", "pending", "paused"):
        return color_output.warning(status)
    else:
        return status


def format_table(headers: list, rows: list) -> str:
    """
    格式化简单表格（无第三方依赖）

    Args:
        headers: 表头列表
        rows: 行列表（每行是值的列表）

    Returns:
        格式化的表格字符串
    """
    if not headers or not rows:
        return ""

    # 计算每列宽度
    col_count = len(headers)
    widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < col_count:
                widths[i] = max(widths[i], len(str(cell)))

    # 构建表格
    def format_row(cells):
        return " | ".join(str(c).ljust(widths[i]) for i, c in enumerate(cells))

    lines = [
        format_row(headers),
        "-+-".join("-" * w for w in widths),
    ]
    for row in rows:
        lines.append(format_row(row))

    return "\n".join(lines)
