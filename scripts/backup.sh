#!/bin/bash

#################################################
# 监控系统备份脚本
# 用途: 备份 VictoriaMetrics 数据和 Grafana 配置
#################################################

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 默认配置
BACKUP_DIR="${BACKUP_DIR:-./backup}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 创建备份目录
create_backup_dir() {
    local backup_path="$BACKUP_DIR/$TIMESTAMP"
    mkdir -p "$backup_path"
    echo "$backup_path"
}

# 备份 VictoriaMetrics 数据
backup_victoriametrics() {
    log_info "备份 VictoriaMetrics 数据..."

    local backup_path=$1
    local vm_backup="$backup_path/victoriametrics-data.tar.gz"

    # 创建快照
    log_info "创建 VictoriaMetrics 快照..."
    curl -s http://localhost:8428/snapshot/create >/dev/null

    # 备份数据
    docker run --rm \
        -v monitoring-deployment_vmdata:/source:ro \
        -v "$backup_path:/backup" \
        alpine tar czf "/backup/victoriametrics-data.tar.gz" -C /source .

    local size=$(du -sh "$vm_backup" | awk '{print $1}')
    log_success "VictoriaMetrics 数据备份完成 (大小: $size)"
}

# 备份 Grafana 数据
backup_grafana() {
    log_info "备份 Grafana 数据..."

    local backup_path=$1
    local grafana_backup="$backup_path/grafana-data.tar.gz"

    docker run --rm \
        -v monitoring-deployment_grafana-data:/source:ro \
        -v "$backup_path:/backup" \
        alpine tar czf "/backup/grafana-data.tar.gz" -C /source .

    local size=$(du -sh "$grafana_backup" | awk '{print $1}')
    log_success "Grafana 数据备份完成 (大小: $size)"
}

# 备份 Alertmanager 数据
backup_alertmanager() {
    log_info "备份 Alertmanager 数据..."

    local backup_path=$1
    local am_backup="$backup_path/alertmanager-data.tar.gz"

    docker run --rm \
        -v monitoring-deployment_alertmanager-data:/source:ro \
        -v "$backup_path:/backup" \
        alpine tar czf "/backup/alertmanager-data.tar.gz" -C /source .

    local size=$(du -sh "$am_backup" | awk '{print $1}')
    log_success "Alertmanager 数据备份完成 (大小: $size)"
}

# 备份配置文件
backup_configs() {
    log_info "备份配置文件..."

    local backup_path=$1
    local config_backup="$backup_path/configs.tar.gz"

    tar czf "$config_backup" \
        config/ \
        docker-compose.yaml \
        .env 2>/dev/null || tar czf "$config_backup" config/ docker-compose.yaml

    local size=$(du -sh "$config_backup" | awk '{print $1}')
    log_success "配置文件备份完成 (大小: $size)"
}

# 创建备份清单
create_manifest() {
    local backup_path=$1
    local manifest="$backup_path/backup-manifest.txt"

    cat > "$manifest" <<EOF
备份时间: $(date '+%Y-%m-%d %H:%M:%S')
备份目录: $backup_path
主机名: $(hostname)
系统信息: $(uname -a)

备份内容:
EOF

    ls -lh "$backup_path" | tail -n +2 >> "$manifest"

    log_success "备份清单已创建: $manifest"
}

# 清理旧备份
cleanup_old_backups() {
    log_info "清理超过 $RETENTION_DAYS 天的旧备份..."

    local deleted_count=0
    while IFS= read -r -d '' backup_dir; do
        rm -rf "$backup_dir"
        deleted_count=$((deleted_count + 1))
    done < <(find "$BACKUP_DIR" -maxdepth 1 -type d -mtime +$RETENTION_DAYS -print0)

    if [ $deleted_count -gt 0 ]; then
        log_success "已删除 $deleted_count 个旧备份"
    else
        log_info "没有需要清理的旧备份"
    fi
}

# 显示备份信息
show_backup_info() {
    local backup_path=$1

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_success "备份完成！"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "备份位置: $backup_path"
    echo ""
    echo "备份文件:"
    ls -lh "$backup_path" | tail -n +2 | awk '{print "  " $9 " - " $5}'
    echo ""
    echo "恢复命令:"
    echo "  ./scripts/restore.sh $backup_path"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

# 主函数
main() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  监控系统备份"
    echo "  $(date '+%Y-%m-%d %H:%M:%S')"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    # 检查是否在正确的目录
    if [ ! -f "docker-compose.yaml" ]; then
        log_error "请在项目根目录运行此脚本"
        exit 1
    fi

    # 创建备份目录
    local backup_path=$(create_backup_dir)
    log_info "备份目录: $backup_path"
    echo ""

    # 执行备份
    backup_victoriametrics "$backup_path"
    backup_grafana "$backup_path"
    backup_alertmanager "$backup_path"
    backup_configs "$backup_path"
    create_manifest "$backup_path"

    # 清理旧备份
    echo ""
    cleanup_old_backups

    # 显示备份信息
    show_backup_info "$backup_path"
}

# 执行主函数
main "$@"
