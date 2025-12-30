# 环境监测数据采集与分析处理系统

> 基于 MQTT 协议的物联网环境监测系统 - 完整的数据采集、传输、存储与可视化解决方案

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![MQTT](https://img.shields.io/badge/MQTT-Mosquitto-orange.svg)](https://mosquitto.org/)
[![PyQt5](https://img.shields.io/badge/GUI-PyQt5-green.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 目录

- [项目概述](#-项目概述)
- [系统架构](#-系统架构)
- [功能特性](#-功能特性)
- [快速开始](#-快速开始)
- [模块详解](#-模块详解)
- [部署指南](#-部署指南)
- [API 文档](#-api-文档)
- [常见问题](#-常见问题)
- [项目结构](#-项目结构)
- [技术栈](#-技术栈)
- [贡献指南](#-贡献指南)
- [许可证](#-许可证)

---

## 🎯 项目概述

本项目实现了一个完整的物联网环境监测系统，模拟真实的环境数据采集场景，涵盖从传感器数据发布、消息中转、数据存储到可视化展示的全流程。系统基于 MQTT 协议实现设备间的松耦合通信，采用发布/订阅模式确保系统的可扩展性和可靠性。

### 应用场景

- 🌾 **智慧农业**：监测温室大棚环境参数，实现精准农业管理
- 🏢 **智能楼宇**：实时监控室内环境质量，优化空调系统运行
- 🌤️ **气象监测**：收集区域气象数据，支持天气预报和气候研究
- 🏭 **工业生产**：监控生产车间环境参数，保障产品质量和生产安全

### 数据说明

- **数据周期**：2014年2月13日 - 3月4日（共20天）
- **监测指标**：温度(temperature)、湿度(humidity)、气压(pressure)
- **采样间隔**：10-30分钟不等
- **数据量级**：每个指标约 2000+ 条记录
- **数据格式**：ISO8601 时间戳 + 数值（支持缺失值处理）

---

## 🏗️ 系统架构

```
┌──────────────────────────────────────────────────────────────────┐
│                        D-ui (图形化界面)                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   发布端控制     │  │   实时监控       │  │   数据可视化     │  │
│  │  (QProcess)     │  │   (MQTT订阅)    │  │   (HTTP查询)    │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
         │                        │                      │
         │ 控制脚本                │ MQTT订阅             │ HTTP请求
         ↓                        ↓                      ↓
┌─────────────────┐      ┌──────────────────────┐      ┌─────────────────┐
│   B-publisher   │      │   A-deploy           │      │   C-collector   │
│   (数据发布端)   │─────→│  MQTT Broker +       │─────→│   (数据采集端)   │
│                 │ 发布  │  Gateway Proxy       │ 订阅  │                 │
└─────────────────┘      └──────────────────────┘      └─────────────────┘
  ingest/env/*               验证·清洗·转发              env/* + SQLite + FastAPI
```

### 数据流向

1. **B-publisher** 读取本地数据文件，发布原始数据到 `ingest/env/{metric}`
2. **Gateway Proxy** 订阅原始数据，进行验证、清洗、去重后转发到 `env/{metric}`
3. **C-collector** 订阅清洗后的数据，存储到 SQLite 数据库，提供 HTTP API
4. **D-ui** 控制发布端脚本运行，订阅 MQTT 实时数据，通过 HTTP API 查询历史数据并可视化

---

## ✨ 功能特性

### 核心功能

- ✅ **MQTT 消息中转**：基于 Mosquitto，支持发布/订阅模式
- ✅ **数据质量保障**：Gateway Proxy 实现数据验证、清洗、去重
- ✅ **权限控制**：基于 ACL 的细粒度权限管理（4个角色）
- ✅ **数据持久化**：SQLite 数据库存储，支持高效查询
- ✅ **RESTful API**：提供实时数据、历史数据、统计数据接口
- ✅ **可视化展示**：实时趋势图、数据表格、每日统计
- ✅ **脚本控制**：GUI 控制发布端运行（开始/暂停/停止/调速）

### 数据处理

- **格式验证**：JSON 格式校验、必需字段检查
- **时间验证**：ISO8601 时间格式验证
- **类型转换**：字符串数字转换、空字符串处理
- **去重机制**：基于 (metric, timestamp) 的 LRU 缓存去重
- **缺失值处理**：空字符串统一转换为 `null`

---

## 🚀 快速开始

### 环境要求

- **操作系统**：Windows / Linux / macOS
- **Python**：3.8+
- **依赖服务**：Mosquitto MQTT Broker（已部署在 139.224.237.20:1883）

### 安装步骤

#### 1. 克隆项目

```bash
git clone https://github.com/your-repo/iot-project.git
cd iot-project
```

#### 2. 安装 Python 依赖

```bash
# B-publisher 模块
cd B-publisher
pip install paho-mqtt

# C-collector 模块
cd ../C-collector
pip install -r requirements.txt

# D-ui 模块
cd ../D-ui
pip install -r requirements.txt
```

### 运行系统

#### 方案一：使用 GUI（推荐）

```bash
cd D-ui
python main.py
```

在 GUI 中可以：
1. **发布端控制**：启动/停止数据发布，支持选择指标和发布速率
2. **实时监控**：订阅 MQTT 消息，实时显示数据
3. **数据可视化**：查看历史数据趋势图和统计信息

#### 方案二：命令行运行

**1. 启动数据采集器（必须先启动）**

```bash
cd C-collector
python collector.py
```

**2. 启动 HTTP API 服务**

```bash
cd C-collector
uvicorn api:app --host 0.0.0.0 --port 8000
```

**3. 启动数据发布端**

```bash
cd B-publisher
python publish.py --metric temperature --rate 1
```

参数说明：
- `--metric` / `-m`：指标类型（temperature / humidity / pressure）
- `--rate` / `-r`：发布速率（Hz，每秒发送条数）
- `--start` / `-s`：起始时间（可选，格式：YYYY-MM-DDTHH:MM:SS）
- `--end` / `-e`：结束时间（可选）

**4. 运行时控制**

在发布端运行时，可以通过 stdin 输入命令：
- `pause` - 暂停发布
- `resume` - 恢复发布
- `rate 5` - 修改速率为 5Hz
- `stop` - 停止并退出

---

## 📦 模块详解

### A-deploy：MQTT Broker + Gateway Proxy

**功能定位**：系统的消息中转与数据质量保障层

#### MQTT Broker (Mosquitto)

- **监听地址**：0.0.0.0:1883
- **认证方式**：用户名/密码
- **权限控制**：ACL 访问控制列表
- **持久化**：消息和会话持久化

#### 账号权限

| 用户名 | 密码 | 权限 | 用途 |
|--------|------|------|------|
| publisher | pub123 | 写 `ingest/env/#` | B 模块发布数据 |
| proxy | proxy123 | 读 `ingest/env/#`<br>写 `env/#` | Gateway Proxy 内部使用 |
| collector | col123 | 读 `env/#` | C/D 模块订阅数据 |
| admin | admin123 | 完全权限 | 管理员调试 |

#### Gateway Proxy

**核心功能**：
1. 订阅原始数据主题 `ingest/env/#`
2. 数据验证（JSON 格式、字段完整性、时间格式）
3. 数据清洗（类型转换、空值处理）
4. 去重处理（基于 metric + timestamp）
5. 转发到正式主题 `env/{metric}`

**处理流程**：

```
原始数据 → JSON解析 → 字段验证 → 时间格式验证 → 去重检查 → 数据清洗 → 转发
   ↓          ↓          ↓           ↓           ↓          ↓        ↓
  失败      失败       失败        失败        重复      类型转换   env/{metric}
   ↓          ↓          ↓           ↓           ↓          ↓
  丢弃      丢弃       丢弃        丢弃        丢弃      null处理
```

**详细文档**：[A-deploy/iot-project/README.md](A-deploy/iot-project/README.md)

---

### B-publisher：数据发布端

**功能定位**：模拟传感器设备，发布环境监测数据

#### 核心特性

- 读取本地数据文件（temperature.txt / humidity.txt / pressure.txt）
- 按时间顺序发布数据到 MQTT Broker
- 支持可配置的发布速率（Hz）
- 支持时间区间过滤
- 运行时动态控制（暂停/恢复/调速/停止）

#### 数据文件格式

```json
{"2014-02-13T06:20:00": "3.0", "2014-02-13T13:50:00": "7.0", ...}
```

#### 发布主题

- `ingest/env/temperature` - 温度数据
- `ingest/env/humidity` - 湿度数据
- `ingest/env/pressure` - 气压数据

#### 消息格式

```json
{
  "ts": "2014-02-13T06:20:00",
  "value": 3.0
}
```

**详细文档**：[B-publisher/README.md](B-publisher/README.md)

---

### C-collector：数据采集端

**功能定位**：数据持久化与 API 服务层

#### 核心功能

1. **MQTT 订阅**：订阅 `env/#`，接收清洗后的数据
2. **数据存储**：写入 SQLite 数据库（自动去重）
3. **HTTP API**：提供数据查询接口

#### 数据库设计

```sql
CREATE TABLE measurements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric TEXT NOT NULL,           -- 指标类型
    ts TEXT NOT NULL,                -- 时间戳（ISO8601）
    value REAL,                      -- 数值（可为NULL）
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(metric, ts)               -- 防止重复数据
);
```

#### HTTP API 接口

**1. 实时数据**

```
GET /api/realtime?metric=temperature&limit=200
```

返回最新的 N 条数据（按时间倒序）。

**2. 历史数据**

```
GET /api/history?metric=temperature&from=2014-02-13T00:00:00&to=2014-02-14T00:00:00
```

返回指定时间范围内的数据。

**3. 统计数据**

```
GET /api/stats?metric=temperature&from=2014-02-13T00:00:00&to=2014-02-14T00:00:00
```

返回统计信息（最大值、最小值、平均值、数据条数）。

**详细文档**：[C-collector/README.md](C-collector/README.md)

---

### D-ui：图形化界面

**功能定位**：用户交互与数据可视化层

#### 核心功能

1. **发布端控制**：通过 QProcess 控制 B-publisher 脚本
2. **实时监控**：订阅 MQTT 消息，实时显示数据
3. **数据可视化**：折线图、数据表格、每日统计
4. **多指标支持**：温度、湿度、气压独立控制

#### 界面结构

```
主窗口
├── 首页
│   ├── 发布端按钮 → 发布端控制页面
│   └── 订阅端按钮 → 数据可视化页面
│
├── 发布端控制页面
│   ├── 温度发布控制（开始/停止/日志）
│   ├── 湿度发布控制
│   └── 气压发布控制
│
└── 数据可视化页面
    ├── 温度标签页
    │   ├── 订阅控制
    │   ├── 数据表格（日期/时间点/数值/统计）
    │   └── 趋势图表（Matplotlib）
    ├── 湿度标签页
    └── 气压标签页
```

#### 技术实现

- **GUI 框架**：PyQt5
- **图表绘制**：Matplotlib
- **进程控制**：QProcess（管理发布端脚本）
- **多线程**：MQTT 订阅和 HTTP 请求在后台线程执行
- **信号槽**：线程间安全通信

**详细文档**：[D-ui/README.md](D-ui/README.md)

---

## 🔧 部署指南

### 一、服务器部署（A 模块）

#### 1. 安装 Mosquitto

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install mosquitto mosquitto-clients
```

**CentOS/RHEL:**
```bash
sudo yum install mosquitto mosquitto-clients
```

#### 2. 配置 Mosquitto

```bash
cd A-deploy/iot-project/deploy/broker
sudo cp mosquitto-system.conf /etc/mosquitto/mosquitto.conf
sudo cp acl /etc/mosquitto/acl
```

#### 3. 生成密码文件

```bash
cd A-deploy/iot-project/deploy/broker
bash generate_passwords.sh
sudo cp /tmp/mosquitto_passwords /etc/mosquitto/password_file
```

#### 4. 启动 Broker

```bash
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
sudo systemctl status mosquitto
```

#### 5. 部署 Gateway Proxy

```bash
cd A-deploy/iot-project/deploy/proxy
cp config.example.env .env
# 编辑 .env 配置文件

# 安装依赖
pip install -r requirements.txt

# 运行 Proxy
python app/main.py
```

---

### 二、客户端部署（B/C/D 模块）

#### 1. 配置连接信息

修改各模块的配置文件，将 MQTT Broker 地址设置为服务器 IP：

**B-publisher/publish.py:**
```python
BROKER_HOST = "139.224.237.20"  # 修改为实际服务器IP
BROKER_PORT = 1883
```

**C-collector/collector.py:**
```python
BROKER_HOST = "139.224.237.20"
BROKER_PORT = 1883
USERNAME = "collector"
PASSWORD = "col123"
```

**D-ui/config.py:**
```python
MQTT_HOST = "139.224.237.20"
MQTT_PORT = 1883
MQTT_USERNAME = "collector"
MQTT_PASSWORD = "col123"
```

#### 2. 验证连接

使用 mosquitto_sub 测试连接：

```bash
mosquitto_sub -h 139.224.237.20 -p 1883 -u collector -P col123 -t "env/#" -v
```

---

### 三、系统启动顺序

**正确的启动顺序**：

1. **启动 MQTT Broker**（服务器）
   ```bash
   sudo systemctl start mosquitto
   ```

2. **启动 Gateway Proxy**（服务器）
   ```bash
   cd A-deploy/iot-project/deploy/proxy
   python app/main.py
   ```

3. **启动 C-collector**（客户端 - 必须先启动）
   ```bash
   cd C-collector
   python collector.py
   ```

4. **启动 API 服务**（客户端）
   ```bash
   cd C-collector
   uvicorn api:app --host 0.0.0.0 --port 8000
   ```

5. **启动 D-ui**（客户端）
   ```bash
   cd D-ui
   python main.py
   ```

6. **在 GUI 中启动发布端**（或命令行启动 B-publisher）

---

## 📚 API 文档

### C-collector HTTP API

#### 基础信息

- **Base URL**: `http://localhost:8000`
- **返回格式**: JSON
- **编码**: UTF-8

#### 1. 实时数据

**请求**：
```
GET /api/realtime?metric={metric}&limit={limit}
```

**参数**：
- `metric` (必填): 指标类型（temperature / humidity / pressure）
- `limit` (可选): 返回条数，默认 200

**响应示例**：
```json
{
  "metric": "temperature",
  "count": 10,
  "data": [
    {
      "ts": "2014-02-13T23:50:00",
      "value": 6.0
    },
    {
      "ts": "2014-02-13T23:40:00",
      "value": 6.0
    }
  ]
}
```

#### 2. 历史数据

**请求**：
```
GET /api/history?metric={metric}&from={start}&to={end}
```

**参数**：
- `metric` (必填): 指标类型
- `from` (必填): 起始时间（ISO8601 格式）
- `to` (必填): 结束时间（ISO8601 格式）

**响应示例**：
```json
{
  "metric": "temperature",
  "from": "2014-02-13T00:00:00",
  "to": "2014-02-14T00:00:00",
  "count": 150,
  "data": [...]
}
```

#### 3. 统计数据

**请求**：
```
GET /api/stats?metric={metric}&from={start}&to={end}
```

**响应示例**：
```json
{
  "metric": "temperature",
  "from": "2014-02-13T00:00:00",
  "to": "2014-02-14T00:00:00",
  "count": 150,
  "max": 12.5,
  "min": 3.0,
  "avg": 7.8,
  "missing_count": 5
}
```

---

## ❓ 常见问题

### 1. 数据库数据很少或没有数据？

**原因**：
- C-collector 没有运行
- MQTT 主题不匹配
- 数据被覆盖（相同时间戳）

**解决方法**：
1. 确保 C-collector 已启动并显示 "✓ 订阅成功! 等待消息..."
2. 检查 C-collector 日志，确认是否收到消息
3. 运行检查脚本：
   ```bash
   cd C-collector
   python verify.py
   ```

### 2. MQTT 连接失败？

**检查清单**：
- [ ] Broker 是否正常运行？`sudo systemctl status mosquitto`
- [ ] 防火墙是否开放 1883 端口？
- [ ] 用户名密码是否正确？
- [ ] 网络连接是否正常？

**测试连接**：
```bash
mosquitto_sub -h 139.224.237.20 -p 1883 -u collector -P col123 -t "env/#" -v
```

### 3. GUI 无法启动发布端？

**检查**：
1. B-publisher 脚本路径是否正确？
2. Python 环境是否已安装 paho-mqtt？
3. 查看 GUI 日志输出

### 4. 数据发布速度慢？

**优化方法**：
- 提高发布速率：在 GUI 中设置或使用 `--rate` 参数
- 运行时调速：输入 `rate 10` 设置为 10Hz
- 检查网络延迟

### 5. Gateway Proxy 大量丢弃数据？

**检查**：
1. 查看 Proxy 日志，确认丢弃原因
2. 常见原因：
   - 数据格式不正确（JSON 解析失败）
   - 缺少必需字段（ts / value）
   - 时间格式不符合 ISO8601
   - 重复数据被去重

---

## 📁 项目结构

```
loT/
├── README.md                    # 项目总体说明
├── 项目说明文档.md              # 详细设计文档
├── 运行说明.md                  # 运行指南
│
├── A-deploy/                    # A 模块：MQTT Broker + Gateway Proxy
│   └── iot-project/
│       ├── README.md            # A 模块说明
│       ├── deploy/
│       │   ├── broker/          # Mosquitto 配置
│       │   │   ├── mosquitto-system.conf
│       │   │   ├── acl
│       │   │   └── generate_passwords.sh
│       │   └── proxy/           # Gateway Proxy
│       │       ├── config.example.env
│       │       ├── requirements.txt
│       │       └── app/
│       │           └── main.py
│       └── scripts/             # 测试脚本
│           ├── deploy-system.sh
│           ├── publish_test.py
│           └── subscribe_test.py
│
├── B-publisher/                 # B 模块：数据发布端
│   ├── README.md                # B 模块说明
│   ├── publish.py               # 主程序
│   └── data/                    # 数据文件
│       ├── temperature.txt
│       ├── humidity.txt
│       └── pressure.txt
│
├── C-collector/                 # C 模块：数据采集端
│   ├── README.md                # C 模块说明
│   ├── collector.py             # MQTT 订阅 + SQLite 存储
│   ├── api.py                   # FastAPI HTTP 接口
│   ├── config.py                # 配置文件
│   ├── verify.py                # 验证脚本
│   ├── requirements.txt
│   └── data/
│       └── measurements.db      # SQLite 数据库（自动创建）
│
├── D-ui/                        # D 模块：图形化界面
│   ├── README.md                # D 模块说明
│   ├── main.py                  # 主程序入口
│   ├── config.py                # 配置管理
│   ├── requirements.txt
│   ├── pages/                   # 界面页面
│   │   ├── home.py             # 首页
│   │   ├── publisher.py        # 发布端控制页面
│   │   ├── viewer.py           # 数据可视化页面
│   │   └── combined.py         # 组合页面
│   ├── workers/                 # 后台线程
│   │   ├── http_worker.py      # HTTP 请求工作线程
│   │   └── mqtt_worker.py      # MQTT 订阅工作线程
│   └── resources/               # 资源文件
│
└── docs/                        # 文档目录
    ├── sample_message.json      # 消息样例
    └── topic-spec.md            # Topic 规范
```

---

## 🛠️ 技术栈

### 通信协议

- **MQTT**: 轻量级物联网消息传输协议
- **HTTP/REST**: C-D 模块间 API 通信

### 核心技术

- **MQTT Broker**: Eclipse Mosquitto
- **消息库**: paho-mqtt (Python MQTT 客户端)
- **数据库**: SQLite（轻量级、无服务器）
- **Web 框架**: FastAPI（高性能异步框架）
- **GUI 框架**: PyQt5（跨平台桌面应用）
- **数据可视化**: Matplotlib（科学绘图库）

### Python 依赖包

```
# A-deploy (Gateway Proxy)
paho-mqtt>=1.6.1

# B-publisher
paho-mqtt>=1.6.1

# C-collector
paho-mqtt>=1.6.1
fastapi>=0.68.0
uvicorn>=0.15.0

# D-ui
PyQt5>=5.15.0
paho-mqtt>=1.6.1
matplotlib>=3.3.0
requests>=2.25.0
```

---

## 🎓 学习资源

### MQTT 协议

- [MQTT 官方文档](https://mqtt.org/)
- [Eclipse Mosquitto 文档](https://mosquitto.org/documentation/)
- [Paho MQTT Python 文档](https://www.eclipse.org/paho/index.php?page=clients/python/docs/index.php)

## 👥 团队成员

本项目由《物联网应用基础》课程小组完成：

- **A 模块**（MQTT Broker + Gateway Proxy）：负责消息中转与数据质量保障
- **B 模块**（数据发布端）：负责模拟传感器数据发布
- **C 模块**（数据采集端）：负责数据存储与 API 服务
- **D 模块**（图形化界面）：负责用户交互与数据可视化

---
