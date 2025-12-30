# 🚀 快速启动指南 (Quick Start Guide)

<div align="center">

**5 分钟快速部署完整可观测性平台**

*Metrics + Logs + Topology | 自动化部署 | 开箱即用*

</div>

---

## 📋 目录

- [前置要求](#-前置要求)
- [快速部署](#-快速部署)
- [访问服务](#-访问服务)
- [基础配置](#-基础配置)
- [验证部署](#-验证部署)
- [下一步](#-下一步)
- [常见问题](#-常见问题)

---

## 📦 前置要求

在开始之前，请确保您的系统满足以下要求：

| 要求 | 最低配置 | 推荐配置 |
|------|---------|---------|
| **操作系统** | Linux / macOS / Windows | Ubuntu 22.04 LTS |
| **Docker** | 20.10+ | 24.0+ |
| **Docker Compose** | 2.0+ | 2.20+ |
| **内存** | 4 GB | 8 GB+ |
| **磁盘空间** | 20 GB | 50 GB+ |
| **CPU** | 2 核心 | 4 核心+ |

### 检查环境

```bash
# 检查 Docker 版本
docker --version
# 输出示例: Docker version 24.0.7

# 检查 Docker Compose 版本
docker-compose --version
# 输出示例: Docker Compose version 2.23.0

# 检查可用内存
free -h

# 检查磁盘空间
df -h
```

---

## 🚀 快速部署

### 1️⃣ 克隆仓库

```bash
# 克隆项目
git clone https://github.com/YOUR-USERNAME/monitoring-platform.git
cd monitoring-platform

# 查看项目结构
ls -la
```

### 2️⃣ 配置环境变量（可选）

```bash
# 复制示例配置
cp .env.example .env

# 编辑配置（可选）
vim .env
```

**.env 主要配置项：**

```bash
# Grafana 管理员账号
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin

# VictoriaMetrics 数据保留期（月）
VM_RETENTION_MONTHS=12

# LLDP 发现间隔（秒）
DISCOVERY_INTERVAL=300
```

### 3️⃣ 构建和启动服务

```bash
# 构建拓扑发现服务
docker-compose build topology-discovery topology-exporter

# 启动所有服务（后台运行）
docker-compose up -d

# 查看启动日志
docker-compose logs -f
```

**启动时间：** 首次启动约需 2-3 分钟，请耐心等待。

### 4️⃣ 检查服务状态

```bash
# 查看所有服务状态
docker-compose ps

# 预期输出：所有服务状态为 "Up"
```

**关键服务清单：**

| 服务 | 状态 | 端口 | 作用 |
|------|------|------|------|
| victoriametrics | Up | 8428 | 时序数据库 |
| vmagent | Up | 8429 | 指标采集 |
| vmalert | Up | 8880 | 告警引擎 |
| alertmanager | Up | 9093 | 告警管理 |
| grafana | Up | 3000 | 可视化 |
| loki | Up | 3100 | 日志聚合 |
| topology-discovery | Up | - | 拓扑发现 |
| topology-exporter | Up | 9700 | 拓扑指标 |

---

## 🌐 访问服务

### 主要服务地址

| 服务 | URL | 默认账号 | 说明 |
|------|-----|----------|------|
| **Grafana** | http://localhost:3000 | admin / admin | 可视化平台 |
| **VictoriaMetrics** | http://localhost:8428 | - | 时序数据库 UI |
| **Alertmanager** | http://localhost:9093 | - | 告警管理界面 |
| **vmalert** | http://localhost:8880 | - | 告警规则状态 |
| **Loki** | http://localhost:3100/ready | - | 日志系统状态 |

### 🎨 访问 Grafana

1. **打开浏览器** 访问：http://localhost:3000
2. **登录账号**：
   - 用户名：`admin`
   - 密码：`admin`
3. **首次登录** 会要求修改密码（可跳过）
4. **预置 Dashboard** 已自动加载，可直接使用

### 📊 查看预置 Dashboard

Grafana 左侧菜单 → **Dashboards** → 浏览以下 Dashboard：

- **Network Topology - LLDP Auto-Discovery** - 网络拓扑图
- **Node Exporter Full** - Linux 主机监控
- **VMware vSphere Overview** - VMware 虚拟化监控
- **SNMP Device Monitoring** - 网络设备监控
- **Loki Logs** - 日志查询和分析

---

## ⚙️ 基础配置

### 1️⃣ 配置网络设备（LLDP 拓扑发现）

编辑设备清单文件：

```bash
vim config/topology/devices.yml
```

**添加您的网络设备：**

```yaml
devices:
  # 核心交换机
  - name: Switch-Core-01
    host: 192.168.1.100
    type: switch
    tier: core                    # 设备层级：core/aggregation/access
    location: dc1-rack-A01
    snmp_community: public
    snmp_version: 2c

  # 接入交换机
  - name: Switch-Access-01
    host: 192.168.1.101
    type: switch
    tier: access
    location: dc1-rack-B01
    snmp_community: public
    snmp_version: 2c

  # ESXi 主机
  - name: ESXi-Host-01
    host: 192.168.1.200
    type: esxi
    tier: core
    location: dc1-rack-A01
    snmp_community: public
    snmp_version: 2c
```

**保存后重启拓扑发现服务：**

```bash
docker-compose restart topology-discovery
```

### 2️⃣ 配置网络设备 Syslog

在您的网络设备上配置 Syslog，将日志发送到监控服务器：

#### Cisco 设备

```cisco
configure terminal
logging host <YOUR_MONITORING_IP>
logging trap informational
logging facility local6

! 启用 LLDP
lldp run

! 保存配置
end
write memory
```

#### Arista 设备

```arista
configure
logging host <YOUR_MONITORING_IP>
logging level informational
logging format hostname fqdn

! 启用 LLDP
lldp run

! 保存配置
end
write memory
```

#### Juniper 设备

```juniper
set system syslog host <YOUR_MONITORING_IP> any info
set protocols lldp interface all
commit
```

### 3️⃣ 配置 VMware vCenter（可选）

如果您有 VMware 环境，编辑 Telegraf 配置：

```bash
vim config/telegraf/telegraf.conf
```

**修改 vSphere 配置段：**

```toml
[[inputs.vsphere]]
  vcenters = ["https://vcenter.example.com/sdk"]
  username = "monitoring@vsphere.local"
  password = "your-password"
  insecure_skip_verify = true

  # 采集间隔
  interval = "60s"

  # 采集对象
  vm_metric_include = []
  host_metric_include = []
  cluster_metric_include = []
  datastore_metric_include = []
```

**重启 Telegraf：**

```bash
docker-compose restart telegraf-vmware
```

### 4️⃣ 配置告警通知

编辑 Alertmanager 配置：

```bash
vim config/alertmanager/alertmanager.yml
```

**配置邮件通知：**

```yaml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@example.com'
  smtp_auth_username: 'alerts@example.com'
  smtp_auth_password: 'your-app-password'
  smtp_require_tls: true

route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'email-notifications'

receivers:
  - name: 'email-notifications'
    email_configs:
      - to: 'ops-team@example.com'
        send_resolved: true
```

**重启 Alertmanager：**

```bash
docker-compose restart alertmanager
```

---

## ✅ 验证部署

### 1️⃣ 验证服务健康状态

```bash
# 检查所有服务状态
docker-compose ps

# 查看服务日志（无错误）
docker-compose logs --tail=50
```

### 2️⃣ 验证拓扑发现

```bash
# 检查拓扑数据文件
cat data/topology/topology.json | jq '.'

# 检查生成的标签文件
cat config/vmagent/targets/topology-switches.json | jq '.'
cat config/vmagent/targets/topology-servers.json | jq '.'

# 检查拓扑指标
curl http://localhost:9700/metrics | grep topology_device_info
```

**预期输出：**

```
# HELP topology_device_info Device topology information
# TYPE topology_device_info gauge
topology_device_info{device_name="Switch-Core-01",device_tier="core",...} 1
```

### 3️⃣ 验证指标采集

```bash
# 查询所有采集目标
curl 'http://localhost:8428/api/v1/query?query=up' | jq '.'

# 查询拓扑标签是否注入
curl 'http://localhost:8428/api/v1/query?query=up{topology_discovered="true"}' | jq '.'

# 查询网络设备指标
curl 'http://localhost:8428/api/v1/query?query=ifHCInOctets' | jq '.'
```

### 4️⃣ 验证日志采集

```bash
# 查看 Loki 状态
curl http://localhost:3100/ready

# 查看 Promtail 采集日志
docker-compose logs promtail

# 查看 Syslog-NG 接收日志
docker-compose logs syslog-ng

# 在 Grafana 中查询日志
# Explore → Loki → {job="syslog"}
```

### 5️⃣ 验证告警规则

```bash
# 查看告警规则状态
curl http://localhost:8880/api/v1/rules | jq '.'

# 查看当前告警
curl http://localhost:8880/api/v1/alerts | jq '.'

# 查看 Alertmanager 状态
curl http://localhost:9093/api/v2/status | jq '.'
```

---

## 🎯 下一步

恭喜！您已成功部署完整的可观测性平台。接下来可以：

### 📚 深入学习

- [完整功能文档](FINAL-REPORT.md) - 了解所有功能特性
- [可观测性指南](docs/OBSERVABILITY-GUIDE.md) - Metrics + Logs + Topology 联动
- [拓扑发现详解](docs/TOPOLOGY-DISCOVERY.md) - LLDP 自动发现原理
- [告警手册](docs/RUNBOOK.md) - 完整的告警处理流程

### ⚙️ 高级配置

- [性能调优](docs/PERFORMANCE-TUNING.md) - 大规模环境优化
- [gNMI 网络监控](docs/GNMI-MONITORING.md) - 新一代流式遥测
- [硬件监控](docs/HARDWARE-MONITORING.md) - Redfish + IPMI
- [VMware 多集群](docs/VMWARE-SOLUTION-COMPARISON.md) - 方案对比

### 🔧 日常运维

```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f [service_name]

# 重启服务
docker-compose restart [service_name]

# 重载配置（无需重启）
curl -X POST http://localhost:8429/-/reload  # vmagent
curl -X POST http://localhost:9093/-/reload  # alertmanager

# 停止所有服务
docker-compose down

# 清理数据（谨慎使用！）
docker-compose down -v
```

---

## ❓ 常见问题

### Q1: 服务无法启动

**检查步骤：**

```bash
# 1. 查看日志
docker-compose logs [service_name]

# 2. 检查端口占用
sudo netstat -tulpn | grep -E '3000|8428|9093'

# 3. 检查磁盘空间
df -h

# 4. 检查内存
free -h
```

### Q2: 拓扑发现没有数据

**检查步骤：**

```bash
# 1. 确认设备配置正确
cat config/topology/devices.yml

# 2. 检查 SNMP 连通性
snmpwalk -v2c -c public <device_ip> 1.0.8802.1.1.2

# 3. 查看发现日志
docker-compose logs topology-discovery

# 4. 手动触发发现
docker-compose restart topology-discovery
```

### Q3: Grafana 没有数据

**检查步骤：**

```bash
# 1. 检查数据源连接
curl http://localhost:3000/api/datasources

# 2. 检查 VictoriaMetrics 有数据
curl 'http://localhost:8428/api/v1/query?query=up'

# 3. 检查 vmagent 采集状态
curl http://localhost:8429/targets

# 4. 重启 Grafana
docker-compose restart grafana
```

### Q4: 告警不发送

**检查步骤：**

```bash
# 1. 检查告警规则
curl http://localhost:8880/api/v1/rules

# 2. 检查 Alertmanager 配置
docker-compose exec alertmanager amtool config show

# 3. 测试告警发送
docker-compose exec alertmanager amtool alert add alertname=test severity=warning

# 4. 查看 Alertmanager 日志
docker-compose logs alertmanager
```

### Q5: 日志采集失败

**检查步骤：**

```bash
# 1. 检查 Loki 状态
curl http://localhost:3100/ready

# 2. 检查 Promtail 日志
docker-compose logs promtail

# 3. 检查 Syslog 端口
sudo netstat -ulpn | grep 514

# 4. 测试 Syslog 发送
logger -n localhost -P 514 "Test message"
```

---

## 📞 获取帮助

如果遇到问题，您可以：

- 📖 查看 [完整文档](README.md)
- 🐛 提交 [GitHub Issue](https://github.com/YOUR-USERNAME/monitoring-platform/issues)
- 💬 参与 [GitHub Discussions](https://github.com/YOUR-USERNAME/monitoring-platform/discussions)
- 📚 查看 [FAQ 文档](docs/FAQ.md)

---

## 🎉 完成！

您现在拥有一个完整的企业级基础设施可观测性平台：

```
✅ Metrics 指标监控 - VictoriaMetrics
✅ Logs 日志聚合 - Loki
✅ Topology 拓扑发现 - LLDP Auto-Discovery
✅ Alerting 智能告警 - Alertmanager (20+ 抑制规则)
✅ Visualization 可视化 - Grafana (预置 Dashboard)
✅ Root Cause Analysis 根因分析 - 自动识别故障源
```

**享受您的可观测性之旅！** 🚀

---

<div align="center">

**Made with ❤️ by the Community**

[⬆ 返回顶部](#-快速启动指南-quick-start-guide)

</div>
