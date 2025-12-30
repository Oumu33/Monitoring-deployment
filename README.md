# 🚀 Enterprise Infrastructure Observability Platform

<div align="center">

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-20.10%2B-blue.svg)](https://www.docker.com/)
[![VictoriaMetrics](https://img.shields.io/badge/VictoriaMetrics-latest-green.svg)](https://victoriametrics.com/)
[![Grafana](https://img.shields.io/badge/Grafana-latest-orange.svg)](https://grafana.com/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

**完整的企业级基础设施可观测性平台**
*Metrics + Logs + Topology | 自动根因分析 | 智能告警 | 零配置*

[快速开始](#-quick-start) • [功能特性](#-features) • [架构设计](#-architecture) • [文档](#-documentation) • [贡献](#-contributing)

</div>

---

## 📖 目录

- [🎯 项目简介](#-项目简介)
- [✨ 核心特性](#-核心特性)
- [🏗️ 系统架构](#️-系统架构)
- [🚀 快速开始](#-快速开始)
- [📊 监控覆盖](#-监控覆盖)
- [🗺️ 拓扑自动发现](#️-拓扑自动发现)
- [📝 日志聚合](#-日志聚合)
- [🔔 智能告警](#-智能告警)
- [📚 完整文档](#-完整文档)
- [🛠️ 维护管理](#️-维护管理)
- [🤝 贡献指南](#-贡献指南)
- [📄 许可证](#-许可证)

---

## 🎯 项目简介

这是一个**生产就绪**的企业级基础设施可观测性平台，基于 **VictoriaMetrics** 构建，实现了：

- ✅ **完整可观测性三支柱**：Metrics（指标） + Logs（日志） + Topology（拓扑）
- ✅ **自动根因分析**：20+ 智能抑制规则，从 20 个告警降到 1 个根因告警
- ✅ **拓扑自动发现**：LLDP 自动采集，零配置生成网络拓扑图
- ✅ **全方位监控**：主机、虚拟化、网络、硬件、服务、日志一网打尽
- ✅ **企业级性能**：单节点支持 100+ 设备，保留 12 个月数据

### 🎯 适用场景

| 场景 | 说明 |
|------|------|
| **混合基础设施** | Linux 主机 + VMware + 网络设备 + 物理服务器 |
| **多数据中心** | 支持多 vCenter、多网段统一监控 |
| **DevOps 团队** | 快速部署、自动化程度高、低维护成本 |
| **企业级生产** | 高可用、高性能、完整的告警和可视化 |

---

## ✨ 核心特性

### 🎯 智能根因分析

**传统监控的痛点**：核心交换机故障 → 收到 20 封告警邮件 → 手动排查 30 分钟

**本平台的方案**：
```
1. 检测到 Switch-Core-01 (tier=core) 故障
2. 自动抑制所有下游告警（tier=access 交换机、连接的服务器）
3. 发送 1 封精准根因邮件："核心交换机故障，影响 5 台接入交换机和 20 台服务器"
4. 定位时间：< 1 分钟
```

**效果对比**：

| 指标 | 传统监控 | 本平台 | 提升 |
|------|---------|--------|------|
| 告警数量 | 20+ 封邮件 | 1 封根因邮件 | **95% ↓** |
| 故障定位 | 30 分钟 | 1 分钟 | **97% ↓** |
| 运维压力 | 高 | 低 | **显著降低** |

### 🗺️ 拓扑自动发现（零配置）

- **LLDP 自动采集**：每 5 分钟自动采集所有网络设备邻居信息
- **智能层级计算**：自动识别 core/aggregation/access 层级
- **标签自动注入**：设备标签自动应用到所有监控指标
- **可视化拓扑图**：Grafana Node Graph 自动渲染网络拓扑
- **告警联动**：拓扑标签直接用于 Alertmanager 根因分析

### 📊 全方位监控

<table>
<tr>
<td width="33%">

**🖥️ 主机监控**
- CPU / 内存 / 磁盘
- 网络流量 / 连接数
- 进程 / 服务状态
- 文件系统 / IO

</td>
<td width="33%">

**☁️ 虚拟化监控**
- VMware vSphere
- ESXi 主机资源
- VM 性能指标
- 数据存储容量

</td>
<td width="33%">

**🌐 网络监控**
- SNMP (传统设备)
- gNMI (流式遥测)
- 接口流量/错误
- BGP/OSPF 状态

</td>
</tr>
<tr>
<td width="33%">

**🔍 服务监控**
- HTTP/HTTPS 可用性
- SSL 证书过期
- API 健康检查
- DNS 解析监控

</td>
<td width="33%">

**🔧 硬件监控**
- 服务器温度
- 风扇转速
- 电源状态
- RAID / 硬盘健康

</td>
<td width="33%">

**📝 日志聚合**
- 系统日志 (Syslog)
- 网络设备日志
- 应用日志
- 容器日志

</td>
</tr>
</table>

### ⚡ 技术亮点

| 特性 | 说明 | 优势 |
|------|------|------|
| **三层标签注入** | File SD + Telegraf Processor + Recording Rules | 覆盖所有采集器 |
| **推送 + 拉取混合** | SNMP/node_exporter (拉取) + Telegraf (推送) | 最佳性能 |
| **gNMI 流式遥测** | 替代 SNMP，秒级实时数据 | 新一代网络监控 |
| **Loki 日志聚合** | 比 ELK 轻量 10 倍 | 低资源占用 |
| **VictoriaMetrics** | 比 Prometheus 快 10 倍，存储省 7 倍 | 企业级性能 |

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        数据采集层                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Node Exporter ──┐                                               │
│  SNMP Exporter ──┼──> vmagent ──> VictoriaMetrics               │
│  Blackbox  ──────┘         ↓            ↓                        │
│                         vmalert ──> Alertmanager                 │
│  Telegraf (VMware) ─────────┘            ↓                       │
│  Telegraf (gNMI) ────────────────────> Grafana                   │
│                                          ↓                        │
│  Promtail ──────> Loki ──────────────> Grafana                   │
│  Syslog-NG ──────┘                                               │
│                                                                   │
│  LLDP Discovery ──> Topology Exporter ──> VictoriaMetrics       │
│        ↓                                                         │
│   拓扑标签自动注入到所有设备指标                                    │
└─────────────────────────────────────────────────────────────────┘
```

### 核心组件

| 组件 | 作用 | 端口 |
|------|------|------|
| **VictoriaMetrics** | 时序数据库（12 个月保留） | 8428 |
| **vmagent** | 指标采集代理 | 8429 |
| **vmalert** | 告警规则引擎 | 8880 |
| **Alertmanager** | 智能告警管理 | 9093 |
| **Grafana** | 可视化平台 | 3000 |
| **Loki** | 日志聚合存储 | 3100 |
| **Topology Exporter** | 拓扑指标导出 | 9700 |

---

## 🚀 快速开始

### 前置要求

- Docker 20.10+
- Docker Compose 2.0+
- 4GB+ 可用内存
- 20GB+ 可用磁盘

### ⚡ 5 分钟快速部署

```bash
# 1. 克隆仓库
git clone https://github.com/YOUR-USERNAME/monitoring-platform.git
cd monitoring-platform

# 2. 配置环境变量（可选）
cp .env.example .env
vim .env

# 3. 启动所有服务
docker-compose up -d

# 4. 检查服务状态
docker-compose ps

# 5. 访问 Grafana
# URL: http://localhost:3000
# 默认账号: admin / admin
```

### 🔧 配置监控目标

#### 1️⃣ 添加 Linux 主机

编辑 `config/vmagent/prometheus.yml`：

```yaml
- job_name: 'node-exporter'
  static_configs:
    - targets: ['192.168.1.10:9100']
      labels:
        instance: 'web-server-01'
        role: 'web'
```

#### 2️⃣ 配置 VMware vCenter

编辑 `config/telegraf/telegraf.conf`：

```toml
[[inputs.vsphere]]
  vcenters = ["https://vcenter.example.com/sdk"]
  username = "monitoring@vsphere.local"
  password = "your-password"
  insecure_skip_verify = true
```

#### 3️⃣ 添加网络设备（SNMP）

```yaml
- job_name: 'snmp-exporter'
  static_configs:
    - targets:
      - 192.168.1.100  # 交换机
      - 192.168.1.101  # 路由器
```

#### 4️⃣ 配置拓扑发现

编辑 `config/topology/devices.yml`：

```yaml
devices:
  - name: Switch-Core-01
    host: 192.168.1.100
    type: switch
    tier: core
    snmp_community: public
```

```bash
# 启动拓扑发现
docker-compose up -d topology-discovery topology-exporter
```

### 📧 配置告警通知

编辑 `config/alertmanager/alertmanager.yml`：

```yaml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@example.com'
  smtp_auth_username: 'alerts@example.com'
  smtp_auth_password: 'your-app-password'
```

---

## 📊 监控覆盖

### 监控类型

| 类型 | 监控对象 | 采集器 | 指标数量 |
|------|---------|--------|----------|
| 🖥️ **主机** | CPU、内存、磁盘、网络 | Node Exporter | 500+ |
| ☁️ **虚拟化** | VMware vSphere | Telegraf | 300+ |
| 🌐 **网络** | 交换机、路由器（SNMP） | SNMP Exporter | 200+ |
| 🌐 **网络** | 新设备（gNMI 流式） | Telegraf gNMI | 实时推送 |
| 🔍 **服务** | HTTP/HTTPS/ICMP/TCP | Blackbox | 50+ |
| 🔧 **硬件** | 温度、风扇、电源 | Redfish/IPMI | 100+ |
| 📝 **日志** | Syslog、应用日志 | Loki | 无限 |
| 🗺️ **拓扑** | LLDP 自动发现 | Topology Discovery | 自动 |

### 预置告警规则

- ✅ **主机告警**（15 条）：CPU、内存、磁盘、网络
- ✅ **VMware 告警**（12 条）：ESXi、VM、数据存储
- ✅ **网络告警**（10 条）：设备宕机、接口 Down、流量异常
- ✅ **服务告警**（8 条）：网站宕机、SSL 证书过期
- ✅ **监控系统告警**（5 条）：采集失败、存储不足

---

## 🗺️ 拓扑自动发现

### 工作原理

```
网络设备 (LLDP)
    ↓ SNMP
LLDP Discovery (Python)
    ├─ 采集邻居信息
    ├─ 生成拓扑图
    ├─ 计算层级 (core/agg/access)
    └─ 生成标签文件
        ↓
vmagent (File SD)
    ├─ topology-switches.json (SNMP 设备)
    └─ topology-servers.json (Linux 主机)
        ↓
VictoriaMetrics
    所有指标自动带拓扑标签:
    up{device_tier="core", connected_switch="SW-01"}
```

### 自动生成的标签

```json
{
  "device_name": "Server-01",
  "device_type": "server",
  "device_tier": "access",
  "device_location": "dc1-rack-A01",
  "connected_switch": "Switch-Access-01",
  "connected_switch_port": "Gi0/1",
  "topology_discovered": "true"
}
```

### 根因分析示例

**场景**：核心交换机故障

```
检测到的告警：
1. SwitchDown (Switch-Core-01, tier=core)         ← 根因
2. SwitchDown (Switch-Access-01, tier=access)     ← 被抑制
3. SwitchDown (Switch-Access-02, tier=access)     ← 被抑制
4. HostDown (Server-01, connected_switch=Access-01) ← 被抑制
5. HostDown (Server-02, connected_switch=Access-02) ← 被抑制

Alertmanager 处理：
- 检测到 Switch-Core-01 (tier=core) 故障
- 自动抑制所有 tier=access 的交换机告警
- 自动抑制连接到这些交换机的服务器告警

最终发送 1 封邮件：
"核心交换机 Switch-Core-01 故障，影响 2 个接入交换机和 2 台服务器"
```

详细文档：[docs/TOPOLOGY-DISCOVERY.md](docs/TOPOLOGY-DISCOVERY.md)

---

## 📝 日志聚合

### 日志来源

- **主机日志**（Promtail）：Syslog、Auth、Docker、Nginx
- **网络设备日志**（Syslog-NG）：Cisco、Arista、Juniper、Huawei

### Metrics + Logs 联动

**查询示例**：

```promql
# Metrics: 网络延迟突增
rate(node_network_receive_bytes_total[5m])

# Logs: 同一时间的交换机日志
{job="syslog", host="Switch-Core-01"} |~ "error|down"
```

**Grafana 统一视图**：点击时间点，所有面板联动，快速定位问题

详细文档：[docs/OBSERVABILITY-GUIDE.md](docs/OBSERVABILITY-GUIDE.md)

---

## 🔔 智能告警

### 20+ 抑制规则

| 规则类型 | 示例 | 效果 |
|---------|------|------|
| **主机级别** | 主机宕机 → 抑制 CPU/内存告警 | 避免重复告警 |
| **拓扑级别** | 核心交换机故障 → 抑制接入交换机 | 识别根因 |
| **虚拟化级别** | ESXi 宕机 → 抑制所有 VM 告警 | 层级抑制 |
| **服务级别** | 网站宕机 → 抑制慢响应告警 | 关联分析 |

### 优先级路由

| 优先级 | 响应时间 | 通知方式 | 重复间隔 |
|-------|---------|---------|---------|
| **P0** | 15 分钟 | 邮件 + 电话 + 短信 | 5 分钟 |
| **P1** | 30 分钟 | 邮件 + 短信 | 15 分钟 |
| **P2** | 2 小时 | 邮件 | 1 小时 |
| **P3** | 工作日 | 邮件 | 24 小时 |

---

## 📚 完整文档

### 📖 核心文档

| 文档 | 说明 |
|------|------|
| [🚀 快速启动](QUICKSTART.md) | 5 分钟快速部署指南 |
| [📊 可观测性指南](docs/OBSERVABILITY-GUIDE.md) | Metrics + Logs + 根因分析 |
| [🗺️ 拓扑发现](docs/TOPOLOGY-DISCOVERY.md) | LLDP 自动发现 + 标签注入 |
| [📋 最终报告](FINAL-REPORT.md) | 完整功能清单 + 数据流 |

### 🔧 配置指南

| 文档 | 说明 |
|------|------|
| [gNMI 网络监控](docs/GNMI-MONITORING.md) | 新一代流式遥测监控 |
| [硬件监控](docs/HARDWARE-MONITORING.md) | Redfish + IPMI 配置 |
| [VMware 多集群](docs/VMWARE-SOLUTION-COMPARISON.md) | 方案对比和选型 |
| [交换机监控](docs/SWITCH-MONITORING.md) | SNMP 详细配置 |

### 📚 进阶文档

| 文档 | 说明 |
|------|------|
| [性能调优](docs/PERFORMANCE-TUNING.md) | 大规模环境优化 |
| [故障排查](docs/FAQ.md) | 常见问题 FAQ |
| [真实场景](docs/REAL-WORLD-SCENARIOS.md) | 实战案例分析 |
| [告警手册](docs/RUNBOOK.md) | 完整 Runbook |

---

## 🛠️ 维护管理

### 日常操作

```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f victoriametrics
docker-compose logs -f vmagent

# 重启服务
docker-compose restart vmagent

# 更新配置（自动重载）
curl -X POST http://localhost:8429/-/reload
```

### 数据备份

```bash
# 备份 VictoriaMetrics
docker run --rm \
  -v monitoring_vmdata:/source \
  -v $(pwd)/backup:/backup alpine \
  tar czf /backup/vm-$(date +%Y%m%d).tar.gz -C /source .

# 备份 Grafana
docker run --rm \
  -v monitoring_grafana-data:/source \
  -v $(pwd)/backup:/backup alpine \
  tar czf /backup/grafana-$(date +%Y%m%d).tar.gz -C /source .
```

### 访问地址

| 服务 | URL | 默认账号 |
|------|-----|---------|
| Grafana | http://localhost:3000 | admin / admin |
| VictoriaMetrics | http://localhost:8428 | - |
| vmalert | http://localhost:8880 | - |
| Alertmanager | http://localhost:9093 | - |
| Loki | http://localhost:3100 | - |

---

## 🤝 贡献指南

我们欢迎所有形式的贡献！

### 如何贡献

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 贡献方向

- 🐛 报告 Bug
- 💡 提出新功能建议
- 📝 改进文档
- ✨ 提交新的 Exporter 集成
- 🔧 优化配置和性能

详细指南：[CONTRIBUTING.md](CONTRIBUTING.md)

---

## 🙏 致谢

本项目基于以下优秀的开源项目：

- [VictoriaMetrics](https://victoriametrics.com/) - 高性能时序数据库
- [Grafana](https://grafana.com/) - 可视化平台
- [Prometheus](https://prometheus.io/) - 监控生态系统
- [Loki](https://grafana.com/oss/loki/) - 日志聚合系统
- [Alertmanager](https://prometheus.io/docs/alerting/latest/alertmanager/) - 告警管理

---

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源协议。

---

## 📞 联系方式

- **GitHub Issues**: [提交问题](https://github.com/YOUR-USERNAME/monitoring-platform/issues)
- **讨论区**: [GitHub Discussions](https://github.com/YOUR-USERNAME/monitoring-platform/discussions)

---

<div align="center">

### ⭐ 如果这个项目对你有帮助，请给一个 Star！⭐

**Made with ❤️ by the Community**

[⬆ 返回顶部](#-enterprise-infrastructure-observability-platform)

</div>
