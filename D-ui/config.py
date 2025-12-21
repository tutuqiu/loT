"""
配置管理模块
"""
import os
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    """应用配置"""
    # C-collector API 基础URL
    C_API_BASE: str = "http://127.0.0.1:8000"
    
    # B-publisher 脚本路径（相对于项目根目录）
    PUBLISHER_SCRIPT: str = "B-publisher/publish.py"
    
    # Python 解释器路径
    PYTHON_EXECUTABLE: str = sys.executable
    
    # 默认参数
    DEFAULT_RATE: float = 1.0
    DEFAULT_LIMIT: int = 200
    DEFAULT_REFRESH_INTERVAL: int = 1000  # 毫秒（1秒刷新一次，更及时）
    
    # MQTT配置（与实际IoT项目保持一致）
    # 注意：B-publisher使用admin/admin123，C-collector使用collector/col123
    # D-ui作为订阅端，使用collector用户（有订阅权限）
    MQTT_BROKER_HOST: str = "139.224.237.20"
    MQTT_BROKER_PORT: int = 1883
    MQTT_USERNAME: str = "collector"
    MQTT_PASSWORD: str = "col123"
    MQTT_USE_WEBSOCKETS: bool = False  # 使用TCP连接（1883端口）
    MQTT_WS_PATH: str = "/mqtt"  # WebSocket路径（如果使用WebSocket）
    
    # 项目根目录（loT目录）- 使用__file__的绝对路径
    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent  # D-ui -> loT
    
    def get_publisher_script_path(self) -> Path:
        """获取发布脚本的绝对路径"""
        script_path = self.PROJECT_ROOT / self.PUBLISHER_SCRIPT
        
        # 如果路径不存在，尝试多种方式查找
        if not script_path.exists():
            import os
            # 方式1: 从当前工作目录查找
            cwd = Path(os.getcwd())
            if (cwd / "B-publisher" / "publish.py").exists():
                return cwd / "B-publisher" / "publish.py"
            if (cwd / "loT" / "B-publisher" / "publish.py").exists():
                return cwd / "loT" / "B-publisher" / "publish.py"
            # 方式2: 从脚本所在目录向上查找
            script_dir = Path(__file__).resolve().parent
            for parent in [script_dir.parent, script_dir.parent.parent]:
                test_path = parent / "B-publisher" / "publish.py"
                if test_path.exists():
                    return test_path
        
        return script_path
    
    def get_api_url(self, endpoint: str) -> str:
        """构建完整的API URL"""
        base = self.C_API_BASE.rstrip('/')
        endpoint = endpoint.lstrip('/')
        return f"{base}/{endpoint}"


# 全局配置实例
config = Config()

