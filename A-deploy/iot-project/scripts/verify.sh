#!/bin/bash
# 快速验证脚本 - 检查部署是否成功
# 使用方法: ./verify.sh [broker_host]

set -e

MQTT_HOST="${1:-localhost}"
MQTT_PORT="1883"

echo "=========================================="
echo "IoT Project - 部署验证"
echo "=========================================="
echo "Broker: ${MQTT_HOST}:${MQTT_PORT}"
echo "=========================================="
echo ""

# 检查工具
if ! command -v mosquitto_pub &> /dev/null || ! command -v mosquitto_sub &> /dev/null; then
    echo "❌ mosquitto-clients 未安装"
    echo "请安装: apt-get install mosquitto-clients"
    exit 1
fi

echo "✓ 工具检查通过"
echo ""

# 测试项目
TOTAL=0
PASSED=0

# 测试 1: 连接测试（admin 账号）
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "测试 1: Broker 连接（admin 账号）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TOTAL=$((TOTAL+1))

if timeout 5 mosquitto_sub -h "${MQTT_HOST}" -p "${MQTT_PORT}" -u admin -P admin123 -t '$SYS/broker/version' -C 1 &>/dev/null; then
    echo "✓ PASSED - 可以连接 Broker"
    PASSED=$((PASSED+1))
else
    echo "✗ FAILED - 无法连接 Broker"
fi
echo ""

# 测试 2: Publisher 权限测试
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "测试 2: Publisher 权限（发布到 ingest/env/temperature）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TOTAL=$((TOTAL+1))

if mosquitto_pub -h "${MQTT_HOST}" -p "${MQTT_PORT}" -u publisher -P pub123 \
    -t "ingest/env/temperature" \
    -m '{"ts":"2025-12-16T10:00:00","value":25}' \
    -q 0 2>/dev/null; then
    echo "✓ PASSED - Publisher 可以发布到 ingest/env/temperature"
    PASSED=$((PASSED+1))
else
    echo "✗ FAILED - Publisher 发布失败"
fi
echo ""

# 测试 3: Collector 权限测试
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "测试 3: Collector 权限（订阅 env/#）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TOTAL=$((TOTAL+1))

# 在后台订阅
timeout 2 mosquitto_sub -h "${MQTT_HOST}" -p "${MQTT_PORT}" -u collector -P col123 \
    -t "env/#" -q 0 &>/dev/null &
SUB_PID=$!

sleep 1

if kill -0 ${SUB_PID} 2>/dev/null; then
    kill ${SUB_PID} 2>/dev/null || true
    echo "✓ PASSED - Collector 可以订阅 env/#"
    PASSED=$((PASSED+1))
else
    echo "✗ FAILED - Collector 订阅失败"
fi
echo ""

# 测试 4: 端到端测试（通过代理转发）
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "测试 4: 端到端转发（ingest → proxy → env）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TOTAL=$((TOTAL+1))

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%S")
TEST_VALUE=$(awk 'BEGIN{srand(); print int(rand()*100)}')
TEST_MSG="{\"ts\":\"${TIMESTAMP}\",\"value\":${TEST_VALUE}}"

# 在后台订阅 env/temperature
RECEIVED_FILE="/tmp/iot_test_$$.txt"
timeout 5 mosquitto_sub -h "${MQTT_HOST}" -p "${MQTT_PORT}" -u collector -P col123 \
    -t "env/temperature" -C 1 > "${RECEIVED_FILE}" 2>&1 &
SUB_PID=$!

sleep 1

# 发布到 ingest/env/temperature
mosquitto_pub -h "${MQTT_HOST}" -p "${MQTT_PORT}" -u publisher -P pub123 \
    -t "ingest/env/temperature" \
    -m "${TEST_MSG}" \
    -q 0

# 等待接收
sleep 2

# 检查是否收到
if [ -f "${RECEIVED_FILE}" ] && grep -q "\"value\":${TEST_VALUE}" "${RECEIVED_FILE}"; then
    echo "✓ PASSED - 消息成功转发"
    echo "  发送: ${TEST_MSG}"
    echo "  接收: $(cat ${RECEIVED_FILE})"
    PASSED=$((PASSED+1))
else
    echo "✗ FAILED - 消息未收到或转发失败"
    if [ -f "${RECEIVED_FILE}" ]; then
        echo "  接收到: $(cat ${RECEIVED_FILE})"
    fi
fi

# 清理
kill ${SUB_PID} 2>/dev/null || true
rm -f "${RECEIVED_FILE}"
echo ""

# 测试 5: 无效消息测试（代理应丢弃）
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "测试 5: 无效消息过滤（缺少 ts 字段）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TOTAL=$((TOTAL+1))

# 在后台订阅（期望收不到）
RECEIVED_FILE="/tmp/iot_test_invalid_$$.txt"
timeout 3 mosquitto_sub -h "${MQTT_HOST}" -p "${MQTT_PORT}" -u collector -P col123 \
    -t "env/temperature" -C 1 > "${RECEIVED_FILE}" 2>&1 &
SUB_PID=$!

sleep 1

# 发布无效消息（缺少 ts）
mosquitto_pub -h "${MQTT_HOST}" -p "${MQTT_PORT}" -u publisher -P pub123 \
    -t "ingest/env/temperature" \
    -m '{"value":99}' \
    -q 0

# 等待
sleep 2

# 检查是否被过滤
if [ ! -s "${RECEIVED_FILE}" ]; then
    echo "✓ PASSED - 无效消息被正确过滤（未转发）"
    PASSED=$((PASSED+1))
else
    echo "✗ FAILED - 无效消息未被过滤"
    echo "  接收到: $(cat ${RECEIVED_FILE})"
fi

# 清理
kill ${SUB_PID} 2>/dev/null || true
rm -f "${RECEIVED_FILE}"
echo ""

# 总结
echo "=========================================="
echo "验证结果"
echo "=========================================="
echo "通过: ${PASSED} / ${TOTAL}"
echo ""

if [ ${PASSED} -eq ${TOTAL} ]; then
    echo "🎉 所有测试通过！部署成功！"
    echo ""
    echo "下一步："
    echo "  1. 通知 B 部分使用 publisher 账号发布数据"
    echo "  2. 通知 C 部分使用 collector 账号订阅数据"
    echo "  3. 查看代理日志: docker compose logs -f proxy"
    exit 0
else
    echo "⚠️  部分测试失败，请检查配置和日志"
    echo ""
    echo "排查步骤："
    echo "  1. 检查容器状态: docker compose ps"
    echo "  2. 查看日志: docker compose logs"
    echo "  3. 参考文档: deploy/broker/README.md"
    exit 1
fi
