import json
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
pending_mids=set()

def on_connect(client, userdata, flags, rc):
    """连接回调"""
    if rc == 0:
        print("✓ 已连接到 Broker")
    else:
        print(f"✗ 连接失败 (错误码: {rc})")
        sys.exit(1)

def on_publish(client, userdata, mid):
    """发布回调"""
    pending_mids.discard(mid)
    # print(f"✓ 消息已发送 (message_id: {mid})")

def publish_data(metric,rate_hz=1):
    input_dict={
        'temperature': 'B-publisher/data/temperature.txt',
        'humidity': 'B-publisher/data/humidity.txt',
        'pressure': 'B-publisher/data/pressure.txt'
    }

    payloads=read_file(input_dict[metric])
    
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
    
    # 发布
    topic = f"ingest/env/{metric}"

    interval = 1.0 / rate_hz  # 每条间隔秒
    start = time.perf_counter()
    print(f"发布主题: {topic}")

    for i,payload in enumerate(payloads):
        target = start + i * interval
        now = time.perf_counter()
        if target > now:
            time.sleep(target - now)

        print(f"Payload: {json.dumps(payload)}")
        result = client.publish(topic, json.dumps(payload), qos=0)
        pending_mids.add(result.mid)

    while pending_mids:
        time.sleep(0.1)
    
    # 断开连接
    client.loop_stop()
    client.disconnect()
    
    print("✓ 完成")


def read_file(path):
    results=[]
    with open(path, 'r') as file:
        for line in file:
            data = json.loads(line)
            for key, value in data.items():
                result={
                    "ts": key,
                    "value": None if value=="" else float(value)
                }
                # result={
                #     "topic": topic,
                #     "payload": {
                #         "ts": key,
                #         "value": None if value=="" else float(value)
                #     }
                # }
                results.append(result)
    results.sort(key=lambda r: r["ts"])
    return results
    
    
if __name__ == "__main__":
    publish_data("temperature",1)