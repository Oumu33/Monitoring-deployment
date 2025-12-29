# 监控系统部署方案

基于 VictoriaMetrics 的企业级监控系统，涵盖基础设施、虚拟化、网络设备和服务可用性全方位监控。

## 系统架构

```
┌──────────────────────────────────────────────────────────────────┐
│                         监控数据流                                 │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Node Exporter ────┐                                              │
│  SNMP Exporter ────┼──> vmagent ──┐                              │
│  Blackbox Exporter ┘               │                              │
│                                    v                              │
│  Telegraf (VMware) ───────> VictoriaMetrics                      │
│                                    │                              │
│                                    v                              │
│                               vmalert ──> Alertmanager            │
│                                    │                              │
│                                    v                              │
│                                 Grafana                           │
└──────────────────────────────────────────────────────────────────┘
```

## 组件说明

### 核心组件
- **VictoriaMetrics**: 高性能时序数据库，存储所有监控指标
- **vmagent**: 指标采集代理，负责从各个 exporter 收集数据
- **vmalert**: 告警规则引擎，评估告警规则并触发告警
- **Alertmanager**: 告警管理和通知分发
- **Grafana**: 数据可视化平台

### 数据采集组件
- **Node Exporter**: Linux 主机指标采集（CPU、内存、磁盘、网络）
- **Telegraf**: VMware vSphere 环境监控（单实例支持多 vCenter）
- **SNMP Exporter**: 网络设备监控（交换机、路由器 - 传统）
- **Telegraf gNMI**: 网络设备监控（支持 gNMI 的新设备 - 流式遥测）
- **Blackbox Exporter**: 服务可用性探测（HTTP、ICMP、TCP、DNS）
- **Redfish Exporter**: 服务器硬件监控（Dell iDRAC、HPE iLO 等）
- **IPMI Exporter**: 老服务器硬件监控（兜底方案）

## 监控覆盖

| 监控类型 | 覆盖内容 | 采集组件 |
|---------|---------|---------|
| 🖥️ 主机监控 | CPU、内存、磁盘、网络、进程 | Node Exporter |
| ☁️ 虚拟化监控 | VM、ESXi、数据存储、集群 | Telegraf |
| 🌐 网络监控（传统）| 交换机、路由器、端口、流量 | SNMP Exporter |
| 🌐 网络监控（现代）| 交换机、路由器、实时遥测 | Telegraf gNMI |
| 🔍 服务监控 | 网站可用性、API健康、SSL证书 | Blackbox Exporter |
| 📡 连通性监控 | Ping、端口探测、响应时间 | Blackbox Exporter |
| 🔧 硬件监控 | 温度、风扇、电源、RAID、硬盘健康 | Redfish + IPMI Exporter |
| 📝 日志监控 | 系统日志、网络设备日志、应用日志 | Loki + Promtail + Syslog-NG |
| 🗺️ 拓扑发现 | LLDP 自动拓扑、网络层级、设备关系 | Topology Discovery (自动化) |

## 前置要求

- Docker 20.10+
- Docker Compose 2.0+
- 至少 4GB 可用内存
- 至少 20GB 可用磁盘空间

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/Oumu33/Monitoring-deployment.git
cd Monitoring-deployment
```

### 2. 配置环境变量

```bash
cp .env.example .env
vim .env
```

编辑 `.env` 文件,配置以下必要参数:

```bash
# Grafana 管理员账号
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=your-secure-password
```

### 3. 配置 VMware vCenter 连接

编辑 `config/telegraf/telegraf.conf`,修改 vCenter 连接信息:

```toml
[[inputs.vsphere]]
  vcenters = ["https://vcenter.example.com/sdk"]
  username = "monitoring@vsphere.local"
  password = "your-vcenter-password"
  insecure_skip_verify = true

  [inputs.vsphere.tags]
    datacenter = "dc1"
    env = "production"
```

**添加多个 vCenter**: 复制 `[[inputs.vsphere]]` 配置块即可。

### 4. 下载 SNMP Exporter 配置文件(推荐)

```bash
cd config/snmp-exporter
wget https://github.com/prometheus/snmp_exporter/releases/latest/download/snmp.yml
cd ../..
```

### 5. 配置监控目标

编辑 `config/vmagent/prometheus.yml`,添加你的监控目标:

```yaml
# 添加 Linux 主机
- job_name: 'node-exporter'
  static_configs:
    - targets: ['192.168.1.10:9100']
      labels:
        instance: 'web-server-01'

# 添加 SNMP 设备（交换机、路由器）
- job_name: 'snmp-exporter'
  static_configs:
    - targets:
      - 192.168.1.100  # 交换机 IP
      - 192.168.1.101  # 路由器 IP

# 添加服务可用性探测（Blackbox）
# HTTP/HTTPS 网站监控
- job_name: 'blackbox-http'
  static_configs:
    - targets:
      - https://www.company.com
      - http://internal-app.local

# ICMP Ping 探测
- job_name: 'blackbox-icmp'
  static_configs:
    - targets:
      - 192.168.1.100  # 交换机
      - 192.168.1.1    # 网关
```

### 6. 配置告警通知

编辑 `config/alertmanager/alertmanager.yml`,配置邮件通知:

```yaml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@example.com'
  smtp_auth_username: 'alerts@example.com'
  smtp_auth_password: 'your-app-password'
```

### 7. 启动服务

```bash
docker-compose up -d
```

### 8. 验证服务状态

```bash
docker-compose ps
```

所有服务应该处于 `Up` 状态。

## 访问地址

- **Grafana**: http://localhost:3000 (默认账号: admin/admin)
- **Loki**: http://localhost:3100
- **VictoriaMetrics**: http://localhost:8428
- **vmalert**: http://localhost:8880
- **Alertmanager**: http://localhost:9093
- **Node Exporter**: http://localhost:9100/metrics
- **SNMP Exporter**: http://localhost:9116/metrics
- **Blackbox Exporter**: http://localhost:9115/metrics
- **Redfish Exporter**: http://localhost:9610/metrics
- **IPMI Exporter**: http://localhost:9290/metrics

## 监控目标配置

### Linux 主机监控

在需要监控的 Linux 主机上安装 Node Exporter:

```bash
# 使用 Docker
docker run -d \
  --name=node-exporter \
  --net="host" \
  --pid="host" \
  -v "/:/host:ro,rslave" \
  prom/node-exporter:latest \
  --path.rootfs=/host
```

或者使用系统服务安装,参考: https://github.com/prometheus/node_exporter

### VMware 监控配置

1. 在 vCenter 中创建只读监控账号
2. 编辑 `config/telegraf/telegraf.conf`,配置 vCenter 连接信息
3. Telegraf 会自动发现并监控所有 ESXi 主机和虚拟机

**监控多个 vCenter**:
在配置文件中添加多个 `[[inputs.vsphere]]` 块即可：

```toml
# vCenter 1
[[inputs.vsphere]]
  vcenters = ["https://vcenter-dc1.example.com/sdk"]
  username = "monitoring@vsphere.local"
  password = "password1"
  [inputs.vsphere.tags]
    datacenter = "dc1"

# vCenter 2
[[inputs.vsphere]]
  vcenters = ["https://vcenter-dc2.example.com/sdk"]
  username = "monitoring@vsphere.local"
  password = "password2"
  [inputs.vsphere.tags]
    datacenter = "dc2"
```

**多 vCenter 监控**:
- **优势**: 单实例监控多个 vCenter，资源节省 70%
- **详细指南**: [VMware 多集群监控方案对比](docs/VMWARE-SOLUTION-COMPARISON.md)

### SNMP 设备监控

1. 确保网络设备开启 SNMP(v2c 或 v3)
2. 在 `config/vmagent/prometheus.yml` 中添加设备 IP
3. 根据设备类型选择合适的 SNMP 模块

详细配置请参考: [config/snmp-exporter/README.md](config/snmp-exporter/README.md)

### 网络设备监控（gNMI - 流式遥测）

gNMI（gRPC Network Management Interface）是新一代网络设备监控协议，采用**流式推送**方式，相比 SNMP 具有更高的实时性和效率。

**适用设备**:
- Cisco IOS-XR、NX-OS（2018+）
- Arista EOS
- Juniper Junos
- Huawei CloudEngine（新款）

**核心优势**:
- ✅ **实时推送**: 秒级数据更新（vs SNMP 30-60秒轮询）
- ✅ **标准化**: OpenConfig YANG 模型统一所有厂商
- ✅ **高效**: Protocol Buffers 比 SNMP 编码效率高 3-10 倍
- ✅ **安全**: 基于 gRPC + TLS

**配置步骤**:

1. **检测设备支持**

```bash
./scripts/test-gnmi-device.sh \
  -h 192.168.1.100 \
  -p 57400 \
  -u admin \
  -P password
```

2. **配置认证信息**

```bash
cd config/telegraf-gnmi
cp .env.gnmi.example .env.gnmi
vim .env.gnmi  # 编辑用户名密码
```

3. **配置监控目标**

编辑 `config/telegraf-gnmi/telegraf-gnmi.conf`:

```toml
[[inputs.gnmi]]
  addresses = ["192.168.1.100:57400"]  # Cisco 设备
  username = "${GNMI_USERNAME}"
  password = "${GNMI_PASSWORD}"

  # 订阅接口流量
  [[inputs.gnmi.subscription]]
    name = "interface_counters"
    path = "/interfaces/interface/state/counters"
    subscription_mode = "sample"
    sample_interval = "10s"
```

4. **启动服务**

```bash
docker-compose up -d telegraf-gnmi
```

**监控能力**:
- ✅ 接口流量实时监控（秒级更新）
- ✅ 接口状态变化即时推送
- ✅ CPU/内存实时监控
- ✅ BGP/OSPF 协议状态
- ✅ 光模块温度和功率

**SNMP vs gNMI 对比**:

| 特性 | SNMP | gNMI |
|------|------|------|
| 采集方式 | 轮询（Poll） | 推送（Subscribe） |
| 实时性 | 30-60秒 | 秒级/毫秒级 |
| 数据模型 | MIB（厂商各异） | YANG（统一标准） |
| 网络开销 | 高 | 低 |
| 设备支持 | 所有设备 | 2018+ 新设备 |

**推荐策略**: **SNMP + gNMI 混合架构**
- 新设备使用 gNMI（高性能、实时）
- 老设备继续用 SNMP（兼容性）

详细配置请参考: [docs/GNMI-MONITORING.md](docs/GNMI-MONITORING.md)

### Blackbox 服务可用性监控

Blackbox Exporter 用于监控服务可用性和网络连通性。

**支持的探测类型**:
- **HTTP/HTTPS**: 网站可用性、API 健康检查
- **ICMP**: Ping 探测，检测设备是否在线
- **TCP**: 端口连通性检测（数据库、SSH 等）
- **DNS**: DNS 解析监控

**配置示例**:

```yaml
# 1. HTTP/HTTPS 网站监控
- job_name: 'blackbox-http'
  static_configs:
    - targets:
      - https://www.company.com    # 监控公司网站
      - http://oa.company.local    # 监控内部应用

# 2. ICMP Ping 探测
- job_name: 'blackbox-icmp'
  static_configs:
    - targets:
      - 192.168.1.100  # 交换机
      - 192.168.1.1    # 网关
      - 192.168.2.10   # ESXi 主机

# 3. TCP 端口探测
- job_name: 'blackbox-tcp'
  static_configs:
    - targets:
      - 192.168.3.10:3306   # MySQL
      - 192.168.4.10:22     # SSH
      - vcenter.local:443   # vCenter
```

**监控能力**:
- ✅ 网站是否可访问
- ✅ 响应时间监控
- ✅ SSL 证书过期检测
- ✅ 设备 Ping 连通性
- ✅ 网络延迟和丢包率
- ✅ 服务端口可用性

详细配置请参考: [examples/blackbox-monitoring-examples.yml](examples/blackbox-monitoring-examples.yml)

### 服务器硬件监控

使用 **Redfish + IPMI 双轨制**监控物理服务器硬件健康：

**监控方案**:
- **Redfish Exporter**: 统一监控支持 Redfish 的新服务器（推荐）
  - Dell iDRAC 9+
  - HPE iLO 4/5/6
  - Supermicro（新款）
  - Lenovo XClarity

- **IPMI Exporter**: 兜底监控老服务器
  - 不支持 Redfish 的旧设备
  - 2012 年之前的服务器

**配置步骤**:

1. **配置 Redfish 监控**（新服务器）

编辑 `config/redfish-exporter/redfish.yml`:

```yaml
hosts:
  dell-server-01:
    username: "root"
    password: "calvin"              # 修改为实际密码
    host_address: "192.168.1.100"   # iDRAC IP 地址
```

在 `config/vmagent/prometheus.yml` 中添加目标:

```yaml
- job_name: 'redfish-hardware'
  static_configs:
    - targets:
      - dell-server-01              # 对应 redfish.yml 中的主机名
```

2. **配置 IPMI 监控**（老服务器）

在 `config/vmagent/prometheus.yml` 中添加:

```yaml
- job_name: 'ipmi-hardware'
  static_configs:
    - targets: ['192.168.2.10']     # IPMI IP 地址
      labels:
        instance: 'old-server-01'
```

**监控能力**:
- ✅ CPU/主板温度监控
- ✅ 风扇转速和状态
- ✅ 电源状态（冗余电源）
- ✅ RAID 控制器健康
- ✅ 硬盘 SMART 数据
- ✅ 内存 ECC 错误
- ✅ 硬件事件日志

详细配置请参考: [docs/HARDWARE-MONITORING.md](docs/HARDWARE-MONITORING.md)

## 日志聚合和可观测性

本系统实现了完整的**基础设施可观测性**架构：**Metrics（指标）+ Logs（日志）+ Topology（拓扑）**，实现自动根因分析和智能告警。

### 架构特点

- ✅ **Metrics**: VictoriaMetrics 采集所有指标（CPU、网络、硬件等）
- ✅ **Logs**: Loki 聚合所有日志（系统日志、网络设备日志、应用日志）
- ✅ **拓扑依赖**: 通过标签（datacenter、network_segment、rack）建立关联
- ✅ **自动根因分析**: Alertmanager 智能抑制连锁告警，只发送根因告警
- ✅ **统一视图**: Grafana 关联展示 Metrics 和 Logs

### 日志采集

**1. 主机日志**（Promtail 采集）:
- 系统日志（Syslog）
- 认证日志（SSH 登录）
- Docker 容器日志
- Nginx 访问/错误日志
- 应用日志（JSON 格式）

**2. 网络设备日志**（Syslog-NG 接收）:
- Cisco、Arista、Juniper 等网络设备
- 交换机、路由器 Syslog
- 支持 UDP/TCP 514、6514 端口

### 配置步骤

**1. 启动日志服务**

```bash
docker-compose up -d loki promtail syslog-ng
```

**2. 配置网络设备发送 Syslog**

**Cisco**:
```
logging host 192.168.1.X
logging trap informational
```

**Arista**:
```
logging host 192.168.1.X
logging level informational
```

**3. 在 Grafana 中查询日志**

Loki 数据源已自动配置，使用 LogQL 查询：

```logql
# 查看所有网络设备日志
{job="syslog", source="network-devices"}

# 接口 Down 事件
{job="syslog"} |~ "Interface.*down|link down"

# BGP 邻居问题
{job="syslog"} |~ "BGP.*down"

# SSH 登录失败
{job="auth"} |~ "Failed password"
```

### 根因分析示例

**场景**: 网站访问缓慢

**传统方式**（7 个告警邮件）:
1. WebsiteSlow (www.company.com)
2. WebsiteSlow (api.company.com)
3. NetworkLatency (ESXi-Host-01)
4. NetworkLatency (ESXi-Host-02)
5. SwitchCPUHigh (Switch-Core-01)
6. SwitchTrafficStorm (Switch-Core-01) ← 根因
7. ...

运维人员需要手动排查 30 分钟。

**可观测性方式**（1 个智能告警）:

```
Subject: 🚨 Critical: 核心交换机流量风暴

根因: Switch-Core-01 Eth1/1 流量风暴
影响: 3 个服务、2 台 ESXi 主机
建议: 检查 Eth1/1 连接设备，可能是 DDoS 或环路

详细信息:
  - Metrics: CPU 98%
  - Logs: Unicast storm detected on Eth1/1
  - 拓扑: 影响 network-seg-core-01 整个网段

Grafana: http://grafana/d/network-overview
Loki Logs: {host="Switch-Core-01"} [17:00:00]
```

运维人员 1 分钟定位根因，10 分钟解决问题。

### Metrics + Logs 关联查询

在 Grafana Dashboard 中：

**Panel 1**: Metrics - 网站响应时间
```promql
probe_http_duration_seconds{instance="www.company.com"}
```

**Panel 2**: Logs - 同一时间段的网络日志
```logql
{job="syslog", source="network-devices"} |~ "error|critical"
```

点击时间点，所有视图联动，快速定位问题。

详细配置请参考: [docs/OBSERVABILITY-GUIDE.md](docs/OBSERVABILITY-GUIDE.md)

## 拓扑自动发现（LLDP）

**完全自动化**的网络拓扑发现系统，无需手动维护 CMDB！

### 功能特性

- ✅ **LLDP 自动采集**: 每 5 分钟自动采集所有网络设备的邻居信息
- ✅ **拓扑关系生成**: 自动构建设备连接关系图
- ✅ **层级自动计算**: 根据连接数量判断核心/汇聚/接入层级
- ✅ **标签自动化**: 自动为每个设备生成拓扑标签（connected_switch、device_tier 等）
- ✅ **可视化**: Grafana Node Graph 自动渲染网络拓扑图
- ✅ **告警关联**: 标签自动用于 Alertmanager 根因分析

### 架构

```
网络设备 (LLDP)
    ↓ SNMP
Topology Discovery 容器
    ├→ 采集 LLDP 邻居
    ├→ 生成拓扑图
    ├→ 自动计算层级
    └→ 更新 Prometheus 标签
        ↓
VictoriaMetrics (带拓扑标签的指标)
        ↓
Alertmanager (根据拓扑抑制连锁告警)
        ↓
Grafana (可视化拓扑图)
```

### 快速开始

**1. 配置设备列表**

编辑 `config/topology/devices.yml`:

```yaml
devices:
  - name: Switch-Core-01
    host: 192.168.1.100
    type: switch
    tier: core
    vendor: cisco
    snmp_community: public
```

**2. 启用设备 LLDP**

```
# Cisco
lldp run
snmp-server community public RO

# Arista
lldp run
snmp-server community public ro
```

**3. 启动拓扑发现**

```bash
# 构建镜像
docker-compose build topology-discovery

# 启动服务
docker-compose up -d topology-discovery

# 查看发现的拓扑
cat data/topology/topology.json
```

**4. 在 Grafana 查看拓扑图**

1. 登录 Grafana
2. 导入 Dashboard: `config/grafana/dashboards/network-topology.json`
3. 查看自动生成的网络拓扑可视化

### 自动生成的标签

拓扑发现自动为每个设备添加标签：

```json
{
  "device_name": "Server-01",
  "device_tier": "access",
  "connected_switch": "Switch-Access-01",
  "connected_port": "Gi0/1",
  "topology_discovered": "true"
}
```

这些标签用于：
- **Alertmanager**: 根据拓扑抑制连锁告警
- **Grafana**: 可视化设备关系
- **查询**: 快速定位影响范围

### 根因分析示例

**场景**: 核心交换机故障

```
传统方式:
- 收到 20 个告警（交换机、服务器、服务...）
- 手动排查 30 分钟找根因

自动拓扑方式:
- 系统检测到 Switch-Core-01 (tier=core) 故障
- 自动抑制所有 tier=access 交换机告警
- 自动抑制连接到这些交换机的服务器告警
- 发送 1 封邮件: "核心交换机 Switch-Core-01 故障，影响 5 台接入交换机和 20 台服务器"
- 1 分钟定位根因
```

详细配置请参考: [docs/TOPOLOGY-DISCOVERY.md](docs/TOPOLOGY-DISCOVERY.md)

## Grafana 仪表板

### 推荐的仪表板

登录 Grafana 后,导入以下仪表板(Import -> 输入 ID):

- **Node Exporter Full** (ID: 1860) - Linux 主机监控
- **VMware vSphere - Overview** (ID: 11243) - VMware 环境监控
- **SNMP Stats** (ID: 11169) - SNMP 设备监控
- **VictoriaMetrics - vmagent** (ID: 12683) - vmagent 监控

## 告警配置

系统预配置了以下告警规则:

### 主机告警
- 主机宕机
- CPU 使用率过高 (>80%)
- 内存使用率过高 (>85%)
- 磁盘空间不足 (<15%)
- 磁盘 I/O 等待过高
- 网络接口下线

### VMware 告警
- 虚拟机宕机
- ESXi 主机资源使用率过高
- 数据存储空间不足

### 网络设备告警
- SNMP 设备无法访问
- 网络接口下线
- 接口错误率过高
- 接口流量过高

### 监控系统告警
- 监控组件服务宕机
- 采集目标无法访问
- 存储空间不足

告警规则配置文件位于 `config/vmalert/alerts/` 目录。

## 维护操作

### 查看日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f victoriametrics
docker-compose logs -f vmagent
```

### 重启服务

```bash
# 重启所有服务
docker-compose restart

# 重启特定服务
docker-compose restart vmagent
```

### 更新配置

修改配置文件后,重启相应服务:

```bash
# 更新 vmagent 配置
docker-compose restart vmagent

# 更新告警规则
docker-compose restart vmalert

# 更新 Alertmanager 配置
docker-compose restart alertmanager
```

### 数据备份

```bash
# 备份 VictoriaMetrics 数据
docker run --rm -v monitoring-deployment_vmdata:/source -v $(pwd)/backup:/backup alpine \
  tar czf /backup/vm-data-$(date +%Y%m%d).tar.gz -C /source .

# 备份 Grafana 数据
docker run --rm -v monitoring-deployment_grafana-data:/source -v $(pwd)/backup:/backup alpine \
  tar czf /backup/grafana-data-$(date +%Y%m%d).tar.gz -C /source .
```

### 清理和重置

```bash
# 停止所有服务
docker-compose down

# 删除所有数据(谨慎操作!)
docker-compose down -v

# 重新启动
docker-compose up -d
```

## 性能优化

### VictoriaMetrics 优化

- 数据保留时间: 修改 `docker-compose.yaml` 中的 `--retentionPeriod` 参数
- 内存限制: 添加 `--memory.allowedPercent=60` 限制内存使用

### vmagent 优化

- 减少采集间隔: 修改 `scrape_interval` 为更大的值(如 30s 或 60s)
- 批量写入: 添加 `--remoteWrite.maxBlockSize=8388608` 增加批量大小

### 网络优化

- 将监控组件与监控目标部署在同一网段
- 对于 VMware 监控,建议部署在 vCenter 网络附近
- SNMP 监控使用较长的采集间隔(60s+)

## 故障排查

### 服务无法启动

```bash
# 检查端口占用
netstat -tlnp | grep -E '(3000|8428|9093|9116)'

# 检查 Docker 日志
docker-compose logs
```

### 无法采集数据

1. 检查 vmagent 日志: `docker-compose logs vmagent`
2. 验证目标可达性: `curl http://target:port/metrics`
3. 检查防火墙规则

### 告警不触发

1. 检查 vmalert 日志: `docker-compose logs vmalert`
2. 访问 vmalert UI: http://localhost:8880
3. 验证告警规则语法

### Telegraf VMware 监控报错

1. 检查 vCenter 连接信息: `config/telegraf/telegraf.conf`
2. 确认监控账号权限（需要只读权限）
3. 查看详细日志: `docker-compose logs telegraf-vmware`
4. 验证 vCenter SDK 地址格式: `https://vcenter-fqdn/sdk`

## 目录结构

```
.
├── docker-compose.yaml          # Docker Compose 配置
├── .env.example                 # 环境变量示例
├── .gitignore                   # Git 忽略文件
├── README.md                    # 本文档
└── config/                      # 配置文件目录
    ├── vmagent/
    │   └── prometheus.yml       # vmagent 采集配置
    ├── vmalert/
    │   └── alerts/              # 告警规则
    │       ├── node-alerts.yml  # Linux 主机告警
    │       ├── vmware-alerts.yml  # VMware 告警
    │       ├── switch-alerts.yml  # 交换机告警
    │       └── system-alerts.yml  # 监控系统告警
    ├── alertmanager/
    │   └── alertmanager.yml     # Alertmanager 配置
    ├── telegraf/
    │   └── telegraf.conf        # Telegraf VMware 监控配置
    ├── grafana/
    │   ├── provisioning/        # Grafana 自动配置
    │   │   ├── datasources/     # 数据源配置
    │   │   └── dashboards/      # 仪表板配置
    │   └── dashboards/          # 仪表板 JSON 文件
    └── snmp-exporter/
        ├── snmp.yml             # SNMP 配置
        └── README.md            # SNMP 配置说明
```

## 安全建议

1. **修改默认密码**: 修改 Grafana 管理员密码
2. **限制访问**: 使用防火墙或反向代理限制访问
3. **HTTPS**: 在生产环境中使用 HTTPS
4. **密钥管理**: 不要将密码提交到 Git 仓库
5. **网络隔离**: 将监控系统部署在独立的网络段
6. **定期备份**: 定期备份配置和数据
7. **及时更新**: 定期更新 Docker 镜像

## 扩展功能

### 添加 Blackbox Exporter(HTTP/ICMP 探测)

在 `docker-compose.yaml` 中添加:

```yaml
blackbox-exporter:
  image: prom/blackbox-exporter:latest
  ports:
    - "9115:9115"
  volumes:
    - ./config/blackbox/blackbox.yml:/etc/blackbox/blackbox.yml
  networks:
    - monitoring
```

### 添加 cAdvisor(容器监控)

```yaml
cadvisor:
  image: gcr.io/cadvisor/cadvisor:latest
  ports:
    - "8080:8080"
  volumes:
    - /:/rootfs:ro
    - /var/run:/var/run:ro
    - /sys:/sys:ro
    - /var/lib/docker/:/var/lib/docker:ro
  networks:
    - monitoring
```

## 参考文档

### 官方文档
- [VictoriaMetrics 官方文档](https://docs.victoriametrics.com/)
- [vmagent 文档](https://docs.victoriametrics.com/vmagent.html)
- [vmalert 文档](https://docs.victoriametrics.com/vmalert.html)
- [Alertmanager 文档](https://prometheus.io/docs/alerting/latest/alertmanager/)
- [Grafana 文档](https://grafana.com/docs/grafana/latest/)
- [Node Exporter 文档](https://github.com/prometheus/node_exporter)
- [SNMP Exporter 文档](https://github.com/prometheus/snmp_exporter)
- [VMware Exporter 文档](https://github.com/pryorda/vmware_exporter)

### 本项目文档
- [🚀 快速启动指南](QUICKSTART.md) - 5 分钟快速部署（从这里开始！）
- [可观测性完整架构指南](docs/OBSERVABILITY-GUIDE.md) - Metrics + Logs + 根因分析（核心）
- [LLDP 拓扑自动发现](docs/TOPOLOGY-DISCOVERY.md) - 自动拓扑发现 + 标签自动化（推荐）
- [gNMI 网络监控指南](docs/GNMI-MONITORING.md) - 新一代流式遥测监控（推荐）
- [服务器硬件监控指南](docs/HARDWARE-MONITORING.md) - Redfish + IPMI 硬件监控配置
- [VMware 多集群监控方案对比](docs/VMWARE-SOLUTION-COMPARISON.md) - 选择最适合的 VMware 监控方案
- [Telegraf 多 vCenter 监控指南](docs/TELEGRAF-VMWARE.md) - 单实例监控多个 vCenter
- [多 VMware 实例部署](docs/VMWARE-MULTI-INSTANCE.md) - vmware-exporter 多容器部署
- [多 VMware 集群配置](docs/MULTI-VMWARE.md) - 多数据中心和多租户场景
- [交换机监控配置](docs/SWITCH-MONITORING.md) - SNMP 交换机监控详细指南
- [性能调优指南](docs/PERFORMANCE-TUNING.md) - 系统性能优化
- [常见问题 FAQ](docs/FAQ.md) - 常见问题解答

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request!

## 联系方式

如有问题,请在 GitHub 仓库提交 Issue。
