# IoT 项目 - B/C 部分使用指南

## 📡 连接信息

**MQTT Broker 地址：**
```
主机: 139.224.237.20
端口: 1883
```

**账号信息：**
- **B 部分（发布端）**: `publisher` / `pub123`
- **C 部分（订阅端）**: `collector` / `col123`

---

## 📤 B 部分 - 数据发布端

### 发布规则

**Topic：**
- `ingest/env/temperature` - 温度数据
- `ingest/env/humidity` - 湿度数据
- `ingest/env/pressure` - 气压数据

**Payload 格式：**
```json
{"ts":"2025-12-16T23:30:00","value":25.3}
```

- `ts`: ISO8601 时间格式 `YYYY-MM-DDTHH:MM:SS`
- `value`: 数字或 `null`

### 测试方法

#### 方法 1：Python 脚本（推荐）

**安装依赖：**
```bash
pip3 install paho-mqtt
```

**使用测试脚本：**
```bash
# 下载测试脚本 publish_test.py
python3 publish_test.py temperature 25.3
python3 publish_test.py humidity 60.5
python3 publish_test.py pressure 1013.25
```

#### 方法 2：命令行工具

**macOS：**
```bash
brew install mosquitto

mosquitto_pub -h 139.224.237.20 -u publisher -P pub123 \
  -t "ingest/env/temperature" \
  -m '{"ts":"2025-12-16T23:30:00","value":25.3}'
```

**Windows：**
```powershell
# 安装: winget install Eclipse.Mosquitto

mosquitto_pub.exe -h 139.224.237.20 -u publisher -P pub123 `
  -t 'ingest/env/temperature' `
  -m '{"ts":"2025-12-16T23:30:00","value":25.3}'
```

#### 方法 3：Python 代码集成

```python
import paho.mqtt.client as mqtt
import json
from datetime import datetime
import time

# 连接
client = mqtt.Client()
client.username_pw_set("publisher", "pub123")
client.connect("139.224.237.20", 1883, 60)
client.loop_start()

# 发布
payload = {
    "ts": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    "value": 25.3
}
client.publish("ingest/env/temperature", json.dumps(payload))

# 等待发送完成
time.sleep(1)
client.loop_stop()
client.disconnect()
```

---

## 📥 C 部分 - 数据订阅端

### 订阅规则

**Topic：**
- `env/temperature` - 温度数据（已清洗）
- `env/humidity` - 湿度数据（已清洗）
- `env/pressure` - 气压数据（已清洗）
- `env/#` - 订阅所有数据

**数据保证：**
- ✅ JSON 格式已验证
- ✅ 时间戳 ISO8601 格式已验证
- ✅ 数值已转换（字符串数字→数字，空串→null）
- ✅ 去重处理（30秒内不重复）

### 测试方法

#### 方法 1：Python 脚本（推荐）

**安装依赖：**
```bash
pip3 install paho-mqtt
```

**使用测试脚本：**
```bash
# 下载测试脚本 subscribe_test.py
python3 subscribe_test.py
```

#### 方法 2：命令行工具

**macOS：**
```bash
brew install mosquitto

mosquitto_sub -h 139.224.237.20 -u collector -P col123 -t "env/#" -v
```

**Windows：**
```powershell
# 安装: winget install Eclipse.Mosquitto

mosquitto_sub.exe -h 139.224.237.20 -u collector -P col123 -t 'env/#' -v
```

#### 方法 3：Python 代码集成

```python
import paho.mqtt.client as mqtt
import json

def on_message(client, userdata, msg):
    data = json.loads(msg.payload.decode())
    print(f"Topic: {msg.topic}")
    print(f"Time: {data['ts']}, Value: {data['value']}")

client = mqtt.Client()
client.username_pw_set("collector", "col123")
client.on_message = on_message
client.connect("139.224.237.20", 1883, 60)
client.subscribe("env/#")
client.loop_forever()
```

---

## 🧪 端到端测试

1. **C 部分先启动订阅：**
   ```bash
   python3 subscribe_test.py
   ```

2. **B 部分发布测试数据：**
   ```bash
   python3 publish_test.py temperature 25.3
   ```

3. **验证 C 部分收到数据：**
   ```
   [env/temperature]
     时间: 2025-12-16T23:30:00
     数值: 25.3
   ```

---

## ⚠️ 常见问题

### 1. 连接失败 "not authorised"
- 检查用户名/密码是否正确
- B 使用 `publisher/pub123`
- C 使用 `collector/col123`

### 2. 发布成功但 C 收不到数据
- 确认 B 发布到 `ingest/env/*`（注意 `ingest/` 前缀）
- 确认 C 订阅 `env/*`（无 `ingest/` 前缀）
- JSON 格式必须正确：`{"ts":"...","value":...}`

### 3. 时间格式错误导致数据被丢弃
- 必须使用 ISO8601 格式：`2025-12-16T23:30:00`
- 可以用 Python: `datetime.now().strftime("%Y-%m-%dT%H:%M:%S")`

### 4. Python 发布后立即退出没发送成功
- 使用提供的 `publish_test.py` 脚本（已处理）
- 或添加 `time.sleep(1)` 等待发送完成

---