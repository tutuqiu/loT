#!/bin/bash
# 发布测试脚本 - 使用 publisher 账号向 ingest/env/* 发布样例数据
# 使用方法: ./test_pub.sh [broker_host] [metric]

set -e

# 从环境变量或参数读取配置
MQTT_HOST="${1:-localhost}"
METRIC="${2:-temperature}"
MQTT_PORT="${MQTT_PORT:-1883}"
MQTT_USER="${MQTT_USER:-publisher}"
MQTT_PASS="${MQTT_PASS:-pub123}"

# 支持的 metrics
ALLOWED_METRICS=("temperature" "humidity" "pressure")

# 检查 metric 是否合法
if [[ ! " ${ALLOWED_METRICS[@]} " =~ " ${METRIC} " ]]; then
    echo "错误: 不支持的 metric '${METRIC}'"
    echo "支持的 metrics: ${ALLOWED_METRICS[*]}"
    exit 1
fi

# 构造 topic
TOPIC="ingest/env/${METRIC}"

echo "=========================================="
echo "MQTT 发布测试"
echo "=========================================="
echo "Broker:   ${MQTT_HOST}:${MQTT_PORT}"
echo "User:     ${MQTT_USER}"
echo "Topic:    ${TOPIC}"
echo "=========================================="
echo ""

# 检查 mosquitto_pub 是否安装
if ! command -v mosquitto_pub &> /dev/null; then
    echo "错误: mosquitto_pub 未安装"
    echo "请安装: apt-get install mosquitto-clients"
    exit 1
fi

# 生成样例数据
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%S")

# 根据 metric 生成不同的测试值
case "${METRIC}" in
    temperature)
        VALUE=$(awk -v min=15 -v max=35 'BEGIN{srand(); print min+rand()*(max-min)}')
        ;;
    humidity)
        VALUE=$(awk -v min=30 -v max=80 'BEGIN{srand(); print min+rand()*(max-min)}')
        ;;
    pressure)
        VALUE=$(awk -v min=990 -v max=1030 'BEGIN{srand(); print min+rand()*(max-min)}')
        ;;
esac

# 构造 JSON payload
PAYLOAD=$(cat <<EOF
{"ts":"${TIMESTAMP}","value":${VALUE}}
EOF
)

echo "发布消息:"
echo "  Payload: ${PAYLOAD}"
echo ""

# 发布消息
mosquitto_pub \
    -h "${MQTT_HOST}" \
    -p "${MQTT_PORT}" \
    -u "${MQTT_USER}" \
    -P "${MQTT_PASS}" \
    -t "${TOPIC}" \
    -m "${PAYLOAD}" \
    -q 0

echo "✓ 消息已发布"
echo ""
echo "提示: 运行 ./test_sub.sh ${MQTT_HOST} 查看订阅端是否收到"
