#!/bin/bash
# 生成 Mosquitto 密码文件的脚本
# 使用方法: ./generate_passwords.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PASSWORD_FILE="${SCRIPT_DIR}/password_file"

echo "正在生成 Mosquitto 密码文件..."
echo "位置: ${PASSWORD_FILE}"
echo ""

# 删除旧文件
rm -f "${PASSWORD_FILE}"

# 创建账号（密码与用户名相同，用于演示）
# 实际生产环境请使用强密码

echo "创建账号: admin (密码: admin123)"
touch "${PASSWORD_FILE}"
mosquitto_passwd -b "${PASSWORD_FILE}" admin admin123

echo "创建账号: publisher (密码: pub123)"
mosquitto_passwd -b "${PASSWORD_FILE}" publisher pub123

echo "创建账号: proxy (密码: proxy123)"
mosquitto_passwd -b "${PASSWORD_FILE}" proxy proxy123

echo "创建账号: collector (密码: col123)"
mosquitto_passwd -b "${PASSWORD_FILE}" collector col123

echo ""
echo "✓ 密码文件生成完成！"
echo ""
echo "账号列表："
echo "  admin      / admin123    - 完全权限（管理员）"
echo "  publisher  / pub123      - 只能发布到 ingest/env/#"
echo "  proxy      / proxy123    - 读取 ingest/env/#，写入 env/#"
echo "  collector  / col123      - 只能订阅 env/#"
echo ""
echo "请妥善保管密码！"
