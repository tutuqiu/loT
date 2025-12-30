#!/bin/bash
# 订阅测试脚本 - 使用 collector 账号订阅 env/# 接收官方数据
# 使用方法: ./test_sub.sh [broker_host]

set -e

# 从环境变量或参数读取配置
MQTT_HOST="${1:-localhost}"
MQTT_PORT="${MQTT_PORT:-1883}"
MQTT_USER="${MQTT_USER:-collector}"
MQTT_PASS="${MQTT_PASS:-col123}"

echo "=========================================="
echo "MQTT 订阅测试"
echo "=========================================="
echo "Broker:   ${MQTT_HOST}:${MQTT_PORT}"
echo "User:     ${MQTT_USER}"
echo "Topic:    env/#"
echo "=========================================="
echo ""

# 检查 mosquitto_sub 是否安装
if ! command -v mosquitto_sub &> /dev/null; then
    echo "错误: mosquitto_sub 未安装"
    echo "请安装: apt-get install mosquitto-clients"
    exit 1
fi

echo "正在订阅 env/# (按 Ctrl+C 退出)..."
echo ""

# 订阅所有官方 topic
mosquitto_sub \
    -h "${MQTT_HOST}" \
    -p "${MQTT_PORT}" \
    -u "${MQTT_USER}" \
    -P "${MQTT_PASS}" \
    -t "env/#" \
    -v \
    -F "%I %t %p"
