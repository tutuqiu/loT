"""
HTTP 请求工作线程模块
"""
import requests
from PyQt5.QtCore import QThread, pyqtSignal


class HttpWorker(QThread):
    """HTTP请求工作线程"""
    
    finished = pyqtSignal(dict)  # 成功时发送数据
    error = pyqtSignal(str)  # 失败时发送错误信息
    
    def __init__(self, url: str, params: dict = None, parent=None):
        super().__init__(parent)
        self.url = url
        self.params = params or {}
    
    def run(self):
        """执行HTTP请求"""
        try:
            print(f"[HTTP Worker] 请求: {self.url}, 参数: {self.params}")
            response = requests.get(self.url, params=self.params, timeout=5)
            response.raise_for_status()
            data = response.json()
            print(f"[HTTP Worker] 响应成功: 收到 {len(data.get('points', []))} 个数据点")
            self.finished.emit(data)
        except requests.exceptions.Timeout:
            print(f"[HTTP Worker] 请求超时: {self.url}")
            self.error.emit("请求超时")
        except requests.exceptions.ConnectionError:
            print(f"[HTTP Worker] 连接失败: {self.url}")
            self.error.emit("连接失败，请检查C-collector是否运行")
        except requests.exceptions.HTTPError as e:
            print(f"[HTTP Worker] HTTP错误: {e}")
            self.error.emit(f"HTTP错误: {e}")
        except ValueError as e:
            print(f"[HTTP Worker] JSON解析失败: {e}")
            self.error.emit(f"JSON解析失败: {e}")
        except Exception as e:
            print(f"[HTTP Worker] 未知错误: {e}")
            self.error.emit(f"未知错误: {e}")

