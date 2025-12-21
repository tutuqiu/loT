"""
数据查看页面模块
"""
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QTableWidget, QTableWidgetItem, QTabWidget, QMessageBox
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont, QColor
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates
import matplotlib
# 配置matplotlib中文字体
try:
    # Windows系统使用Microsoft YaHei
    matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS', 'DejaVu Sans']
    matplotlib.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
except:
    pass
from config import config
from workers.http_worker import HttpWorker
try:
    from workers.mqtt_worker import MQTTSubscriber
    MQTT_AVAILABLE = True
except ImportError as e:
    print(f"警告: MQTT功能不可用: {e}")
    MQTTSubscriber = None
    MQTT_AVAILABLE = False


class SubscriptionWidget(QWidget):
    """订阅组件（类似Vue的SubscriptionEnd）"""
    
    def __init__(self, metric: str, parent=None):
        super().__init__(parent)
        self.metric = metric
        self.mqtt_subscriber = None
        self.is_subscribed = False
        self.data_list = []  # 存储接收到的数据
        self.refresh_timer = QTimer()  # 用于定时刷新图表
        self.refresh_timer.timeout.connect(self.refresh_chart_from_api)
        self._chart_data = []  # 存储实时图表数据点 [(datetime, value), ...]
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 订阅按钮
        self.subscribe_btn = QPushButton(f"订阅{self.get_metric_name()}数据")
        self.subscribe_btn.setMinimumHeight(50)
        self.subscribe_btn.setFont(QFont("Microsoft YaHei", 14))
        self.subscribe_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.subscribe_btn.clicked.connect(self.toggle_subscription)
        layout.addWidget(self.subscribe_btn)
        
        # 实时数据图表显示（使用matplotlib）
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
        from matplotlib.figure import Figure
        import matplotlib.dates as mdates
        
        self.figure = Figure(figsize=(10, 4))
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_xlabel("时间")
        self.ax.set_ylabel(f"{self.get_metric_name()}")
        self.ax.set_title(f"{self.get_metric_name()}数据趋势图（等待数据...）")
        self.ax.grid(True, alpha=0.3)
        self.canvas.draw()
        layout.addWidget(self.canvas)
        
        # 数据表格
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["日期", "时间点", f"{self.get_metric_name()}值"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        
        # 用于跟踪当前日期和统计信息
        self.current_date = None
        self.daily_data = []  # 存储当天的数据点 [(time, value), ...]
        
        self.setLayout(layout)
    
    def get_metric_name(self) -> str:
        """获取指标中文名称"""
        names = {
            'temperature': '温度',
            'humidity': '湿度',
            'pressure': '气压'
        }
        return names.get(self.metric, self.metric)
    
    def toggle_subscription(self):
        """切换订阅状态"""
        if not self.is_subscribed:
            self.start_subscription()
        else:
            self.stop_subscription()
    
    def start_subscription(self):
        """开始订阅"""
        if not MQTT_AVAILABLE:
            QMessageBox.warning(self, "错误", "MQTT功能不可用，请安装paho-mqtt: pip install paho-mqtt")
            return
        
        if self.mqtt_subscriber and self.mqtt_subscriber.isRunning():
            # 如果已经在运行，直接订阅主题
            topic = f"env/{self.metric}"  # 使用实际项目的主题格式
            self.mqtt_subscriber.subscribe_topic(topic)
            self.is_subscribed = True
            self.subscribe_btn.setText(f"取消订阅{self.get_metric_name()}数据")
            return
        
        # 创建MQTT订阅者
        try:
            from config import config
            self.mqtt_subscriber = MQTTSubscriber(
                broker_host=config.MQTT_BROKER_HOST,
                broker_port=config.MQTT_BROKER_PORT,
                username=config.MQTT_USERNAME,
                password=config.MQTT_PASSWORD,
                use_websockets=config.MQTT_USE_WEBSOCKETS,
                ws_path=config.MQTT_WS_PATH,
                parent=self
            )
            self.mqtt_subscriber.connected.connect(self.on_mqtt_connected)
            self.mqtt_subscriber.message_received.connect(self.on_message_received)
            self.mqtt_subscriber.error.connect(self.on_mqtt_error)
            
            # 初始化图表数据
            if not hasattr(self, '_chart_data'):
                self._chart_data = []
            
            self.mqtt_subscriber.start()
        except Exception as e:
            error_msg = f"启动MQTT订阅失败: {e}"
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "错误", f"{error_msg}\n\n请检查：\n1. MQTT broker是否可访问\n2. 网络连接是否正常\n3. 用户名密码是否正确")
    
    def stop_subscription(self):
        """停止订阅"""
        topic = f"env/{self.metric}"  # 使用实际项目的主题格式
        if self.mqtt_subscriber:
            self.mqtt_subscriber.unsubscribe_topic(topic)
            self.mqtt_subscriber.stop()
            self.mqtt_subscriber = None
        self.is_subscribed = False
        self.subscribe_btn.setText(f"订阅{self.get_metric_name()}数据")
        
        # 停止定时刷新
        self.refresh_timer.stop()
        
        # 如果还有未显示的当天数据，显示统计信息
        if self.current_date and self.daily_data:
            self.add_daily_statistics_row()
            self.current_date = None
            self.daily_data = []
        
        QMessageBox.information(self, "提示", f"已取消订阅{self.get_metric_name()}数据")
    
    def on_mqtt_connected(self):
        """MQTT连接成功"""
        # 使用实际项目的主题格式：env/temperature, env/humidity, env/pressure
        topic = f"env/{self.metric}"
        self.mqtt_subscriber.subscribe_topic(topic)
        self.is_subscribed = True
        self.subscribe_btn.setText(f"取消订阅{self.get_metric_name()}数据")
        QMessageBox.information(self, "成功", f"已订阅{self.get_metric_name()}数据")
        
        # 初始化图表数据（清空之前的数据，只通过MQTT消息来更新）
        if not hasattr(self, '_chart_data'):
            self._chart_data = []
        else:
            # 清空之前的数据，避免闪烁
            self._chart_data = []
        
        # 清空图表显示
        self.ax.clear()
        self.ax.set_xlabel("时间")
        self.ax.set_ylabel(f"{self.get_metric_name()}")
        self.ax.set_title(f"{self.get_metric_name()}数据趋势图（等待数据...）")
        self.ax.grid(True, alpha=0.3)
        self.canvas.draw()
    
    def on_message_received(self, topic: str, data: dict):
        """接收到MQTT消息（通过信号调用，已在主线程）"""
        try:
            # 实际项目使用主题格式：env/temperature, env/humidity, env/pressure
            expected_topic = f"env/{self.metric}"
            if topic == expected_topic:
                # 实际项目的消息格式：{"ts": "2014-02-13T00:00:00", "value": 4.0}
                
                # 检查是否是实际项目的格式（有ts和value字段）
                if 'ts' in data and 'value' in data:
                    # 实际项目格式：单条数据点
                    ts = data.get('ts', '')
                    value = data.get('value')
                    
                    if value is None:
                        return
                    
                    # 解析时间戳
                    dt = self.parse_timestamp(ts)
                    if dt is None:
                        return
                    
                    # 提取日期和时间
                    date_str = dt.strftime('%Y-%m-%d')
                    time_str = dt.strftime('%H:%M:%S')
                    
                    # 检查是否是新的一天
                    if self.current_date is None:
                        self.current_date = date_str
                        self.daily_data = []
                    elif self.current_date != date_str:
                        # 新的一天开始，先显示前一天的统计信息
                        self.add_daily_statistics_row()
                        # 重置为新的日期
                        self.current_date = date_str
                        self.daily_data = []
                    
                    # 添加到当天数据
                    self.daily_data.append((dt, float(value)))
                    
                    # 添加到数据列表
                    value_str = f"{value:.2f}"
                    self.data_list.append({
                        'date': date_str,
                        'time': time_str,
                        'value': value_str,
                        'graph': ''
                    })
                    
                    # 使用QTimer确保UI更新在主线程中执行
                    def update_ui():
                        try:
                            # 更新表格：显示日期、时间点和数值
                            row = self.table.rowCount()
                            self.table.insertRow(row)
                            self.table.setItem(row, 0, QTableWidgetItem(date_str))
                            self.table.setItem(row, 1, QTableWidgetItem(time_str))
                            self.table.setItem(row, 2, QTableWidgetItem(value_str))
                            
                            # 更新实时图表：将新接收到的数据点添加到图表中
                            self.update_chart_with_new_point(ts, value)
                        except Exception as e:
                            pass
                    
                    QTimer.singleShot(0, update_ui)
        except Exception as e:
            pass
    
    def add_daily_statistics_row(self):
        """添加一天的统计信息行（最高/最低/平均）"""
        if not self.daily_data:
            return
        
        # 计算统计信息
        values = [item[1] for item in self.daily_data]
        max_value = max(values)
        min_value = min(values)
        avg_value = sum(values) / len(values)
        
        # 添加统计行（在最后一行显示统计信息）
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # 第一列：显示日期
        date_item = QTableWidgetItem(self.current_date)
        date_item.setBackground(QColor(230, 230, 230))  # 设置背景色以区分
        font = QFont()
        font.setBold(True)
        date_item.setFont(font)
        self.table.setItem(row, 0, date_item)
        
        # 第二列：显示统计信息（最高/最低/平均）
        stats_text = f"最高: {max_value:.2f} | 最低: {min_value:.2f} | 平均: {avg_value:.2f}"
        stats_item = QTableWidgetItem(stats_text)
        stats_item.setBackground(QColor(230, 230, 230))
        stats_item.setFont(font)
        self.table.setItem(row, 1, stats_item)
        
        # 第三列：留空或显示汇总标记
        summary_item = QTableWidgetItem("汇总")
        summary_item.setBackground(QColor(230, 230, 230))
        summary_item.setFont(font)
        self.table.setItem(row, 2, summary_item)
    
    def parse_timestamp(self, ts_str: str):
        """解析时间戳字符串为datetime对象"""
        from datetime import datetime
        try:
            if 'T' in ts_str:
                if ts_str.endswith('Z'):
                    ts_clean = ts_str[:-1]
                elif '+' in ts_str:
                    ts_clean = ts_str.split('+')[0]
                else:
                    ts_clean = ts_str
                
                try:
                    return datetime.strptime(ts_clean, '%Y-%m-%dT%H:%M:%S')
                except ValueError:
                    try:
                        return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                    except ValueError:
                        return None
            else:
                return datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
        except Exception:
            return None
    
    def update_chart_with_new_point(self, ts_str: str, value):
        """使用新接收到的数据点更新图表（必须在主线程中调用）"""
        try:
            # 解析时间戳
            dt = self.parse_timestamp(ts_str)
            if dt is None or value is None:
                return
            
            if not hasattr(self, '_chart_data'):
                self._chart_data = []
            
            self._chart_data.append((dt, float(value)))
            
            # 限制数据点数量（只保留最近200个点）
            if len(self._chart_data) > 200:
                self._chart_data = self._chart_data[-200:]
            
            # 重新绘制图表（使用QTimer确保在主线程中）
            QTimer.singleShot(0, self.redraw_chart)
        except Exception as e:
            pass
    
    def redraw_chart(self):
        """重新绘制图表（必须在主线程中调用）"""
        try:
            if not hasattr(self, '_chart_data') or not self._chart_data:
                return
            
            if not hasattr(self, 'ax') or not hasattr(self, 'canvas'):
                return
            
            if not hasattr(self, 'figure'):
                return
            
            import matplotlib.dates as mdates
            
            # 绘制图表
            self.ax.clear()
            self.ax.set_xlabel("时间")
            self.ax.set_ylabel(f"{self.get_metric_name()}")
            self.ax.set_title(f"{self.get_metric_name()}数据趋势图（实时数据）")
            self.ax.grid(True, alpha=0.3)
            
            # 提取时间和数值（创建副本以避免在绘制时数据被修改）
            chart_data_copy = list(self._chart_data)
            times = [item[0] for item in chart_data_copy]
            values = [item[1] for item in chart_data_copy]
            
            if times and values:
                self.ax.plot(times, values, marker='o', markersize=3, linewidth=1.5, label=self.get_metric_name())
                self.ax.legend()
                
                # 格式化x轴
                self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d\n%H:%M:%S'))
                self.figure.autofmt_xdate()
            
            # 使用draw_idle而不是draw，更安全
            self.canvas.draw_idle()
        except Exception as e:
            pass
    
    def on_mqtt_error(self, error_msg: str):
        """MQTT错误"""
        QMessageBox.critical(self, "MQTT错误", error_msg)
    
    def refresh_chart_from_api(self):
        """从C-collector API获取数据并更新图表"""
        from config import config
        url = config.get_api_url("/api/realtime")
        params = {"metric": self.metric, "limit": 200}
        
        worker = HttpWorker(url, params, self)
        worker.finished.connect(self.on_api_data_received)
        worker.error.connect(lambda e: None)  # 静默处理错误，避免频繁弹窗
        worker.finished.connect(worker.deleteLater)
        worker.error.connect(worker.deleteLater)
        worker.start()
    
    def on_api_data_received(self, data: dict):
        """接收到API数据，更新图表"""
        points = data.get('points', [])
        if not points:
            return
        
        # 解析数据
        from datetime import datetime
        import matplotlib.dates as mdates
        
        times = []
        values = []
        
        for point in points:
            try:
                ts_str = point.get('ts', '')
                value = point.get('value')
                
                # 解析时间
                if 'T' in ts_str:
                    if ts_str.endswith('Z'):
                        ts_clean = ts_str[:-1]
                    elif '+' in ts_str:
                        ts_clean = ts_str.split('+')[0]
                    else:
                        ts_clean = ts_str
                    
                    try:
                        dt = datetime.strptime(ts_clean, '%Y-%m-%dT%H:%M:%S')
                    except ValueError:
                        try:
                            dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                        except ValueError:
                            continue
                else:
                    dt = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
                times.append(dt)
                
                if value is not None:
                    values.append(float(value))
                else:
                    values.append(None)
            except Exception as e:
                continue
        
        # 绘制图表
        self.ax.clear()
        self.ax.set_xlabel("时间")
        self.ax.set_ylabel(f"{self.get_metric_name()}")
        self.ax.set_title(f"{self.get_metric_name()}数据趋势图")
        self.ax.grid(True, alpha=0.3)
        
        if times and values:
            # 过滤掉None值
            valid_times = []
            valid_values = []
            for t, v in zip(times, values):
                if v is not None:
                    valid_times.append(t)
                    valid_values.append(v)
            
            if valid_times:
                self.ax.plot(valid_times, valid_values, marker='o', markersize=3, linewidth=1.5, label=self.get_metric_name())
                self.ax.legend()
                
                # 格式化x轴
                self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d\n%H:%M:%S'))
                self.figure.autofmt_xdate()
        
        self.canvas.draw()


class ViewerPage(QWidget):
    """数据查看页面（订阅端）"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(50, 50, 50, 50)
        
        # 导航栏
        nav_layout = QHBoxLayout()
        btn_home = QPushButton("主页")
        btn_home.clicked.connect(self.on_home_clicked)
        nav_layout.addWidget(btn_home)
        
        btn_publisher = QPushButton("发布端")
        btn_publisher.clicked.connect(self.on_publisher_clicked)
        nav_layout.addWidget(btn_publisher)
        
        nav_layout.addStretch()
        layout.addLayout(nav_layout)
        
        # 标题
        title = QLabel("订阅端")
        title.setFont(QFont("Microsoft YaHei", 24, QFont.Bold))
        layout.addWidget(title)
        
        # Tab 控件（三个指标，类似Vue版本）
        self.tab_widget = QTabWidget()
        
        # 使用新的订阅组件
        self.temp_widget = SubscriptionWidget("temperature")
        self.humidity_widget = SubscriptionWidget("humidity")
        self.pressure_widget = SubscriptionWidget("pressure")
        
        self.tab_widget.addTab(self.temp_widget, "温度数据")
        self.tab_widget.addTab(self.humidity_widget, "湿度数据")
        self.tab_widget.addTab(self.pressure_widget, "气压数据")
        
        layout.addWidget(self.tab_widget)
        
        self.setLayout(layout)
    
    def on_home_clicked(self):
        """返回主页"""
        if hasattr(self, 'main_window') and self.main_window:
            self.main_window.switch_to_home()
    
    def on_publisher_clicked(self):
        """跳转到发布端控制页面"""
        if hasattr(self, 'main_window') and self.main_window:
            self.main_window.switch_to_publisher()
    

