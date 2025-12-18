# C-Collector 数据采集器

IoT项目的数据采集模块，负责订阅MQTT消息并存储到SQLite数据库。

## 📁 文件说明

```
C-collector/
├── collector.py          # 主程序：MQTT订阅 + 写入 SQLite
├── api.py                # FastAPI 应用：对外提供 HTTP API
├── verify.py             # 验证脚本：检查数据库状态
├── config.py             # 配置文件（旧版，可参考）
├── requirements.txt      # Python依赖
├── data/                 # 数据目录（自动创建）
│   └── measurements.db   # SQLite数据库
└── README.md             # 本文件
```

## 🚀 快速开始

### 1. 安装依赖（采集器 + API）

```bash
cd C-collector
pip install -r requirements.txt
```

### 2. 配置连接信息（MQTT）

编辑 `config.py` 或直接修改 `collector.py` 中的配置：

```python
BROKER_HOST = "139.224.237.20"  # MQTT Broker地址
BROKER_PORT = 1883
USERNAME = "subscriber"          # 用户名
PASSWORD = "sub123"              # 密码
```

### 3. 运行采集器（MQTT → SQLite）

```bash
python collector.py
```

成功运行后会看到：

```
============================================================
IoT数据采集器 - Collector模块
============================================================
✓ 数据库已初始化: data/measurements.db

正在连接到 139.224.237.20:1883...
✓ 已连接到 Broker: 139.224.237.20:1883
✓ 正在订阅主题: env/#
✓ 订阅成功! 等待消息...
------------------------------------------------------------

💡 提示: 按 Ctrl+C 停止采集并查看统计信息

📊 [temperature] ts=2014-02-13T00:00:00, value=4.0
📊 [temperature] ts=2014-02-13T00:20:00, value=4.0
...
```

### 4. 启动 FastAPI HTTP API（C → D）

按照项目契约，C 需要提供给 D 三个 HTTP 接口：

1. 实时：`GET /api/realtime?metric=temperature&limit=200`  
2. 历史：`GET /api/history?metric=temperature&from=...&to=...`  
3. 统计：`GET /api/stats?metric=temperature&from=...&to=...`

启动方式（默认端口 `8000`）：

```bash
cd C-collector
uvicorn api:app --host 0.0.0.0 --port 8000
```

或直接（开发调试用）：

```bash
python api.py
```

当看到类似输出：

```text
INFO:     Uvicorn running on http://0.0.0.0:8000
```

说明 HTTP API 已经启动，D 端可以通过 `http://<C服务器IP>:8000` 访问。

---

## ✅ 验证方法

### 方法1：使用验证脚本（推荐，验证 SQLite）

```bash
python verify.py
```

会显示详细的数据库统计信息：
- 总记录数
- 各指标的统计（数量、最小值、最大值、平均值）
- 最近10条记录
- 数据连续性检查

### 方法2：查看实时日志（MQTT → SQLite）

采集器运行时会实时打印接收到的消息：

```
📊 [temperature] ts=2014-02-13T03:00:00, value=3.0
📊 [humidity] ts=2014-02-13T03:00:00, value=85.0
📊 [pressure] ts=2014-02-13T03:00:00, value=1013.2
```

### 方法3：直接查询数据库（SQLite）

```bash
# 进入数据库
sqlite3 data/measurements.db

# 查看记录数
SELECT metric, COUNT(*) FROM measurements GROUP BY metric;

# 查看最近10条
SELECT * FROM measurements ORDER BY received_at DESC LIMIT 10;

# 查看统计信息
SELECT metric, 
       COUNT(*) as total,
       COUNT(value) as valid,
       MIN(value) as min,
       MAX(value) as max,
       AVG(value) as avg
FROM measurements 
GROUP BY metric;
```

### 方法4：使用mosquitto命令行验证（MQTT）

### 方法5：验证 HTTP API（给 D 使用的接口）

假设 C 机器的 IP 为 `127.0.0.1`（本机），使用 `curl` 或浏览器访问：

1）实时接口：

```bash
curl "http://127.0.0.1:8000/api/realtime?metric=temperature&limit=5"
```

预期返回（示例）：

```json
{"metric":"temperature","points":[{"ts":"2014-02-13T00:00:00","value":4.0}, ...]}
```

2）历史接口：

```bash
curl "http://127.0.0.1:8000/api/history?metric=temperature&from=2014-02-13T00:00:00&to=2014-02-13T05:00:00"
```

3）统计接口：

```bash
curl "http://127.0.0.1:8000/api/stats?metric=temperature&from=2014-02-13T00:00:00&to=2014-02-13T23:59:59"
```

预期返回（示例）：

```json
{"metric":"temperature","count":100,"missing":3,"min":1.0,"max":10.0,"mean":5.5}
```

在另一个终端监听MQTT消息（确保采集器也能收到）：

```bash
mosquitto_sub -h 139.224.237.20 -t "env/#" -v -u subscriber -P sub123
```

## 🗄️ 数据库结构

### measurements 表

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键（自增）|
| metric | TEXT | 指标类型（temperature/humidity/pressure）|
| ts | TEXT | 原始时间戳（ISO 8601格式）|
| value | REAL | 测量值（NULL表示缺失）|
| received_at | TEXT | 接收时间（ISO 8601格式）|

**索引：**
- `idx_metric_ts`: (metric, ts) - 用于快速查询和去重
- `idx_received_at`: (received_at) - 用于时间序列查询

**唯一约束：** (metric, ts) - 防止重复数据

## 📊 Day 2 验收标准

根据计划，Day 2的验收标准是：

> **DB 记录数持续增长，且三种 metric 都有数据**

### 验收步骤：

1. **启动采集器**
   ```bash
   python collector.py
   ```

2. **启动Publisher（在B-publisher目录）**
   ```bash
   cd ../B-publisher
   python read_data.py
   ```

3. **等待10-30秒后，运行验证**
   ```bash
   python verify.py
   ```

4. **检查输出**
   - ✓ 总记录数 > 0
   - ✓ temperature 有数据
   - ✓ humidity 有数据
   - ✓ pressure 有数据

## 🔧 配置说明

### MQTT配置
- `BROKER_HOST`: MQTT Broker IP地址
- `BROKER_PORT`: MQTT Broker端口（默认1883）
- `USERNAME/PASSWORD`: 认证信息（如果Broker需要）
- `SUBSCRIBE_TOPIC`: 订阅主题（env/# 订阅所有env下的主题）

### 数据库配置
- `DB_PATH`: SQLite数据库文件路径（默认：data/measurements.db）

### 日志配置
- `VERBOSE`: 是否打印详细的消息接收日志（True/False）

## 🐛 常见问题

### 1. 连接失败
```
✗ 连接失败: [Errno 111] Connection refused
```
**解决方法：**
- 检查BROKER_HOST和BROKER_PORT是否正确
- 确认Mosquitto Broker已启动
- 检查防火墙设置

### 2. 认证失败
```
✗ 连接失败 (错误码: 5)
```
**解决方法：**
- 错误码5表示认证失败
- 检查USERNAME和PASSWORD是否正确
- 确认Broker的ACL配置

### 3. 收不到消息
**可能原因：**
- Publisher没有运行或Topic不匹配
- 检查Publisher使用的是 `env/temperature` 而不是 `ingest/env/temperature`
- 网络问题

**调试方法：**
```bash
# 使用mosquitto_sub测试
mosquitto_sub -h 139.224.237.20 -t "env/#" -v
```

### 4. 数据库为空
**检查步骤：**
1. Collector是否正常连接到Broker
2. Publisher是否在发送数据
3. Topic是否匹配（env/temperature等）

## 📈 性能说明

- **QoS=0**: 消息可能丢失，但性能最好
- **唯一约束**: 自动去重相同(metric, ts)的数据
- **批量写入**: 如需优化可改为批量插入
- **索引**: 已创建必要索引，查询效率高

## 🔄 下一步（Day 3）

Day 3将在此基础上添加：
- FastAPI HTTP接口
- `/api/realtime` 实时数据查询
- `/api/history` 历史数据查询
- `/api/stats` 统计信息接口

## 📝 注意事项

1. **数据去重**: 使用(metric, ts)作为唯一键，重复数据会被覆盖
2. **NULL值处理**: value为NULL的记录会正常存储
3. **时间戳格式**: 保持原始ISO 8601格式，便于后续处理
4. **自动重连**: MQTT客户端会自动重连（on_disconnect回调）

## 🤝 联调说明

与B（Publisher）联调时确保：
- Topic格式：`env/temperature`, `env/humidity`, `env/pressure`
- Payload格式：`{"ts": "2014-02-13T00:00:00", "value": 3.0}` 或 `{"ts": "...", "value": null}`
- Broker地址一致

---

**Day 2 任务完成标志：**
- [x] 能够连接到MQTT Broker
- [x] 成功订阅 env/# 主题
- [x] 解析JSON消息
- [x] 存储到SQLite数据库
- [x] 三种指标（temperature/humidity/pressure）都有数据
- [x] 记录数持续增长

