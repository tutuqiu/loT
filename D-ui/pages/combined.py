"""
组合页面模块 - 发布端和订阅端在同一界面
"""
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QComboBox, QDateEdit, QSplitter
)
from PyQt5.QtCore import (
    QProcess, Qt, pyqtSignal, QObject, QDate
)
from PyQt5.QtGui import QFont
from config import config
from .publisher import PublisherController
from .viewer import SubscriptionWidget


class CombinedPage(QWidget):
    """组合页面 - 发布端在左，订阅端在右"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # 创建三个控制器，每个metric一个
        self.controllers = {
            'temperature': PublisherController('temperature', self),
            'humidity': PublisherController('humidity', self),
            'pressure': PublisherController('pressure', self)
        }
        self.init_ui()
        self.connect_signals()
    
    def init_ui(self):
        """初始化UI"""
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：发布端
        publisher_widget = self.create_publisher_widget()
        splitter.addWidget(publisher_widget)
        
        # 右侧：订阅端
        subscriber_widget = self.create_subscriber_widget()
        splitter.addWidget(subscriber_widget)
        
        # 设置分割比例（左侧30%，右侧70%）
        splitter.setSizes([300, 900])
        
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)
    
    def create_publisher_widget(self):
        """创建发布端控件 - 使用下拉框选择指标"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # 标题
        title = QLabel("发布端")
        title.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        layout.addWidget(title)
        
        # 指标选择下拉框
        metric_group = QGroupBox("发布类型")
        metric_layout = QVBoxLayout()
        
        self.metric_combo = QComboBox()
        self.metric_combo.addItems(["温度", "湿度", "气压"])
        self.metric_combo.setFont(QFont("Microsoft YaHei", 12))
        self.metric_combo.setMinimumHeight(35)
        self.metric_combo.currentIndexChanged.connect(self.on_metric_selected)
        metric_layout.addWidget(self.metric_combo)
        
        metric_group.setLayout(metric_layout)
        layout.addWidget(metric_group)
        
        # 为每个metric创建控制组（初始隐藏）
        self.metric_widgets = {}
        metric_configs = [
            ('temperature', '温度'),
            ('humidity', '湿度'),
            ('pressure', '气压')
        ]
        
        for metric, metric_name in metric_configs:
            metric_widget = self.create_metric_control_group(metric, metric_name)
            self.metric_widgets[metric] = metric_widget
            layout.addWidget(metric_widget)
            # 初始只显示第一个
            if metric != 'temperature':
                metric_widget.hide()
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_metric_control_group(self, metric: str, metric_name: str):
        """为单个metric创建控制组"""
        group = QGroupBox(f"{metric_name}数据")
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # 速率选择
        rate_layout = QHBoxLayout()
        rate_label = QLabel("速率:")
        rate_label.setFont(QFont("Microsoft YaHei", 10))
        rate_layout.addWidget(rate_label)
        
        rate_combo = QComboBox()
        rate_combo.addItems(["1", "2", "5"])
        rate_combo.setCurrentText("1")
        rate_combo.setFont(QFont("Microsoft YaHei", 10))
        rate_combo.setMinimumHeight(30)
        rate_layout.addWidget(rate_combo)
        rate_layout.addStretch()
        layout.addLayout(rate_layout)
        
        # 日期选择
        date_layout = QHBoxLayout()
        start_date = QDateEdit()
        start_date.setDate(QDate(2014, 2, 13))
        start_date.setMinimumDate(QDate(2014, 2, 13))
        start_date.setMaximumDate(QDate(2014, 6, 8))
        start_date.setCalendarPopup(True)
        start_date.setDisplayFormat("yyyy-MM-dd")
        start_date.setFont(QFont("Microsoft YaHei", 9))
        start_date.setMinimumHeight(30)
        
        end_date = QDateEdit()
        end_date.setDate(QDate(2014, 6, 8))
        end_date.setMinimumDate(QDate(2014, 2, 13))
        end_date.setMaximumDate(QDate(2014, 6, 8))
        end_date.setCalendarPopup(True)
        end_date.setDisplayFormat("yyyy-MM-dd")
        end_date.setFont(QFont("Microsoft YaHei", 9))
        end_date.setMinimumHeight(30)
        
        # 连接日期验证
        start_date.dateChanged.connect(lambda d: self.on_start_date_changed(d, end_date))
        end_date.dateChanged.connect(lambda d: self.on_end_date_changed(d, start_date))
        
        date_layout.addWidget(QLabel("开始:"))
        date_layout.addWidget(start_date)
        date_layout.addWidget(QLabel("结束:"))
        date_layout.addWidget(end_date)
        layout.addLayout(date_layout)
        
        # 控制按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(5)
        
        btn_start = QPushButton("开始")
        btn_start.setMinimumHeight(35)
        btn_start.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        btn_start.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
                color: #7f8c8d;
            }
        """)
        
        btn_pause = QPushButton("暂停")
        btn_pause.setMinimumHeight(35)
        btn_pause.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        btn_pause.setEnabled(False)
        btn_pause.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
                color: #7f8c8d;
            }
        """)
        
        btn_stop = QPushButton("停止")
        btn_stop.setMinimumHeight(35)
        btn_stop.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        btn_stop.setEnabled(False)
        btn_stop.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
                color: #7f8c8d;
            }
        """)
        
        btn_layout.addWidget(btn_start)
        btn_layout.addWidget(btn_pause)
        btn_layout.addWidget(btn_stop)
        layout.addLayout(btn_layout)
        
        # 状态显示
        status_label = QLabel("状态: 未启动")
        status_label.setFont(QFont("Microsoft YaHei", 9))
        status_label.setStyleSheet("color: #7f8c8d;")
        layout.addWidget(status_label)
        
        group.setLayout(layout)
        
        # 存储控件引用
        group.rate_combo = rate_combo
        group.start_date = start_date
        group.end_date = end_date
        group.btn_start = btn_start
        group.btn_pause = btn_pause
        group.btn_stop = btn_stop
        group.status_label = status_label
        group.metric = metric
        group.metric_name = metric_name
        
        # 连接信号
        btn_start.clicked.connect(lambda: self.on_metric_start(metric))
        btn_pause.clicked.connect(lambda: self.on_metric_pause(metric))
        btn_stop.clicked.connect(lambda: self.on_metric_stop(metric))
        
        return group
    
    def create_subscriber_widget(self):
        """创建订阅端控件"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # 标题
        title = QLabel("订阅端")
        title.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        layout.addWidget(title)
        
        # 创建订阅组件（使用现有的SubscriptionWidget）
        # 使用TabWidget来显示三个指标的订阅
        from PyQt5.QtWidgets import QTabWidget
        
        tabs = QTabWidget()
        tabs.setFont(QFont("Microsoft YaHei", 12))
        
        # 创建三个订阅组件（温度、湿度、气压）
        self.subscription_widgets = {}
        for metric in ['temperature', 'humidity', 'pressure']:
            sub_widget = SubscriptionWidget(metric=metric, parent=self)
            self.subscription_widgets[metric] = sub_widget
            
            metric_names = {
                'temperature': '温度',
                'humidity': '湿度',
                'pressure': '气压'
            }
            tabs.addTab(sub_widget, metric_names[metric])
        
        layout.addWidget(tabs)
        
        widget.setLayout(layout)
        return widget
    
    def connect_signals(self):
        """连接控制器信号"""
        for metric, controller in self.controllers.items():
            controller.status_changed.connect(self.on_metric_status_changed)
    
    def on_metric_selected(self, index):
        """指标选择改变时，切换显示对应的控制组"""
        metrics = ['temperature', 'humidity', 'pressure']
        selected_metric = metrics[index]
        
        # 隐藏所有控制组
        for metric, widget in self.metric_widgets.items():
            widget.hide()
        
        # 显示选中的控制组
        if selected_metric in self.metric_widgets:
            self.metric_widgets[selected_metric].show()
    
    def on_metric_start(self, metric: str):
        """开始发布指定metric"""
        controller = self.controllers[metric]
        widget = self.metric_widgets[metric]
        
        # 获取选择的速率和日期
        rate = float(widget.rate_combo.currentText())
        start_ts = widget.start_date.date().toString("yyyy-MM-dd")
        end_ts = widget.end_date.date().toString("yyyy-MM-dd")
        
        # 如果当前在运行，先停止
        if controller.status != "Stopped":
            controller.stop()
        
        # 启动发布
        if controller.start(rate=rate, start_ts=start_ts, end_ts=end_ts):
            widget.status_label.setText(f"状态: 正在发布（速率: {rate} Hz）")
            widget.btn_start.setEnabled(False)
            widget.btn_pause.setEnabled(True)
            widget.btn_stop.setEnabled(True)
            widget.rate_combo.setEnabled(False)
            widget.start_date.setEnabled(False)
            widget.end_date.setEnabled(False)
        else:
            widget.status_label.setText("状态: 启动失败")
    
    def on_metric_pause(self, metric: str):
        """暂停/继续指定metric"""
        controller = self.controllers[metric]
        widget = self.metric_widgets[metric]
        
        if controller.status == "Running":
            controller.pause()
            widget.status_label.setText("状态: 已暂停")
            widget.btn_pause.setText("继续")
        elif controller.status == "Paused":
            controller.resume()
            rate = widget.rate_combo.currentText()
            widget.status_label.setText(f"状态: 正在发布（速率: {rate} Hz）")
            widget.btn_pause.setText("暂停")
    
    def on_metric_stop(self, metric: str):
        """停止指定metric"""
        controller = self.controllers[metric]
        widget = self.metric_widgets[metric]
        
        controller.stop()
        widget.status_label.setText("状态: 已停止")
        widget.btn_start.setEnabled(True)
        widget.btn_pause.setEnabled(False)
        widget.btn_stop.setEnabled(False)
        widget.btn_pause.setText("暂停")
        widget.rate_combo.setEnabled(True)
        widget.start_date.setEnabled(True)
        widget.end_date.setEnabled(True)
    
    def on_metric_status_changed(self, metric: str, status: str):
        """metric状态变化回调"""
        widget = self.metric_widgets[metric]
        
        if status == "Stopped":
            widget.status_label.setText("状态: 已停止")
            widget.btn_start.setEnabled(True)
            widget.btn_pause.setEnabled(False)
            widget.btn_stop.setEnabled(False)
            widget.btn_pause.setText("暂停")
            widget.rate_combo.setEnabled(True)
            widget.start_date.setEnabled(True)
            widget.end_date.setEnabled(True)
        elif status == "Running":
            rate = widget.rate_combo.currentText()
            widget.status_label.setText(f"状态: 正在发布（速率: {rate} Hz）")
            widget.btn_start.setEnabled(False)
            widget.btn_pause.setEnabled(True)
            widget.btn_stop.setEnabled(True)
            widget.btn_pause.setText("暂停")
        elif status == "Paused":
            widget.status_label.setText("状态: 已暂停")
            widget.btn_pause.setText("继续")
    
    def on_start_date_changed(self, date, end_date_widget):
        """开始日期改变时，确保结束日期不早于开始日期"""
        if date > end_date_widget.date():
            end_date_widget.setDate(date)
    
    def on_end_date_changed(self, date, start_date_widget):
        """结束日期改变时，确保开始日期不晚于结束日期"""
        if date < start_date_widget.date():
            start_date_widget.setDate(date)

