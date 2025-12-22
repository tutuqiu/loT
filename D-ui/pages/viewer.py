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
        self.data_list = []  # 存储接收到的数据（用于表格）
        self._chart_data = []  # 存储实时图表数据点 [(datetime, value), ...]
        self._prediction_points = []  # 存储未来预测数据点 [(datetime, value), ...]
        self._historical_fit_points = []  # 存储历史拟合数据点 [(datetime, value), ...]，固定不变
        self._prediction_start_time = None  # 记录开始预测的时间（第10个数据点的时间）
        self._prediction_window = 100  # 预测时使用的最近数据点个数（增加窗口以改善拟合）
        self._redraw_timer = QTimer()  # 用于防抖，避免频繁重绘
        self._redraw_timer.setSingleShot(True)
        self._redraw_timer.timeout.connect(self.redraw_chart)
        self._pending_redraw = False  # 标记是否有待重绘的任务
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

        # 预测说明标签
        self.prediction_label = QLabel(
            f"预测说明：当收到10个实时数据点后，将使用最近最多 {self._prediction_window} 个数据点的加权移动平均/线性趋势外推未来走势。历史预测点（红点）固定不变，未来预测（红色虚线）持续更新。"
        )
        self.prediction_label.setWordWrap(True)
        self.prediction_label.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        layout.addWidget(self.prediction_label)
        
        # 数据表格
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["日期", "时间点", f"{self.get_metric_name()}值"])
        # 设置列宽比例：日期列较窄，时间点列较宽（用于显示统计信息），温度值列中等
        self.table.setColumnWidth(0, 120)  # 日期列：120像素
        self.table.setColumnWidth(1, 400)  # 时间点列：400像素（较宽，用于显示统计信息）
        self.table.setColumnWidth(2, 150)  # 温度值列：150像素（较窄）
        self.table.horizontalHeader().setStretchLastSection(False)  # 禁用自动拉伸最后一列
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
        
        
        # 停止重绘定时器
        if hasattr(self, '_redraw_timer'):
            self._redraw_timer.stop()
        
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
        
        # 重置预测点（开始新的订阅时，清空之前的预测点）
        self._prediction_points = []
        self._historical_fit_points = []
        self._prediction_start_time = None  # 重置预测开始时间
        
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
            
            # 检查是否已存在相同时间戳的点（避免重复）
            for i, (existing_dt, _) in enumerate(self._chart_data):
                if existing_dt == dt:
                    # 如果已存在，更新值而不是添加新点
                    self._chart_data[i] = (dt, float(value))
                    # 使用防抖机制，避免频繁重绘
                    if not self._redraw_timer.isActive():
                        self._redraw_timer.start(100)  # 100ms防抖
                    return
            
            # 添加新点
            self._chart_data.append((dt, float(value)))
            
            # 不在添加数据时截断，避免在重绘过程中丢失数据
            # 数据清理将在重绘完成后进行
            
            # 使用防抖机制，避免频繁重绘（高速更新时）
            # 如果定时器已经在运行，重置它（延长等待时间）
            if self._redraw_timer.isActive():
                self._redraw_timer.stop()
            self._redraw_timer.start(200)  # 200ms防抖，确保数据不会丢失
        except Exception as e:
            pass
        
    def _compute_linear_prediction(self, times, values):
        """
        使用最近 self._prediction_window 个点做加权移动平均+线性回归，外推未来一小段时间。
        同时生成历史拟合点，确保预测曲线与历史数据高度拟合。
        返回预测点的 (pred_times, pred_values) 列表。
        """
        try:
            n = len(times)
            if n < 10:
                # 数据点太少，不做预测
                return [], []

            window = min(self._prediction_window, n)
            recent_times = times[-window:]
            recent_values = values[-window:]

            # 使用移动平均平滑数据，提高拟合效果
            # 使用加权移动平均，给最近的数据更高权重
            smoothed_values = []
            ma_window = min(5, window // 4)  # 移动平均窗口，约为总窗口的1/4
            if ma_window < 1:
                ma_window = 1
            
            for i in range(len(recent_values)):
                # 计算加权移动平均
                start_idx = max(0, i - ma_window + 1)
                end_idx = i + 1
                weights = []
                weighted_sum = 0
                weight_sum = 0
                for j in range(start_idx, end_idx):
                    # 越近的数据权重越大
                    weight = (j - start_idx + 1) / (end_idx - start_idx)
                    weights.append(weight)
                    weighted_sum += recent_values[j] * weight
                    weight_sum += weight
                if weight_sum > 0:
                    smoothed_values.append(weighted_sum / weight_sum)
                else:
                    smoothed_values.append(recent_values[i])

            # 将时间转换为数值（天数）
            x = [mdates.date2num(t) for t in recent_times]
            y = smoothed_values  # 使用平滑后的数据

            # 使用加权线性回归，给最近的数据点更高权重
            x_mean = sum(x) / window
            y_mean = sum(y) / window

            # 计算加权协方差和方差
            num = 0
            den = 0
            for i, (xi, yi) in enumerate(zip(x, y)):
                # 权重：越近的数据权重越大
                weight = (i + 1) / window
                num += weight * (xi - x_mean) * (yi - y_mean)
                den += weight * (xi - x_mean) ** 2
            
            if den == 0:
                return [], []
            
            slope = num / den
            intercept = y_mean - slope * x_mean

            # 估算时间步长：使用窗口内跨度 / (window-1)
            if window >= 2:
                total_span = x[-1] - x[0]
                step = total_span / (window - 1) if total_span > 0 else 1.0 / (24 * 60)
            else:
                step = 1.0 / (24 * 60)  # 兜底：约 1 分钟

            future_points = 10  # 预测未来 10 个点
            start_x = x[-1]

            pred_times = []
            pred_values = []

            # 不仅预测未来，还要生成历史拟合点（从窗口开始到结束）
            # 这样可以确保预测曲线与历史数据高度拟合
            historical_pred_times = []
            historical_pred_values = []
            
            # 生成历史拟合点（从窗口的第一个点开始）
            for i, xi in enumerate(x):
                yi = slope * xi + intercept
                t = mdates.num2date(xi)
                if getattr(t, "tzinfo", None) is not None:
                    t = t.replace(tzinfo=None)
                historical_pred_times.append(t)
                historical_pred_values.append(yi)

            # 生成未来预测点
            for i in range(1, future_points + 1):
                xi = start_x + i * step
                yi = slope * xi + intercept
                
                # 限制预测值在合理范围内（基于历史数据的范围）
                min_y = min(recent_values)
                max_y = max(recent_values)
                data_range = max_y - min_y
                margin = max(0.2 * data_range, 1.0)  # 允许20%的波动范围
                low = min_y - margin
                high = max_y + margin
                
                if yi < low:
                    yi = low
                elif yi > high:
                    yi = high

                t = mdates.num2date(xi)
                if getattr(t, "tzinfo", None) is not None:
                    t = t.replace(tzinfo=None)

                pred_times.append(t)
                pred_values.append(yi)

            # 返回历史拟合点 + 未来预测点
            # 历史拟合点用于显示红色点，未来预测点用于显示红色虚线
            all_pred_times = historical_pred_times + pred_times
            all_pred_values = historical_pred_values + pred_values

            return all_pred_times, all_pred_values
        except Exception:
            return [], []

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
            
            # 在绘制前立即创建数据快照，确保数据不会被修改
            # 使用深拷贝避免引用问题，并立即截断到合理大小用于显示
            # 注意：这里截断的是用于显示的数据，不影响原始 _chart_data
            chart_data_snapshot = list(self._chart_data)  # 创建快照
            
            # 如果数据点太多，只显示最近1500个点（用于图表显示）
            # 但保留完整的 _chart_data 用于预测计算
            # 增加显示的数据点数量，确保历史数据不会消失
            if len(chart_data_snapshot) > 1500:
                chart_data_snapshot = chart_data_snapshot[-1500:]
            
            # 在重绘完成后，清理过旧的数据（只保留最近2000个点）
            # 这样可以避免内存无限增长，同时确保重绘时数据完整
            if len(self._chart_data) > 2000:
                self._chart_data = self._chart_data[-2000:]
            
            if not chart_data_snapshot:
                return
            
            times = [item[0] for item in chart_data_snapshot]
            values = [item[1] for item in chart_data_snapshot]
            
            # 绘制图表
            self.ax.clear()
            self.ax.set_xlabel("时间")
            self.ax.set_ylabel(f"{self.get_metric_name()}")
            self.ax.set_title(f"{self.get_metric_name()}数据趋势图（实时数据 + 线性趋势预测）")
            self.ax.grid(True, alpha=0.3)
            
            # 确保数据按时间排序
            if times:
                sorted_pairs = sorted(zip(times, values))
                times = [t for t, v in sorted_pairs]
                values = [v for t, v in sorted_pairs]

            if times and values:
                # 先画历史曲线
                self.ax.plot(
                    times,
                    values,
                    marker="o",
                    markersize=3,
                    linewidth=1.5,
                    color="#3498db",
                    label=f"{self.get_metric_name()}历史数据",
                )

                # 计算新的预测点（使用完整的 _chart_data 进行预测，而不是只使用显示的数据）
                # 这样可以获得更准确的预测
                full_times = [item[0] for item in self._chart_data]
                full_values = [item[1] for item in self._chart_data]
                last_real_time = full_times[-1] if full_times else None
                
                # 获取已有真实数据的时间点集合（用于过滤已实现的预测点）
                real_times_set = {t.replace(second=0, microsecond=0) for t in full_times}
                
                # 从第10个数据点开始，每次收到新数据时都更新预测
                # 历史预测点（红点）：固定不变，一旦生成就不再改变，只从第10个数据点开始
                # 未来预测点（红色虚线）：持续更新
                min_points_for_fit = 10  # 至少需要10个点就可以生成预测
                
                if len(full_times) >= min_points_for_fit:
                    # 记录开始预测的时间（第10个数据点的时间）
                    if self._prediction_start_time is None:
                        self._prediction_start_time = full_times[min_points_for_fit - 1]  # 第10个数据点（索引9）
                    
                    # 使用最新的数据进行预测（最多使用 _prediction_window 个点）
                    fit_window = min(self._prediction_window, len(full_times))
                    pred_times, pred_values = self._compute_linear_prediction(
                        full_times[-fit_window:], 
                        full_values[-fit_window:]
                    )
                    
                    if pred_times and pred_values and last_real_time and self._prediction_start_time:
                        # 分离历史拟合点和未来预测点
                        new_historical_fit_points = []
                        future_pred_points = []
                        
                        # 获取已有历史预测点的时间集合（用于判断是否需要添加新的历史预测点）
                        existing_historical_times = {t.replace(second=0, microsecond=0) for t, v in self._historical_fit_points}
                        
                        # 确保预测开始时间是 naive datetime
                        prediction_start = self._prediction_start_time
                        if prediction_start.tzinfo is not None:
                            prediction_start = prediction_start.replace(tzinfo=None)
                        
                        for t, v in zip(pred_times, pred_values):
                            t_minute = t.replace(second=0, microsecond=0)
                            # 确保时间是 naive datetime
                            if t.tzinfo is not None:
                                t = t.replace(tzinfo=None)
                            
                            if t < last_real_time:
                                # 历史拟合点：只从第10个数据点开始，如果该时间点还没有历史预测点，就添加它（固定）
                                if t >= prediction_start and t_minute not in existing_historical_times:
                                    new_historical_fit_points.append((t, v))
                            elif t >= last_real_time:
                                # 未来预测点：会随着新数据更新
                                if t_minute not in real_times_set:
                                    future_pred_points.append((t, v))
                        
                        # 添加新的历史拟合点（固定不变）
                        if new_historical_fit_points:
                            self._historical_fit_points.extend(new_historical_fit_points)
                            # 按时间排序
                            self._historical_fit_points = sorted(self._historical_fit_points, key=lambda x: x[0])
                        
                        # 更新未来预测点（持续更新）
                        if future_pred_points:
                            self._prediction_points = future_pred_points
                
                # 绘制预测点：分为历史拟合（红点，固定不变）和未来预测（红色虚线，会更新）
                if last_real_time:
                    # 确保 last_real_time 是 naive datetime
                    if last_real_time.tzinfo is not None:
                        last_real_time = last_real_time.replace(tzinfo=None)
                    
                    # 绘制历史拟合点（固定不变）
                    if self._historical_fit_points:
                        historical_fit = []
                        for t, v in self._historical_fit_points:
                            # 确保预测点时间也是 naive datetime
                            if t.tzinfo is not None:
                                t = t.replace(tzinfo=None)
                            historical_fit.append((t, v))
                        
                        if historical_fit:
                            hist_times = [t for t, v in historical_fit]
                            hist_values = [v for t, v in historical_fit]
                            # 按时间排序
                            sorted_pairs = sorted(zip(hist_times, hist_values))
                            hist_times = [t for t, v in sorted_pairs]
                            hist_values = [v for t, v in sorted_pairs]
                            
                            # 绘制为红色点，用于显示拟合效果（固定不变）
                            self.ax.scatter(
                                hist_times,
                                hist_values,
                                color="#e74c3c",
                                marker="o",
                                s=20,  # 稍微减小点的大小，避免过于突出
                                alpha=0.6,  # 稍微降低透明度，使拟合效果更自然
                                label=f"{self.get_metric_name()}历史拟合",
                                zorder=5
                            )
                    
                    # 绘制未来预测（红色虚线，会更新）
                    if self._prediction_points:
                        future_pred = []
                        for t, v in self._prediction_points:
                            # 确保预测点时间也是 naive datetime
                            if t.tzinfo is not None:
                                t = t.replace(tzinfo=None)
                            
                            if t >= last_real_time:
                                # 只绘制未来预测点
                                future_pred.append((t, v))
                        
                        if future_pred:
                            future_times = [t for t, v in future_pred]
                            future_values = [v for t, v in future_pred]
                            # 确保按时间排序
                            sorted_pairs = sorted(zip(future_times, future_values))
                            future_times = [t for t, v in sorted_pairs]
                            future_values = [v for t, v in sorted_pairs]
                            
                            # 绘制未来预测线
                            self.ax.plot(
                                future_times,
                                future_values,
                                linestyle="--",
                                linewidth=1.5,
                                color="#e74c3c",
                                label=f"{self.get_metric_name()}未来预测",
                                zorder=4
                            )

                # 格式化 x 轴
                self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d\n%H:%M:%S'))
                self.figure.autofmt_xdate()

                self.ax.legend()

            # 使用draw_idle而不是draw，更安全
            self.canvas.draw_idle()
        except Exception as e:
            pass
        
    def on_mqtt_error(self, error_msg: str):
        """MQTT错误"""
        QMessageBox.critical(self, "MQTT错误", error_msg)
    
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
        
        # 标题和速度显示
        title_layout = QHBoxLayout()
        title = QLabel("订阅端")
        title.setFont(QFont("Microsoft YaHei", 24, QFont.Bold))
        title_layout.addWidget(title)
        
        title_layout.addStretch()
        
        # 当前发布速度显示
        self.speed_label = QLabel("当前发布速度: 1.0 Hz")
        self.speed_label.setFont(QFont("Microsoft YaHei", 12))
        self.speed_label.setStyleSheet("color: #7f8c8d; padding: 5px;")
        title_layout.addWidget(self.speed_label)
        
        layout.addLayout(title_layout)
        
        # 定时更新速度显示
        self.speed_timer = QTimer()
        self.speed_timer.timeout.connect(self.update_speed_display)
        self.speed_timer.start(500)  # 每500ms更新一次
        
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
    
    def update_speed_display(self):
        """更新速度显示"""
        from config import config
        current_rate = config.CURRENT_PUBLISH_RATE
        self.speed_label.setText(f"当前发布速度: {current_rate:.1f} Hz")
    
    def on_publisher_clicked(self):
        """跳转到发布端控制页面"""
        if hasattr(self, 'main_window') and self.main_window:
            self.main_window.switch_to_publisher()
    

