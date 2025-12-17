"""
配置文件 - 可根据实际部署环境修改
"""

# MQTT Broker配置
BROKER_HOST = "139.224.237.20"
BROKER_PORT = 1883
USERNAME = "subscriber"
PASSWORD = "sub123"

# 订阅主题
SUBSCRIBE_TOPIC = "env/#"

# 数据库配置
DB_PATH = "data/measurements.db"

# 日志配置
VERBOSE = True

