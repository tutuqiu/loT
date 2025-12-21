"""
发布端控制页面模块
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox
)
from PyQt5.QtCore import (
    QProcess, QTimer, Qt, pyqtSignal, QObject
)
from PyQt5.QtGui import QFont
from config import config


class PublisherController(QObject):
    """发布端控制器（封装QProcess）"""
    
    status_changed = pyqtSignal(str, str)  # metric, status
    output_received = pyqtSignal(str, str)  # metric, output
    
    def __init__(self, metric: str, parent=None):
        super().__init__(parent)
        self.metric = metric
        self.process: QProcess = None
        self.status = "Stopped"  # Stopped / Running / Paused
    
    def start(self, rate: float, start_ts: str = None, end_ts: str = None):
        """启动发布脚本"""
        if self.process and self.process.state() != QProcess.NotRunning:
            return False
        
        script_path = config.get_publisher_script_path()
        if not script_path.exists():
            self.output_received.emit(
                self.metric,
                f"✗ 错误：找不到脚本文件 {script_path}\n"
            )
            return False
        
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        
        # 连接信号
        self.process.readyReadStandardOutput.connect(self.on_output)
        self.process.readyReadStandardError.connect(self.on_output)
        self.process.finished.connect(self.on_finished)
        self.process.errorOccurred.connect(self.on_error)
        
        # 构建命令
        args = [
            str(script_path),
            "--metric", self.metric,
            "--rate", str(rate)
        ]
        if start_ts:
            args.extend(["--start", start_ts])
        if end_ts:
            args.extend(["--end", end_ts])
        
        # 启动进程
        self.process.start(config.PYTHON_EXECUTABLE, args)
        
        if not self.process.waitForStarted(3000):
            self.output_received.emit(
                self.metric,
                f"✗ 启动失败：{self.process.errorString()}\n"
            )
            return False
        
        self.status = "Running"
        self.status_changed.emit(self.metric, self.status)
        return True
    
    def pause(self):
        """暂停"""
        if self.process and self.process.state() != QProcess.NotRunning:
            self.process.write(b"pause\n")
            self.status = "Paused"
            self.status_changed.emit(self.metric, self.status)
    
    def resume(self):
        """恢复"""
        if self.process and self.process.state() != QProcess.NotRunning:
            self.process.write(b"resume\n")
            self.status = "Running"
            self.status_changed.emit(self.metric, self.status)
    
    def set_rate(self, rate: float):
        """动态修改速率"""
        if self.process and self.process.state() != QProcess.NotRunning:
            self.process.write(f"rate {rate}\n".encode('utf-8'))
    
    def stop(self):
        """停止（优雅退出+兜底）"""
        if not self.process or self.process.state() == QProcess.NotRunning:
            return
        
        # 1. 优雅停止
        self.process.write(b"stop\n")
        if self.process.waitForFinished(2000):
            self.status = "Stopped"
            self.status_changed.emit(self.metric, self.status)
            return
        
        # 2. terminate
        self.process.terminate()
        if self.process.waitForFinished(1000):
            self.status = "Stopped"
            self.status_changed.emit(self.metric, self.status)
            return
        
        # 3. kill
        self.process.kill()
        self.process.waitForFinished(1000)
        self.status = "Stopped"
        self.status_changed.emit(self.metric, self.status)
    
    def on_output(self):
        """处理输出"""
        data = self.process.readAllStandardOutput()
        text = bytes(data).decode('utf-8', errors='ignore')
        self.output_received.emit(self.metric, text)
    
    def on_finished(self, exit_code, exit_status):
        """进程结束"""
        self.status = "Stopped"
        self.status_changed.emit(self.metric, self.status)
        self.output_received.emit(
            self.metric,
            f"\n进程已结束 (退出码: {exit_code})\n"
        )
    
    def on_error(self, error):
        """进程错误"""
        error_msg = {
            QProcess.FailedToStart: "启动失败",
            QProcess.Crashed: "进程崩溃",
            QProcess.Timedout: "超时",
            QProcess.WriteError: "写入错误",
            QProcess.ReadError: "读取错误",
            QProcess.UnknownError: "未知错误"
        }.get(error, f"错误码: {error}")
        
        self.output_received.emit(
            self.metric,
            f"✗ 进程错误：{error_msg}\n"
        )


class PublisherPage(QWidget):
    """发布端控制页面（简化版，类似Vue设计）"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # 创建三个控制器
        self.controllers = {
            'temperature': PublisherController('temperature', self),
            'humidity': PublisherController('humidity', self),
            'pressure': PublisherController('pressure', self)
        }
        # 按钮状态
        self.button_states = {
            'temperature': False,  # False=停止, True=运行
            'humidity': False,
            'pressure': False
        }
        self.init_ui()
        self.connect_signals()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(50, 50, 50, 50)
        
        # 导航栏
        nav_layout = QHBoxLayout()
        btn_home = QPushButton("主页")
        btn_home.clicked.connect(self.on_home_clicked)
        nav_layout.addWidget(btn_home)
        
        btn_viewer = QPushButton("订阅端")
        btn_viewer.clicked.connect(self.on_viewer_clicked)
        nav_layout.addWidget(btn_viewer)
        
        nav_layout.addStretch()
        layout.addLayout(nav_layout)
        
        # 标题
        title = QLabel("发布端")
        title.setFont(QFont("Microsoft YaHei", 24, QFont.Bold))
        layout.addWidget(title)
        
        # 按钮组（每个指标分为开始和停止两个按钮）
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(20)
        
        # 温度控制组
        temp_group = QGroupBox("温度数据")
        temp_layout = QHBoxLayout()
        temp_layout.setSpacing(15)
        
        self.btn_temp_start = QPushButton("开始发布温度数据")
        self.btn_temp_start.setMinimumHeight(50)
        self.btn_temp_start.setFont(QFont("Microsoft YaHei", 14))
        self.btn_temp_start.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        temp_layout.addWidget(self.btn_temp_start)
        
        self.btn_temp_stop = QPushButton("停止发布温度数据")
        self.btn_temp_stop.setMinimumHeight(50)
        self.btn_temp_stop.setFont(QFont("Microsoft YaHei", 14))
        self.btn_temp_stop.setEnabled(False)
        self.btn_temp_stop.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
                color: #7f8c8d;
            }
        """)
        temp_layout.addWidget(self.btn_temp_stop)
        
        temp_group.setLayout(temp_layout)
        buttons_layout.addWidget(temp_group)
        
        # 湿度控制组
        humidity_group = QGroupBox("湿度数据")
        humidity_layout = QHBoxLayout()
        humidity_layout.setSpacing(15)
        
        self.btn_humidity_start = QPushButton("开始发布湿度数据")
        self.btn_humidity_start.setMinimumHeight(50)
        self.btn_humidity_start.setFont(QFont("Microsoft YaHei", 14))
        self.btn_humidity_start.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        humidity_layout.addWidget(self.btn_humidity_start)
        
        self.btn_humidity_stop = QPushButton("停止发布湿度数据")
        self.btn_humidity_stop.setMinimumHeight(50)
        self.btn_humidity_stop.setFont(QFont("Microsoft YaHei", 14))
        self.btn_humidity_stop.setEnabled(False)
        self.btn_humidity_stop.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
                color: #7f8c8d;
            }
        """)
        humidity_layout.addWidget(self.btn_humidity_stop)
        
        humidity_group.setLayout(humidity_layout)
        buttons_layout.addWidget(humidity_group)
        
        # 气压控制组
        pressure_group = QGroupBox("气压数据")
        pressure_layout = QHBoxLayout()
        pressure_layout.setSpacing(15)
        
        self.btn_pressure_start = QPushButton("开始发布气压数据")
        self.btn_pressure_start.setMinimumHeight(50)
        self.btn_pressure_start.setFont(QFont("Microsoft YaHei", 14))
        self.btn_pressure_start.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        pressure_layout.addWidget(self.btn_pressure_start)
        
        self.btn_pressure_stop = QPushButton("停止发布气压数据")
        self.btn_pressure_stop.setMinimumHeight(50)
        self.btn_pressure_stop.setFont(QFont("Microsoft YaHei", 14))
        self.btn_pressure_stop.setEnabled(False)
        self.btn_pressure_stop.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
                color: #7f8c8d;
            }
        """)
        pressure_layout.addWidget(self.btn_pressure_stop)
        
        pressure_group.setLayout(pressure_layout)
        buttons_layout.addWidget(pressure_group)
        
        layout.addLayout(buttons_layout)
        
        # 响应信息显示
        self.response_label = QLabel("")
        self.response_label.setWordWrap(True)
        self.response_label.setStyleSheet("color: #7f8c8d; padding: 10px;")
        layout.addWidget(self.response_label)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def connect_signals(self):
        """连接信号"""
        # 连接开始按钮
        self.btn_temp_start.clicked.connect(lambda: self.start_publish('temperature'))
        self.btn_humidity_start.clicked.connect(lambda: self.start_publish('humidity'))
        self.btn_pressure_start.clicked.connect(lambda: self.start_publish('pressure'))
        
        # 连接停止按钮
        self.btn_temp_stop.clicked.connect(lambda: self.stop_publish('temperature'))
        self.btn_humidity_stop.clicked.connect(lambda: self.stop_publish('humidity'))
        self.btn_pressure_stop.clicked.connect(lambda: self.stop_publish('pressure'))
        
        # 连接控制器信号
        for metric, controller in self.controllers.items():
            controller.status_changed.connect(self.on_status_changed)
            controller.output_received.connect(self.on_output_received)
    
    def start_publish(self, metric: str):
        """开始发布"""
        controller = self.controllers[metric]
        # 启动发布（使用默认速率1.0 Hz）
        if controller.start(rate=1.0):
            self.button_states[metric] = True
            self.response_label.setText(f"{self.get_metric_name(metric)} 数据发布已启动")
        else:
            self.response_label.setText(f"{self.get_metric_name(metric)} 数据发布启动失败，请查看日志")
    
    def stop_publish(self, metric: str):
        """停止发布"""
        controller = self.controllers[metric]
        controller.stop()
        self.button_states[metric] = False
        self.response_label.setText(f"{self.get_metric_name(metric)} 数据发布已停止")
    
    def on_status_changed(self, metric: str, status: str):
        """状态变化"""
        # 按钮映射
        start_btn_map = {
            'temperature': self.btn_temp_start,
            'humidity': self.btn_humidity_start,
            'pressure': self.btn_pressure_start
        }
        stop_btn_map = {
            'temperature': self.btn_temp_stop,
            'humidity': self.btn_humidity_stop,
            'pressure': self.btn_pressure_stop
        }
        
        if status == "Stopped":
            self.button_states[metric] = False
            # 启用开始按钮，禁用停止按钮
            if metric in start_btn_map:
                start_btn_map[metric].setEnabled(True)
            if metric in stop_btn_map:
                stop_btn_map[metric].setEnabled(False)
        elif status == "Running":
            self.button_states[metric] = True
            # 禁用开始按钮，启用停止按钮
            if metric in start_btn_map:
                start_btn_map[metric].setEnabled(False)
            if metric in stop_btn_map:
                stop_btn_map[metric].setEnabled(True)
    
    def on_output_received(self, metric: str, text: str):
        """接收输出"""
        # 可以在这里显示日志，但为了简化界面，暂时不显示
        pass
    
    def get_metric_name(self, metric: str) -> str:
        """获取指标中文名称"""
        names = {
            'temperature': '温度',
            'humidity': '湿度',
            'pressure': '气压'
        }
        return names.get(metric, metric)
    
    def on_home_clicked(self):
        """返回主页"""
        if hasattr(self, 'main_window') and self.main_window:
            self.main_window.switch_to_home()
    
    def on_viewer_clicked(self):
        """跳转到数据查看页面"""
        if hasattr(self, 'main_window') and self.main_window:
            self.main_window.switch_to_viewer()

