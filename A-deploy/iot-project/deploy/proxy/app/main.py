#!/usr/bin/env python3
"""
MQTT Gateway Proxy Service
IoT Project - Group A

功能：
1. 订阅 ingest/env/# 并转发到 env/#
2. 校验和清洗 payload
3. 日志记录每条消息
4. 防循环（只订阅 ingest 前缀）
5. 可选：去重（同一 metric 同一 ts）
"""

import os
import sys
import json
import time
import logging
import signal
from datetime import datetime
from collections import OrderedDict
from typing import Optional, Dict, Any, Tuple

import paho.mqtt.client as mqtt


# ============================================================
# 配置类
# ============================================================

class Config:
    """从环境变量读取配置"""
    
    BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
    BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
    USERNAME = os.getenv("MQTT_USERNAME", "proxy")
    PASSWORD = os.getenv("MQTT_PASSWORD", "proxy123")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # 去重配置
    DEDUP_ENABLED = os.getenv("DEDUP_ENABLED", "true").lower() == "true"
    DEDUP_CACHE_SIZE = int(os.getenv("DEDUP_CACHE_SIZE", "1000"))
    DEDUP_CACHE_TTL = int(os.getenv("DEDUP_CACHE_TTL", "300"))
    
    # Topic 映射规则
    INGEST_PREFIX = "ingest/env/"
    OUTPUT_PREFIX = "env/"
    
    # 支持的 metrics
    ALLOWED_METRICS = ["temperature", "humidity", "pressure"]


# ============================================================
# 日志配置
# ============================================================

def setup_logging():
    """配置日志"""
    log_level = getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO)
    
    # 日志格式
    log_format = (
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt='%Y-%m-%dT%H:%M:%S',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger("MQTTProxy")


logger = setup_logging()


# ============================================================
# 去重缓存（可选功能）
# ============================================================

class DedupCache:
    """LRU 缓存，用于去重"""
    
    def __init__(self, max_size: int, ttl: int):
        self.max_size = max_size
        self.ttl = ttl
        self.cache: OrderedDict[str, float] = OrderedDict()
    
    def is_duplicate(self, metric: str, ts: str) -> bool:
        """检查是否重复"""
        key = f"{metric}:{ts}"
        current_time = time.time()
        
        # 清理过期条目
        self._evict_expired(current_time)
        
        # 检查是否存在
        if key in self.cache:
            return True
        
        # 添加到缓存
        self.cache[key] = current_time
        
        # 限制缓存大小
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)  # 删除最旧的
        
        return False
    
    def _evict_expired(self, current_time: float):
        """清理过期条目"""
        keys_to_remove = [
            key for key, timestamp in self.cache.items()
            if current_time - timestamp > self.ttl
        ]
        for key in keys_to_remove:
            del self.cache[key]


# ============================================================
# Payload 验证与清洗
# ============================================================

class PayloadValidator:
    """Payload 验证与清洗器"""
    
    @staticmethod
    def validate_and_clean(payload_str: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        验证并清洗 payload
        
        返回: (cleaned_payload, error_reason)
        如果验证失败，返回 (None, reason)
        如果验证成功，返回 (cleaned_payload, None)
        """
        
        # 1. 必须是合法 JSON
        try:
            data = json.loads(payload_str)
        except json.JSONDecodeError as e:
            return None, f"Invalid JSON: {str(e)}"
        
        if not isinstance(data, dict):
            return None, "Payload must be a JSON object"
        
        # 2. 必须有 ts 和 value 字段
        if "ts" not in data:
            return None, "Missing required field: ts"
        if "value" not in data:
            return None, "Missing required field: value"
        
        ts = data["ts"]
        value = data["value"]
        
        # 3. 验证 ts 格式（基本 ISO8601 校验）
        if not isinstance(ts, str):
            return None, f"Field 'ts' must be string, got {type(ts).__name__}"
        
        if not PayloadValidator._is_valid_iso8601(ts):
            return None, f"Field 'ts' is not valid ISO8601 format: {ts}"
        
        # 4. 清洗 value
        cleaned_value, modified = PayloadValidator._clean_value(value)
        
        # 构造清洗后的 payload
        cleaned_payload = {
            "ts": ts,
            "value": cleaned_value
        }
        
        return cleaned_payload, None
    
    @staticmethod
    def _is_valid_iso8601(ts_str: str) -> bool:
        """
        基本 ISO8601 格式验证
        接受格式：YYYY-MM-DDTHH:MM:SS
        """
        try:
            # 尝试解析（支持多种格式）
            datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
            return True
        except ValueError:
            return False
    
    @staticmethod
    def _clean_value(value: Any) -> Tuple[Any, bool]:
        """
        清洗 value 字段
        
        返回: (cleaned_value, was_modified)
        
        规则：
        - 如果是 number，直接返回
        - 如果是 null，返回 null
        - 如果是字符串数字（如 "23.5"），转为 number
        - 如果是空字符串 ""，转为 null
        - 其他情况视为错误（但在这里转为 null）
        """
        modified = False
        
        # null 或 None
        if value is None:
            return None, modified
        
        # 数字类型
        if isinstance(value, (int, float)):
            return value, modified
        
        # 字符串类型
        if isinstance(value, str):
            # 空字符串 → null
            if value == "":
                return None, True
            
            # 尝试转换为数字
            try:
                # 尝试整数
                if '.' not in value:
                    return int(value), True
                else:
                    return float(value), True
            except ValueError:
                # 无法转换，返回 null
                return None, True
        
        # 其他类型：返回 null
        return None, True


# ============================================================
# MQTT 代理网关
# ============================================================

class MQTTGateway:
    """MQTT 代理网关"""
    
    def __init__(self):
        self.client: Optional[mqtt.Client] = None
        self.connected = False
        self.should_stop = False
        
        # 统计信息
        self.stats = {
            "received": 0,
            "forwarded": 0,
            "dropped": 0,
            "duplicated": 0,
            "modified": 0
        }
        
        # 去重缓存
        if Config.DEDUP_ENABLED:
            self.dedup_cache = DedupCache(
                Config.DEDUP_CACHE_SIZE,
                Config.DEDUP_CACHE_TTL
            )
            logger.info(f"Deduplication enabled (cache size: {Config.DEDUP_CACHE_SIZE}, TTL: {Config.DEDUP_CACHE_TTL}s)")
        else:
            self.dedup_cache = None
            logger.info("Deduplication disabled")
    
    def setup(self):
        """设置 MQTT 客户端"""
        logger.info("Setting up MQTT Gateway...")
        
        # 创建客户端
        self.client = mqtt.Client(
            client_id=f"proxy-gateway-{int(time.time())}",
            clean_session=True,
            protocol=mqtt.MQTTv311
        )
        
        # 设置用户名密码
        self.client.username_pw_set(Config.USERNAME, Config.PASSWORD)
        
        # 绑定回调
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        
        logger.info(f"Broker: {Config.BROKER_HOST}:{Config.BROKER_PORT}")
        logger.info(f"Username: {Config.USERNAME}")
    
    def connect(self):
        """连接到 Broker"""
        while not self.should_stop:
            try:
                logger.info(f"Connecting to MQTT Broker at {Config.BROKER_HOST}:{Config.BROKER_PORT}...")
                self.client.connect(
                    Config.BROKER_HOST,
                    Config.BROKER_PORT,
                    keepalive=60
                )
                # 进入消息循环
                self.client.loop_forever()
                
            except ConnectionRefusedError:
                logger.error("Connection refused. Retrying in 5 seconds...")
                time.sleep(5)
            except Exception as e:
                logger.error(f"Connection error: {e}. Retrying in 5 seconds...")
                time.sleep(5)
    
    def on_connect(self, client, userdata, flags, rc):
        """连接成功回调"""
        if rc == 0:
            self.connected = True
            logger.info("✓ Connected to MQTT Broker successfully")
            
            # 订阅 ingest/env/# (防止循环：不订阅 env/#)
            subscribe_topic = f"{Config.INGEST_PREFIX}#"
            client.subscribe(subscribe_topic, qos=0)
            logger.info(f"✓ Subscribed to: {subscribe_topic}")
            
            logger.info("Gateway is ready to forward messages")
            logger.info(f"Mapping: {Config.INGEST_PREFIX}* → {Config.OUTPUT_PREFIX}*")
            
        else:
            error_messages = {
                1: "Connection refused - incorrect protocol version",
                2: "Connection refused - invalid client identifier",
                3: "Connection refused - server unavailable",
                4: "Connection refused - bad username or password",
                5: "Connection refused - not authorized"
            }
            error_msg = error_messages.get(rc, f"Unknown error (code: {rc})")
            logger.error(f"✗ Connection failed: {error_msg}")
            self.connected = False
    
    def on_disconnect(self, client, userdata, rc):
        """断开连接回调"""
        self.connected = False
        if rc != 0:
            logger.warning(f"Unexpected disconnection (code: {rc}). Will attempt to reconnect...")
        else:
            logger.info("Disconnected from MQTT Broker")
    
    def on_message(self, client, userdata, msg):
        """收到消息回调"""
        self.stats["received"] += 1
        
        topic = msg.topic
        payload = msg.payload.decode('utf-8', errors='ignore')
        
        # 提取 metric（temperature, humidity, pressure）
        if not topic.startswith(Config.INGEST_PREFIX):
            logger.warning(f"Received message from unexpected topic: {topic}")
            return
        
        metric = topic[len(Config.INGEST_PREFIX):]
        
        # 检查是否是允许的 metric
        if metric not in Config.ALLOWED_METRICS:
            logger.warning(f"Unknown metric '{metric}', dropping message | topic={topic}")
            self.stats["dropped"] += 1
            return
        
        # 验证和清洗 payload
        cleaned_payload, error_reason = PayloadValidator.validate_and_clean(payload)
        
        if cleaned_payload is None:
            # 验证失败，丢弃
            logger.warning(
                f"DROP | topic={topic} | reason={error_reason} | "
                f"raw_payload={payload[:100]}"
            )
            self.stats["dropped"] += 1
            return
        
        # 检查是否修正过
        was_modified = (json.dumps(cleaned_payload, separators=(',', ':')) != payload)
        if was_modified:
            self.stats["modified"] += 1
        
        # 去重检查（可选）
        if self.dedup_cache:
            ts = cleaned_payload["ts"]
            if self.dedup_cache.is_duplicate(metric, ts):
                logger.info(
                    f"DUPLICATE | topic={topic} | ts={ts} | "
                    f"value={cleaned_payload['value']} | dropped"
                )
                self.stats["duplicated"] += 1
                return
        
        # 转发到输出 topic
        output_topic = f"{Config.OUTPUT_PREFIX}{metric}"
        output_payload = json.dumps(cleaned_payload, separators=(',', ':'))
        
        try:
            client.publish(
                output_topic,
                output_payload,
                qos=0,
                retain=False
            )
            
            self.stats["forwarded"] += 1
            
            # 记录日志
            status = "MODIFIED" if was_modified else "FORWARD"
            logger.info(
                f"{status} | {topic} → {output_topic} | "
                f"ts={cleaned_payload['ts']} | value={cleaned_payload['value']}"
            )
            
        except Exception as e:
            logger.error(f"Failed to publish to {output_topic}: {e}")
            self.stats["dropped"] += 1
    
    def stop(self):
        """停止网关"""
        logger.info("Stopping MQTT Gateway...")
        self.should_stop = True
        
        if self.client and self.connected:
            self.client.disconnect()
        
        # 打印统计信息
        logger.info("=" * 60)
        logger.info("Gateway Statistics:")
        logger.info(f"  Total received:  {self.stats['received']}")
        logger.info(f"  Forwarded:       {self.stats['forwarded']}")
        logger.info(f"  Modified:        {self.stats['modified']}")
        logger.info(f"  Duplicated:      {self.stats['duplicated']}")
        logger.info(f"  Dropped:         {self.stats['dropped']}")
        logger.info("=" * 60)
    
    def run(self):
        """运行网关"""
        self.setup()
        self.connect()


# ============================================================
# 主函数
# ============================================================

def signal_handler(sig, frame):
    """处理退出信号"""
    logger.info(f"Received signal {sig}, shutting down...")
    if gateway:
        gateway.stop()
    sys.exit(0)


# 全局 gateway 实例
gateway: Optional[MQTTGateway] = None


def main():
    """主函数"""
    global gateway
    
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("=" * 60)
    logger.info("MQTT Gateway Proxy Service")
    logger.info("IoT Project - Group A")
    logger.info("=" * 60)
    
    # 创建并运行网关
    gateway = MQTTGateway()
    
    try:
        gateway.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        if gateway:
            gateway.stop()


if __name__ == "__main__":
    main()
