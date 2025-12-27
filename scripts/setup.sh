#!/bin/bash

#################################################
# VictoriaMetrics 监控系统快速部署脚本
# 作者: Claude Code
# 用途: 自动化部署和初始配置
#################################################

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 检查前置条件
check_prerequisites() {
    log_info "检查系统前置条件..."

    # 检查 Docker
    if ! command_exists docker; then
        log_error "Docker 未安装，请先安装 Docker"
        log_info "安装命令: curl -fsSL https://get.docker.com | sh"
        exit 1
    fi
    log_success "Docker 已安装: $(docker --version)"

    # 检查 Docker Compose
    if ! command_exists docker-compose && ! docker compose version >/dev/null 2>&1; then
        log_error "Docker Compose 未安装"
        exit 1
    fi
    log_success "Docker Compose 已安装"

    # 检查磁盘空间
    available_space=$(df -BG . | tail -1 | awk '{print $4}' | sed 's/G//')
    if [ "$available_space" -lt 20 ]; then
        log_warning "可用磁盘空间少于 20GB，当前为 ${available_space}GB"
        read -p "是否继续? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    log_success "磁盘空间充足: ${available_space}GB 可用"

    # 检查内存
    total_mem=$(free -g | grep Mem | awk '{print $2}')
    if [ "$total_mem" -lt 4 ]; then
        log_warning "系统内存少于 4GB，当前为 ${total_mem}GB"
    fi
    log_success "系统内存: ${total_mem}GB"
}

# 初始化配置
initialize_config() {
    log_info "初始化配置文件..."

    # 检查 .env 文件
    if [ ! -f .env ]; then
        log_info "创建 .env 配置文件..."
        cp .env.example .env
        log_warning ".env 文件已创建，请编辑配置后重新运行"

        # 提示用户配置
        echo ""
        echo "请配置以下必要参数:"
        echo "1. GRAFANA_ADMIN_PASSWORD - Grafana 管理员密码"
        echo "2. VSPHERE_HOST - VMware vCenter 地址"
        echo "3. VSPHERE_USER - VMware 用户名"
        echo "4. VSPHERE_PASSWORD - VMware 密码"
        echo ""
        read -p "是否现在编辑配置文件? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            ${EDITOR:-vi} .env
        else
            log_warning "请手动编辑 .env 文件后运行: $0"
            exit 0
        fi
    fi
    log_success ".env 配置文件已存在"
}

# 下载 SNMP Exporter 配置
download_snmp_config() {
    log_info "检查 SNMP Exporter 配置..."

    if [ ! -f config/snmp-exporter/snmp.yml ] || [ $(wc -l < config/snmp-exporter/snmp.yml) -lt 100 ]; then
        log_info "下载官方 SNMP Exporter 配置文件..."

        if command_exists wget; then
            wget -q -O config/snmp-exporter/snmp.yml \
                https://github.com/prometheus/snmp_exporter/releases/latest/download/snmp.yml
            log_success "SNMP 配置文件下载完成"
        elif command_exists curl; then
            curl -sL -o config/snmp-exporter/snmp.yml \
                https://github.com/prometheus/snmp_exporter/releases/latest/download/snmp.yml
            log_success "SNMP 配置文件下载完成"
        else
            log_warning "wget 和 curl 都未安装，跳过 SNMP 配置下载"
            log_info "请手动下载: https://github.com/prometheus/snmp_exporter/releases/latest/download/snmp.yml"
        fi
    else
        log_success "SNMP 配置文件已存在"
    fi
}

# 创建必要的目录
create_directories() {
    log_info "创建必要的目录..."
    mkdir -p backup
    mkdir -p logs
    log_success "目录创建完成"
}

# 验证配置文件
validate_config() {
    log_info "验证配置文件..."

    # 验证 docker-compose.yaml
    if docker-compose config >/dev/null 2>&1 || docker compose config >/dev/null 2>&1; then
        log_success "Docker Compose 配置验证通过"
    else
        log_error "Docker Compose 配置验证失败"
        exit 1
    fi
}

# 拉取 Docker 镜像
pull_images() {
    log_info "拉取 Docker 镜像..."

    if docker-compose pull 2>/dev/null || docker compose pull 2>/dev/null; then
        log_success "镜像拉取完成"
    else
        log_error "镜像拉取失败"
        exit 1
    fi
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

# 等待服务就绪
wait_for_services() {
    log_info "等待服务启动..."
    sleep 10

    # 检查服务状态
    local failed_services=0

    for service in victoriametrics vmagent vmalert alertmanager grafana; do
        if docker-compose ps | grep -q "$service.*Up" 2>/dev/null || \
           docker compose ps | grep -q "$service.*running" 2>/dev/null; then
            log_success "$service 运行正常"
        else
            log_error "$service 启动失败"
            failed_services=$((failed_services + 1))
        fi
    done

    if [ $failed_services -gt 0 ]; then
        log_error "有 $failed_services 个服务启动失败，请检查日志"
        return 1
    fi
}

# 显示访问信息
show_access_info() {
    local host_ip=$(hostname -I | awk '{print $1}')

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_success "监控系统部署完成！"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "访问地址:"
    echo "  Grafana:          http://${host_ip}:3000"
    echo "                    默认账号: admin / admin"
    echo ""
    echo "  VictoriaMetrics:  http://${host_ip}:8428"
    echo "  vmalert:          http://${host_ip}:8880"
    echo "  Alertmanager:     http://${host_ip}:9093"
    echo ""
    echo "下一步操作:"
    echo "  1. 访问 Grafana 导入仪表板 (推荐 ID: 1860, 11243, 11169)"
    echo "  2. 编辑 config/vmagent/prometheus.yml 添加监控目标"
    echo "  3. 编辑 config/alertmanager/alertmanager.yml 配置告警通知"
    echo "  4. 重启服务使配置生效: docker-compose restart"
    echo ""
    echo "常用命令:"
    echo "  查看日志:    docker-compose logs -f"
    echo "  重启服务:    docker-compose restart"
    echo "  停止服务:    docker-compose down"
    echo "  健康检查:    ./scripts/health-check.sh"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

# 主函数
main() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  VictoriaMetrics 监控系统 - 快速部署脚本"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    check_prerequisites
    initialize_config
    download_snmp_config
    create_directories
    validate_config
    pull_images
    start_services

    if wait_for_services; then
        show_access_info
    else
        log_error "部署过程中出现错误，请检查日志"
        log_info "查看日志: docker-compose logs"
        exit 1
    fi
}

# 执行主函数
main "$@"
