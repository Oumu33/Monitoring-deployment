#!/bin/bash
# ===================================================================
# gNMI 设备支持检测脚本
# 用途: 测试网络设备是否支持 gNMI 以及支持的 YANG 模型
# ===================================================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 帮助信息
show_help() {
    cat << EOF
用法: $0 [选项]

检测网络设备是否支持 gNMI 协议

选项:
    -h, --host      设备 IP 地址（必需）
    -p, --port      gNMI 端口（默认: 57400）
    -u, --user      用户名（必需）
    -P, --password  密码（必需）
    --help          显示此帮助信息

厂商默认端口:
    Cisco IOS-XR:  57400
    Juniper Junos: 32767
    Arista EOS:    6030
    Huawei:        50051

示例:
    $0 -h 192.168.1.100 -p 57400 -u admin -P password

EOF
}

# 解析参数
HOST=""
PORT="57400"
USER=""
PASSWORD=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--host)
            HOST="$2"
            shift 2
            ;;
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -u|--user)
            USER="$2"
            shift 2
            ;;
        -P|--password)
            PASSWORD="$2"
            shift 2
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            print_error "未知参数: $1"
            show_help
            exit 1
            ;;
    esac
done

# 检查必需参数
if [[ -z "$HOST" || -z "$USER" || -z "$PASSWORD" ]]; then
    print_error "缺少必需参数"
    show_help
    exit 1
fi

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    print_error "Docker 未安装，请先安装 Docker"
    exit 1
fi

print_info "开始检测设备: $HOST:$PORT"
echo ""

# ===== 测试 1: 网络连通性 =====
print_info "测试 1: 网络连通性"
if ping -c 3 -W 2 "$HOST" &> /dev/null; then
    print_success "设备 $HOST 可达"
else
    print_warning "设备 $HOST Ping 不通（可能禁用了 ICMP）"
fi
echo ""

# ===== 测试 2: gNMI 端口连通性 =====
print_info "测试 2: gNMI 端口 $PORT 连通性"
if timeout 5 bash -c "cat < /dev/null > /dev/tcp/$HOST/$PORT" 2>/dev/null; then
    print_success "端口 $PORT 开放"
else
    print_error "端口 $PORT 无法连接"
    print_info "请检查:"
    echo "  1. 设备是否启用了 gNMI"
    echo "  2. 防火墙规则"
    echo "  3. 端口号是否正确（Cisco: 57400, Juniper: 32767, Arista: 6030）"
    exit 1
fi
echo ""

# ===== 测试 3: gNMI Capabilities =====
print_info "测试 3: 获取 gNMI Capabilities（支持的 YANG 模型）"

GNMI_OUTPUT=$(docker run --rm ghcr.io/openconfig/gnmic:latest \
    -a "$HOST:$PORT" \
    -u "$USER" -p "$PASSWORD" \
    --insecure \
    capabilities 2>&1)

if [[ $? -eq 0 ]]; then
    print_success "gNMI 连接成功！"
    echo ""
    echo "$GNMI_OUTPUT" | grep -A 100 "gNMI version:" || echo "$GNMI_OUTPUT"
    echo ""

    # 检查是否支持 OpenConfig
    if echo "$GNMI_OUTPUT" | grep -q "openconfig"; then
        print_success "设备支持 OpenConfig 模型"
    else
        print_warning "设备可能不支持 OpenConfig 模型（仅支持厂商私有模型）"
    fi
else
    print_error "gNMI 连接失败"
    echo "$GNMI_OUTPUT"
    print_info "可能的原因:"
    echo "  1. 用户名或密码错误"
    echo "  2. 用户权限不足（需要 gNMI 权限）"
    echo "  3. TLS 证书问题"
    echo "  4. 设备不支持 gNMI"
    exit 1
fi
echo ""

# ===== 测试 4: 测试订阅（接口计数器）=====
print_info "测试 4: 测试 OpenConfig 接口计数器订阅"

SUBSCRIBE_OUTPUT=$(timeout 15 docker run --rm ghcr.io/openconfig/gnmic:latest \
    -a "$HOST:$PORT" \
    -u "$USER" -p "$PASSWORD" \
    --insecure \
    subscribe \
    --path "/interfaces/interface/state/counters" \
    --mode sample \
    --sample-interval 5s 2>&1 || true)

if echo "$SUBSCRIBE_OUTPUT" | grep -q "in-octets\|out-octets\|update"; then
    print_success "接口计数器订阅成功（接收到数据）"
    echo ""
    echo "示例数据（前 20 行）:"
    echo "$SUBSCRIBE_OUTPUT" | head -20
else
    print_warning "接口计数器订阅可能不支持"
    echo "$SUBSCRIBE_OUTPUT" | head -10
fi
echo ""

# ===== 测试总结 =====
echo "========================================"
print_info "检测完成！"
echo "========================================"
echo ""
print_info "设备信息:"
echo "  - IP: $HOST"
echo "  - 端口: $PORT"
echo ""

print_info "下一步:"
echo "  1. 编辑配置文件: config/telegraf-gnmi/telegraf-gnmi.conf"
echo "  2. 添加设备地址: addresses = [\"$HOST:$PORT\"]"
echo "  3. 配置认证信息: config/telegraf-gnmi/.env.gnmi"
echo "  4. 启动 gNMI 监控: docker-compose up -d telegraf-gnmi"
echo ""
