#!/usr/bin/env python3
"""
MQTT 发布测试脚本 - B 部分使用
发布数据到 ingest/env/* 主题
"""
import paho.mqtt.client as mqtt
import json
import time
import sys
from datetime import datetime

# 连接配置
BROKER_HOST = "139.224.237.20"
BROKER_PORT = 1883
USERNAME = "publisher"
PASSWORD = "pub123"

# 发布成功标志
published = False

def on_connect(client, userdata, flags, rc):
    """连接回调"""
    if rc == 0:
        print("✓ 已连接到 Broker")
    else:
        print(f"✗ 连接失败 (错误码: {rc})")
        sys.exit(1)

def on_publish(client, userdata, mid):
    """发布回调"""
    global published
    published = True
    print(f"✓ 消息已发送 (message_id: {mid})")

def publish_data(metric, value):
    """
    发布数据
    
    Args:
        metric: temperature, humidity, pressure
        value: 数值或 None
    """
    # 创建客户端
    client = mqtt.Client()
    client.username_pw_set(USERNAME, PASSWORD)
    client.on_connect = on_connect
    client.on_publish = on_publish
    
    # 连接
    print(f"正在连接到 {BROKER_HOST}:{BROKER_PORT}...")
    try:
        client.connect(BROKER_HOST, BROKER_PORT, 60)
    except Exception as e:
        print(f"✗ 连接失败: {e}")
        sys.exit(1)
    
    # 启动网络循环
    client.loop_start()
    
    # 等待连接成功
    time.sleep(1)
    
    # 构造 payload
    topic = f"ingest/env/{metric}"
    payload = {
        "ts": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "value": value
    }
    
    # 发布
    print(f"发布主题: {topic}")
    print(f"Payload: {json.dumps(payload)}")
    
    result = client.publish(topic, json.dumps(payload), qos=0)
    
    # 等待发送完成（最多等待 3 秒）
    for i in range(30):
        if published:
            break
        time.sleep(0.1)
    
    if not published:
        print("⚠️  发送可能未完成")
    
    # 断开连接
    client.loop_stop()
    client.disconnect()
    
    print("✓ 完成")

if __name__ == "__main__":
    # 示例：发送温度数据
    if len(sys.argv) == 3:
        metric = sys.argv[1]
        try:
            value = float(sys.argv[2]) if sys.argv[2].lower() != "null" else None
        except ValueError:
            print(f"✗ 无效的数值: {sys.argv[2]}")
            sys.exit(1)
        
        if metric not in ["temperature", "humidity", "pressure"]:
            print(f"✗ 无效的 metric: {metric}")
            print("  支持: temperature, humidity, pressure")
            sys.exit(1)
        
        publish_data(metric, value)
    else:
        print("用法: python3 publish_test.py <metric> <value>")
        print("")
        print("示例:")
        print("  python3 publish_test.py temperature 25.3")
        print("  python3 publish_test.py humidity 60.5")
        print("  python3 publish_test.py pressure 1013.25")
        print("  python3 publish_test.py temperature null")
        print("")
        print("默认测试（温度 66.6）:")
        publish_data("temperature", 66.6)
