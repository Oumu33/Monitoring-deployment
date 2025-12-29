# 实战演示：联动分析快速定位故障

## 目录
- [场景 1: 网站访问缓慢](#场景-1-网站访问缓慢)
- [场景 2: 服务器批量宕机](#场景-2-服务器批量宕机)
- [场景 3: 间歇性网络故障](#场景-3-间歇性网络故障)

---

## 场景 1: 网站访问缓慢

### 问题描述
17:00 用户反馈网站访问很慢，页面加载需要 5 秒。

### 传统方式（30 分钟）

```
17:01 - 收到告警邮件（7 封）:
  1. WebsiteSlow (www.company.com)
  2. WebsiteSlow (api.company.com)
  3. NetworkLatency (ESXi-Host-01)
  4. NetworkLatency (ESXi-Host-02)
  5. SwitchCPUHigh (Switch-Core-01)
  6. InterfaceErrors (Switch-Core-01 Eth1/1)
  7. TrafficStorm (Switch-Core-01)

17:02 - 运维人员开始排查:
  - 登录 Grafana 查看网站响应时间 (2 分钟)
  - 逐个检查服务器 CPU/内存 (5 分钟)
  - 检查数据库性能 (3 分钟)
  - 检查网络延迟 (3 分钟)
  - 发现网络延迟异常，怀疑交换机问题 (5 分钟)
  - SSH 登录交换机查看 CPU (2 分钟)
  - 发现 CPU 98%，查看日志 (5 分钟)
  - 找到流量风暴日志 (5 分钟)

17:30 - 定位根因: Switch-Core-01 Eth1/1 流量风暴
```

### 可观测性平台方式（1 分钟）

```
17:01 - 收到 1 封智能告警邮件:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚨 [P0 紧急] 核心交换机流量风暴
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚡ 根因: Switch-Core-01 Eth1/1 接口流量风暴
📅 时间: 2025-12-29 17:00:01
⏱️ 持续: 1 分钟

━━━ 时间线（自动关联）━━━

17:00:00  [LOG]    Switch-Core-01: Unicast storm detected on Eth1/1
17:00:01  [METRIC] Switch-Core-01: CPU 从 20% → 98%
17:00:01  [METRIC] ESXi-Host-01/02: 网络延迟 从 1ms → 200ms
17:00:02  [METRIC] www.company.com: 响应时间 从 800ms → 5200ms

━━━ 根因分析 ━━━

原因: 交换机 Eth1/1 端口检测到单播流量风暴
结果: CPU 过载 → 网络延迟 → 应用响应慢

━━━ 影响范围（基于拓扑）━━━

设备层面:
  - Switch-Core-01 (tier=core)
  - Switch-Access-01, 02 (连接到 Core-01)
  - ESXi-Host-01, 02 (连接到 Access-01/02)

服务层面:
  - www.company.com (运行在 ESXi-Host-01)
  - api.company.com (运行在 ESXi-Host-01)
  - oa.company.com (运行在 ESXi-Host-02)

用户影响:
  - 预计 500+ 活跃用户受影响

━━━ 建议处理 ━━━

1. 立即: shutdown 接口 Eth1/1 隔离故障源
   命令: Switch-Core-01# interface Eth1/1
          Switch-Core-01(config-if)# shutdown

2. 调查: 检查 Eth1/1 连接的设备（可能是 DDoS 或网络环路）
   连接设备: Server-DB-01 (192.168.1.50)

3. 长期: 启用风暴控制
   命令: storm-control unicast level 10.00

━━━ 快速链接 ━━━

📊 Grafana 拓扑图: http://grafana/d/topology?t=17:00:00
📝 Loki 日志查询: {host="Switch-Core-01"} [16:59:00 - 17:01:00]
📈 Metrics 分析:  http://grafana/d/network?t=17:00:00
📖 Runbook:       http://wiki/network/traffic-storm

━━━ 告警抑制 ━━━

已自动抑制以下连锁告警（避免告警轰炸）:
  ✓ WebsiteSlow (www.company.com) - 根因已知
  ✓ WebsiteSlow (api.company.com) - 根因已知
  ✓ NetworkLatency (ESXi-Host-01/02) - 根因已知
  ✓ SwitchCPUHigh (Switch-Core-01) - 根因已知

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**运维人员操作**:

```
17:01 - 收到邮件，阅读 30 秒
17:02 - 点击 Grafana 拓扑图，确认影响范围 30 秒
17:03 - 执行 shutdown 命令隔离故障接口
17:05 - 问题解决，网站恢复正常
```

**总耗时: < 5 分钟**（vs 传统 30 分钟）

### 系统如何做到的？

**1. Metrics 检测异常**:
```promql
# Blackbox 检测到响应时间异常
probe_http_duration_seconds{instance="www.company.com"} > 3
```

**2. 拓扑自动关联**:
```json
// 从标签得知依赖关系
{
  "www.company.com": {
    "runs_on": "ESXi-Host-01",
    "connected_switch": "Switch-Access-01",
    "uplink_switch": "Switch-Core-01",
    "network_segment": "seg-core-01"
  }
}
```

**3. Logs 提供根因证据**:
```logql
# Loki 查询同一时间段的日志
{job="syslog", host="Switch-Core-01"} [16:59:00 - 17:01:00]

# 找到根因日志
17:00:00 - %STORM_CONTROL-2-UNICAST_STORM: Unicast storm detected on Eth1/1
```

**4. Alertmanager 智能抑制**:
```yaml
# 抑制规则生效
- source_match_re:
    alertname: '(TrafficStorm|BroadcastStorm)'
  target_match_re:
    alertname: '(SwitchCPUHigh|NetworkLatency|WebsiteSlow)'
  equal: ['network_segment']  # 同一网段的连锁告警被抑制
```

---

## 场景 2: 服务器批量宕机

### 问题描述
凌晨 3:00，数据中心机房 A01 机架突然断电，15 台服务器宕机。

### 传统方式（45 分钟）

```
03:01 - 收到 50+ 封告警邮件:
  - 15 个 HostDown
  - 30 个 VMDown
  - 10 个 ServiceDown
  - ...

03:02 - 运维人员被手机轰炸惊醒
03:05 - 逐个查看告警，试图找规律 (10 分钟)
03:15 - 发现都是 rack A01 的服务器
03:20 - 怀疑机架电源问题
03:25 - 电话联系机房值班人员
03:30 - 确认 A01 机架 PDU 故障
03:45 - 开始恢复计划
```

### 可观测性平台方式（2 分钟）

```
03:01 - 收到 1 封智能告警（根因直达）:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚨 [P0 紧急] 数据中心机房断电
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚡ 根因推断: 机房 dc1-rack-A01 大面积断电
📅 时间: 2025-12-29 03:00:45
⏱️ 同时故障设备: 15 台

━━━ 故障模式识别 ━━━

模式: 同一机架设备在同一秒内全部宕机
  → 极大可能是物理层故障（电源/网络）

━━━ 影响范围（按机架聚合）━━━

机架: dc1-rack-A01
├─ 物理服务器: 15 台（全部 DOWN）
│   ├─ ESXi-Host-01, 02, 03 (虚拟化主机)
│   ├─ Server-DB-01, 02 (数据库服务器)
│   └─ Server-Web-01~10 (Web 服务器)
│
├─ 虚拟机: 45 个（全部 DOWN）
│
├─ 业务服务: 12 个（全部中断）
│   ├─ 订单系统
│   ├─ 支付网关
│   └─ 用户中心
│
└─ 用户影响: 所有在线用户（约 2000 人）

━━━ 硬件日志（最后记录）━━━

03:00:44  [REDFISH] ESXi-Host-01: Power supply 2 失电
03:00:44  [REDFISH] ESXi-Host-02: Power supply 2 失电
03:00:44  [IPMI]    Server-DB-01: AC power lost

→ 所有设备 Power supply 2 同时失电
→ 确认: A01 机架 PDU-2 故障

━━━ 建议处理 ━━━

紧急:
1. 联系机房值班: 检查 rack A01 PDU-2
2. 如有冗余电源, 切换到 PDU-1
3. 准备业务切换到灾备机房

恢复计划:
1. 数据库服务器优先（Server-DB-01/02）
2. 核心业务服务器（订单/支付）
3. 其他服务器

━━━ 已抑制告警 ━━━

同一根因的 50 个连锁告警已自动抑制:
  ✓ 15 个 HostDown
  ✓ 30 个 VMDown
  ✓ 10 个 ServiceDown

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**系统如何识别的？**

```yaml
# Alertmanager 分组规则
route:
  group_by: ['rack', 'datacenter']  # 按机架分组

# 拓扑标签（自动生成）
labels:
  rack: 'A01'
  datacenter: 'dc1'
  power_source: 'PDU-2'

# 硬件日志关联
{job="redfish", rack="A01"} |~ "power|失电"

# 故障模式识别
# 15 个设备在同一秒内宕机 + 同一机架 → 物理层故障
```

---

## 场景 3: 间歇性网络故障

### 问题描述
用户反馈 API 偶尔超时，但不是每次都超时，难以定位。

### 传统方式（数小时/数天）

```
难以定位，因为:
  - 问题不稳定复现
  - 需要持续观察
  - 可能需要抓包分析
  - 涉及多个环节（应用/网络/数据库）
```

### 可观测性平台方式（10 分钟）

**步骤 1: Grafana 中设置关联 Dashboard**

```
Panel 1 (上): API 响应时间（Metrics）
  probe_http_duration_seconds{instance="api.company.com"}

Panel 2 (中): 网络延迟（Metrics）
  probe_icmp_duration_seconds{instance="192.168.1.100"}

Panel 3 (下): 网络设备日志（Logs）
  {job="syslog", source="network-devices"} |~ "error|flap|down"
```

**步骤 2: 时间同步，发现规律**

```
15:23:10 - API 响应时间: 50ms  → 2000ms (峰值)
15:23:10 - 网络延迟:      1ms   → 150ms  (峰值)
15:23:10 - 日志: Switch-Core-01: Interface Eth0/1 link flapped

15:45:30 - API 响应时间: 50ms  → 1800ms (峰值)
15:45:30 - 网络延迟:      1ms   → 140ms  (峰值)
15:45:30 - 日志: Switch-Core-01: Interface Eth0/1 link flapped

规律: 每次 API 超时都伴随 Eth0/1 接口抖动！
```

**步骤 3: 查询拓扑，确认连接**

```logql
# 查询 Eth0/1 连接的设备
topology_edges{source="Switch-Core-01", source_port="Eth0/1"}

# 结果: Eth0/1 连接到 Server-API-01
```

**步骤 4: 查看硬件日志**

```logql
{job="syslog", host="Server-API-01"} |~ "network|eth|link"

# 发现:
15:23:10 - Server-API-01: eth0: Link is Down
15:23:12 - Server-API-01: eth0: Link is Up
```

**根因**: Server-API-01 网卡接触不良，导致间歇性断连

**解决**: 更换网线或网卡

---

## 总结：联动的威力

### 传统方式 vs 可观测性平台

| 场景 | 传统方式 | 可观测性平台 | 提升 |
|------|---------|-------------|------|
| **网站慢** | 30 分钟，7 封邮件 | 1 分钟，1 封邮件 | **30x** |
| **大面积故障** | 45 分钟，50+ 封邮件 | 2 分钟，1 封邮件 | **22x** |
| **间歇性故障** | 数小时/数天 | 10 分钟 | **数十倍** |

### 关键联动点

```
1. Metrics ←→ Topology
   ├─ 通过标签关联设备关系
   └─ 自动计算影响范围

2. Metrics ←→ Logs
   ├─ 时间戳对齐
   └─ 同一时间段的日志和指标

3. Topology ←→ Alerting
   ├─ 基于拓扑抑制连锁告警
   └─ 根因推断

4. All ←→ Grafana
   └─ 统一可视化，点击联动
```

---

## 实战技巧

### 1. 时间范围对齐

在 Grafana 中：
- 设置全局时间范围
- 所有 Panel 使用相同时间
- 点击某个时间点，所有图表联动

### 2. 标签规范

确保所有监控目标都有：
```yaml
labels:
  datacenter: dc1
  rack: A01
  network_segment: seg-core-01
  connected_switch: Switch-Core-01
```

### 3. 日志查询技巧

```logql
# 基础查询
{job="syslog", host="Switch-Core-01"}

# 时间范围
{job="syslog"} [17:00:00 - 17:05:00]

# 正则过滤
{job="syslog"} |~ "error|critical|down"

# 多条件
{job="syslog", network_segment="seg-core-01"} |~ "Interface.*down"

# 统计
count_over_time({job="syslog"} |~ "error" [5m])
```

### 4. 拓扑查询技巧

```promql
# 查找连接到特定交换机的所有设备
up{connected_switch="Switch-Core-01"}

# 查找特定层级的所有设备
up{device_tier="core"}

# 影响分析: 交换机故障会影响哪些服务器？
count by (connected_switch) (up{connected_switch="Switch-Core-01"})
```

---

**联动的核心**: Metrics + Logs + Topology 三者缺一不可！

- **Metrics**: 告诉你"发生了什么"
- **Logs**: 告诉你"为什么发生"
- **Topology**: 告诉你"影响了什么"

三者结合 → 快速定位 → 快速解决 🚀
