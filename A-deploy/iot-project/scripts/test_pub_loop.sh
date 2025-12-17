#!/bin/bash
# 循环发布测试脚本 - 持续发送数据用于演示
# 使用方法: ./test_pub_loop.sh [broker_host] [interval_seconds]

set -e

MQTT_HOST="${1:-localhost}"
INTERVAL="${2:-2}"

echo "=========================================="
echo "MQTT 循环发布测试"
echo "=========================================="
echo "Broker:     ${MQTT_HOST}"
echo "Interval:   ${INTERVAL}s"
echo "按 Ctrl+C 停止"
echo "=========================================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 轮流发布三种 metrics
METRICS=("temperature" "humidity" "pressure")
counter=0

while true; do
    metric="${METRICS[$((counter % 3))]}"
    
    echo "[$(date '+%H:%M:%S')] 发布 ${metric}..."
    "${SCRIPT_DIR}/test_pub.sh" "${MQTT_HOST}" "${metric}"
    
    counter=$((counter + 1))
    sleep "${INTERVAL}"
done
