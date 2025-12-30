# 环境监测数据采集与分析处理系统

本项目为《物联网应用基础》课程期末小组项目，基于 MQTT 发布/订阅实现环境监测数据的发布、清洗转发、入库与可视化展示。更完整的设计说明与细节请见：`项目说明文档.md`。

## 项目部署流程（A/B/C/D 全链路）

> 说明：以下为最小可跑通流程，按顺序执行。具体配置项与说明以 `项目说明文档.md` 为准。

### 1. A 模块：Broker + Gateway Proxy

1) 安装并配置 Mosquitto（含认证与 ACL）
- 安装 Mosquitto 与客户端工具（按系统选择包管理器）
- 拷贝配置：
  - `A-deploy/iot-project/deploy/broker/mosquitto-system.conf` → `/etc/mosquitto/mosquitto.conf`
  - `A-deploy/iot-project/deploy/broker/acl` → `/etc/mosquitto/acl`
- 生成密码文件：
  - `A-deploy/iot-project/deploy/broker/generate_passwords.sh`
- 启动服务：
  - `sudo systemctl enable mosquitto`
  - `sudo systemctl start mosquitto`

2) 启动 Gateway Proxy
- 进入目录：`A-deploy/iot-project/deploy/proxy`
- 复制并编辑配置：`config.example.env` → `.env`
- 安装依赖并运行：
  - `pip install -r requirements.txt`
  - `python app/main.py`

### 2. B 模块：数据发布端（Publisher）

- 进入目录：`B-publisher`
- 安装依赖：`pip install paho-mqtt`
- 启动发布（示例）：
  - `python publish.py --metric temperature --rate 1`
- 运行中控制：`pause` / `resume` / `rate N` / `stop`

### 3. C 模块：数据采集端（Collector + API）

- 进入目录：`C-collector`
- 安装依赖：`pip install -r requirements.txt`
- 启动采集器（订阅 env/# 写入 SQLite）：
  - `python collector.py`
- 启动 HTTP API：
  - `uvicorn api:app --host 0.0.0.0 --port 8000`
- 可选验证：`python verify.py`（查看库内统计）

### 4. D 模块：图形化界面（UI）

- 进入目录：`D-ui`
- 安装依赖：`pip install -r requirements.txt`
- 启动界面：
  - `python main.py`
- UI 中选择指标与速率，Start 启动发布；日志窗口可看到发布与订阅状态

### 5. 启动顺序

1) Mosquitto Broker  
2) Gateway Proxy  
3) C-collector  
4) C-collector API  
5) D-ui  
6) 通过 UI 启动 B-publisher（或命令行启动）  

## 常见问题

### 1) 订阅端没有数据？
- 确认 Proxy 已启动且无报错（ingest → env 的转发链路）
- 确认 Publisher 发布到 `ingest/env/<metric>`，Collector/UI 订阅 `env/#`
- 确认账号权限（ACL）与用户名密码一致

### 2) 数据库数据很少/看起来不增长？
- Collector 使用 `UNIQUE(metric, ts)`，相同时间戳会被覆盖
- 确认 Publisher 是否真的在持续发布（查看控制台进度日志）

### 3) MQTT 连接失败？
- Broker 是否正常运行、端口 1883 是否可达
- 用户名/密码是否正确，匿名是否被禁用

### 4) UI 无法启动发布端？
- 检查 `D-ui/config.py` 中脚本路径是否正确
- 确认已安装 `paho-mqtt`（B-publisher 依赖）
