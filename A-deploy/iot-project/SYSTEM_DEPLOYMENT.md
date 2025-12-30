# 系统部署完整指南

本文档介绍如何在 Ubuntu 服务器上部署 MQTT Broker + Gateway Proxy 服务。

---

## 🚀 完整部署流程

### 前置条件

- Ubuntu 18.04+ 服务器
- Root 或 sudo 权限
- Python 3.6+

### 第一步：准备项目文件

```bash
# 1. 上传项目到服务器
# 使用 scp 或其他方式将整个 iot-project 目录上传到 /home/iot-project

# 2. 进入项目目录
cd /home/iot-project

# 3. 给脚本添加执行权限
chmod +x scripts/*.sh deploy/broker/generate_passwords.sh
```

### 第二步：一键部署

```bash
# 运行系统部署脚本
cd /home/iot-project/scripts
sudo ./deploy-system.sh
```

脚本会自动完成以下操作：
1. ✅ 安装 Mosquitto MQTT Broker
2. ✅ 生成密码文件
3. ✅ 配置 Mosquitto
4. ✅ 启动 Mosquitto 服务
5. ✅ 安装 Python 依赖
6. ✅ 配置代理服务为 systemd 服务
7. ✅ 启动代理服务
8. ✅ 配置防火墙

**预期输出**：
```
========================================
✅ 部署完成！
========================================

服务状态：
● mosquitto.service - Mosquitto MQTT Broker
   Active: active (running)
● mqtt-proxy.service - MQTT Gateway Proxy Service
   Active: active (running)

连接信息：
  Broker: <公网IP>:1883
  本地:   localhost:1883
```

### 第三步：验证部署

#### 方法1：自动验证（推荐）

```bash
cd /home/iot-project/scripts
./verify.sh localhost
```

预期输出：`通过: 5 / 5` ✅

#### 方法2：手动验证

**终端 1 - 订阅测试：**
```bash
mosquitto_sub -h localhost -u collector -P col123 -t "env/#" -v
```

**终端 2 - 发布测试：**
```bash
mosquitto_pub -h localhost -u publisher -P pub123 \
  -t "ingest/env/temperature" \
  -m '{"ts":"2025-12-16T10:30:00","value":25.3}'
```

如果终端 1 收到消息，说明部署成功！🎉

---

## 📊 服务管理

### 查看服务状态

```bash
# 查看所有服务
systemctl status mosquitto mqtt-proxy

# 单独查看 Mosquitto
systemctl status mosquitto

# 单独查看代理服务
systemctl status mqtt-proxy
```

### 查看日志

```bash
# 查看 Mosquitto 日志
tail -f /var/log/mosquitto/mosquitto.log

# 查看代理服务日志（实时）
journalctl -u mqtt-proxy -f

# 查看代理最近50条日志
journalctl -u mqtt-proxy -n 50
```

### 重启服务

```bash
# 重启 Mosquitto
sudo systemctl restart mosquitto

# 重启代理服务
sudo systemctl restart mqtt-proxy

# 同时重启两个服务
sudo systemctl restart mosquitto mqtt-proxy
```

### 停止服务

```bash
# 停止服务
sudo systemctl stop mosquitto mqtt-proxy

# 禁用开机自启
sudo systemctl disable mosquitto mqtt-proxy
```

### 启动服务

```bash
# 启动服务
sudo systemctl start mosquitto mqtt-proxy

# 启用开机自启
sudo systemctl enable mosquitto mqtt-proxy
```

---

## 🔌 连接信息

### Broker 地址
- **远程连接**: `<服务器公网IP>:1883`
- **本地连接**: `localhost:1883`

### 账号信息

| 用户名 | 密码 | 权限 | 用途 |
|--------|------|------|------|
| `publisher` | `pub123` | 只能发布到 `ingest/env/#` | 发布端 B |
| `collector` | `col123` | 只能订阅 `env/#` | 订阅端 C |
| `proxy` | `proxy123` | 读 `ingest/env/#`，写 `env/#` | 代理服务（内部）|
| `admin` | `admin123` | 完全权限 | 管理员调试 |

### Topic 规范

**上游 Topic**（B 发布）:
- `ingest/env/temperature`
- `ingest/env/humidity`
- `ingest/env/pressure`

**下游 Topic**（C 订阅）:
- `env/temperature`
- `env/humidity`
- `env/pressure`

**Payload 格式**:
```json
{"ts":"2025-12-16T10:30:00","value":25.3}
```

---

## 🧪 测试与调试

### 基础连接测试

```bash
# 测试 admin 账号
mosquitto_sub -h localhost -u admin -P admin123 -t '$SYS/#' -C 1

# 测试 publisher 账号
mosquitto_pub -h localhost -u publisher -P pub123 \
  -t "ingest/env/temperature" -m '{"ts":"2025-12-16T10:00:00","value":20}'

# 测试 collector 账号
mosquitto_sub -h localhost -u collector -P col123 -t "env/#" -C 1
```

### 端到端测试

使用测试脚本：

```bash
cd /home/iot-project/scripts

# 订阅测试
./test_sub.sh localhost

# 发布测试（另一个终端）
./test_pub.sh localhost temperature
./test_pub.sh localhost humidity
./test_pub.sh localhost pressure

# 循环发布（演示用）
./test_pub_loop.sh localhost 2
```

### 查看代理统计

代理服务停止时会输出统计信息：

```bash
# 停止代理（会输出统计）
sudo systemctl stop mqtt-proxy

# 查看最后的日志（包含统计）
journalctl -u mqtt-proxy -n 30
```

---

## 🐛 故障排查

### 问题 1: Mosquitto 无法启动

**检查日志：**
```bash
journalctl -u mosquitto -n 50
# 或
tail -50 /var/log/mosquitto/mosquitto.log
```

**常见原因：**
- 端口 1883 被占用
- 密码文件权限错误
- 配置文件语法错误

**解决：**
```bash
# 检查端口占用
sudo netstat -tlnp | grep 1883

# 检查配置文件
mosquitto -c /etc/mosquitto/mosquitto.conf -v

# 修复权限
sudo chown mosquitto:mosquitto /etc/mosquitto/password_file
sudo chmod 600 /etc/mosquitto/password_file
```

### 问题 2: 代理服务无法启动

**检查日志：**
```bash
journalctl -u mqtt-proxy -n 50
```

**常见原因：**
- Python 依赖未安装
- 无法连接到 Mosquitto
- 权限问题

**解决：**
```bash
# 重新安装依赖
sudo pip3 install paho-mqtt python-dotenv

# 测试 Mosquitto 连接
mosquitto_sub -h localhost -u proxy -P proxy123 -t '$SYS/#' -C 1

# 检查服务配置
systemctl cat mqtt-proxy
```

### 问题 3: 防火墙阻止连接

**检查防火墙：**
```bash
sudo ufw status
```

**开放端口：**
```bash
sudo ufw allow 1883/tcp
```

**检查阿里云安全组：**
- 登录阿里云控制台
- 进入 ECS 实例
- 配置安全组规则
- 添加入方向规则：TCP 1883

### 问题 4: 消息未转发

**检查代理日志：**
```bash
journalctl -u mqtt-proxy -f
```

**查找 DROP 记录：**
```bash
journalctl -u mqtt-proxy | grep DROP
```

根据日志中的原因修正 Payload 格式。

---

## 🔧 配置文件位置

```
/etc/mosquitto/mosquitto.conf     - Mosquitto 主配置
/etc/mosquitto/acl                - 权限控制列表
/etc/mosquitto/password_file      - 加密密码文件
/etc/systemd/system/mqtt-proxy.service  - 代理服务配置
/var/lib/mosquitto/               - Mosquitto 数据目录
/var/log/mosquitto/               - Mosquitto 日志目录
```

---

## 📝 维护建议

### 日常监控

```bash
# 查看服务状态
systemctl status mosquitto mqtt-proxy

# 查看实时日志
journalctl -u mosquitto -u mqtt-proxy -f

# 查看系统资源占用
htop
# 或
ps aux | grep -E 'mosquitto|python3.*main.py'
```

### 定期备份

```bash
# 备份配置
sudo tar czf /backup/mqtt-config-$(date +%Y%m%d).tar.gz \
  /etc/mosquitto/ \
  /etc/systemd/system/mqtt-proxy.service

# 备份数据
sudo tar czf /backup/mqtt-data-$(date +%Y%m%d).tar.gz \
  /var/lib/mosquitto/
```

### 日志轮转

Mosquitto 日志会自动轮转（由 logrotate 管理），systemd 日志默认也有限制。

查看日志大小：
```bash
du -sh /var/log/mosquitto/
journalctl --disk-usage
```

---

## 🎯 给小组成员的对接说明

### 给 B 部分（发布端）

**连接信息：**
```python
BROKER_HOST = "<服务器公网IP>"
BROKER_PORT = 1883
USERNAME = "publisher"
PASSWORD = "pub123"
```

**测试命令：**
```bash
mosquitto_pub -h <服务器IP> -u publisher -P pub123 \
  -t "ingest/env/temperature" \
  -m '{"ts":"2025-12-16T10:30:00","value":25.3}'
```

### 给 C 部分（订阅端）

**连接信息：**
```python
BROKER_HOST = "<服务器公网IP>"
BROKER_PORT = 1883
USERNAME = "collector"
PASSWORD = "col123"
```

**测试命令：**
```bash
mosquitto_sub -h <服务器IP> -u collector -P col123 -t "env/#" -v
```

---

## 📞 技术支持

遇到问题：
1. 查看服务状态和日志
2. 运行 verify.sh 验证脚本
3. 参考故障排查章节
4. 联系 A 部分负责人

---

**部署完成后请保留此文档作为运维参考！**
