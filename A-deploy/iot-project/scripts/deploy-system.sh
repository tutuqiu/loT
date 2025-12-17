#!/bin/bash
# IoT Project - 系统部署脚本（无 Docker）
# 使用方法: sudo ./deploy-system.sh

set -e

echo "=========================================="
echo "IoT Project - 系统部署"
echo "MQTT Broker + Proxy Gateway"
echo "=========================================="
echo ""

# 检查是否以 root 运行
if [ "$EUID" -ne 0 ]; then 
    echo "❌ 请使用 sudo 运行此脚本"
    echo "   sudo ./deploy-system.sh"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"

echo "项目目录: ${PROJECT_ROOT}"
echo ""

# ============================================================
# 步骤 1: 安装 Mosquitto
# ============================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤 1/7: 安装 Mosquitto MQTT Broker"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 更新包列表（忽略第三方仓库错误）
apt-get update || echo "⚠️  部分仓库更新失败，但不影响继续"
apt-get install -y mosquitto mosquitto-clients

echo "✓ Mosquitto 安装完成"
mosquitto -h | head -1
echo ""

# ============================================================
# 步骤 2: 生成密码文件
# ============================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤 2/7: 生成密码文件"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd "${PROJECT_ROOT}/deploy/broker"

if [ -f password_file ]; then
    echo "密码文件已存在，跳过生成"
else
    echo "生成密码文件..."
    chmod +x generate_passwords.sh
    ./generate_passwords.sh
fi

echo "✓ 密码文件准备完成"
echo ""

# ============================================================
# 步骤 3: 配置 Mosquitto
# ============================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤 3/7: 配置 Mosquitto"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 停止服务
systemctl stop mosquitto 2>/dev/null || true

# 备份并清理旧配置
if [ -f /etc/mosquitto/mosquitto.conf ]; then
    mv /etc/mosquitto/mosquitto.conf /etc/mosquitto/mosquitto.conf.bak.$(date +%Y%m%d%H%M%S) 2>/dev/null || true
fi

# 清理 conf.d 目录中的配置（可能包含 bridge 等冲突配置）
if [ -d /etc/mosquitto/conf.d ]; then
    mkdir -p /etc/mosquitto/conf.d.bak.$(date +%Y%m%d%H%M%S)
    mv /etc/mosquitto/conf.d/* /etc/mosquitto/conf.d.bak.$(date +%Y%m%d%H%M%S)/ 2>/dev/null || true
fi

# 复制配置文件
cp "${PROJECT_ROOT}/deploy/broker/mosquitto-system.conf" /etc/mosquitto/mosquitto.conf
cp "${PROJECT_ROOT}/deploy/broker/acl" /etc/mosquitto/acl
cp "${PROJECT_ROOT}/deploy/broker/password_file" /etc/mosquitto/password_file

# 设置权限
chown mosquitto:mosquitto /etc/mosquitto/password_file
chmod 600 /etc/mosquitto/password_file
chown mosquitto:mosquitto /etc/mosquitto/acl
chmod 644 /etc/mosquitto/acl

# 创建必要目录
mkdir -p /var/lib/mosquitto
mkdir -p /var/log/mosquitto
chown -R mosquitto:mosquitto /var/lib/mosquitto
chown -R mosquitto:mosquitto /var/log/mosquitto

echo "✓ Mosquitto 配置完成"
echo ""

# ============================================================
# 步骤 4: 启动 Mosquitto
# ============================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤 4/7: 启动 Mosquitto"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

systemctl daemon-reload
systemctl start mosquitto
systemctl enable mosquitto
sleep 2

if systemctl is-active --quiet mosquitto; then
    echo "✓ Mosquitto 启动成功"
else
    echo "❌ Mosquitto 启动失败，错误日志："
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    journalctl -u mosquitto -n 30 --no-pager
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "测试配置文件："
    mosquitto -c /etc/mosquitto/mosquitto.conf -v || true
    exit 1
fi
echo ""

# ============================================================
# 步骤 5: 安装 Python 依赖
# ============================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤 5/7: 安装 Python 依赖"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

apt-get install -y python3 python3-pip
pip3 install paho-mqtt python-dotenv

echo "✓ Python 依赖安装完成"
python3 --version
echo ""

# ============================================================
# 步骤 6: 配置代理服务
# ============================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤 6/7: 配置代理服务（systemd）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cat > /etc/systemd/system/mqtt-proxy.service <<EOF
[Unit]
Description=MQTT Gateway Proxy Service
Documentation=https://github.com/your-project
After=network.target mosquitto.service
Requires=mosquitto.service

[Service]
Type=simple
User=root
WorkingDirectory=${PROJECT_ROOT}/deploy/proxy
Environment="MQTT_BROKER_HOST=localhost"
Environment="MQTT_BROKER_PORT=1883"
Environment="MQTT_USERNAME=proxy"
Environment="MQTT_PASSWORD=proxy123"
Environment="LOG_LEVEL=INFO"
Environment="DEDUP_ENABLED=true"
ExecStart=/usr/bin/python3 ${PROJECT_ROOT}/deploy/proxy/app/main.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=mqtt-proxy

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
echo "✓ 代理服务配置完成"
echo ""

# ============================================================
# 步骤 7: 启动代理服务
# ============================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤 7/7: 启动代理服务"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

systemctl start mqtt-proxy
systemctl enable mqtt-proxy
sleep 3

if systemctl is-active --quiet mqtt-proxy; then
    echo "✓ 代理服务启动成功"
else
    echo "❌ 代理服务启动失败"
    echo "查看日志: journalctl -u mqtt-proxy -n 50"
    exit 1
fi
echo ""

# ============================================================
# 配置防火墙
# ============================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "配置防火墙"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if command -v ufw &> /dev/null; then
    ufw allow 1883/tcp
    echo "✓ 防火墙规则已添加（ufw）"
elif command -v firewall-cmd &> /dev/null; then
    firewall-cmd --permanent --add-port=1883/tcp
    firewall-cmd --reload
    echo "✓ 防火墙规则已添加（firewalld）"
else
    echo "⚠️  未检测到防火墙，请手动开放 1883 端口"
fi
echo ""

# ============================================================
# 完成
# ============================================================
echo "=========================================="
echo "✅ 部署完成！"
echo "=========================================="
echo ""
echo "服务状态："
systemctl status mosquitto --no-pager -l | head -3
systemctl status mqtt-proxy --no-pager -l | head -3
echo ""

PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo "<获取失败>")
echo "连接信息："
echo "  Broker: ${PUBLIC_IP}:1883"
echo "  本地:   localhost:1883"
echo ""
echo "账号信息："
echo "  publisher / pub123  - 发布端 B 使用"
echo "  collector / col123  - 订阅端 C 使用"
echo "  proxy     / proxy123 - 代理服务（内部）"
echo "  admin     / admin123 - 管理员（调试）"
echo ""
echo "管理命令："
echo "  查看 Mosquitto 状态:  systemctl status mosquitto"
echo "  查看代理状态:         systemctl status mqtt-proxy"
echo "  查看 Mosquitto 日志:  tail -f /var/log/mosquitto/mosquitto.log"
echo "  查看代理日志:         journalctl -u mqtt-proxy -f"
echo "  重启 Mosquitto:       systemctl restart mosquitto"
echo "  重启代理:             systemctl restart mqtt-proxy"
echo "  停止所有服务:         systemctl stop mosquitto mqtt-proxy"
echo ""
echo "快速测试："
echo "  订阅: mosquitto_sub -h localhost -u collector -P col123 -t 'env/#' -v"
echo "  发布: mosquitto_pub -h localhost -u publisher -P pub123 \\"
echo "          -t 'ingest/env/temperature' \\"
echo "          -m '{\"ts\":\"2025-12-16T10:30:00\",\"value\":25.3}'"
echo ""
echo "建议运行验证脚本测试部署："
echo "  cd ${PROJECT_ROOT}/scripts"
echo "  ./verify.sh localhost"
echo ""
