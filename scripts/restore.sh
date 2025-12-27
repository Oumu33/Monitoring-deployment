#!/bin/bash

#################################################
# 监控系统恢复脚本
# 用途: 从备份恢复 VictoriaMetrics 数据和 Grafana 配置
#################################################

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查备份目录
check_backup_dir() {
    local backup_path=$1

    if [ -z "$backup_path" ]; then
        log_error "请指定备份目录"
        echo "用法: $0 <备份目录>"
        echo "示例: $0 ./backup/20240101_120000"
        exit 1
    fi

    if [ ! -d "$backup_path" ]; then
        log_error "备份目录不存在: $backup_path"
        exit 1
    fi

    # 检查必要的备份文件
    local required_files=(
        "victoriametrics-data.tar.gz"
        "grafana-data.tar.gz"
        "configs.tar.gz"
    )

    for file in "${required_files[@]}"; do
        if [ ! -f "$backup_path/$file" ]; then
            log_error "缺少备份文件: $file"
            exit 1
        fi
    done

    log_success "备份目录验证通过"
}

# 显示备份信息
show_backup_info() {
    local backup_path=$1

    echo ""
    echo "备份信息:"

    if [ -f "$backup_path/backup-manifest.txt" ]; then
        cat "$backup_path/backup-manifest.txt"
    else
        echo "  备份目录: $backup_path"
        echo "  文件列表:"
        ls -lh "$backup_path" | tail -n +2 | awk '{print "    " $9 " - " $5}'
    fi

    echo ""
}

# 确认恢复
confirm_restore() {
    log_warning "恢复操作将覆盖当前所有数据！"
    echo ""
    read -p "是否继续? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "恢复操作已取消"
        exit 0
    fi
}

# 停止服务
stop_services() {
    log_info "停止监控服务..."

    if docker-compose down 2>/dev/null || docker compose down 2>/dev/null; then
        log_success "服务已停止"
    else
        log_error "停止服务失败"
        exit 1
    fi
}

# 恢复 VictoriaMetrics 数据
restore_victoriametrics() {
    log_info "恢复 VictoriaMetrics 数据..."

    local backup_path=$1
    local vm_backup="$backup_path/victoriametrics-data.tar.gz"

    # 删除现有数据
    docker volume rm monitoring-deployment_vmdata 2>/dev/null || true

    # 创建新 volume
    docker volume create monitoring-deployment_vmdata

    # 恢复数据
    docker run --rm \
        -v monitoring-deployment_vmdata:/data \
        -v "$backup_path:/backup" \
        alpine sh -c "cd /data && tar xzf /backup/victoriametrics-data.tar.gz"

    log_success "VictoriaMetrics 数据恢复完成"
}

# 恢复 Grafana 数据
restore_grafana() {
    log_info "恢复 Grafana 数据..."

    local backup_path=$1
    local grafana_backup="$backup_path/grafana-data.tar.gz"

    # 删除现有数据
    docker volume rm monitoring-deployment_grafana-data 2>/dev/null || true

    # 创建新 volume
    docker volume create monitoring-deployment_grafana-data

    # 恢复数据
    docker run --rm \
        -v monitoring-deployment_grafana-data:/data \
        -v "$backup_path:/backup" \
        alpine sh -c "cd /data && tar xzf /backup/grafana-data.tar.gz"

    log_success "Grafana 数据恢复完成"
}

# 恢复 Alertmanager 数据
restore_alertmanager() {
    log_info "恢复 Alertmanager 数据..."

    local backup_path=$1
    local am_backup="$backup_path/alertmanager-data.tar.gz"

    if [ -f "$am_backup" ]; then
        # 删除现有数据
        docker volume rm monitoring-deployment_alertmanager-data 2>/dev/null || true

        # 创建新 volume
        docker volume create monitoring-deployment_alertmanager-data

        # 恢复数据
        docker run --rm \
            -v monitoring-deployment_alertmanager-data:/data \
            -v "$backup_path:/backup" \
            alpine sh -c "cd /data && tar xzf /backup/alertmanager-data.tar.gz"

        log_success "Alertmanager 数据恢复完成"
    else
        log_warning "未找到 Alertmanager 备份，跳过"
    fi
}

# 恢复配置文件
restore_configs() {
    log_info "恢复配置文件..."

    local backup_path=$1
    local config_backup="$backup_path/configs.tar.gz"

    # 备份当前配置
    if [ -d "config" ]; then
        log_info "备份当前配置到 config.backup..."
        mv config config.backup.$(date +%Y%m%d_%H%M%S)
    fi

    # 恢复配置
    tar xzf "$config_backup"

    log_success "配置文件恢复完成"
}

# 启动服务
start_services() {
    log_info "启动监控服务..."

    if docker-compose up -d 2>/dev/null || docker compose up -d 2>/dev/null; then
        log_success "服务启动成功"
    else
        log_error "服务启动失败"
        exit 1
    fi
}

# 验证恢复
verify_restore() {
    log_info "等待服务启动..."
    sleep 10

    log_info "验证服务状态..."

    local services=("victoriametrics" "vmagent" "vmalert" "alertmanager" "grafana")
    local all_healthy=true

    for service in "${services[@]}"; do
        if docker ps --format '{{.Names}}' | grep -q "^${service}$"; then
            log_success "$service 运行正常"
        else
            log_error "$service 未运行"
            all_healthy=false
        fi
    done

    if [ "$all_healthy" = true ]; then
        log_success "所有服务运行正常"
    else
        log_warning "部分服务未正常启动，请检查日志"
    fi
}

# 主函数
main() {
    local backup_path=$1

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  监控系统恢复"
    echo "  $(date '+%Y-%m-%d %H:%M:%S')"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # 检查是否在正确的目录
    if [ ! -f "docker-compose.yaml" ]; then
        log_error "请在项目根目录运行此脚本"
        exit 1
    fi

    # 检查备份目录
    check_backup_dir "$backup_path"

    # 显示备份信息
    show_backup_info "$backup_path"

    # 确认恢复
    confirm_restore

    echo ""

    # 执行恢复
    stop_services
    echo ""
    restore_victoriametrics "$backup_path"
    restore_grafana "$backup_path"
    restore_alertmanager "$backup_path"
    restore_configs "$backup_path"
    echo ""
    start_services
    echo ""
    verify_restore

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_success "恢复完成！"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "访问地址:"
    echo "  Grafana: http://localhost:3000"
    echo "  VictoriaMetrics: http://localhost:8428"
    echo ""
    echo "建议运行健康检查:"
    echo "  ./scripts/health-check.sh"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

# 执行主函数
main "$@"
