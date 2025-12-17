# IoT Project - Part A: MQTT Broker + Gateway Proxy

## 📋 项目概述

本项目实现了物联网数据平台的核心组件：**MQTT Broker** 和 **Gateway Proxy 代理服务**。

- **MQTT Broker**: 基于 Eclipse Mosquitto，提供可靠的消息中转服务
- **Gateway Proxy**: Python 实现的智能数据网关，负责数据验证、清洗、去重和转发

---

## 🏗️ 系统架构

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   B 部分         │         │   A 部分          │         │   C 部分         │
│  (数据发布端)    │ ──────> │  MQTT Broker +   │ ──────> │  (数据订阅端)    │
│                 │         │  Gateway Proxy   │         │                 │
└─────────────────┘         └──────────────────┘         └─────────────────┘
     发布到                      验证、清洗、               订阅来自
 ingest/env/*                   转发                      env/*
```

**数据流：**
1. B 部分传感器发布原始数据到 `ingest/env/{temperature,humidity,pressure}`
2. Gateway Proxy 订阅 `ingest/env/#`，进行数据验证和清洗
3. Gateway Proxy 转发清洗后的数据到 `env/{temperature,humidity,pressure}`
4. C 部分订阅 `env/#`，接收高质量数据

---

## ✨ 核心功能

### MQTT Broker (Mosquitto)

- ✅ 监听端口 `0.0.0.0:1883`
- ✅ ACL 权限控制（4 个账号角色）
- ✅ 密码加密认证
- ✅ 持久化存储
- ✅ 系统日志

### Gateway Proxy 代理服务

#### 1. 数据验证
- JSON 格式校验
- 必需字段检查（`ts`, `value`）
- ISO8601 时间格式验证
- Metric 类型白名单（temperature/humidity/pressure）

#### 2. 数据清洗
- 字符串数字转换（`"25.3"` → `25.3`）
- 空字符串处理（`""` → `null`）
- 标准化输出格式

#### 3. 去重机制
- LRU 缓存（基于 metric + timestamp）
- 可配置时间窗口（默认 30 秒）
- 自动淘汰过期数据

#### 4. 监控与日志
- 详细的转发日志
- 统计信息（接收/转发/丢弃/去重/修正）
- DROP 日志包含丢弃原因

---

## 🔐 账号与权限

| 用户名 | 密码 | 权限 | 用途 |
|--------|------|------|------|
| `publisher` | `pub123` | 只能发布到 `ingest/env/#` | B 部分使用 |
| `collector` | `col123` | 只能订阅 `env/#` | C 部分使用 |
| `proxy` | `proxy123` | 读 `ingest/env/#`<br>写 `env/#` | 代理服务（内部）|
| `admin` | `admin123` | 完全权限 | 管理员调试 |

---

## 📡 Topic 规范

### 上游 Topic（B 发布）
- `ingest/env/temperature` - 温度数据
- `ingest/env/humidity` - 湿度数据
- `ingest/env/pressure` - 气压数据

### 下游 Topic（C 订阅）
- `env/temperature` - 温度数据（已清洗）
- `env/humidity` - 湿度数据（已清洗）
- `env/pressure` - 气压数据（已清洗）

### Payload 格式
```json
{
  "ts": "2025-12-17T10:30:00",
  "value": 25.3
}
```

- `ts`: ISO8601 格式时间戳（`YYYY-MM-DDTHH:MM:SS`）
- `value`: 数值或 `null`

---

## 🚀 快速开始

### 部署服务器

详细部署步骤请参考 [SYSTEM_DEPLOYMENT.md](SYSTEM_DEPLOYMENT.md)

**快速部署命令：**
```bash
cd /home/iot-project/scripts
sudo ./deploy-system.sh
```

### B/C 部分同学

连接信息和使用方法请参考 [CLIENT_GUIDE.md](CLIENT_GUIDE.md)

---

## 📁 项目结构

```
iot-project/
├── deploy/
│   ├── broker/
│   │   ├── mosquitto-system.conf    # Mosquitto 配置文件
│   │   ├── acl                       # ACL 权限控制
│   │   ├── password_file             # 加密密码文件（需生成）
│   │   └── generate_passwords.sh    # 密码生成脚本
│   └── proxy/
│       ├── app/
│       │   └── main.py               # Gateway Proxy 主程序
│       ├── requirements.txt          # Python 依赖
│       └── config.example.env        # 配置示例
├── scripts/
│   ├── deploy-system.sh              # 系统部署脚本
│   ├── verify.sh                     # 验证脚本
│   ├── test_pub.sh                   # 发布测试
│   ├── test_sub.sh                   # 订阅测试
│   ├── publish_test.py               # Python 发布测试
│   └── subscribe_test.py             # Python 订阅测试
├── docs/
│   ├── topic-spec.md                 # Topic 规范文档
│   └── sample_message.json           # 消息示例
├── README.md                         # 本文档
├── SYSTEM_DEPLOYMENT.md              # 部署指南
└── CLIENT_GUIDE.md                   # B/C 部分使用指南
```

---

## 🧪 测试验证

### 自动验证
```bash
cd /home/iot-project/scripts
./verify.sh localhost
```

### 手动测试

**终端 1 - 订阅：**
```bash
mosquitto_sub -h localhost -u collector -P col123 -t "env/#" -v
```

**终端 2 - 发布：**
```bash
mosquitto_pub -h localhost -u publisher -P pub123 \
  -t "ingest/env/temperature" \
  -m '{"ts":"2025-12-17T10:30:00","value":25.3}'
```

---

## 🔧 服务管理

```bash
# 查看服务状态
systemctl status mosquitto mqtt-proxy

# 查看实时日志
journalctl -u mqtt-proxy -f
tail -f /var/log/mosquitto/mosquitto.log

# 重启服务
sudo systemctl restart mosquitto mqtt-proxy

# 停止服务
sudo systemctl stop mosquitto mqtt-proxy
```

---

## 🎯 技术亮点

1. **数据质量保障** - JSON验证、字段校验、时间格式标准化
2. **智能数据清洗** - 自动类型转换、空值处理
3. **防重复机制** - LRU 缓存去重
4. **生产级部署** - systemd 服务化、自动重启、开机自启
5. **安全性** - ACL 细粒度权限控制、密码加密
6. **可观测性** - 详细日志、统计信息、问题追溯
7. **高扩展性** - 配置驱动、模块化设计
8. **容错稳定** - 自动重连、异常捕获、优雅关闭

---

## 📊 部署信息

- **服务器**: 139.224.237.20
- **端口**: 1883
- **协议**: MQTT v3.1.1
- **部署方式**: 系统部署（systemd）

---

## 👥 团队分工

- **A 部分**: MQTT Broker + Gateway Proxy 部署与维护
- **B 部分**: 数据发布端（传感器模拟）
- **C 部分**: 数据订阅端（数据处理）

---

## 📞 支持

- 部署文档: [SYSTEM_DEPLOYMENT.md](SYSTEM_DEPLOYMENT.md)
- 客户端指南: [CLIENT_GUIDE.md](CLIENT_GUIDE.md)
- 遇到问题请查看服务日志或联系 A 部分负责人

---

**项目状态**: ✅ 已部署运行

**最后更新**: 2025-12-17
