#!/usr/bin/env python3
"""
MQTT 订阅测试脚本 - C 部分使用
订阅 env/* 主题的数据
"""
import paho.mqtt.client as mqtt
import json
import sys

# 连接配置
BROKER_HOST = "139.224.237.20"
BROKER_PORT = 1883
USERNAME = "collector"
PASSWORD = "col123"

def on_connect(client, userdata, flags, rc):
    """连接回调"""
    if rc == 0:
        print("✓ 已连接到 Broker")
        client.subscribe("env/#", qos=0)
        print("✓ 已订阅: env/#")
        print("-" * 60)
        print("等待消息... (按 Ctrl+C 退出)")
        print("-" * 60)
    else:
        error_messages = {
            1: "协议版本错误",
            2: "客户端 ID 错误",
            3: "服务器不可用",
            4: "用户名或密码错误",
            5: "未授权"
        }
        error_msg = error_messages.get(rc, f"未知错误 (code: {rc})")
        print(f"✗ 连接失败: {error_msg}")
        sys.exit(1)

def on_message(client, userdata, msg):
    """消息回调"""
    try:
        payload = json.loads(msg.payload.decode())
        print(f"[{msg.topic}]")
        print(f"  时间: {payload.get('ts', 'N/A')}")
        print(f"  数值: {payload.get('value', 'N/A')}")
        print("-" * 60)
    except json.JSONDecodeError:
        print(f"[{msg.topic}] {msg.payload.decode()}")
        print("-" * 60)

def on_disconnect(client, userdata, rc):
    """断开连接回调"""
    if rc != 0:
        print(f"✗ 意外断开连接 (code: {rc})")

if __name__ == "__main__":
    print("=" * 60)
    print("MQTT 订阅测试 - C 部分")
    print("=" * 60)
    
    # 创建客户端
    client = mqtt.Client()
    client.username_pw_set(USERNAME, PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    
    # 连接
    print(f"正在连接到 {BROKER_HOST}:{BROKER_PORT}...")
    try:
        client.connect(BROKER_HOST, BROKER_PORT, 60)
    except Exception as e:
        print(f"✗ 连接失败: {e}")
        sys.exit(1)
    
    # 进入消息循环
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n")
        print("✓ 已停止")
        client.disconnect()
