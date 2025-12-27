#!/bin/bash

#################################################
# 监控系统健康检查脚本
# 用途: 检查所有服务和端点的健康状态
#################################################

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 统计
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

# 日志函数
log_check() {
    echo -en "${BLUE}[CHECK]${NC} $1 ... "
}

log_pass() {
    echo -e "${GREEN}✓ PASS${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
}

log_fail() {
    echo -e "${RED}✗ FAIL${NC} $1"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
}

log_warn() {
    echo -e "${YELLOW}⚠ WARNING${NC} $1"
}

# 检查 Docker 服务状态
check_docker_services() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Docker 服务状态检查"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    local services=(
        "victoriametrics"
        "vmagent"
        "vmalert"
        "alertmanager"
        "grafana"
        "node-exporter"
        "snmp-exporter"
        "vmware-exporter"
    )

    for service in "${services[@]}"; do
        TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
        log_check "$service 容器运行状态"

        if docker ps --format '{{.Names}}' | grep -q "^${service}$"; then
            # 检查容器健康状态
            local status=$(docker inspect --format='{{.State.Status}}' "$service" 2>/dev/null)
            if [ "$status" = "running" ]; then
                log_pass
            else
                log_fail "状态: $status"
            fi
        else
            log_fail "容器未运行"
        fi
    done
}

# 检查 HTTP 端点
check_http_endpoint() {
    local name=$1
    local url=$2
    local expected_code=${3:-200}

    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    log_check "$name HTTP 端点 ($url)"

    local http_code=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")

    if [ "$http_code" = "$expected_code" ]; then
        log_pass
    else
        log_fail "HTTP $http_code (期望 $expected_code)"
    fi
}

# 检查服务端点
check_service_endpoints() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  服务端点健康检查"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    check_http_endpoint "VictoriaMetrics" "http://localhost:8428/health"
    check_http_endpoint "vmagent" "http://localhost:8429/health"
    check_http_endpoint "vmalert" "http://localhost:8880/health"
    check_http_endpoint "Alertmanager" "http://localhost:9093/-/healthy"
    check_http_endpoint "Grafana" "http://localhost:3000/api/health"
    check_http_endpoint "Node Exporter" "http://localhost:9100/metrics"
    check_http_endpoint "SNMP Exporter" "http://localhost:9116/metrics"
    check_http_endpoint "VMware Exporter" "http://localhost:9272/healthz"
}

# 检查指标采集
check_metrics_collection() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  指标采集检查"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # 检查 vmagent 采集目标
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    log_check "vmagent 采集目标状态"

    local targets=$(curl -s http://localhost:8429/targets 2>/dev/null | grep -o '"health":"up"' | wc -l)
    if [ "$targets" -gt 0 ]; then
        log_pass
        echo "       ↳ $targets 个目标状态正常"
    else
        log_fail "没有健康的采集目标"
    fi

    # 检查 VictoriaMetrics 存储的时间序列数
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    log_check "VictoriaMetrics 时间序列数量"

    local metrics=$(curl -s http://localhost:8428/api/v1/status/tsdb 2>/dev/null | grep -o '"totalSeries":[0-9]*' | grep -o '[0-9]*')
    if [ -n "$metrics" ] && [ "$metrics" -gt 0 ]; then
        log_pass
        echo "       ↳ $metrics 个时间序列"
    else
        log_fail "没有时间序列数据"
    fi
}

# 检查告警规则
check_alert_rules() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  告警规则检查"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    log_check "vmalert 规则加载状态"

    local rules=$(curl -s http://localhost:8880/api/v1/rules 2>/dev/null | grep -o '"file":"[^"]*"' | wc -l)
    if [ "$rules" -gt 0 ]; then
        log_pass
        echo "       ↳ $rules 个规则组已加载"
    else
        log_fail "没有加载告警规则"
    fi

    # 检查当前触发的告警
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    log_check "当前触发的告警"

    local firing=$(curl -s http://localhost:8880/api/v1/alerts 2>/dev/null | grep -o '"state":"firing"' | wc -l)
    if [ "$firing" -eq 0 ]; then
        log_pass
        echo "       ↳ 没有触发的告警"
    else
        log_warn "有 $firing 个告警正在触发"
    fi
}

# 检查资源使用
check_resource_usage() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  资源使用情况"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # CPU 和内存使用
    echo ""
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" \
        victoriametrics vmagent vmalert alertmanager grafana 2>/dev/null | head -6

    # 磁盘使用
    echo ""
    echo "磁盘使用:"
    df -h . | tail -1 | awk '{print "  可用空间: " $4 " / " $2 " (" $5 " 已用)"}'

    # Docker volumes 大小
    echo ""
    echo "Docker Volumes 大小:"
    for volume in vmdata vmagentdata grafana-data alertmanager-data; do
        local vol_name="monitoring-deployment_${volume}"
        if docker volume inspect "$vol_name" >/dev/null 2>&1; then
            local size=$(docker run --rm -v "${vol_name}:/data" alpine du -sh /data 2>/dev/null | awk '{print $1}')
            echo "  $volume: $size"
        fi
    done
}

# 检查日志错误
check_logs_for_errors() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  最近日志错误检查 (最近 5 分钟)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    local services=("victoriametrics" "vmagent" "vmalert" "alertmanager")

    for service in "${services[@]}"; do
        local errors=$(docker logs --since 5m "$service" 2>&1 | grep -iE "error|fatal|panic" | wc -l)
        if [ "$errors" -gt 0 ]; then
            echo -e "${YELLOW}⚠${NC} $service: 发现 $errors 条错误日志"
            echo "   查看详情: docker logs $service | grep -iE 'error|fatal|panic'"
        fi
    done
}

# 显示总结
show_summary() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  健康检查总结"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "  总检查项: $TOTAL_CHECKS"
    echo -e "  通过: ${GREEN}$PASSED_CHECKS${NC}"
    echo -e "  失败: ${RED}$FAILED_CHECKS${NC}"
    echo ""

    local success_rate=$((PASSED_CHECKS * 100 / TOTAL_CHECKS))

    if [ "$FAILED_CHECKS" -eq 0 ]; then
        echo -e "${GREEN}✓ 所有检查通过！系统运行正常${NC}"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        return 0
    elif [ "$success_rate" -ge 80 ]; then
        echo -e "${YELLOW}⚠ 系统基本正常，但有 $FAILED_CHECKS 项检查失败${NC}"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        return 1
    else
        echo -e "${RED}✗ 系统存在严重问题，请检查失败的项目${NC}"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        return 2
    fi
}

# 主函数
main() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  监控系统健康检查"
    echo "  $(date '+%Y-%m-%d %H:%M:%S')"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # 检查是否在正确的目录
    if [ ! -f "docker-compose.yaml" ]; then
        echo -e "${RED}错误: 请在项目根目录运行此脚本${NC}"
        exit 1
    fi

    check_docker_services
    check_service_endpoints
    check_metrics_collection
    check_alert_rules
    check_resource_usage
    check_logs_for_errors
    show_summary
}

# 执行主函数
main "$@"
