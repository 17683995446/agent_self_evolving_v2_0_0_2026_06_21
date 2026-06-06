"""
阶段70: 系统监控大盘接口标准化

第一性原理:
1. 可视化是认知的加速器：人脑处理图像远快于文本
2. 全局视图才能发现关联：单点监控无法发现系统性问题
3. 监控必须可定制：不同角色关注不同指标

设计原则:
- Widget: 基础展示组件
- Panel: 面板，包含多个Widget
- Dashboard: 监控大盘，管理多个Panel
- DataSource: 数据源，从各模块采集指标
- 支持实时刷新、多视图、历史对比、下钻分析
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum


class WidgetType(Enum):
    """组件类型"""
    METRIC = "metric"          # 单指标
    CHART = "chart"            # 图表
    TABLE = "table"            # 表格
    GAUGE = "gauge"            # 仪表盘
    HEATMAP = "heatmap"        # 热力图
    LOG_VIEW = "log_view"      # 日志视图
    ALERT_LIST = "alert_list"  # 告警列表


class RefreshMode(Enum):
    """刷新模式"""
    REALTIME = "realtime"      # 实时
    INTERVAL = "interval"      # 定时
    MANUAL = "manual"          # 手动


@dataclass
class Widget:
    """基础展示组件"""
    widget_id: str
    widget_type: WidgetType
    title: str
    data: Any = None
    config: Dict[str, Any] = field(default_factory=dict)
    refresh_mode: RefreshMode = RefreshMode.INTERVAL
    refresh_interval_sec: float = 5.0
    last_updated: float = field(default_factory=time.time)

    def update(self, data: Any) -> None:
        """更新数据"""
        self.data = data
        self.last_updated = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """序列化"""
        return {
            "widget_id": self.widget_id,
            "widget_type": self.widget_type.value,
            "title": self.title,
            "data": self.data,
            "config": self.config,
            "refresh_mode": self.refresh_mode.value,
            "refresh_interval_sec": self.refresh_interval_sec,
            "last_updated": self.last_updated,
        }


@dataclass
class Panel:
    """面板"""
    panel_id: str
    title: str
    widgets: List[Widget] = field(default_factory=list)
    layout: Dict[str, Any] = field(default_factory=dict)

    def add_widget(self, widget: Widget) -> None:
        """添加组件"""
        self.widgets.append(widget)

    def remove_widget(self, widget_id: str) -> bool:
        """移除组件"""
        for i, w in enumerate(self.widgets):
            if w.widget_id == widget_id:
                self.widgets.pop(i)
                return True
        return False

    def get_widget(self, widget_id: str) -> Optional[Widget]:
        """获取组件"""
        for w in self.widgets:
            if w.widget_id == widget_id:
                return w
        return None

    def to_dict(self) -> Dict[str, Any]:
        """序列化"""
        return {
            "panel_id": self.panel_id,
            "title": self.title,
            "widgets": [w.to_dict() for w in self.widgets],
            "layout": self.layout,
        }


# ============================================================
# 数据源
# ============================================================

class DataSource:
    """
    数据源

    从系统各模块采集指标数据
    """

    def __init__(self, source_id: str, source_type: str):
        self.source_id = source_id
        self.source_type = source_type
        self._fetchers: Dict[str, Callable[[], Any]] = {}
        self._lock = threading.Lock()

    def register_fetcher(self, metric_name: str, fetcher: Callable[[], Any]) -> None:
        """注册数据获取器"""
        with self._lock:
            self._fetchers[metric_name] = fetcher

    def fetch(self, metric_name: str) -> Any:
        """获取指标数据"""
        with self._lock:
            fetcher = self._fetchers.get(metric_name)
        if fetcher:
            try:
                return fetcher()
            except Exception as e:
                return {"error": str(e)}
        return None

    def fetch_all(self) -> Dict[str, Any]:
        """获取所有指标"""
        result: Dict[str, Any] = {}
        with self._lock:
            fetchers = dict(self._fetchers)
        for name, fetcher in fetchers.items():
            try:
                result[name] = fetcher()
            except Exception as e:
                result[name] = {"error": str(e)}
        return result

    def list_metrics(self) -> List[str]:
        """列出所有指标名"""
        with self._lock:
            return list(self._fetchers.keys())


# ============================================================
# 监控大盘
# ============================================================

class Dashboard:
    """
    系统监控大盘

    汇总展示系统运行状态的多视图面板
    """

    def __init__(self, dashboard_id: str, title: str = "System Dashboard"):
        self.dashboard_id = dashboard_id
        self.title = title
        self._panels: Dict[str, Panel] = {}
        self._data_sources: Dict[str, DataSource] = {}
        self._running = False
        self._refresh_thread: Optional[threading.Thread] = None
        self._refresh_interval_sec = 5.0
        self._lock = threading.RLock()

    def add_panel(self, panel: Panel) -> None:
        """添加面板"""
        with self._lock:
            self._panels[panel.panel_id] = panel

    def remove_panel(self, panel_id: str) -> bool:
        """移除面板"""
        with self._lock:
            return self._panels.pop(panel_id, None) is not None

    def get_panel(self, panel_id: str) -> Optional[Panel]:
        """获取面板"""
        with self._lock:
            return self._panels.get(panel_id)

    def add_data_source(self, source: DataSource) -> None:
        """添加数据源"""
        with self._lock:
            self._data_sources[source.source_id] = source

    def refresh_widget(self, panel_id: str, widget_id: str) -> bool:
        """刷新指定组件"""
        with self._lock:
            panel = self._panels.get(panel_id)
        if panel is None:
            return False

        widget = panel.get_widget(widget_id)
        if widget is None:
            return False

        # 从数据源获取数据
        data = {}
        with self._lock:
            sources = dict(self._data_sources)
        for source in sources.values():
            fetched = source.fetch(widget_id)
            if fetched is not None:
                data[source.source_id] = fetched

        if not data:
            data = {"status": "no_data"}

        widget.update(data)
        return True

    def refresh_all(self) -> Dict[str, Any]:
        """刷新所有组件"""
        refreshed = 0
        errors = 0

        with self._lock:
            panels = dict(self._panels)
            sources = dict(self._data_sources)

        for panel in panels.values():
            for widget in panel.widgets:
                try:
                    data = {}
                    for source in sources.values():
                        fetched = source.fetch(widget.widget_id)
                        if fetched is not None:
                            data[source.source_id] = fetched
                    if not data:
                        data = {"status": "no_data"}
                    widget.update(data)
                    refreshed += 1
                except Exception:
                    errors += 1

        return {"refreshed": refreshed, "errors": errors, "timestamp": time.time()}

    def start_auto_refresh(self, interval_sec: float = 5.0) -> None:
        """启动自动刷新"""
        self._refresh_interval_sec = interval_sec
        self._running = True

        def _refresh_loop():
            while self._running:
                self.refresh_all()
                time.sleep(self._refresh_interval_sec)

        self._refresh_thread = threading.Thread(target=_refresh_loop, daemon=True)
        self._refresh_thread.start()

    def stop_auto_refresh(self) -> None:
        """停止自动刷新"""
        self._running = False

    def get_snapshot(self) -> Dict[str, Any]:
        """获取大盘快照"""
        with self._lock:
            return {
                "dashboard_id": self.dashboard_id,
                "title": self.title,
                "panels": {pid: p.to_dict() for pid, p in self._panels.items()},
                "data_sources": list(self._data_sources.keys()),
                "auto_refresh": self._running,
            }

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            total_widgets = sum(len(p.widgets) for p in self._panels.values())
            return {
                "dashboard_id": self.dashboard_id,
                "panels_count": len(self._panels),
                "widgets_count": total_widgets,
                "data_sources_count": len(self._data_sources),
                "auto_refresh": self._running,
            }


# ============================================================
# 便捷函数
# ============================================================

def create_dashboard(dashboard_id: str, title: str = "System Dashboard") -> Dashboard:
    """创建监控大盘"""
    return Dashboard(dashboard_id=dashboard_id, title=title)


def create_panel(panel_id: str, title: str) -> Panel:
    """创建面板"""
    return Panel(panel_id=panel_id, title=title)


def create_widget(
    widget_id: str,
    widget_type: WidgetType,
    title: str,
    refresh_mode: RefreshMode = RefreshMode.INTERVAL,
    refresh_interval_sec: float = 5.0,
) -> Widget:
    """创建组件"""
    return Widget(
        widget_id=widget_id,
        widget_type=widget_type,
        title=title,
        refresh_mode=refresh_mode,
        refresh_interval_sec=refresh_interval_sec,
    )


def create_data_source(source_id: str, source_type: str) -> DataSource:
    """创建数据源"""
    return DataSource(source_id=source_id, source_type=source_type)
