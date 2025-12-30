# 📘 完整部署和使用手册 (Deployment Guide)

<div align="center">

**企业级可观测性平台详细部署指南**

*每个组件的详细配置 | 数据流向 | 分布式部署*

</div>

---

## 📋 目录

- [架构总览](#-架构总览)
- [数据流向图](#-数据流向图)
- [组件详细配置](#-组件详细配置)
  - [VictoriaMetrics - 时序数据库](#1-victoriametrics---时序数据库)
  - [vmagent - 指标采集代理](#2-vmagent---指标采集代理)
  - [Node Exporter - 主机监控](#3-node-exporter---主机监控)
  - [SNMP Exporter - 网络设备监控](#4-snmp-exporter---网络设备监控)
  - [Telegraf VMware - 虚拟化监控](#5-telegraf-vmware---虚拟化监控)
  - [Telegraf gNMI - 流式网络监控](#6-telegraf-gnmi---流式网络监控)
  - [Blackbox Exporter - 服务监控](#7-blackbox-exporter---服务监控)
  - [Redfish Exporter - 硬件监控](#8-redfish-exporter---硬件监控)
  - [LLDP Topology Discovery - 拓扑发现](#9-lldp-topology-discovery---拓扑发现)
  - [Topology Exporter - 拓扑指标](#10-topology-exporter---拓扑指标)
  - [Loki - 日志聚合](#11-loki---日志聚合)
  - [Promtail - 日志采集](#12-promtail---日志采集)
  - [Syslog-NG - 网络设备日志](#13-syslog-ng---网络设备日志)
  - [vmalert - 告警引擎](#14-vmalert---告警引擎)
  - [Alertmanager - 告警管理](#15-alertmanager---告警管理)
  - [Grafana - 可视化](#16-grafana---可视化)
- [设备添加指南](#-设备添加指南)
- [分布式部署场景](#-分布式部署场景)
- [故障排查](#-故障排查)

---

## 🏗 架构总览

### 单机部署架构（默认）

```
┌─────────────────────────────────────────────────────────────────┐
│                    监控服务器 (Monitoring Server)                 │
│                      IP: 192.168.1.50                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ VictoriaMetrics │  │      Loki       │  │     Grafana     │ │
│  │   :8428         │  │     :3100       │  │      :3000      │ │
│  │  (时序数据库)    │  │   (日志存储)     │  │    (可视化)      │ │
│  └────────▲────────┘  └────────▲────────┘  └─────────────────┘ │
│           │                    │                                │
│  ┌────────┴────────┐  ┌────────┴────────┐  ┌─────────────────┐ │
│  │    vmagent      │  │    Promtail     │  │   Syslog-NG     │ │
│  │     :8429       │  │                 │  │     :514        │ │
│  │  (指标采集)      │  │  (日志采集)      │  │  (日志接收)      │ │
│  └────────▲────────┘  └─────────────────┘  └────────▲────────┘ │
│           │                                          │          │
│  ┌────────┴────────────────────────────────────────┴──────┐    │
│  │              采集器 (Exporters)                          │    │
│  │  • SNMP Exporter :9116                                 │    │
│  │  • Blackbox Exporter :9115                             │    │
│  │  • Redfish Exporter :9610                              │    │
│  │  • Topology Exporter :9700                             │    │
│  │  • Telegraf VMware (推送到 :8428)                       │    │
│  │  • LLDP Discovery (定时任务)                            │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
           │                                          │
           │ (SNMP/HTTP 拉取)                        │ (Syslog 推送)
           ▼                                          ▼
┌──────────────────────┐              ┌──────────────────────────┐
│   监控目标设备        │              │      网络设备            │
│  • Linux 服务器       │              │  • Cisco 交换机          │
│  • Windows 服务器     │              │  • Arista 交换机         │
│  • VMware ESXi       │              │  • Juniper 路由器        │
│  • 物理服务器 (iLO)   │              │  • Huawei 交换机         │
└──────────────────────┘              └──────────────────────────┘
```

### 分布式部署架构（高级）

```
┌─────────────────────────────────────────────────────────────────┐
│                   中心监控服务器 (Central Server)                 │
│                      IP: 192.168.1.50                            │
├─────────────────────────────────────────────────────────────────┤
│  VictoriaMetrics (:8428) ◄─── 接收所有 vmagent 数据              │
│  Loki (:3100)            ◄─── 接收所有 Promtail 数据             │
│  Grafana (:3000)         ◄─── 统一可视化                        │
│  Alertmanager (:9093)    ◄─── 统一告警管理                      │
│  vmalert (:8880)         ◄─── 告警规则评估                      │
└─────────────────────────────────────────────────────────────────┘
           ▲                    ▲                    ▲
           │                    │                    │
           │ (远程写入)          │ (远程写入)          │ (远程写入)
           │                    │                    │
┌──────────┴────────┐  ┌────────┴────────┐  ┌────────┴────────┐
│  数据中心 A (DC-A) │  │  数据中心 B (DC-B) │  │   分支机构 C     │
│  192.168.1.0/24   │  │  192.168.2.0/24   │  │  192.168.3.0/24 │
├───────────────────┤  ├───────────────────┤  ├─────────────────┤
│  vmagent          │  │  vmagent          │  │  vmagent        │
│  Promtail         │  │  Promtail         │  │  Promtail       │
│  SNMP Exporter    │  │  SNMP Exporter    │  │  Node Exporter  │
│  Node Exporter    │  │  Blackbox         │  │                 │
│  LLDP Discovery   │  │                   │  │                 │
└───────────────────┘  └───────────────────┘  └─────────────────┘
```

---

## 🔄 数据流向图

### Metrics（指标）数据流

```
监控目标                     采集器                      代理              存储              可视化
┌────────┐                ┌────────┐               ┌────────┐        ┌────────┐        ┌────────┐
│ Linux  │─┐              │  Node  │               │        │        │Victoria│        │        │
│ Server │ │ :9100/metrics│Exporter│──┐            │        │        │Metrics │        │        │
└────────┘ └─────────────►└────────┘  │            │        │        │        │        │        │
                                       │ HTTP GET   │ vmagent│─ Write─►│ :8428  │◄─Query─│Grafana │
┌────────┐                ┌────────┐  │   (拉取)   │        │ (推送) │        │        │        │
│ Switch │─┐ SNMP (UDP)   │  SNMP  │  │            │ :8429  │        │        │        │ :3000  │
│        │ └─────────────►│Exporter│──┤            │        │        │        │        │        │
└────────┘                └────────┘  │            └────────┘        └────────┘        └────────┘
                          :9116       │                                    ▲                 ▲
┌────────┐                ┌────────┐  │                                    │                 │
│ ESXi   │  vSphere API   │Telegraf│──┘                                    │                 │
│ vCenter│───────────────►│ VMware │─────── 直接推送 ─────────────────────┘                 │
└────────┘                └────────┘         (Write to :8428)                               │
                                                                                             │
┌────────┐                ┌────────┐                ┌────────┐                              │
│ LLDP   │  SNMP (UDP)    │  LLDP  │  生成文件      │Topology│─ 暴露指标 ──────────────────┘
│ Devices│───────────────►│Discovery│───────────────►│Exporter│    :9700/metrics
└────────┘                └────────┘                └────────┘    (被 vmagent 拉取)
                          (Python 脚本)
```

### Logs（日志）数据流

```
日志源                      采集器                      存储              可视化
┌────────┐                ┌────────┐               ┌────────┐        ┌────────┐
│ Linux  │  /var/log/*    │Promtail│──┐            │        │        │        │
│ Server │───────────────►│        │  │            │        │        │        │
└────────┘                └────────┘  │ HTTP POST  │  Loki  │◄─Query─│Grafana │
                                      ├───────────►│        │        │        │
┌────────┐                ┌────────┐  │  (推送)    │ :3100  │        │ :3000  │
│ Docker │  容器日志       │Promtail│──┤            │        │        │        │
│Container│───────────────►│        │  │            └────────┘        └────────┘
└────────┘                └────────┘  │
                                      │
┌────────┐                ┌────────┐  │
│Network │  Syslog (UDP)  │Syslog  │  │
│ Device │─────:514──────►│  -NG   │──┘
└────────┘                └────────┘
                          (写入文件 → 被 Promtail 读取)
```

### Alerting（告警）数据流

```
数据源                      规则引擎                    告警管理              通知
┌────────┐                ┌────────┐               ┌────────┐        ┌────────┐
│Victoria│  PromQL 查询   │vmalert │  发送告警     │Alert   │ SMTP   │ Email  │
│Metrics │───────────────►│        │──────────────►│manager │───────►│        │
│        │                │ :8880  │               │        │        └────────┘
└────────┘                └────────┘               │ :9093  │        ┌────────┐
                          • 评估规则                │        │ Webhook│ 钉钉   │
┌────────┐                • 计算阈值               │        │───────►│ 企业微信│
│  Loki  │  LogQL 查询    ┌────────┐               │        │        └────────┘
│        │───────────────►│  Loki  │  发送告警     │        │
│        │                │  Ruler │──────────────►│ 智能:  │
└────────┘                └────────┘               │• 分组  │
                          • 日志告警                │• 抑制  │
                                                   │• 路由  │
                                                   └────────┘
```

---

## 📦 组件详细配置

### 1. VictoriaMetrics - 时序数据库

#### 作用
- 存储所有 Metrics 指标数据（CPU、内存、网络、拓扑等）
- 提供 PromQL 查询接口
- 高性能存储（比 Prometheus 快 10 倍）

#### 数据接收
| 来源 | 接口 | 协议 | 说明 |
|------|------|------|------|
| vmagent | `:8428/api/v1/write` | HTTP POST | 指标写入 |
| Telegraf | `:8428/api/v1/write` | HTTP POST | VMware 指标 |
| Grafana | `:8428/api/v1/query` | HTTP GET | 查询接口 |
| vmalert | `:8428/api/v1/query` | HTTP GET | 告警查询 |

#### 配置文件位置
```
docker-compose.yaml (VictoriaMetrics 服务段)
```

#### 关键配置参数
```yaml
services:
  victoriametrics:
    image: victoriametrics/victoria-metrics:latest
    ports:
      - "8428:8428"  # ← 对外暴露端口
    volumes:
      - vmdata:/storage  # ← 数据持久化
    command:
      - "--storageDataPath=/storage"      # 数据目录
      - "--httpListenAddr=:8428"          # 监听地址
      - "--retentionPeriod=12"            # 保留 12 个月
```

#### 添加监控目标方式
**不直接添加！** VictoriaMetrics 只负责存储，目标由 vmagent 配置。

#### 验证方式
```bash
# 1. 检查服务健康
curl http://localhost:8428/health

# 2. 查询所有目标
curl 'http://localhost:8428/api/v1/query?query=up'

# 3. 查看存储统计
curl http://localhost:8428/metrics | grep vm_rows
```

#### 分布式部署配置
**场景：中心服务器接收多个数据中心的数据**

中心服务器（192.168.1.50）:
```yaml
victoriametrics:
  ports:
    - "8428:8428"  # 对所有网段开放
```

远程 vmagent（192.168.2.100）:
```yaml
vmagent:
  command:
    - "--remoteWrite.url=http://192.168.1.50:8428/api/v1/write"  # ← 指向中心
```

---

### 2. vmagent - 指标采集代理

#### 作用
- 拉取各种 Exporter 的指标（SNMP、Node、Blackbox 等）
- 读取文件服务发现配置（拓扑标签注入）
- 将数据推送到 VictoriaMetrics

#### 数据流向
```
拉取 ← SNMP Exporter (:9116)
拉取 ← Node Exporter (:9100)
拉取 ← Blackbox Exporter (:9115)
拉取 ← Topology Exporter (:9700)
  │
  └─► VictoriaMetrics (:8428/api/v1/write)
```

#### 配置文件位置
```
config/vmagent/prometheus.yml          # 主配置
config/vmagent/targets/*.json          # 目标列表（文件服务发现）
```

#### 关键配置结构
```yaml
# config/vmagent/prometheus.yml
global:
  scrape_interval: 15s          # 全局采集间隔

scrape_configs:
  # ===== Job 1: Linux 主机（静态配置）=====
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['192.168.1.10:9100', '192.168.1.11:9100']
        labels:
          env: 'production'
          datacenter: 'dc1'

  # ===== Job 2: Linux 主机（拓扑自动发现）=====
  - job_name: 'node-topology'
    file_sd_configs:
      - files:
        - /etc/prometheus/targets/topology-servers.json  # ← 拓扑发现生成
        refresh_interval: 60s  # 每 60 秒重新读取

  # ===== Job 3: SNMP 网络设备（拓扑自动发现）=====
  - job_name: 'snmp-topology'
    file_sd_configs:
      - files:
        - /etc/prometheus/targets/topology-switches.json  # ← 拓扑发现生成
    metrics_path: /snmp
    params:
      module: [if_mib]  # 使用 if_mib 模块
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: snmp-exporter:9116  # ← SNMP Exporter 地址

  # ===== Job 4: Blackbox 服务监控 =====
  - job_name: 'blackbox-http'
    metrics_path: /probe
    params:
      module: [http_2xx]
    static_configs:
      - targets:
        - http://www.example.com
        - https://api.example.com
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: blackbox-exporter:9115  # ← Blackbox Exporter 地址

  # ===== Job 5: 拓扑指标 =====
  - job_name: 'topology-exporter'
    static_configs:
      - targets: ['topology-exporter:9700']
```

#### 添加监控目标方式

**方式 1：静态配置（适合固定目标）**
```yaml
# 编辑 config/vmagent/prometheus.yml
scrape_configs:
  - job_name: 'my-servers'
    static_configs:
      - targets:
        - '192.168.1.20:9100'  # 新服务器 1
        - '192.168.1.21:9100'  # 新服务器 2
        labels:
          team: 'backend'
```

**方式 2：文件服务发现（拓扑自动发现）**
```yaml
# 1. 添加设备到拓扑配置
# 编辑 config/topology/devices.yml
devices:
  - name: Server-New-01
    host: 192.168.1.20
    type: server
    tier: access

# 2. 重启拓扑发现（会自动生成 topology-servers.json）
docker-compose restart topology-discovery

# 3. vmagent 会在 60 秒内自动加载新目标
```

**方式 3：手动创建文件发现**
```bash
# 创建 config/vmagent/targets/custom-servers.json
cat > config/vmagent/targets/custom-servers.json << 'EOF'
[
  {
    "targets": ["192.168.1.30:9100", "192.168.1.31:9100"],
    "labels": {
      "job": "custom-servers",
      "env": "test"
    }
  }
]
EOF

# 在 prometheus.yml 中添加
# scrape_configs:
#   - job_name: 'custom-servers'
#     file_sd_configs:
#       - files: ['/etc/prometheus/targets/custom-servers.json']
```

#### 验证方式
```bash
# 1. 检查所有采集目标
curl http://localhost:8429/targets | jq '.data.activeTargets[] | {job: .labels.job, instance: .labels.instance, health: .health}'

# 2. 重新加载配置（无需重启）
curl -X POST http://localhost:8429/-/reload

# 3. 查看采集统计
curl http://localhost:8429/metrics | grep vmagent_scraped_samples_sum
```

#### 分布式部署配置
**场景：远程机房部署 vmagent，数据发往中心**

远程机房（192.168.2.100）:
```yaml
# docker-compose.yaml
vmagent:
  image: victoriametrics/vmagent:latest
  volumes:
    - ./config/vmagent/prometheus.yml:/etc/prometheus/prometheus.yml
  command:
    - "--promscrape.config=/etc/prometheus/prometheus.yml"
    - "--remoteWrite.url=http://192.168.1.50:8428/api/v1/write"  # ← 中心地址
    - "--remoteWrite.label=datacenter=dc2"  # ← 添加数据中心标签
```

---

### 3. Node Exporter - 主机监控

#### 作用
- 暴露 Linux/Unix 主机的系统指标
- CPU、内存、磁盘、网络、文件系统等

#### 数据暴露
- **端口**: `:9100/metrics`
- **协议**: HTTP GET
- **格式**: Prometheus Exposition Format

#### 部署方式

**方式 1：Docker 部署（监控宿主机）**
```yaml
# docker-compose.yaml
node-exporter:
  image: prom/node-exporter:latest
  ports:
    - "9100:9100"
  volumes:
    - /proc:/host/proc:ro      # 挂载宿主机 proc
    - /sys:/host/sys:ro        # 挂载宿主机 sys
    - /:/rootfs:ro             # 挂载宿主机根目录
  command:
    - '--path.procfs=/host/proc'
    - '--path.sysfs=/host/sys'
    - '--path.rootfs=/rootfs'
```

**方式 2：系统服务部署（推荐用于生产服务器）**
```bash
# 在每台 Linux 服务器上执行

# 1. 下载 Node Exporter
wget https://github.com/prometheus/node_exporter/releases/download/v1.7.0/node_exporter-1.7.0.linux-amd64.tar.gz
tar xvfz node_exporter-1.7.0.linux-amd64.tar.gz
sudo cp node_exporter-1.7.0.linux-amd64/node_exporter /usr/local/bin/

# 2. 创建 systemd 服务
sudo cat > /etc/systemd/system/node_exporter.service << 'EOF'
[Unit]
Description=Node Exporter
After=network.target

[Service]
Type=simple
User=nobody
ExecStart=/usr/local/bin/node_exporter \
  --web.listen-address=:9100 \
  --collector.filesystem.mount-points-exclude=^/(dev|proc|sys|var/lib/docker/.+)($|/)

[Install]
WantedBy=multi-user.target
EOF

# 3. 启动服务
sudo systemctl daemon-reload
sudo systemctl enable node_exporter
sudo systemctl start node_exporter

# 4. 验证
curl http://localhost:9100/metrics
```

#### 添加到监控

**方法 1：静态添加**
```yaml
# config/vmagent/prometheus.yml
scrape_configs:
  - job_name: 'node-exporter'
    static_configs:
      - targets:
        - '192.168.1.10:9100'  # 服务器 1
        - '192.168.1.11:9100'  # 服务器 2
        labels:
          datacenter: 'dc1'
          role: 'web'
```

**方法 2：拓扑自动发现**
```yaml
# 1. 添加到 config/topology/devices.yml
devices:
  - name: Web-Server-01
    host: 192.168.1.10
    type: server
    tier: access
    location: dc1-rack-A01

# 2. 重启拓扑发现
docker-compose restart topology-discovery

# 3. 自动生成 config/vmagent/targets/topology-servers.json
# [
#   {
#     "targets": ["192.168.1.10:9100"],
#     "labels": {
#       "device_name": "Web-Server-01",
#       "device_tier": "access",
#       "device_location": "dc1-rack-A01"
#     }
#   }
# ]
```

#### 验证方式
```bash
# 在目标服务器上
curl http://localhost:9100/metrics | grep node_cpu

# 在监控服务器上
curl 'http://localhost:8428/api/v1/query?query=up{job="node-exporter"}'
```

---

### 4. SNMP Exporter - 网络设备监控

#### 作用
- 通过 SNMP 协议采集网络设备指标
- 支持 Cisco、Arista、Juniper、Huawei 等

#### 工作原理
```
vmagent → SNMP Exporter → SNMP (UDP :161) → Network Device
  请求     :9116/snmp       查询 OID              返回数据
```

#### 配置文件位置
```
config/snmp-exporter/snmp.yml    # SNMP 模块配置
```

#### 关键配置
```yaml
# config/snmp-exporter/snmp.yml
modules:
  # 模块 1：接口监控（if_mib）
  if_mib:
    walk:
      - 1.3.6.1.2.1.2         # IF-MIB
      - 1.3.6.1.2.1.31        # IF-MIB High Capacity
    lookups:
      - source_indexes: [ifIndex]
        lookup: ifName
        drop_source_indexes: false
    overrides:
      ifName:
        type: DisplayString
      ifAlias:
        type: DisplayString

  # 模块 2：LLDP 拓扑发现
  lldp:
    walk:
      - 1.0.8802.1.1.2        # LLDP-MIB
```

#### 添加网络设备

**方法 1：静态添加**
```yaml
# config/vmagent/prometheus.yml
scrape_configs:
  - job_name: 'snmp-switches'
    scrape_interval: 30s
    metrics_path: /snmp
    params:
      module: [if_mib]  # 使用哪个 SNMP 模块
    static_configs:
      - targets:
        - 192.168.1.100  # 交换机 IP（不带端口！）
        - 192.168.1.101
        labels:
          snmp_community: 'public'
    relabel_configs:
      # 1. 将 target 设置为 SNMP 查询参数
      - source_labels: [__address__]
        target_label: __param_target
      # 2. 将 target 显示为 instance 标签
      - source_labels: [__param_target]
        target_label: instance
      # 3. 将实际请求地址改为 SNMP Exporter
      - target_label: __address__
        replacement: snmp-exporter:9116
```

**方法 2：拓扑自动发现**
```yaml
# 1. 添加到 config/topology/devices.yml
devices:
  - name: Switch-Core-01
    host: 192.168.1.100
    type: switch
    tier: core
    location: dc1-rack-A01
    snmp_community: public
    snmp_version: 2c

# 2. 拓扑发现自动生成 topology-switches.json
# [
#   {
#     "targets": ["192.168.1.100"],
#     "labels": {
#       "device_name": "Switch-Core-01",
#       "device_tier": "core",
#       "device_type": "switch",
#       "device_location": "dc1-rack-A01"
#     }
#   }
# ]

# 3. vmagent 配置（已存在）
# scrape_configs:
#   - job_name: 'snmp-topology'
#     file_sd_configs:
#       - files: ['/etc/prometheus/targets/topology-switches.json']
```

#### 网络设备配置（必须！）

**Cisco IOS/IOS-XE:**
```cisco
configure terminal
!
! 启用 SNMP
snmp-server community public RO
snmp-server location dc1-rack-A01
snmp-server contact ops@example.com
!
! 启用 LLDP（拓扑发现）
lldp run
!
! 配置 Syslog（日志采集）
logging host 192.168.1.50
logging trap informational
!
end
write memory
```

**Arista EOS:**
```arista
configure
snmp-server community public ro
lldp run
logging host 192.168.1.50
end
write
```

#### 验证方式
```bash
# 1. 手动测试 SNMP Exporter
curl 'http://localhost:9116/snmp?target=192.168.1.100&module=if_mib'

# 2. 检查 vmagent 是否采集到
curl 'http://localhost:8428/api/v1/query?query=ifHCInOctets{instance="192.168.1.100"}'

# 3. 直接测试 SNMP（安装 snmp 工具）
snmpwalk -v2c -c public 192.168.1.100 1.3.6.1.2.1.2.2.1.1  # 接口索引
```

---

### 5. Telegraf VMware - 虚拟化监控

#### 作用
- 采集 VMware vSphere (vCenter/ESXi) 指标
- 推送模式（不是拉取），直接写入 VictoriaMetrics
- 支持拓扑标签注入

#### 数据流向
```
vCenter API → Telegraf → Processor (标签注入) → VictoriaMetrics :8428
```

#### 配置文件位置
```
config/telegraf/telegraf.conf           # 主配置
data/topology/telegraf-labels.json      # 拓扑标签映射
scripts/topology/telegraf_label_injector.py  # 标签注入脚本
```

#### 关键配置
```toml
# config/telegraf/telegraf.conf

# ===== 输出配置 =====
[[outputs.http]]
  url = "http://victoriametrics:8428/api/v1/write"  # ← VictoriaMetrics 地址
  data_format = "prometheusremotewrite"
  [outputs.http.headers]
    Content-Type = "application/x-protobuf"
    Content-Encoding = "snappy"
    X-Prometheus-Remote-Write-Version = "0.1.0"

# ===== 拓扑标签注入 Processor =====
[[processors.execd]]
  command = ["python3", "/scripts/telegraf_label_injector.py"]
  data_format = "influx"
  environment = ["TOPOLOGY_LABELS_FILE=/data/topology/telegraf-labels.json"]

# ===== VMware vSphere 输入 =====
[[inputs.vsphere]]
  ## vCenter 服务器列表
  vcenters = ["https://vcenter.example.com/sdk"]

  ## 认证信息
  username = "monitoring@vsphere.local"
  password = "your-password"
  insecure_skip_verify = true

  ## 采集间隔
  interval = "60s"

  ## 采集超时
  timeout = "30s"

  ## 采集对象
  vm_metric_include = [
    "cpu.usage.average",
    "mem.usage.average",
    "disk.read.average",
    "disk.write.average",
    "net.bytesRx.average",
    "net.bytesTx.average"
  ]

  host_metric_include = [
    "cpu.usage.average",
    "mem.usage.average",
    "disk.read.average",
    "disk.write.average",
    "net.bytesRx.average",
    "net.bytesTx.average"
  ]

  cluster_metric_include = []
  datastore_metric_include = []
```

#### 添加 vCenter

```bash
# 1. 编辑 config/telegraf/telegraf.conf
vim config/telegraf/telegraf.conf

# 修改 vcenters 列表
[[inputs.vsphere]]
  vcenters = [
    "https://vcenter1.example.com/sdk",  # vCenter 1
    "https://vcenter2.example.com/sdk"   # vCenter 2
  ]
  username = "monitoring@vsphere.local"
  password = "your-password"

# 2. 重启 Telegraf
docker-compose restart telegraf-vmware

# 3. 查看日志确认连接成功
docker-compose logs -f telegraf-vmware
```

#### 拓扑标签注入工作原理

```
1. LLDP Discovery 生成 telegraf-labels.json:
{
  "192.168.1.200": {
    "device_name": "ESXi-Host-01",
    "device_tier": "core",
    "connected_switch": "Switch-Core-01"
  },
  "ESXi-Host-01": { ... },
  "esxi-host-01.example.com": { ... }
}

2. Telegraf 采集 VMware 指标:
vsphere_host_cpu_usage,esxi_host=192.168.1.200 value=45.2

3. Processor 匹配并注入标签:
vsphere_host_cpu_usage,esxi_host=192.168.1.200,device_tier=core,connected_switch=Switch-Core-01 value=45.2

4. 推送到 VictoriaMetrics
```

#### 验证方式
```bash
# 1. 检查 Telegraf 状态
docker-compose logs telegraf-vmware | grep "Connected to"

# 2. 检查标签注入
cat data/topology/telegraf-labels.json | jq

# 3. 查询 VictoriaMetrics
curl 'http://localhost:8428/api/v1/query?query=vsphere_host_cpu_usage_average{device_tier!=""}'
```

#### 分布式部署
**场景：每个数据中心一个 vCenter**

数据中心 A:
```toml
# telegraf.conf
[[outputs.http]]
  url = "http://192.168.1.50:8428/api/v1/write"  # 中心地址

[[inputs.vsphere]]
  vcenters = ["https://vcenter-dc-a.local/sdk"]
```

数据中心 B:
```toml
# telegraf.conf
[[outputs.http]]
  url = "http://192.168.1.50:8428/api/v1/write"  # 同一中心

[[inputs.vsphere]]
  vcenters = ["https://vcenter-dc-b.local/sdk"]
```

---

### 6. Telegraf gNMI - 流式网络监控

#### 作用
- 新一代网络设备监控（替代 SNMP）
- 流式遥测（秒级实时数据，无需轮询）
- 支持 Cisco、Arista、Juniper 现代设备

#### 对比 SNMP

| 特性 | SNMP | gNMI |
|------|------|------|
| 协议 | UDP（不可靠） | gRPC（可靠） |
| 模式 | 轮询（Poll） | 流式推送（Stream） |
| 延迟 | 30-60 秒 | 1-10 秒 |
| 性能 | 低 | 高 |
| 设备支持 | 所有设备 | 新设备 |

#### 配置文件位置
```
config/telegraf-gnmi/telegraf-gnmi.conf
config/telegraf-gnmi/.env.gnmi  # 认证信息
```

#### 关键配置
```toml
# config/telegraf-gnmi/telegraf-gnmi.conf

[[outputs.http]]
  url = "http://victoriametrics:8428/api/v1/write"
  data_format = "prometheusremotewrite"

[[inputs.gnmi]]
  ## 设备地址
  addresses = ["192.168.1.100:57400"]  # ← gNMI 端口通常是 57400

  ## 认证（从环境变量读取）
  username = "${GNMI_USERNAME}"
  password = "${GNMI_PASSWORD}"

  ## TLS 配置
  enable_tls = true
  insecure_skip_verify = true

  ## 订阅路径（Cisco IOS-XR 示例）
  [[inputs.gnmi.subscription]]
    name = "interfaces"
    origin = "openconfig"
    path = "/interfaces/interface/state/counters"
    subscription_mode = "sample"
    sample_interval = "10s"  # 每 10 秒推送

  [[inputs.gnmi.subscription]]
    name = "bgp"
    origin = "openconfig"
    path = "/network-instances/network-instance/protocols/protocol/bgp"
    subscription_mode = "sample"
    sample_interval = "30s"
```

#### 网络设备配置（以 Cisco IOS-XR 为例）

```cisco
configure
!
! 启用 gNMI
grpc
 port 57400
 no-tls
!
! 创建用户
username gnmi-user
 group root-lr
 secret your-password
!
! 启用 Model-Driven Telemetry
telemetry model-driven
 sensor-group interfaces
  sensor-path openconfig-interfaces:interfaces/interface
 !
 subscription interfaces-sub
  sensor-group-id interfaces sample-interval 10000
!
commit
end
```

#### 添加 gNMI 设备
```toml
# 编辑 config/telegraf-gnmi/telegraf-gnmi.conf
[[inputs.gnmi]]
  addresses = [
    "192.168.1.100:57400",  # 交换机 1
    "192.168.1.101:57400"   # 交换机 2
  ]
```

#### 验证方式
```bash
# 查看日志
docker-compose logs telegraf-gnmi

# 查询指标
curl 'http://localhost:8428/api/v1/query?query=gnmi_interfaces_interface_state_counters_in_octets'
```

---

### 7. Blackbox Exporter - 服务监控

#### 作用
- 黑盒监控（从外部探测）
- HTTP/HTTPS、ICMP Ping、TCP、DNS

#### 配置文件位置
```
config/blackbox-exporter/blackbox.yml
```

#### 关键配置
```yaml
# config/blackbox-exporter/blackbox.yml
modules:
  # HTTP 2xx 检测
  http_2xx:
    prober: http
    timeout: 5s
    http:
      preferred_ip_protocol: "ip4"
      valid_status_codes: [200, 201, 202]
      fail_if_not_ssl: false

  # HTTPS 证书检测
  http_ssl:
    prober: http
    timeout: 5s
    http:
      fail_if_not_ssl: true
      fail_if_ssl_not_present: true

  # ICMP Ping
  icmp:
    prober: icmp
    timeout: 5s

  # TCP 端口检测
  tcp_connect:
    prober: tcp
    timeout: 5s

  # DNS 查询
  dns_query:
    prober: dns
    timeout: 5s
    dns:
      query_name: "example.com"
      query_type: "A"
```

#### 添加监控目标
```yaml
# config/vmagent/prometheus.yml
scrape_configs:
  # HTTP 网站监控
  - job_name: 'blackbox-http'
    metrics_path: /probe
    params:
      module: [http_2xx]
    static_configs:
      - targets:
        - https://www.google.com
        - https://api.example.com
        - http://internal-service.local:8080
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: blackbox-exporter:9115

  # ICMP Ping 监控
  - job_name: 'blackbox-icmp'
    metrics_path: /probe
    params:
      module: [icmp]
    static_configs:
      - targets:
        - 192.168.1.100  # 核心交换机
        - 192.168.1.1    # 网关
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: blackbox-exporter:9115

  # TCP 端口监控
  - job_name: 'blackbox-tcp'
    metrics_path: /probe
    params:
      module: [tcp_connect]
    static_configs:
      - targets:
        - 192.168.1.50:3306  # MySQL
        - 192.168.1.50:6379  # Redis
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: blackbox-exporter:9115
```

#### 验证方式
```bash
# 手动探测
curl 'http://localhost:9115/probe?target=https://www.google.com&module=http_2xx'

# 查询 VictoriaMetrics
curl 'http://localhost:8428/api/v1/query?query=probe_success'
```

---

### 8. Redfish Exporter - 硬件监控（统一方案）

#### 作用
- **统一监控新一代服务器硬件**（Dell iDRAC、HPE iLO、Lenovo XClarity、Cisco UCS 等）
- 通过 **Redfish REST API** 采集硬件健康状态
- 监控温度、风扇、电源、内存、RAID、硬盘、固件等
- **替代 IPMI 的现代化方案**（更安全、更标准）

#### 数据暴露
- **端口**: `:9610/redfish?target=<host>`
- **协议**: HTTP GET（Exporter 作为代理，调用目标服务器的 Redfish API）
- **格式**: Prometheus Exposition Format

#### 配置文件位置
```
config/redfish-exporter/redfish.yml        # 服务器列表和认证
```

#### 支持的厂商（Redfish 标准）
| 厂商 | 产品 | 默认用户名 | 默认密码 | Redfish 版本 |
|------|------|-----------|---------|-------------|
| Dell | iDRAC 7/8/9 | root | calvin | 1.0+ |
| HPE | iLO 4/5/6 | Administrator | 随机 | 1.0+ |
| Lenovo | XClarity Controller | USERID | PASSW0RD | 1.0+ |
| Cisco | UCS CIMC | admin | password | 1.0+ |
| Supermicro | 新款主板 (X11/X12) | ADMIN | ADMIN | 1.0+ |

#### 关键配置参数
```yaml
# config/redfish-exporter/redfish.yml
hosts:

  # Dell iDRAC 示例
  dell-server-01:
    username: "root"
    password: "calvin"              # ⚠️ 请修改为实际密码
    host_address: "192.168.1.100"   # iDRAC IP 地址
    insecure_skip_verify: true      # 如果使用自签名证书

  # HPE iLO 示例
  hpe-server-02:
    username: "Administrator"
    password: "your-ilo-password"
    host_address: "192.168.1.110"
    insecure_skip_verify: true

  # Lenovo XClarity 示例
  lenovo-server-03:
    username: "USERID"
    password: "PASSW0RD"
    host_address: "192.168.1.120"

  # Supermicro 示例
  supermicro-server-04:
    username: "ADMIN"
    password: "ADMIN"
    host_address: "192.168.1.130"
```

**安全建议**:
- ✅ 修改默认密码
- ✅ 使用只读账号（只需查询权限）
- ✅ 不要将密码提交到 Git（使用 `.env` 文件或 secrets 管理）
- ✅ 限制访问网络（管理网络隔离）

#### 添加新服务器

**步骤 1：验证 Redfish 支持**
```bash
# 测试 Dell iDRAC
curl -k -u root:calvin https://192.168.1.100/redfish/v1/

# 测试 HPE iLO
curl -k -u Administrator:password https://192.168.1.110/redfish/v1/

# 如果返回 JSON 数据（包含 @odata.type），说明支持 Redfish
```

**步骤 2：添加到配置文件**
```yaml
# config/redfish-exporter/redfish.yml
hosts:
  your-server-name:                 # 自定义名称（会作为标签）
    username: "root"
    password: "your-password"
    host_address: "192.168.1.100"   # 管理口 IP
    insecure_skip_verify: true
```

**步骤 3：重启 Redfish Exporter**
```bash
docker-compose restart redfish-exporter
```

**步骤 4：添加到 vmagent**
```yaml
# config/vmagent/prometheus.yml
scrape_configs:
  - job_name: 'redfish'
    scrape_interval: 60s          # 硬件监控可以更慢
    metrics_path: /redfish
    static_configs:
      - targets:
        - dell-server-01          # 对应 redfish.yml 中的名称
        - hpe-server-02
        - lenovo-server-03
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: redfish-exporter:9610
```

**步骤 5：重载 vmagent**
```bash
curl -X POST http://localhost:8429/-/reload
```

#### 验证方式
```bash
# 1. 测试 Exporter（直接查询）
curl 'http://localhost:9610/redfish?target=dell-server-01'

# 2. 检查关键指标
curl 'http://localhost:9610/redfish?target=dell-server-01' | grep -E "redfish_thermal_temperatures|redfish_power_supplies_state|redfish_memory_health_state"

# 预期输出示例:
# redfish_thermal_temperatures_celsius{name="CPU1 Temp",sensor_number="0"} 45
# redfish_power_supplies_state{name="PS1"} 1                  # 1=正常
# redfish_memory_health_state{name="DIMM_A1"} 1              # 1=正常

# 3. 查看 vmagent 采集状态
curl http://localhost:8429/targets | grep redfish

# 4. 查询 VictoriaMetrics
curl 'http://localhost:8428/api/v1/query?query=redfish_thermal_temperatures_celsius'
```

#### 监控指标类别

**1. 温度监控**
```promql
# CPU 温度
redfish_thermal_temperatures_celsius{name=~"CPU.*"}

# 主板温度
redfish_thermal_temperatures_celsius{name=~"System.*|Inlet.*"}

# 硬盘温度
redfish_thermal_temperatures_celsius{name=~"Disk.*"}
```

**2. 风扇监控**
```promql
# 风扇转速（RPM）
redfish_thermal_fans_rpm

# 风扇状态（1=正常，0=异常）
redfish_thermal_fans_health_state
```

**3. 电源监控**
```promql
# 电源状态
redfish_power_supplies_state

# 功耗（瓦特）
redfish_power_consumed_watts

# 输入电压
redfish_power_supplies_input_voltage
```

**4. 内存监控**
```promql
# 内存健康状态
redfish_memory_health_state

# 内存容量
redfish_memory_capacity_bytes
```

**5. RAID 控制器**
```promql
# RAID 控制器状态
redfish_storage_controller_health_state

# 硬盘状态
redfish_storage_drive_health_state

# RAID 卷状态
redfish_storage_volume_health_state
```

**6. 网卡监控**
```promql
# 网卡状态
redfish_network_adapter_health_state

# 网卡链路状态
redfish_network_port_link_status
```

#### 分布式部署配置

**场景：远程机房服务器监控**

远程机房（192.168.2.0/24）:
```yaml
# docker-compose.yaml（仅部署 Redfish Exporter）
services:
  redfish-exporter:
    image: jenningsloy318/redfish_exporter:latest
    ports:
      - "9610:9610"
    volumes:
      - ./redfish.yml:/etc/redfish_exporter/redfish.yml:ro
    command:
      - "--config.file=/etc/redfish_exporter/redfish.yml"
```

```yaml
# redfish.yml（远程机房服务器）
hosts:
  remote-dell-01:
    username: "root"
    password: "password"
    host_address: "192.168.2.100"  # 本地管理网络
  remote-dell-02:
    username: "root"
    password: "password"
    host_address: "192.168.2.101"
```

中心监控服务器:
```yaml
# config/vmagent/prometheus.yml
scrape_configs:
  - job_name: 'redfish-remote-dc2'
    scrape_interval: 120s                # 远程可以更慢
    metrics_path: /redfish
    static_configs:
      - targets:
        - remote-dell-01
        - remote-dell-02
        labels:
          datacenter: dc2                # 添加数据中心标签
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - target_label: __address__
        replacement: 192.168.2.50:9610   # ← 远程 Exporter 地址
```

#### 对比：Redfish vs IPMI

| 特性 | Redfish | IPMI |
|------|---------|------|
| 协议 | REST API (HTTPS) | UDP 623 + RMCP |
| 数据格式 | JSON | 二进制 |
| 安全性 | ✅ 强（HTTPS、RBAC） | ⚠️ 弱（明文密码、CVE 漏洞多） |
| 标准化 | ✅ DMTF 统一标准 | ⚠️ 各厂商实现不同 |
| 支持厂商 | 所有新一代服务器 | 老服务器 |
| 监控粒度 | ✅ 详细（SMART、固件、网卡等） | ⚠️ 基础（温度、风扇、电源） |
| 推荐场景 | **新服务器（2015 年后）** | 老服务器兜底 |

**迁移建议**:
- ✅ 新服务器：优先使用 Redfish
- ⚠️ 老服务器（2015 年前）：如果不支持 Redfish，使用 IPMI Exporter
- 🔄 混合环境：同时部署 Redfish + IPMI，按需选择

#### 故障排查

**问题 1：无法连接到 Redfish API**
```bash
# 检查 1: 测试网络连通性
ping 192.168.1.100

# 检查 2: 测试 HTTPS 端口
curl -k https://192.168.1.100/redfish/v1/

# 可能原因:
# - 管理口 IP 配置错误
# - 防火墙阻止
# - Redfish 功能未启用（进入 iDRAC/iLO 设置启用）
```

**问题 2：认证失败**
```bash
# 测试凭据
curl -k -u root:calvin https://192.168.1.100/redfish/v1/Systems

# 可能原因:
# - 密码错误
# - 账号被锁定
# - 需要修改默认密码后才能使用 API
```

**问题 3：某些指标缺失**
```bash
# 检查 Redfish 版本和支持的功能
curl -k -u root:calvin https://192.168.1.100/redfish/v1/ | jq .RedfishVersion

# 可能原因:
# - 老版本固件（升级 iDRAC/iLO 固件）
# - 硬件不支持（如无 RAID 卡则无 RAID 指标）
```

---

### 9. LLDP Topology Discovery - 拓扑发现

#### 作用
- 通过 SNMP 采集 LLDP 邻居信息
- 自动生成网络拓扑图
- 自动计算设备层级（core/aggregation/access）
- 生成拓扑标签文件供其他组件使用

#### 工作流程
```
1. 每 5 分钟运行一次（定时任务）
2. 读取 config/topology/devices.yml
3. SNMP 查询 LLDP-MIB (1.0.8802.1.1.2)
4. 分析邻居关系
5. 计算设备层级
6. 生成 4 个文件：
   - data/topology/topology.json
   - config/vmagent/targets/topology-switches.json
   - config/vmagent/targets/topology-servers.json
   - data/topology/telegraf-labels.json
7. 重载 vmagent 配置
```

#### 配置文件位置
```
config/topology/devices.yml              # 设备清单
scripts/topology/lldp_discovery.py       # 发现脚本
scripts/topology/run_discovery.sh        # 运行脚本
```

#### 设备清单配置
```yaml
# config/topology/devices.yml
devices:
  # ===== 核心交换机 =====
  - name: Switch-Core-01
    host: 192.168.1.100
    type: switch
    tier: core                    # 手动指定层级（可选）
    location: dc1-rack-A01
    vendor: cisco
    model: Catalyst 9300
    snmp_community: public
    snmp_version: 2c

  # ===== 接入交换机 =====
  - name: Switch-Access-01
    host: 192.168.1.101
    type: switch
    tier: access
    location: dc1-rack-B01
    snmp_community: public
    snmp_version: 2c

  # ===== ESXi 主机 =====
  - name: ESXi-Host-01
    host: 192.168.1.200
    type: esxi
    tier: core
    location: dc1-rack-A01
    snmp_community: public
    snmp_version: 2c

  # ===== Linux 服务器 =====
  - name: Web-Server-01
    host: 192.168.1.10
    type: server
    # tier 会自动计算
    location: dc1-rack-B01
```

#### 添加新设备到拓扑发现

**步骤 1：确保设备启用 LLDP**
```cisco
# Cisco
lldp run

# Arista
lldp run

# Juniper
set protocols lldp interface all
commit
```

**步骤 2：添加到设备清单**
```bash
vim config/topology/devices.yml

# 添加新设备
devices:
  - name: Switch-New-01
    host: 192.168.1.110
    type: switch
    location: dc1-rack-C01
    snmp_community: public
    snmp_version: 2c
```

**步骤 3：重启拓扑发现**
```bash
docker-compose restart topology-discovery

# 查看日志
docker-compose logs -f topology-discovery
```

**步骤 4：验证生成的文件**
```bash
# 查看完整拓扑
cat data/topology/topology.json | jq '.'

# 查看交换机标签文件
cat config/vmagent/targets/topology-switches.json | jq '.'

# 查看服务器标签文件
cat config/vmagent/targets/topology-servers.json | jq '.'
```

#### 生成的文件示例

**topology-switches.json** (供 SNMP Exporter 使用):
```json
[
  {
    "targets": ["192.168.1.100"],
    "labels": {
      "device_name": "Switch-Core-01",
      "device_type": "switch",
      "device_tier": "core",
      "device_location": "dc1-rack-A01",
      "device_vendor": "cisco",
      "topology_discovered": "true"
    }
  },
  {
    "targets": ["192.168.1.101"],
    "labels": {
      "device_name": "Switch-Access-01",
      "device_type": "switch",
      "device_tier": "access",
      "device_location": "dc1-rack-B01",
      "connected_switch": "Switch-Core-01",
      "connected_switch_port": "GigabitEthernet1/0/1",
      "topology_discovered": "true"
    }
  }
]
```

**topology-servers.json** (供 Node Exporter 使用):
```json
[
  {
    "targets": ["192.168.1.10:9100"],
    "labels": {
      "device_name": "Web-Server-01",
      "device_type": "server",
      "device_tier": "access",
      "device_location": "dc1-rack-B01",
      "connected_switch": "Switch-Access-01",
      "connected_switch_port": "GigabitEthernet1/0/10",
      "topology_discovered": "true"
    }
  }
]
```

#### 验证拓扑标签是否注入到指标
```bash
# 查询带拓扑标签的 SNMP 指标
curl 'http://localhost:8428/api/v1/query?query=up{topology_discovered="true",job="snmp-topology"}'

# 查询带拓扑标签的 Node Exporter 指标
curl 'http://localhost:8428/api/v1/query?query=up{topology_discovered="true",job="node-topology"}'

# 查询特定层级的设备
curl 'http://localhost:8428/api/v1/query?query=up{device_tier="core"}'
```

---

### 15. Alertmanager - 告警管理

#### 作用
- 接收 vmalert/Loki Ruler 发送的告警
- 智能分组、抑制、路由
- 发送通知（邮件、钉钉、企业微信等）

#### 配置文件位置
```
config/alertmanager/alertmanager.yml
```

#### 关键配置（含 20+ 抑制规则）
```yaml
# config/alertmanager/alertmanager.yml
global:
  # 邮件配置
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@example.com'
  smtp_auth_username: 'alerts@example.com'
  smtp_auth_password: 'your-app-password'
  smtp_require_tls: true

# 路由配置
route:
  receiver: 'default'
  group_by: ['alertname', 'device_tier', 'datacenter']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 4h

  # 按优先级路由
  routes:
    # P0 - 紧急告警（核心设备故障）
    - match:
        severity: critical
        device_tier: core
      receiver: 'p0-oncall'
      group_wait: 0s
      repeat_interval: 5m

    # P1 - 高优先级（接入设备故障）
    - match:
        severity: critical
      receiver: 'p1-team'
      repeat_interval: 15m

    # P2 - 中等优先级（性能告警）
    - match:
        severity: warning
      receiver: 'p2-email'
      repeat_interval: 1h

# 接收器配置
receivers:
  - name: 'default'
    email_configs:
      - to: 'ops-team@example.com'

  - name: 'p0-oncall'
    email_configs:
      - to: 'oncall@example.com'
        headers:
          Subject: '[P0] {{ .GroupLabels.alertname }}'
    # 钉钉通知
    webhook_configs:
      - url: 'https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN'

  - name: 'p1-team'
    email_configs:
      - to: 'team@example.com'

  - name: 'p2-email'
    email_configs:
      - to: 'notifications@example.com'

# ===== 智能抑制规则（20+ 条）=====
inhibit_rules:
  # ===== 规则 1-5: 主机级别抑制 =====
  # 规则 1: 主机宕机 → 抑制该主机的所有其他告警
  - source_match:
      alertname: 'HostDown'
    target_match_re:
      alertname: '(HostCPUHigh|HostMemoryHigh|HostDiskFull|HostNetworkSlow)'
    equal: ['instance']

  # 规则 2: 主机 CPU 高 → 抑制网络延迟告警
  - source_match:
      alertname: 'HostCPUHigh'
    target_match:
      alertname: 'HostNetworkLatency'
    equal: ['instance']

  # ===== 规则 6-10: 网络拓扑抑制 =====
  # 规则 6: 核心交换机故障 → 抑制接入交换机告警
  - source_match:
      alertname: 'SwitchDown'
      device_tier: 'core'
    target_match:
      alertname: 'SwitchDown'
      device_tier: 'access'
    equal: ['datacenter']  # 同一数据中心

  # 规则 7: 交换机故障 → 抑制连接到该交换机的服务器告警
  - source_match:
      alertname: 'SwitchDown'
    target_match:
      alertname: 'HostDown'
    equal: ['connected_switch']  # ← 拓扑标签！

  # 规则 8: 核心交换机 CPU 高 → 抑制网络延迟告警
  - source_match:
      alertname: 'SwitchCPUHigh'
      device_tier: 'core'
    target_match_re:
      alertname: '(NetworkLatency|PacketLoss)'
    equal: ['datacenter']

  # ===== 规则 11-15: VMware 层级抑制 =====
  # 规则 11: ESXi 主机故障 → 抑制该主机上所有 VM 告警
  - source_match:
      alertname: 'ESXiHostDown'
    target_match_re:
      alertname: '(VMCPUHigh|VMMemoryHigh|VMDiskSlow)'
    equal: ['esxi_host']

  # 规则 12: vCenter 连接丢失 → 抑制所有 VMware 告警
  - source_match:
      alertname: 'vCenterConnectionLost'
    target_match_re:
      alertname: '(ESXi.*|VM.*|Datastore.*)'
    equal: ['vcenter']

  # ===== 规则 16-20: 服务依赖抑制 =====
  # 规则 16: 网站宕机 → 抑制慢响应告警
  - source_match:
      alertname: 'WebsiteDown'
    target_match:
      alertname: 'WebsiteSlowResponse'
    equal: ['instance']

  # 规则 17: 数据库主从切换 → 抑制连接数告警
  - source_match:
      alertname: 'DatabaseFailover'
    target_match:
      alertname: 'DatabaseConnectionHigh'
    equal: ['cluster']
```

#### 配置邮件通知

**Gmail 示例：**
```yaml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'your-email@gmail.com'
  smtp_auth_username: 'your-email@gmail.com'
  smtp_auth_password: 'your-app-password'  # ← 应用专用密码！
  smtp_require_tls: true
```

**企业邮箱示例：**
```yaml
global:
  smtp_smarthost: 'smtp.company.com:25'
  smtp_from: 'alerts@company.com'
  smtp_auth_username: 'alerts@company.com'
  smtp_auth_password: 'password'
  smtp_require_tls: false
```

#### 配置钉钉通知

```yaml
receivers:
  - name: 'dingtalk'
    webhook_configs:
      - url: 'https://oapi.dingtalk.com/robot/send?access_token=YOUR_ACCESS_TOKEN'
        send_resolved: true
```

**钉钉机器人创建步骤：**
1. 打开钉钉群 → 群设置 → 智能群助手 → 添加机器人
2. 选择"自定义"→ 安全设置选择"加签"
3. 复制 Webhook 地址

#### 验证方式
```bash
# 1. 检查配置
docker-compose exec alertmanager amtool config show

# 2. 查看当前告警
curl http://localhost:9093/api/v2/alerts | jq '.'

# 3. 测试发送告警
docker-compose exec alertmanager amtool alert add \
  alertname=TestAlert \
  severity=warning \
  summary="This is a test alert"

# 4. 测试邮件发送
curl -X POST http://localhost:9093/api/v2/alerts -d '[
  {
    "labels": {
      "alertname": "TestEmailAlert",
      "severity": "critical"
    },
    "annotations": {
      "summary": "Test email notification"
    }
  }
]'
```

---

## 📋 设备添加指南

### 场景 1：添加 Linux 服务器

```bash
# ===== 步骤 1: 在目标服务器上安装 Node Exporter =====
wget https://github.com/prometheus/node_exporter/releases/download/v1.7.0/node_exporter-1.7.0.linux-amd64.tar.gz
tar xvfz node_exporter-1.7.0.linux-amd64.tar.gz
sudo cp node_exporter-1.7.0.linux-amd64/node_exporter /usr/local/bin/

sudo cat > /etc/systemd/system/node_exporter.service << 'EOF'
[Unit]
Description=Node Exporter
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/node_exporter --web.listen-address=:9100

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now node_exporter

# ===== 步骤 2: 添加到拓扑发现 =====
# 在监控服务器上编辑
vim config/topology/devices.yml

# 添加设备
devices:
  - name: New-Server-01
    host: 192.168.1.30
    type: server
    location: dc1-rack-D01

# ===== 步骤 3: 重启拓扑发现 =====
docker-compose restart topology-discovery

# ===== 步骤 4: 验证（60秒后）=====
curl 'http://localhost:8428/api/v1/query?query=up{instance="192.168.1.30:9100"}'
```

### 场景 2：添加网络交换机

```bash
# ===== 步骤 1: 在交换机上配置 SNMP 和 LLDP =====
# Cisco 示例
configure terminal
snmp-server community public RO
lldp run
logging host 192.168.1.50  # 监控服务器 IP
end
write memory

# ===== 步骤 2: 测试 SNMP 连通性 =====
# 在监控服务器上
snmpwalk -v2c -c public 192.168.1.120 sysDescr

# ===== 步骤 3: 添加到拓扑发现 =====
vim config/topology/devices.yml

devices:
  - name: Switch-New-01
    host: 192.168.1.120
    type: switch
    tier: access  # 或让系统自动计算
    location: dc1-rack-E01
    snmp_community: public
    snmp_version: 2c

# ===== 步骤 4: 重启拓扑发现 =====
docker-compose restart topology-discovery

# ===== 步骤 5: 验证 =====
# 检查生成的文件
cat config/vmagent/targets/topology-switches.json | grep 192.168.1.120

# 检查 SNMP 采集
curl 'http://localhost:8428/api/v1/query?query=up{instance="192.168.1.120"}'

# 检查接口流量
curl 'http://localhost:8428/api/v1/query?query=ifHCInOctets{instance="192.168.1.120"}'
```

### 场景 3：添加 VMware vCenter

```bash
# ===== 步骤 1: 创建监控账号（在 vCenter 中）=====
# 1. 登录 vCenter
# 2. 菜单 → 管理 → 单点登录 → 用户和组
# 3. 创建用户: monitoring@vsphere.local
# 4. 分配只读权限

# ===== 步骤 2: 编辑 Telegraf 配置 =====
vim config/telegraf/telegraf.conf

# 修改 vSphere 输入
[[inputs.vsphere]]
  vcenters = ["https://vcenter.example.com/sdk"]
  username = "monitoring@vsphere.local"
  password = "your-password"
  insecure_skip_verify = true
  interval = "60s"

# ===== 步骤 3: 重启 Telegraf =====
docker-compose restart telegraf-vmware

# ===== 步骤 4: 查看日志确认连接 =====
docker-compose logs -f telegraf-vmware | grep "Connected to"

# ===== 步骤 5: 验证指标 =====
curl 'http://localhost:8428/api/v1/query?query=vsphere_host_cpu_usage_average'
```

### 场景 4：添加网站监控

```bash
# ===== 编辑 vmagent 配置 =====
vim config/vmagent/prometheus.yml

# 添加到 blackbox-http job
scrape_configs:
  - job_name: 'blackbox-http'
    metrics_path: /probe
    params:
      module: [http_2xx]
    static_configs:
      - targets:
        - https://newwebsite.com        # ← 新网站
        - https://api.newsite.com/health  # ← 新 API
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: blackbox-exporter:9115

# ===== 重载 vmagent =====
curl -X POST http://localhost:8429/-/reload

# ===== 验证 =====
curl 'http://localhost:8428/api/v1/query?query=probe_success{instance="https://newwebsite.com"}'
```

---

## 🌐 分布式部署场景

### 场景 A：多数据中心统一监控

**架构：**
```
                    ┌─────────────────────┐
                    │   中心监控服务器      │
                    │   192.168.1.50      │
                    ├─────────────────────┤
                    │ VictoriaMetrics     │◄──────┐
                    │ Loki                │◄────┐ │
                    │ Grafana             │     │ │
                    │ Alertmanager        │     │ │
                    └─────────────────────┘     │ │
                                                │ │
                    ┌───────────────────────────┘ │
                    │                             │
       ┌────────────┴─────────┐   ┌──────────────┴────────┐
       │   数据中心 A (北京)    │   │   数据中心 B (上海)    │
       │   10.10.0.0/16       │   │   10.20.0.0/16        │
       ├──────────────────────┤   ├───────────────────────┤
       │ vmagent              │   │ vmagent               │
       │ Promtail             │   │ Promtail              │
       │ SNMP Exporter        │   │ SNMP Exporter         │
       │ Node Exporter (多台)  │   │ Node Exporter (多台)   │
       │ LLDP Discovery       │   │ LLDP Discovery        │
       └──────────────────────┘   └───────────────────────┘
```

**中心服务器配置（192.168.1.50）：**
```yaml
# docker-compose.yaml
services:
  victoriametrics:
    ports:
      - "0.0.0.0:8428:8428"  # 监听所有网卡

  loki:
    ports:
      - "0.0.0.0:3100:3100"

  grafana:
    ports:
      - "0.0.0.0:3000:3000"

  alertmanager:
    ports:
      - "0.0.0.0:9093:9093"
```

**数据中心 A 配置（10.10.1.100）：**
```yaml
# docker-compose.yaml（只部署采集组件）
services:
  # vmagent - 指标采集
  vmagent:
    image: victoriametrics/vmagent:latest
    volumes:
      - ./config/vmagent/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./config/vmagent/targets:/etc/prometheus/targets
    command:
      - "--promscrape.config=/etc/prometheus/prometheus.yml"
      - "--remoteWrite.url=http://192.168.1.50:8428/api/v1/write"
      - "--remoteWrite.label=datacenter=beijing"  # ← 添加数据中心标签
      - "--remoteWrite.label=region=north"
    networks:
      - monitoring

  # Promtail - 日志采集
  promtail:
    image: grafana/promtail:latest
    volumes:
      - ./config/promtail/promtail.yml:/etc/promtail/promtail.yml
      - /var/log:/var/log:ro
    command:
      - "-config.file=/etc/promtail/promtail.yml"
      - "-client.url=http://192.168.1.50:3100/loki/api/v1/push"  # ← 中心 Loki
      - "-client.external-labels=datacenter=beijing,region=north"

  # 本地 Exporter
  snmp-exporter:
    image: prom/snmp-exporter:latest
    ports:
      - "9116:9116"
    volumes:
      - ./config/snmp-exporter/snmp.yml:/etc/snmp_exporter/snmp.yml

  # 拓扑发现
  topology-discovery:
    build:
      context: .
      dockerfile: Dockerfile.topology
    volumes:
      - ./config/topology/devices.yml:/etc/topology/devices.yml
      - ./scripts/topology:/scripts
      - ./data/topology:/data/topology
      - ./config/vmagent/targets:/etc/prometheus/targets
    environment:
      - DISCOVERY_INTERVAL=300
```

**数据中心 B 配置（10.20.1.100）：**
```yaml
# 与数据中心 A 类似，但修改标签
services:
  vmagent:
    command:
      - "--remoteWrite.url=http://192.168.1.50:8428/api/v1/write"
      - "--remoteWrite.label=datacenter=shanghai"  # ← 不同标签
      - "--remoteWrite.label=region=south"

  promtail:
    command:
      - "-client.url=http://192.168.1.50:3100/loki/api/v1/push"
      - "-client.external-labels=datacenter=shanghai,region=south"
```

**Grafana 查询示例：**
```promql
# 查询北京数据中心的 CPU
100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle",datacenter="beijing"}[5m])) * 100)

# 查询上海数据中心的网络流量
rate(node_network_receive_bytes_total{datacenter="shanghai"}[5m])

# 对比两个数据中心
sum by (datacenter) (up)
```

---

### 场景 B：边缘机房轻量部署

**架构：**
```
边缘机房（资源受限，10-20 台服务器）
├─ vmagent (轻量采集)
├─ Node Exporter (每台服务器)
└─ 定时同步 → 中心服务器
```

**边缘机房配置（最小化部署）：**
```yaml
# docker-compose.yaml（仅 vmagent）
version: '3.8'

services:
  vmagent:
    image: victoriametrics/vmagent:latest
    container_name: vmagent
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - vmagentdata:/vmagentdata
    command:
      - "--promscrape.config=/etc/prometheus/prometheus.yml"
      - "--remoteWrite.url=http://192.168.1.50:8428/api/v1/write"
      - "--remoteWrite.label=site=edge-office-01"
      - "--remoteWrite.tmpDataPath=/vmagentdata"
      - "--memory.allowedPercent=30"  # 限制内存使用
    restart: unless-stopped
    network_mode: host  # 使用主机网络，减少开销

volumes:
  vmagentdata:
```

**prometheus.yml（简化配置）：**
```yaml
global:
  scrape_interval: 30s  # 延长采集间隔

scrape_configs:
  # 只采集关键指标
  - job_name: 'node'
    static_configs:
      - targets:
        - '10.30.1.10:9100'
        - '10.30.1.11:9100'
        # ... 其他服务器
    metric_relabel_configs:
      # 过滤掉不需要的指标，减少数据量
      - source_labels: [__name__]
        regex: 'node_(network|disk|cpu|memory|filesystem).*'
        action: keep
```

---

### 场景 C：高可用部署

**VictoriaMetrics 集群模式：**
```
                    ┌─────────────┐
                    │  VM Insert  │  (8480)
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
       ┌──────────┐ ┌──────────┐ ┌──────────┐
       │VM Storage│ │VM Storage│ │VM Storage│
       │  Node 1  │ │  Node 2  │ │  Node 3  │
       └────┬─────┘ └────┬─────┘ └────┬─────┘
            └────────────┼────────────┘
                         ▼
                  ┌──────────┐
                  │ VM Select│  (8481)
                  └──────────┘
                         ▲
                         │
                    ┌────┴────┐
                    │ Grafana │
                    └─────────┘
```

详见官方文档：https://docs.victoriametrics.com/Cluster-VictoriaMetrics.html

---

## 🔧 故障排查

### 问题 1：vmagent 无法采集目标

**症状：**
```bash
curl http://localhost:8429/targets
# 显示 target 状态为 "down" 或 "unknown"
```

**排查步骤：**
```bash
# 1. 检查目标是否可达
curl http://192.168.1.10:9100/metrics

# 2. 检查防火墙
sudo iptables -L -n | grep 9100

# 3. 检查 vmagent 日志
docker-compose logs vmagent | grep ERROR

# 4. 检查配置文件语法
docker-compose exec vmagent cat /etc/prometheus/prometheus.yml

# 5. 手动重载配置
curl -X POST http://localhost:8429/-/reload
```

### 问题 2：拓扑发现没有数据

**症状：**
```bash
cat config/vmagent/targets/topology-switches.json
# 输出: []
```

**排查步骤：**
```bash
# 1. 检查设备清单
cat config/topology/devices.yml

# 2. 测试 SNMP 连通性
snmpwalk -v2c -c public 192.168.1.100 1.0.8802.1.1.2

# 3. 查看拓扑发现日志
docker-compose logs topology-discovery

# 4. 手动运行发现脚本
docker-compose exec topology-discovery python3 /scripts/lldp_discovery.py

# 5. 检查权限
ls -la config/vmagent/targets/
# 确保 vmagent 可以读取文件
```

### 问题 3：告警不发送

**症状：**告警触发但不发送邮件

**排查步骤：**
```bash
# 1. 检查 Alertmanager 配置
docker-compose exec alertmanager amtool config show

# 2. 查看当前告警
curl http://localhost:9093/api/v2/alerts | jq '.'

# 3. 检查路由匹配
docker-compose exec alertmanager amtool config routes test \
  severity=critical \
  alertname=TestAlert

# 4. 测试 SMTP 连接
docker-compose exec alertmanager sh -c "
  telnet smtp.gmail.com 587
"

# 5. 查看 Alertmanager 日志
docker-compose logs alertmanager | grep -i error

# 6. 手动发送测试告警
curl -X POST http://localhost:9093/api/v2/alerts -H 'Content-Type: application/json' -d '[
  {
    "labels": {"alertname":"TestAlert","severity":"warning"},
    "annotations": {"summary":"Test alert"}
  }
]'
```

### 问题 4：Grafana 无数据

**排查步骤：**
```bash
# 1. 检查数据源连接
curl http://localhost:3000/api/datasources

# 2. 测试 VictoriaMetrics 查询
curl 'http://localhost:8428/api/v1/query?query=up'

# 3. 检查数据是否存在
curl 'http://localhost:8428/api/v1/label/__name__/values' | jq '.'

# 4. 在 Grafana 中测试查询
# Explore → VictoriaMetrics → 输入: up

# 5. 检查时间范围
# 确保 Grafana 的时间范围包含有数据的时间段
```

---

## 📊 总结

本手册详细说明了：

- ✅ **16 个组件**的详细配置和数据流向
- ✅ **4 种场景**的设备添加方法
- ✅ **3 种部署模式**（单机/分布式/高可用）
- ✅ **完整的故障排查**流程

**关键要点：**
1. **理解数据流**：数据从哪里来，到哪里去
2. **标签注入**：拓扑标签贯穿整个系统
3. **分层架构**：采集层 → 存储层 → 分析层 → 展示层
4. **灵活部署**：支持单机/分布式/边缘等多种场景

---

<div align="center">

**Made with ❤️ by the Community**

[⬆ 返回顶部](#-完整部署和使用手册-deployment-guide)

</div>
