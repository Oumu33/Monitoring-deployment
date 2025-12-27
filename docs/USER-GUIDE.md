# 监控系统完整使用手册

## 目录

- [系统架构和数据流](#系统架构和数据流)
- [快速开始](#快速开始)
- [监控目标配置](#监控目标配置)
- [告警规则配置](#告警规则配置)
- [Grafana 可视化](#grafana-可视化)
- [日常运维](#日常运维)
- [故障排查](#故障排查)

---

## 系统架构和数据流

### 完整架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                          数据采集层                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│  │ Node        │  │ SNMP        │  │ Blackbox    │                 │
│  │ Exporter    │  │ Exporter    │  │ Exporter    │                 │
│  │ :9100       │  │ :9116       │  │ :9115       │                 │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                 │
│         │                │                │                         │
│         │                │                │                         │
│         v                v                v                         │
│  ┌──────────────────────────────────────────────┐                  │
│  │           vmagent :8429                      │                  │
│  │        (指标采集和聚合)                        │ ◄────┐          │
│  └──────────────────┬───────────────────────────┘      │          │
│                     │                                  │          │
│                     │ HTTP Push                        │          │
│  ┌──────────────────┴───────────────────────────┐      │          │
│  │   Telegraf VMware                            │      │          │
│  │   (直接推送，不经过 vmagent)                   │──────┘          │
│  └──────────────────────────────────────────────┘                  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ 所有指标统一写入
                              v
┌─────────────────────────────────────────────────────────────────────┐
│                          存储层                                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │         VictoriaMetrics :8428                                  │ │
│  │         (时序数据库)                                             │ │
│  │                                                                 │ │
│  │  - 接收所有指标数据                                              │ │
│  │  - 高性能存储和压缩                                              │ │
│  │  - 支持 PromQL 查询                                             │ │
│  │  - 数据保留 12 个月                                             │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                    │                    │
                    │ 查询               │ 查询
                    v                    v
┌─────────────────────────────┐   ┌──────────────────────────┐
│       vmalert :8880         │   │    Grafana :3000         │
│       (告警引擎)             │   │    (可视化)               │
│                             │   │                          │
│  - 定期查询 VictoriaMetrics  │   │  - 创建仪表板            │
│  - 评估告警规则              │   │  - 数据可视化            │
│  - 触发告警                 │   │  - 用户界面              │
└──────────┬──────────────────┘   └──────────────────────────┘
           │
           │ 告警通知
           v
┌──────────────────────────────┐
│   Alertmanager :9093         │
│   (告警管理)                  │
│                              │
│  - 告警分组                   │
│  - 告警去重                   │
│  - 路由分发                   │
│  - 通知发送                   │
│    (邮件/微信/钉钉/短信)        │
└──────────────────────────────┘
```

### 数据流详解

#### 流程 1: Node Exporter（Linux 主机监控）

```
1. Node Exporter (每台 Linux 主机)
   └─> 暴露指标: http://host:9100/metrics
       └─> CPU、内存、磁盘、网络数据

2. vmagent (采集器)
   └─> 定期抓取: 每 15 秒访问一次
       └─> 解析 Prometheus 格式指标
           └─> 批量写入: VictoriaMetrics

3. VictoriaMetrics (存储)
   └─> 接收并存储指标
       └─> 压缩、索引、持久化
```

#### 流程 2: SNMP Exporter（网络设备监控）

```
1. vmagent 配置
   └─> targets: [192.168.1.100, 192.168.1.101]  # 交换机 IP

2. vmagent 发起请求
   └─> GET http://snmp-exporter:9116/snmp?target=192.168.1.100&module=if_mib

3. SNMP Exporter 工作
   └─> 接收请求
       └─> 向目标设备 192.168.1.100 发起 SNMP 查询
           └─> 获取设备数据（端口状态、流量、错误率等）
               └─> 转换为 Prometheus 格式
                   └─> 返回给 vmagent

4. vmagent 接收
   └─> 解析指标
       └─> 写入 VictoriaMetrics
```

#### 流程 3: Blackbox Exporter（服务可用性探测）

```
1. vmagent 配置
   └─> targets: [https://www.company.com, 192.168.1.100]

2. vmagent 发起请求
   └─> GET http://blackbox-exporter:9115/probe?target=https://www.company.com&module=http_2xx

3. Blackbox Exporter 工作
   └─> 接收请求
       └─> 向目标 https://www.company.com 发起 HTTP 请求
           └─> 测量响应时间、状态码、SSL 证书
               └─> 或者: ICMP Ping 测量延迟、丢包率
                   └─> 或者: TCP 端口探测连接性
                       └─> 返回探测结果给 vmagent

4. vmagent 接收
   └─> 解析指标
       └─> 写入 VictoriaMetrics
```

#### 流程 4: Telegraf VMware（特殊流程）

```
1. Telegraf 独立工作
   └─> 直接连接 vCenter API
       └─> 采集 VM、ESXi、数据存储指标

2. Telegraf 直接推送
   └─> **不经过 vmagent**
       └─> 直接 HTTP POST 到 VictoriaMetrics
           └─> URL: http://victoriametrics:8428/api/v1/write
               └─> 格式: Prometheus RemoteWrite 协议
```

### 为什么 Telegraf 不经过 vmagent？

**原因**:
- Telegraf 自带数据采集能力（不需要被抓取）
- Telegraf 支持主动推送（Push 模式）
- 减少一层转发，降低延迟
- 简化架构

**对比**:

| 组件 | 工作模式 | 数据流 |
|------|---------|--------|
| Node Exporter | **被动暴露** | Exporter → vmagent → VM |
| SNMP Exporter | **被动暴露** | Exporter → vmagent → VM |
| Blackbox Exporter | **被动暴露** | Exporter → vmagent → VM |
| **Telegraf** | **主动推送** | Telegraf → VM（直接） |

### 告警数据流

```
1. vmalert 定期查询
   └─> 每 30 秒查询一次 VictoriaMetrics
       └─> 执行告警规则表达式
           └─> 例如: node_cpu_usage > 80

2. 触发告警
   └─> 如果条件满足 (CPU > 80%)
       └─> 生成告警事件
           └─> 发送到 Alertmanager

3. Alertmanager 处理
   └─> 接收告警
       └─> 分组（相同类型告警合并）
           └─> 去重（避免重复告警）
               └─> 路由（根据标签发送到不同接收者）
                   └─> 通知（邮件/微信/钉钉）
```

---

## 快速开始

### 1. 启动所有服务

```bash
cd /opt/Monitoring

# 启动所有容器
docker-compose up -d

# 验证服务状态
docker-compose ps

# 所有服务应该显示 "Up"
```

### 2. 访问 Web 界面

- **Grafana**: http://localhost:3000 (admin/admin)
- **VictoriaMetrics**: http://localhost:8428
- **vmalert**: http://localhost:8880
- **Alertmanager**: http://localhost:9093

### 3. 验证数据采集

```bash
# 查看 vmagent 采集目标
curl http://localhost:8429/api/v1/targets | jq

# 查询 VictoriaMetrics 指标
curl 'http://localhost:8428/api/v1/query?query=up' | jq

# 查看 Telegraf VMware 指标
curl 'http://localhost:8428/api/v1/query?query=vsphere_vm_cpu_usage_average' | jq
```

---

## 监控目标配置

### 方式 1: 文件服务发现（推荐）

**特点**: 修改配置 30 秒自动生效，无需重启

#### 添加网络设备

```bash
# 编辑核心交换机配置
vim config/vmagent/targets/core-switches.json

[
  {
    "targets": [
      "192.168.1.100",
      "192.168.1.101"
    ],
    "labels": {
      "device_type": "switch",
      "device_tier": "core",
      "priority": "critical"
    }
  }
]

# 保存后 30 秒自动生效
```

#### 添加 ESXi 主机

```bash
vim config/vmagent/targets/esxi-hosts.json

[
  {
    "targets": [
      "192.168.2.10",
      "192.168.2.11",
      "192.168.2.12"
    ],
    "labels": {
      "device_type": "esxi",
      "cluster": "production",
      "priority": "critical"
    }
  }
]
```

#### 添加网站监控

```bash
vim config/vmagent/targets/websites.json

[
  {
    "targets": [
      "https://www.company.com",
      "https://api.company.com",
      "http://oa.company.local"
    ],
    "labels": {
      "service_type": "http",
      "priority": "critical"
    }
  }
]
```

### 方式 2: 静态配置

编辑 `config/vmagent/prometheus.yml`（需要重启 vmagent）

```yaml
scrape_configs:
  - job_name: 'node-exporter'
    static_configs:
      - targets:
        - 192.168.1.10:9100
        - 192.168.1.11:9100
        labels:
          environment: 'production'
```

---

## 数据流总结

### ✅ 是的，几乎所有数据都经过 vmagent！

**数据流向**:

```
┌─────────────────────────────────────────┐
│        数据源 (Exporters)                │
│                                         │
│  Node Exporter    ────┐                │
│  SNMP Exporter    ────┤                │
│  Blackbox Exporter ───┼──> vmagent ──> VictoriaMetrics
│                       │                │
│  Telegraf VMware  ────┼───────────────> VictoriaMetrics (直接)
└─────────────────────────────────────────┘
```

**具体说明**:

1. **Node Exporter** → vmagent → VictoriaMetrics ✅
2. **SNMP Exporter** → vmagent → VictoriaMetrics ✅
3. **Blackbox Exporter** → vmagent → VictoriaMetrics ✅
4. **Telegraf VMware** → VictoriaMetrics（直接推送）⚠️

**只有 Telegraf 是例外**，它直接推送到 VictoriaMetrics，不经过 vmagent。

---

## 完整使用文档

详细文档请参考：
- [文件服务发现使用指南](FILE-SERVICE-DISCOVERY.md)
- [Blackbox 监控配置](../examples/blackbox-monitoring-examples.yml)
- [VMware 多集群监控](VMWARE-SOLUTION-COMPARISON.md)
- [性能调优指南](PERFORMANCE-TUNING.md)
- [常见问题 FAQ](FAQ.md)
