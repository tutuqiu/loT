import json, sys, time, threading
import paho.mqtt.client as mqtt
from datetime import datetime
import argparse

# 连接配置
BROKER_HOST = "139.224.237.20"
BROKER_PORT = 1883
USERNAME = "publisher"
PASSWORD = "pub123"

# 发布mid集合
pending_mids=set()

pause_event = threading.Event()  # True=运行；False=暂停
stop_event = threading.Event()   # True=停止
resume_event = threading.Event() # True=刚恢复运行 则需要重置next_send
pause_event.set()                # 默认运行

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

def read_file(path,start,end):
    results=[]
    with open(path, 'r') as file:
        for line in file:
            data = json.loads(line)
            for key, value in data.items():
                # 筛选时间区间
                if start is not None and key < start:
                    continue
                if end is not None and key > end:
                    continue

                result={
                    "ts": key,
                    "value": None if value=="" else float(value)
                }
                results.append(result)
    results.sort(key=lambda r: r["ts"])
    return results

def control_loop():
    # 从 stdin 读取控制命令：pause/resume/stop/rate <hz> 
    global rate_hz

    while not stop_event.is_set():
        line = sys.stdin.readline()
        if not line:  # EOF
            time.sleep(0.05)
            continue
        cmd = line.strip().lower()
        if cmd == "pause":
            pause_event.clear()
            print("|| paused", flush=True)
        elif cmd == "resume":
            pause_event.set()
            resume_event.set()  
            print("|| resumed", flush=True)
        elif cmd.startswith("rate "):
            try:
                rate_hz = float(cmd.split()[1])
                print(f"|| rate set to {rate_hz} Hz", flush=True)
            except:
                print("|| invalid rate", flush=True)
        elif cmd == "stop":
            stop_event.set()
            pause_event.set()
            print("|| stopping", flush=True)

def publish_data(metric,rate=1,start=None,end=None):
    global rate_hz
    rate_hz = float(rate)

    # metric 映射文件
    input_dict={
        'temperature': 'B-publisher/data/temperature.txt',
        'humidity': 'B-publisher/data/humidity.txt',
        'pressure': 'B-publisher/data/pressure.txt'
    }

    # 读取制定metric、时间区间的数据
    payloads=read_file(input_dict[metric],start,end)
    
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
    print(f"发布主题: {topic}")

    s = start if start else "/"
    e = end if end else "/"
    print(f"时间区间：{s} ~ {e}" if (start or end) else "时间区间：全部")

    i=0
    next_send = time.perf_counter()
    while i<len(payloads) and not stop_event.is_set():
        pause_event.wait()  # 等待运行信号 pause_event=True 时继续
        
        # 恢复运行时 重置发送时间
        if resume_event.is_set():
            next_send = time.perf_counter()
            resume_event.clear()

        # 控制发送速率
        now = time.perf_counter()
        if next_send > now:
            time.sleep(next_send - now)

        payload = payloads[i]
        print(f"Payload: {json.dumps(payload)}")

        # 发布
        result = client.publish(topic, json.dumps(payload), qos=0)
        pending_mids.add(result.mid)

        # 每条间隔秒 支持动态修改 rate_hz
        interval = 1.0 / max(rate_hz, 0.0001)  
        next_send += interval 

        i+=1

    # 等待回调完成（最多 5 秒，避免卡死）
    t0 = time.time()
    while pending_mids and time.time() - t0 < 5:
        time.sleep(0.05)
    
    # 断开连接
    client.loop_stop()
    client.disconnect()
    
    print("✓ 完成")    
    
if __name__ == "__main__":
    # 读取命令行参数
    parser = argparse.ArgumentParser()
    parser.add_argument("--metric", "-m", choices=["temperature","humidity","pressure"], required=True)
    parser.add_argument("--rate", "-r", type=float, required=True)
    parser.add_argument("--start", "-s", default=None,
                        help="起始时间，如 2014-05-30T07:00:00（包含）")
    parser.add_argument("--end", "-e", default=None,
                        help="终止时间，如 2014-05-30T08:00:00（包含）")
    args = parser.parse_args()

    # 控制线程：读 stdin 可以控制发布的暂停/恢复/修改速率/停止
    t = threading.Thread(target=control_loop, daemon=True)
    t.start()

    publish_data(args.metric, args.rate, args.start, args.end)