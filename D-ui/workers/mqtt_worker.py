"""
MQTT 订阅工作线程模块
"""
import json
import uuid
from PyQt5.QtCore import QThread, pyqtSignal
try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False


class MQTTSubscriber(QThread):
    """MQTT订阅工作线程"""
    
    message_received = pyqtSignal(str, dict)  # topic, data
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self, broker_host="118.89.72.217", broker_port=8083, 
                 username="mqtt_server", password="mqtt_password", 
                 use_websockets=True, ws_path="/mqtt", parent=None):
        super().__init__(parent)
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.username = username
        self.password = password
        self.use_websockets = use_websockets
        self.ws_path = ws_path
        self.client = None
        self.subscribed_topics = set()
        self.running = False
        self._connected = False
    
    def run(self):
        """运行MQTT客户端"""
        if not MQTT_AVAILABLE:
            self.error.emit("paho-mqtt 未安装，请运行: pip install paho-mqtt")
            return
        
        try:
            # 创建客户端
            if self.use_websockets:
                # WebSocket连接需要指定client_id和transport
                client_id = f"pyqt_client_{uuid.uuid4()}"
                self.client = mqtt.Client(
                    client_id=client_id,
                    transport='websockets',
                    clean_session=True
                )
                # 设置WebSocket路径
                try:
                    self.client.ws_set_options(path=self.ws_path)
                except Exception as e:
                    # 如果设置失败，尝试根路径
                    try:
                        self.client.ws_set_options(path="/")
                    except:
                        pass  # 使用默认路径
            else:
                self.client = mqtt.Client(
                    client_id=f"pyqt_client_{uuid.uuid4()}",
                    clean_session=True
                )
            
            self.client.username_pw_set(self.username, self.password)
            self.client.on_connect = self.on_connect
            self.client.on_message = self.on_message
            self.client.on_disconnect = self.on_disconnect
            self.client.on_error = self.on_error_callback
            
            # 连接（WebSocket需要指定路径）
            if self.use_websockets:
                # WebSocket连接，路径通常是/mqtt
                self.client.connect(self.broker_host, self.broker_port, 60)
            else:
                self.client.connect(self.broker_host, self.broker_port, 60)
            
            self.running = True
            self.client.loop_start()
            
            # 等待连接（最多5秒）
            import time
            timeout = 5
            start_time = time.time()
            while not hasattr(self, '_connected') and (time.time() - start_time) < timeout:
                self.msleep(100)
            
            if not hasattr(self, '_connected'):
                self.error.emit("MQTT连接超时")
                self.running = False
                return
            
            # 保持运行
            while self.running:
                self.msleep(100)
            
        except Exception as e:
            error_msg = f"MQTT连接错误: {str(e)}"
            self.error.emit(error_msg)
    
    def on_error_callback(self, client, userdata, error):
        """错误回调"""
        error_msg = f"MQTT客户端错误: {error}"
        self.error.emit(error_msg)
    
    def on_connect(self, client, userdata, flags, rc):
        """连接回调"""
        if rc == 0:
            self._connected = True
            self.connected.emit()
        else:
            error_codes = {
                1: "协议版本不正确",
                2: "客户端ID无效",
                3: "服务器不可用",
                4: "用户名或密码错误",
                5: "未授权"
            }
            error_msg = error_codes.get(rc, f"未知错误码: {rc}")
            self.error.emit(f"MQTT连接失败: {error_msg} (错误码: {rc})")
    
    def on_message(self, client, userdata, msg):
        """消息接收回调"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            data = json.loads(payload)
            self.message_received.emit(topic, data)
        except Exception as e:
            self.error.emit(f"消息解析错误: {str(e)}")
    
    def on_disconnect(self, client, userdata, rc):
        """断开连接回调"""
        self.disconnected.emit()
    
    def subscribe_topic(self, topic: str):
        """订阅主题"""
        if self.client and hasattr(self, '_connected') and self._connected:
            try:
                result, mid = self.client.subscribe(topic, qos=1)
                if result == mqtt.MQTT_ERR_SUCCESS:
                    self.subscribed_topics.add(topic)
                else:
                    self.error.emit(f"订阅主题失败: {topic}")
            except Exception as e:
                self.error.emit(f"订阅主题异常: {str(e)}")
        else:
            self.error.emit("MQTT客户端未连接，请先连接")
    
    def unsubscribe_topic(self, topic: str):
        """取消订阅主题"""
        if self.client and self.client.is_connected():
            self.client.unsubscribe(topic)
            self.subscribed_topics.discard(topic)
    
    def stop(self):
        """停止订阅"""
        self.running = False
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()

