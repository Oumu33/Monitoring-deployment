# 可观测性完整架构使用指南

## 目录
- [系统架构](#系统架构)
- [快速开始](#快速开始)
- [日志查询示例](#日志查询示例)
- [根因分析流程](#根因分析流程)
- [告警关联](#告警关联)

---

## 系统架构

```
┌────────────────────────────────────────────────────────────────┐
│           完整可观测性架构（Observability Stack）                │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📊 Metrics（指标）                                             │
│   ├─ Node Exporter → CPU、内存、磁盘                            │
│   ├─ SNMP/gNMI → 网络设备                                      │
│   ├─ Telegraf → VMware                                         │
│   ├─ Redfish/IPMI → 硬件健康                                   │
│   └─ Blackbox → 服务可用性                                     │
│                ↓                                                │
│         VictoriaMetrics（指标存储）                             │
│                                                                 │
│  📝 Logs（日志）                                                │
│   ├─ Promtail → 主机日志（Syslog、Docker、Nginx）              │
│   └─ Syslog-NG → 网络设备日志（Cisco、Arista、Juniper）        │
│                ↓                                                │
│         Loki（日志存储）                                        │
│                                                                 │
│  🗺️ Topology（拓扑）                                           │
│   └─ 标签关联（datacenter、network_segment、rack）             │
│                                                                 │
│              ↓   ↓   ↓                                          │
│                                                                 │
│  🧠 分析和告警                                                  │
│   ├─ vmalert（指标告警）                                        │
│   ├─ Loki Ruler（日志告警）                                     │
│   └─ Alertmanager（告警聚合、分组、抑制、根因分析）             │
│                ↓                                                │
│  📢 通知（邮件/钉钉/企业微信）                                   │
│                ↓                                                │
│  👁️ Grafana（统一可视化）                                      │
│   ├─ Metrics Dashboard                                         │
│   ├─ Logs Dashboard                                            │
│   └─ 关联视图（Metrics + Logs）                                │
└────────────────────────────────────────────────────────────────┘
```

---

## 快速开始

### 1. 启动所有服务

```bash
cd /opt/Monitoring

# 启动完整栈
docker-compose up -d

# 检查服务状态
docker-compose ps

# 查看日志
docker-compose logs -f loki promtail syslog-ng
```

### 2. 配置网络设备发送 Syslog

**Cisco IOS/IOS-XR**:
```
logging host 192.168.1.X
logging trap informational
logging source-interface GigabitEthernet0/0
```

**Arista EOS**:
```
logging host 192.168.1.X
logging level informational
logging source-interface Management1
```

**Juniper Junos**:
```
set system syslog host 192.168.1.X any info
set system syslog host 192.168.1.X source-address 192.168.1.Y
```

### 3. 访问 Grafana

```
http://localhost:3000
用户名: admin
密码: admin
```

在 Grafana 中：
1. 数据源已自动配置（VictoriaMetrics + Loki）
2. 创建新 Dashboard
3. 添加 Panel，选择 Loki 数据源
4. 使用 LogQL 查询日志

---

## 日志查询示例

### 基本查询

```logql
# 查看所有网络设备日志
{job="syslog", source="network-devices"}

# 查看特定设备日志
{job="syslog", host="192.168.1.100"}

# 包含 "error" 的日志
{job="syslog"} |~ "error"

# 不包含 "debug" 的日志
{job="syslog"} !~ "debug"
```

### 网络设备查询

```logql
# 接口 Down 事件
{job="syslog", source="network-devices"} |~ "Interface.*down|link down"

# BGP 邻居问题
{job="syslog", source="network-devices"} |~ "BGP.*down|neighbor.*down"

# 流量风暴
{job="syslog", source="network-devices"} |~ "storm|broadcast storm"

# Cisco 设备的错误日志
{job="syslog", vendor="cisco"} |~ "error|critical|alert"
```

### 系统日志查询

```logql
# SSH 登录失败
{job="auth"} |~ "Failed password"

# OOM Killer 事件
{job="syslog"} |~ "Out of memory|oom-killer"

# 磁盘错误
{job="syslog"} |~ "I/O error|EXT4-fs error"
```

### 聚合查询

```logql
# 统计每个主机的错误日志数量（5 分钟内）
sum by (host) (count_over_time({job="syslog"} |~ "error" [5m]))

# 统计 SSH 失败次数
sum by (user, ip) (count_over_time({job="auth"} |~ "Failed password" [5m]))

# Nginx 5xx 错误率
sum by (host) (rate({job="nginx"} |~ ` 5\d{2} ` [5m]))
```

---

## 根因分析流程

### 示例：网站访问缓慢

#### 步骤 1: 在 Grafana 中查看 Metrics

```promql
# 网站响应时间
probe_http_duration_seconds{instance="www.company.com"}

# 发现响应时间从 1s 增加到 5s
```

#### 步骤 2: 切换到 Loki，查看时间段内的日志

```logql
# 查看同一时间段的网络设备日志
{job="syslog", source="network-devices"}
  |~ "error|critical|down|storm"

# 发现交换机日志显示流量风暴：
# 10:00:01 - Switch-Core-01: %STORM_CONTROL-2-UNICAST_STORM: Unicast storm detected on Eth1/1
```

#### 步骤 3: 查看 Metrics 确认交换机 CPU

```promql
# 交换机 CPU 使用率
snmp_switch_cpu_usage{instance="Switch-Core-01"}

# 发现 CPU 从 20% 跳到 98%
```

#### 步骤 4: 根因确认

**时间线**:
```
09:59:55 - 交换机 Eth1/1 检测到流量风暴（日志）
10:00:00 - 交换机 CPU 升高到 98%（指标）
10:00:00 - 网站响应时间增加到 5.2s（指标）
```

**根因**: 交换机 Eth1/1 端口流量风暴 → CPU 过载 → 网络延迟 → 网站慢

**影响范围**: 查询拓扑依赖（通过标签 `network_segment`）
```promql
# 查询连接到该交换机的所有服务器
up{connected_switch="Switch-Core-01"}
```

---

## 告警关联

### Alertmanager 自动根因分析

**接收到的原始告警**:
1. WebsiteSlow (www.company.com) - 17:00:00
2. WebsiteSlow (api.company.com) - 17:00:01
3. NetworkLatency (ESXi-Host-01) - 17:00:02
4. NetworkLatency (ESXi-Host-02) - 17:00:02
5. SwitchCPUHigh (Switch-Core-01) - 17:00:03
6. SwitchTrafficStorm (Switch-Core-01) - 17:00:00 ← **根因**

**Alertmanager 处理**:

1. **分组** (group_by: network_segment)
   - 所有告警属于同一 network_segment
   - 合并为 1 个告警组

2. **抑制** (inhibit_rules)
   - 告警 6 (TrafficStorm) 是根因
   - 告警 5 (SwitchCPUHigh) 被告警 6 抑制（同一设备）
   - 告警 1-4 被告警 6 抑制（同一 network_segment）

3. **最终发送 1 封邮件**:

```
Subject: 🚨 Critical: 核心交换机流量风暴

根因: Switch-Core-01 Eth1/1 流量风暴
时间: 2025-12-29 17:00:00
影响:
  - 网络段: network-seg-core-01
  - 3 个服务（www.company.com, api.company.com, oa.company.com）
  - 2 台 ESXi 主机网络延迟

详细信息:
  - 设备: Switch-Core-01
  - 接口: Eth1/1
  - CPU 使用率: 98%
  - 日志: Unicast storm detected on Eth1/1

建议处理:
  1. 检查 Eth1/1 连接的设备
  2. 可能是 DDoS 攻击或网络环路
  3. 临时措施: shutdown 接口 Eth1/1
  4. 永久方案: 启用风暴控制

Grafana Dashboard: http://grafana/d/network-overview
Loki Logs: {host="Switch-Core-01"} [17:00:00 - 17:05:00]
Runbook: http://wiki/network/traffic-storm
```

---

## Metrics + Logs 关联查询

### Grafana Dashboard 示例

**创建关联 Dashboard**:

1. **Panel 1: Metrics - 网站响应时间**
```promql
probe_http_duration_seconds{instance="www.company.com"}
```

2. **Panel 2: Logs - 同一时间段的网络日志**
```logql
{job="syslog", source="network-devices"} |~ "error|critical"
```

3. **Panel 3: Metrics - 交换机 CPU**
```promql
snmp_switch_cpu_usage
```

4. **Panel 4: Logs - 交换机详细日志**
```logql
{job="syslog", host="Switch-Core-01"}
```

**时间同步**: 所有 Panel 使用相同的时间范围，点击一个时间点，所有视图联动。

---

## 最佳实践

### 1. 标签规范（用于关联）

在所有监控配置中添加统一标签：

```yaml
labels:
  datacenter: dc1              # 数据中心
  network_segment: seg-core-01 # 网络段
  rack: A-01                   # 机架
  connected_switch: Switch-01  # 连接的交换机
  esxi_host: ESXi-Host-01     # ESXi 主机（如果是 VM）
  depends_on: mysql-service    # 依赖的服务
```

### 2. 日志保留策略

```yaml
# Loki 配置
limits_config:
  retention_period: 30d  # 生产环境推荐 30-90 天
```

### 3. 查询性能优化

```logql
# ✅ 好：使用精确匹配（更快）
{job="syslog"} |= "error"

# ⚠️ 避免：不必要的正则（慢）
{job="syslog"} |~ ".*error.*"

# ✅ 好：时间范围限制
{job="syslog"} |= "error" [5m]

# ❌ 避免：时间范围太大
{job="syslog"} |= "error" [7d]
```

---

## 故障排查

### Loki 无数据

```bash
# 1. 检查 Loki 服务
docker-compose logs loki

# 2. 检查 Promtail 连接
docker-compose logs promtail

# 3. 测试 Loki API
curl http://localhost:3100/ready

# 4. 手动查询
curl -G 'http://localhost:3100/loki/api/v1/query' \
  --data-urlencode 'query={job="syslog"}'
```

### 网络设备日志未收到

```bash
# 1. 检查 Syslog-NG
docker-compose logs syslog-ng

# 2. 测试端口监听
netstat -ulnp | grep 514

# 3. 手动发送测试日志
logger -n 127.0.0.1 -P 514 "Test message"

# 4. 检查日志文件
ls -la /var/log/network-devices/
```

---

## 参考资料

- [Loki 官方文档](https://grafana.com/docs/loki/latest/)
- [LogQL 查询语法](https://grafana.com/docs/loki/latest/logql/)
- [Promtail 配置](https://grafana.com/docs/loki/latest/clients/promtail/)
- [Alertmanager 抑制规则](https://prometheus.io/docs/alerting/latest/configuration/#inhibit_rule)

---

完整的可观测性 = Metrics + Logs + Topology + 智能关联
