# MQTT Topic & Payload 规范

> 数据来源：temperature.txt / humidity.txt / pressure.txt  
> 原始数据特点：以时间戳字符串为 key、数值为字符串；可能存在空字符串表示缺失值。

## 1. 目的
统一发布端、订阅端、存储分析端、GUI 的 Topic 命名与消息格式，保证各模块可并行开发与稳定联调。

## 2. MQTT 约定
- 编码：UTF-8
- QoS：0（MVP 阶段统一）
- Retain：false（不保留；历史由数据库保存）
- Broker：Mosquitto（地址/端口由 A 同学在 README 中给出，例如 <BROKER_IP>:1883）

## 3. Topic 规范（3 个主题，按指标拆分）
发布端分别向以下 Topic 发布：

1) 温度：
- `env/temperature`

2) 湿度：
- `env/humidity`

3) 气压：
- `env/pressure`

订阅端可按需订阅：
- 只订阅温度：`env/temperature`
- 订阅全部：`env/#`

## 4. Payload JSON 结构（统一格式）

### 4.1 字段定义
每条消息是一个 JSON 对象，字段如下：

| 字段名 | 类型              | 必填 | 含义 |
|------|-------------------|------|------|
| ts   | string            | 是   | 时间戳（ISO 8601 字符串，如 "2014-05-30T07:00:00"） |
| value| number 或 null     | 是   | 指标数值；缺失值用 null |

### 4.2 数据转换规则（必须一致）
- 原始文件里 value 为字符串（例如 "10.0"、"72"、"1024"），发布端必须转换为 number 再发送。
- 若原始 value 为 ""（空字符串）或缺失，发布端发送 `null`。
- ts 直接使用原始文件中的时间戳字符串（不强制转换为毫秒时间戳）。

### 4.3 单位说明（报告中需要统一口径）
- temperature：建议 °C（若老师另有说明以老师为准）
- humidity：建议 %（若老师另有说明以老师为准）
- pressure：建议 hPa（或与老师数据一致）

## 5. 去重与顺序（可选）
若未来升级到 QoS=1，可能出现重复投递。订阅端可用 `(topic, ts)` 作为唯一键进行去重。

## 6. 联调自测（Mosquitto 命令）

### 6.1 订阅（终端1）
```bash
mosquitto_sub -h <BROKER_IP> -t "env/#" -v
```

### 6.2 发布（终端2）
```bash
mosquitto_pub -h <BROKER_IP> -t "env/temperature" -m '{"ts":"2014-05-30T07:00:00","value":11}'
mosquitto_pub -h <BROKER_IP> -t "env/humidity" -m '{"ts":"2014-05-30T07:00:00","value":72}'
mosquitto_pub -h <BROKER_IP> -t "env/pressure" -m '{"ts":"2014-05-30T07:00:00","value":1012}'
```

## 7. 版本记录
- 3 个 topic（temperature/humidity/pressure）；payload 统一 ts/value；QoS=0；retain=false