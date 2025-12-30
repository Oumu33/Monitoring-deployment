#!/bin/bash
# ===================================================================
# 拓扑发现定时任务脚本
# 用途: 定期运行 LLDP 发现并更新拓扑
# ===================================================================

set -e

INTERVAL=${DISCOVERY_INTERVAL:-300}  # 默认 5 分钟运行一次
VMAGENT_URL=${VMAGENT_URL:-http://vmagent:8429}

echo "拓扑发现服务启动"
echo "发现间隔: ${INTERVAL} 秒"
echo "vmagent URL: ${VMAGENT_URL}"

while true; do
    echo "=========================================="
    echo "开始拓扑发现: $(date)"
    echo "=========================================="

    # 运行拓扑发现
    python3 /scripts/lldp_discovery.py

    # 重新加载 vmagent 配置（让它重新读取 file_sd）
    echo "正在重新加载 vmagent 配置..."
    if curl -s -X POST "${VMAGENT_URL}/-/reload" > /dev/null 2>&1; then
        echo "✓ vmagent 配置重载成功"
    else
        echo "⚠ vmagent 重载失败（可能服务未启动）"
    fi

    echo "=========================================="
    echo "完成! 下次运行: $(date -d "+${INTERVAL} seconds")"
    echo "=========================================="

    sleep ${INTERVAL}
done
