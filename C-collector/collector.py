#!/usr/bin/env python3
"""
IoT数据采集器 - Collector模块
订阅MQTT主题 env/# 并将数据存储到SQLite数据库
"""

import json
import sqlite3
import sys
import time
import os
from datetime import datetime
from pathlib import Path
import paho.mqtt.client as mqtt

# ==================== 配置 ====================
# MQTT配置
BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "139.224.237.20")  # 与B-publisher保持一致
BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
USERNAME = os.getenv("MQTT_USERNAME", "admin")  # 使用admin用户，有全部权限
PASSWORD = os.getenv("MQTT_PASSWORD", "admin123")  # 与B-publisher保持一致
SUBSCRIBE_TOPIC = "env/#"

# 数据库配置
DB_PATH = "data/measurements.db"

# 日志配置
VERBOSE = True  # 是否打印详细日志

# ==================== 数据库初始化 ====================
def init_database():
    """初始化SQLite数据库和表结构"""
    # 确保data目录存在
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 创建measurements表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS measurements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            metric TEXT NOT NULL,
            ts TEXT NOT NULL,
            value REAL,
            received_at TEXT NOT NULL,
            UNIQUE(metric, ts)
        )
    ''')
    
    # 创建索引以提高查询效率
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_metric_ts 
        ON measurements(metric, ts)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_received_at 
        ON measurements(received_at)
    ''')
    
    conn.commit()
    conn.close()
    
    print(f"✓ 数据库已初始化: {DB_PATH}")

# ==================== 数据存储 ====================
def save_measurement(metric, ts, value):
    """
    保存测量数据到数据库
    
    Args:
        metric: 指标类型 (temperature/humidity/pressure)
        ts: 时间戳字符串
        value: 测量值 (可以为None)
    
    Returns:
        bool: 是否保存成功
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        received_at = datetime.now().isoformat()
        
        # 使用INSERT OR REPLACE避免重复数据
        cursor.execute('''
            INSERT OR REPLACE INTO measurements (metric, ts, value, received_at)
            VALUES (?, ?, ?, ?)
        ''', (metric, ts, value, received_at))
        
        conn.commit()
        conn.close()
        
        return True
    except Exception as e:
        print(f"✗ 数据库写入失败: {e}")
        return False

# ==================== MQTT回调函数 ====================
def on_connect(client, userdata, flags, rc):
    """MQTT连接回调"""
    if rc == 0:
        print(f"✓ 已连接到 Broker: {BROKER_HOST}:{BROKER_PORT}")
        print(f"✓ 正在订阅主题: {SUBSCRIBE_TOPIC}")
        client.subscribe(SUBSCRIBE_TOPIC, qos=0)
    else:
        print(f"✗ 连接失败 (错误码: {rc})")
        sys.exit(1)

def on_message(client, userdata, msg):
    """MQTT消息回调"""
    try:
        # 解析topic获取metric类型
        topic = msg.topic
        metric = topic.split('/')[-1]  # 从 env/temperature 提取 temperature
        
        # 解析payload
        payload_str = msg.payload.decode('utf-8')
        payload = json.loads(payload_str)
        
        ts = payload.get('ts')
        value = payload.get('value')
        
        # 验证数据
        if not ts:
            print(f"✗ 消息缺少时间戳: {payload_str}")
            return
        
        # 保存到数据库
        if save_measurement(metric, ts, value):
            if VERBOSE:
                value_str = f"{value}" if value is not None else "NULL"
                print(f"📊 [{metric}] ts={ts}, value={value_str}")
        
    except json.JSONDecodeError as e:
        print(f"✗ JSON解析失败: {msg.payload.decode('utf-8', errors='ignore')}")
    except Exception as e:
        print(f"✗ 处理消息失败: {e}")

def on_subscribe(client, userdata, mid, granted_qos):
    """订阅成功回调"""
    print(f"✓ 订阅成功! 等待消息...")
    print("-" * 60)

def on_disconnect(client, userdata, rc):
    """断开连接回调"""
    if rc != 0:
        print(f"⚠ 意外断开连接 (错误码: {rc}), 尝试重连...")

# ==================== 统计信息 ====================
def print_statistics():
    """打印数据库统计信息"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print("\n" + "=" * 60)
        print("📈 数据库统计")
        print("=" * 60)
        
        # 总记录数
        cursor.execute("SELECT COUNT(*) FROM measurements")
        total = cursor.fetchone()[0]
        print(f"总记录数: {total}")
        
        # 各指标统计
        cursor.execute('''
            SELECT metric, 
                   COUNT(*) as count,
                   COUNT(value) as non_null_count,
                   COUNT(*) - COUNT(value) as null_count,
                   MIN(value) as min_val,
                   MAX(value) as max_val,
                   AVG(value) as avg_val
            FROM measurements
            GROUP BY metric
            ORDER BY metric
        ''')
        
        rows = cursor.fetchall()
        for row in rows:
            metric, count, non_null, null_count, min_val, max_val, avg_val = row
            print(f"\n{metric}:")
            print(f"  - 总数: {count}")
            print(f"  - 有效值: {non_null}")
            print(f"  - 缺失值: {null_count}")
            if min_val is not None:
                print(f"  - 最小值: {min_val:.2f}")
                print(f"  - 最大值: {max_val:.2f}")
                print(f"  - 平均值: {avg_val:.2f}")
        
        print("=" * 60 + "\n")
        
        conn.close()
    except Exception as e:
        print(f"统计信息获取失败: {e}")

# ==================== 主程序 ====================
def main():
    """主程序入口"""
    print("=" * 60)
    print("IoT数据采集器 - Collector模块")
    print("=" * 60)
    
    # 初始化数据库
    init_database()
    
    # 创建MQTT客户端
    client = mqtt.Client(client_id="collector_" + str(int(time.time())))
    client.username_pw_set(USERNAME, PASSWORD)
    
    # 设置回调函数
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_subscribe = on_subscribe
    client.on_disconnect = on_disconnect
    
    # 连接到Broker
    print(f"\n正在连接到 {BROKER_HOST}:{BROKER_PORT}...")
    print(f"用户名: {USERNAME}")
    print(f"订阅主题: {SUBSCRIBE_TOPIC}")
    try:
        client.connect(BROKER_HOST, BROKER_PORT, 60)
        print("✓ 连接请求已发送，等待连接确认...")
    except Exception as e:
        print(f"✗ 连接失败: {e}")
        print(f"请检查：")
        print(f"  1. Broker地址是否正确: {BROKER_HOST}:{BROKER_PORT}")
        print(f"  2. 网络连接是否正常")
        print(f"  3. Broker服务是否运行")
        sys.exit(1)
    
    # 启动循环
    try:
        client.loop_start()
        
        # 等待连接完成
        print("等待连接建立...")
        time.sleep(2)  # 给连接一些时间
        
        print("\n💡 提示: 按 Ctrl+C 停止采集并查看统计信息\n")
        print("=" * 60)
        
        # 保持运行
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠ 收到停止信号，正在关闭...")
        client.loop_stop()
        client.disconnect()
        
        # 打印统计信息
        print_statistics()
        
        print("✓ 采集器已停止")

if __name__ == "__main__":
    main()

