# gNMI 网络设备监控配置指南

## 目录
- [什么是 gNMI？](#什么是-gnmi)
- [为什么使用 gNMI？](#为什么使用-gnmi)
- [快速开始](#快速开始)
- [设备支持情况](#设备支持情况)
- [配置详解](#配置详解)
- [监控架构](#监控架构)
- [故障排查](#故障排查)

---

## 什么是 gNMI？

**gNMI (gRPC Network Management Interface)** 是新一代网络设备管理协议，基于 **gRPC** 和 **Protocol Buffers** 构建。

### 技术栈

```
┌─────────────────────────────────────────────┐
│       gNMI 流式遥测技术栈                     │
├─────────────────────────────────────────────┤
│                                              │
│  YANG        → 数据建模（定义数据结构）        │
│  ↓                                           │
│  gNMI        → 传输协议（gRPC + Protobuf）    │
│  ↓                                           │
│  Streaming   → 推送模式（设备主动推送）        │
│  ↓                                           │
│  Telegraf    → 数据采集                       │
│  ↓                                           │
│  VictoriaMetrics → 存储和分析                │
└─────────────────────────────────────────────┘
```

### 核心概念

1. **YANG（Yet Another Next Generation）**
   - 网络设备数据建模语言
   - 标准化设备配置和状态
   - 类似 API 的 Schema

2. **gNMI**
   - 基于 HTTP/2 的 gRPC 协议
   - 高效的二进制编码（Protocol Buffers）
   - 支持双向流式传输

3. **Streaming Telemetry（流式遥测）**
   - 设备主动推送数据（vs SNMP 的轮询）
   - 实时性强（秒级甚至毫秒级）
   - 网络开销低

---

## 为什么使用 gNMI？

### SNMP vs gNMI 对比

| 特性 | SNMP（传统） | gNMI（现代） |
|------|-------------|-------------|
| **发布年份** | 1988 | 2016 |
| **协议** | UDP（不可靠） | HTTP/2 + gRPC（可靠） |
| **数据格式** | ASN.1/BER | Protocol Buffers |
| **数据模型** | MIB（厂商各异） | YANG（标准化） |
| **采集方式** | **轮询（Poll）** | **订阅（Subscribe）** |
| **实时性** | ⚠️ 30-60秒 | ✅ 秒级/毫秒级 |
| **网络开销** | ⚠️ 高 | ✅ 低 |
| **安全性** | ⚠️ 弱（明文） | ✅ 强（TLS） |
| **扩展性** | ⚠️ 差 | ✅ 好 |
| **设备支持** | ✅ 所有 | ⚠️ 新设备 |

### 关键优势

#### 1. **推送 vs 轮询**

**SNMP（轮询）**:
```
采集器: "现在流量多少？"
设备: "100 Mbps"
[等待 30 秒]
采集器: "现在流量多少？"
设备: "150 Mbps"

问题:
- 高频轮询产生大量查询
- 数据不实时（30秒延迟）
- 突发事件可能错过
```

**gNMI（推送）**:
```
采集器: "订阅接口流量，每 5 秒推送一次"
设备: [自动每 5 秒推送数据]
  → 100 Mbps
  → 105 Mbps
  → 110 Mbps

优势:
- 实时数据流
- 减少网络开销
- 立即感知变化
```

#### 2. **标准化数据模型（OpenConfig）**

**SNMP MIB**（厂商各异）:
```
Cisco: .1.3.6.1.2.1.2.2.1.10
Huawei: .1.3.6.1.4.1.2011.5.25.xxx
Arista: .1.3.6.1.4.1.30065.xxx

→ 每个厂商不同，需要单独配置
```

**OpenConfig YANG**（统一标准）:
```
/interfaces/interface[name=GigabitEthernet0/0/0]/state/counters/in-octets

→ 所有厂商统一路径，一次配置
```

#### 3. **高性能**

- **Protocol Buffers** 比 JSON 小 3-10 倍
- **二进制编码**比文本解析快 5-20 倍
- **HTTP/2 多路复用**减少连接开销

---

## 快速开始

### 前置要求

1. **网络设备支持 gNMI**
   - Cisco IOS-XR、NX-OS（2018+）
   - Arista EOS
   - Juniper Junos
   - Huawei CloudEngine（新款）

2. **启用 gNMI 服务**（设备端配置）

### 步骤 1: 检测设备支持

使用自动检测脚本：

```bash
cd /opt/Monitoring
./scripts/test-gnmi-device.sh \
  -h 192.168.1.100 \
  -p 57400 \
  -u admin \
  -P password
```

**输出示例**:
```
[SUCCESS] 设备 192.168.1.100 可达
[SUCCESS] 端口 57400 开放
[SUCCESS] gNMI 连接成功！
[SUCCESS] 设备支持 OpenConfig 模型
```

### 步骤 2: 配置认证信息

```bash
cd config/telegraf-gnmi
cp .env.gnmi.example .env.gnmi
vim .env.gnmi
```

编辑 `.env.gnmi`:
```bash
GNMI_USERNAME=admin
GNMI_PASSWORD=your-password
```

### 步骤 3: 配置监控目标

编辑 `config/telegraf-gnmi/telegraf-gnmi.conf`:

```toml
[[inputs.gnmi]]
  addresses = ["192.168.1.100:57400"]  # 修改为你的设备 IP
  username = "${GNMI_USERNAME}"
  password = "${GNMI_PASSWORD}"

  enable_tls = true
  insecure_skip_verify = true
  encoding = "proto"
  redial = "20s"

  [inputs.gnmi.tags]
    device_type = "router"
    vendor = "cisco"
    location = "dc1"

  # 接口流量统计
  [[inputs.gnmi.subscription]]
    name = "interface_counters"
    origin = "openconfig"
    path = "/interfaces/interface/state/counters"
    subscription_mode = "sample"
    sample_interval = "10s"

  # CPU 使用率
  [[inputs.gnmi.subscription]]
    name = "cpu"
    origin = "openconfig"
    path = "/components/component/cpu/utilization/state"
    subscription_mode = "sample"
    sample_interval = "5s"
```

### 步骤 4: 启动服务

```bash
docker-compose up -d telegraf-gnmi

# 查看日志
docker-compose logs -f telegraf-gnmi
```

### 步骤 5: 验证数据

```bash
# 查询 VictoriaMetrics
curl 'http://localhost:8428/api/v1/query?query=gnmi_interface_counters'
```

---

## 设备支持情况

### Cisco

| 设备系列 | 操作系统 | gNMI 端口 | 最低版本 | OpenConfig 支持 |
|---------|---------|----------|---------|----------------|
| ASR 9000 | IOS-XR | 57400 | 6.5.1+ | ✅ |
| NCS 5500/8000 | IOS-XR | 57400 | 6.6.2+ | ✅ |
| Nexus 9000 | NX-OS | 50051 | 9.3(3)+ | ✅ |
| Catalyst 9000 | IOS-XE | 9339 | 17.3+ | ✅ |

**启用 gNMI（IOS-XR）**:
```
grpc
 port 57400
 tls-trustpoint GNMI
!
telemetry model-driven
 destination-group DGroup1
  address-family ipv4 192.168.1.1 port 5432
```

### Arista

| 设备系列 | 操作系统 | gNMI 端口 | 最低版本 |
|---------|---------|----------|---------|
| 所有系列 | EOS | 6030 | 4.23+ |

**启用 gNMI（EOS）**:
```
management api gnmi
   transport grpc default
```

### Juniper

| 设备系列 | 操作系统 | gNMI 端口 | 最低版本 |
|---------|---------|----------|---------|
| MX/QFX/PTX | Junos | 32767 | 18.3R1+ |

**启用 gNMI（Junos）**:
```
set system services extension-service request-response grpc clear-text port 32767
```

### Huawei

| 设备系列 | 操作系统 | gNMI 端口 | 最低版本 |
|---------|---------|----------|---------|
| CloudEngine | VRP | 50051 | V200R019+ |

---

## 配置详解

### 订阅模式

gNMI 支持三种订阅模式：

#### 1. SAMPLE（采样模式）

按固定时间间隔推送数据：

```toml
[[inputs.gnmi.subscription]]
  name = "interface_counters"
  subscription_mode = "sample"
  sample_interval = "10s"  # 每 10 秒推送一次
```

**适用场景**:
- 流量统计
- CPU/内存使用率
- 温度监控

#### 2. ON_CHANGE（变化推送）

数据变化时立即推送：

```toml
[[inputs.gnmi.subscription]]
  name = "interface_state"
  path = "/interfaces/interface/state/oper-status"
  subscription_mode = "on_change"  # 状态变化时推送
```

**适用场景**:
- 接口 UP/DOWN 状态
- BGP 邻居变化
- 告警事件

#### 3. TARGET_DEFINED（设备自定义）

由设备决定推送频率（不推荐）。

### 常用 YANG 路径

#### 接口监控

```toml
# 接口流量统计
path = "/interfaces/interface/state/counters"
  → in-octets, out-octets, in-packets, out-packets

# 接口状态
path = "/interfaces/interface/state/oper-status"
  → UP, DOWN

# 接口错误
path = "/interfaces/interface/state/counters"
  → in-errors, out-errors, in-discards, out-discards
```

#### 系统资源

```toml
# CPU 使用率
path = "/components/component/cpu/utilization/state"

# 内存使用
path = "/components/component/state/memory"

# 温度
path = "/components/component/state/temperature"
```

#### 路由协议

```toml
# BGP 邻居
path = "/network-instances/network-instance/protocols/protocol/bgp/neighbors"

# OSPF
path = "/network-instances/network-instance/protocols/protocol/ospf"
```

---

## 监控架构

### 混合架构（SNMP + gNMI）

```
┌───────────────────────────────────────────────────┐
│            监控架构（推荐）                         │
├───────────────────────────────────────────────────┤
│                                                    │
│  老设备 (SNMP)                                     │
│   ├─ Cisco 2960 ──┐                               │
│   ├─ HP 5120 ─────┼──> SNMP Exporter ──┐         │
│   └─ 其他老设备 ───┘                     │         │
│                                          v         │
│  新设备 (gNMI)                        vmagent      │
│   ├─ Cisco ASR ───┐                     │         │
│   ├─ Arista 7280 ─┼──> Telegraf gNMI ──┘         │
│   └─ Juniper MX ──┘                     │         │
│                                          v         │
│                                  VictoriaMetrics   │
│                                          │         │
│                                          v         │
│                                       Grafana      │
└───────────────────────────────────────────────────┘
```

### 数据流

```
网络设备 (gNMI Server)
    ↓ [gRPC Stream]
Telegraf gNMI Plugin
    ↓ [Prometheus Remote Write]
VictoriaMetrics
    ↓ [Prometheus Query]
Grafana / vmalert
```

---

## 性能优化

### 1. 合理设置采样间隔

```toml
# 高频监控（关键接口）
sample_interval = "5s"

# 中频监控（一般流量）
sample_interval = "10s"

# 低频监控（状态信息）
sample_interval = "60s"
# 或使用 on_change 模式
```

### 2. 使用 on_change 模式

```toml
# 对于状态类数据，使用 on_change
[[inputs.gnmi.subscription]]
  name = "bgp_neighbors"
  path = "/network-instances/network-instance/protocols/protocol/bgp"
  subscription_mode = "on_change"  # 只在变化时推送
```

### 3. 路径优化

```toml
# ✅ 好：具体路径
path = "/interfaces/interface/state/counters"

# ⚠️ 避免：根路径（数据量太大）
path = "/"

# ⚠️ 避免：过于宽泛的通配符
path = "/interfaces/*"
```

### 4. 使用 Protocol Buffers

```toml
# ✅ 推荐：高效的二进制编码
encoding = "proto"

# ⚠️ 仅调试用：JSON 编码（效率低）
encoding = "json"
```

---

## 故障排查

### 问题 1: 连接失败

**症状**: `connection refused` 或 `timeout`

```bash
# 1. 检查网络连通性
ping 192.168.1.100

# 2. 检查端口
nc -zv 192.168.1.100 57400

# 3. 验证设备配置
# Cisco IOS-XR:
show grpc status

# Arista EOS:
show management api gnmi
```

### 问题 2: 认证失败

**症状**: `authentication failed`

**解决方案**:
- 检查用户名密码
- 确认用户有 gNMI 权限
- 检查 TLS 配置

```toml
# 尝试禁用 TLS（调试用）
enable_tls = false

# 或跳过证书验证
insecure_skip_verify = true
```

### 问题 3: 无数据返回

**症状**: 连接成功但没有数据

```bash
# 1. 测试路径是否支持
docker run --rm ghcr.io/openconfig/gnmic:latest \
  -a 192.168.1.100:57400 \
  -u admin -p password \
  --insecure \
  get --path "/interfaces/interface/state/counters"

# 2. 查看设备支持的模型
docker run --rm ghcr.io/openconfig/gnmic:latest \
  -a 192.168.1.100:57400 \
  -u admin -p password \
  --insecure \
  capabilities
```

**常见原因**:
- YANG 路径不正确
- 设备不支持该路径
- Origin 设置错误（尝试改为厂商私有）

### 问题 4: 性能问题

**症状**: CPU 占用高、数据延迟

**优化方案**:
```toml
# 1. 减少订阅路径
# 只订阅需要的数据

# 2. 增加采样间隔
sample_interval = "30s"  # 从 10s 改为 30s

# 3. 使用 proto 编码
encoding = "proto"

# 4. 调整批量发送
[agent]
  flush_interval = "30s"
```

---

## Grafana 仪表板

### 推荐的 Dashboard

1. **网络接口监控**
   - 入/出流量
   - 错误率
   - 丢包率

2. **设备资源监控**
   - CPU 使用率
   - 内存使用率
   - 温度

3. **协议状态监控**
   - BGP 邻居状态
   - OSPF 邻接关系

### 查询示例

```promql
# 接口入流量（bps）
rate(gnmi_interfaces_interface_state_counters_in_octets[5m]) * 8

# 接口出流量（bps）
rate(gnmi_interfaces_interface_state_counters_out_octets[5m]) * 8

# CPU 使用率
gnmi_components_component_cpu_utilization_state_instant

# 接口错误率
rate(gnmi_interfaces_interface_state_counters_in_errors[5m])
```

---

## 最佳实践

### 1. 逐步迁移

```
阶段 1: 评估
  ├─ 检测设备支持情况
  └─ 选择试点设备

阶段 2: 试点
  ├─ 配置 1-2 台核心设备
  ├─ 验证数据准确性
  └─ 调优性能

阶段 3: 推广
  ├─ 新设备优先使用 gNMI
  ├─ 老设备继续用 SNMP
  └─ SNMP + gNMI 混合架构
```

### 2. 安全配置

```toml
# ✅ 使用环境变量管理密码
username = "${GNMI_USERNAME}"
password = "${GNMI_PASSWORD}"

# ✅ 启用 TLS
enable_tls = true

# ⚠️ 生产环境配置证书
# insecure_skip_verify = false
# tls_ca = "/path/to/ca.pem"
```

### 3. 监控标签规范

```toml
[inputs.gnmi.tags]
  device_type = "router"      # router/switch
  vendor = "cisco"            # cisco/arista/juniper
  model = "asr9k"
  location = "dc1"
  tier = "core"               # core/aggregation/access
  priority = "P0"             # P0/P1/P2
```

---

## 参考资料

- [gNMI 官方规范](https://github.com/openconfig/gnmi)
- [OpenConfig 标准](https://www.openconfig.net/)
- [Telegraf gNMI 插件文档](https://github.com/influxdata/telegraf/tree/master/plugins/inputs/gnmi)
- [gnmic 工具](https://gnmic.openconfig.net/)
- [OpenConfig 路径浏览器](https://openconfig.net/projects/models/)

---

## 下一步

- [ ] 检测设备 gNMI 支持情况
- [ ] 配置认证信息
- [ ] 启动 telegraf-gnmi 服务
- [ ] 导入 Grafana 仪表板
- [ ] 配置告警规则

需要帮助？请参考 [FAQ](FAQ.md) 或提交 Issue。
