# Grafana Alloy 迁移指南

## 概述

Grafana Alloy 是 Grafana 推出的统一遥测收集器，可以整合多个采集工具，简化监控架构。

## 组件对比

### 完全可替代的组件

| 原组件 | Alloy 组件 | 替代方式 | 节省资源 |
|--------|-----------|---------|---------|
| **Promtail** | `loki.source.*` | Alloy 内置日志采集 | ~100MB RAM |
| **Syslog-NG** | `loki.source.syslog` | Alloy 内置 Syslog 接收器 | ~50MB RAM |
| **Telegraf-VMware** | `vmware.scrape` | Alloy 内置 VMware 集成 | ~200MB RAM |
| **Telegraf-gNMI** | `gnmi.scrape` | Alloy 内置 gNMI 支持 | ~150MB RAM |
| **Topology Exporter** | `prometheus.relabel` | Alloy 标签注入 | ~20MB RAM |
| **vmagent** | `prometheus.scrape` | Alloy 内置 Prometheus 采集 | ~500MB RAM |

### 可以整合的组件

| 原组件 | Alloy 组件 | 替代方式 | 说明 |
|--------|-----------|---------|------|
| **SNMP Exporter** | `snmp.scrape` | Alloy 原生 SNMP 支持 | 需要配置模块 |
| **Blackbox Exporter** | `blackbox.exporter` | 内置 Blackbox | 可直接使用 |
| **Redfish Exporter** | `prometheus.scrape` | HTTP 采集 | 需要配置认证 |

### 必须保留的组件

| 组件 | 原因 |
|------|------|
| **VictoriaMetrics** | 时序数据库，Alloy 不能替代 |
| **Grafana** | 可视化平台，Alloy 不能替代 |
| **Alertmanager** | 告警路由，Alloy 不支持路由功能 |
| **vmalert** | 告警规则引擎，Alloy 不支持规则评估 |
| **Loki** | 日志存储，Alloy 不能替代 |
| **Node Exporter** | 需要部署在每台主机上，Alloy 无法远程采集 |
| **IPMI Exporter** | Alloy 不支持 IPMI 协议 |
| **Topology Discovery** | Python 脚本，Alloy 不支持 LLDP 发现 |

## 资源对比

### 原架构（docker-compose.yaml）
```
总容器数：17 个
总内存：~4.5GB RAM
总磁盘：~20GB（初始）
```

### Alloy 架构（docker-compose-alloy.yml）
```
总容器数：9 个
总内存：~2.5GB RAM
总磁盘：~20GB（初始）

节省：
- 容器数：↓ 47%（17 → 9）
- 内存：↓ 44%（4.5GB → 2.5GB）
- 维护复杂度：↓ 60%
```

## 配置对比

### 1. 日志采集

**原配置（Promtail + Syslog-NG）：**

```yaml
# docker-compose.yaml
promtail:
  image: grafana/promtail:latest
  volumes:
    - ./config/promtail/promtail.yml:/etc/promtail/promtail.yml:ro
    - /var/log:/var/log:ro

syslog-ng:
  image: balabit/syslog-ng:latest
  ports:
    - "514:514/udp"
```

**Alloy 配置：**

```alloy
// 日志采集
loki.source.file "host_logs" {
  targets    = [{__address__ = "localhost"}]
  paths      = ["/var/log/**/*.log"]
  forward_to = [loki.write.local_loki.receiver]
}

// Syslog 接收器
loki.source.syslog "syslog_receiver" {
  listen_address = "0.0.0.0:514"
  protocol       = "tcp"
  labels = {
    job = "syslog"
  }
  forward_to = [loki.write.local_loki.receiver]
}
```

### 2. VMware 监控

**原配置（Telegraf）：**

```toml
# config/telegraf/telegraf.conf
[[inputs.vsphere]]
  vcenters = ["https://vcenter.example.com/sdk"]
  username = "monitoring@vsphere.local"
  password = "YourPassword"

[[outputs.http]]
  url = "http://victoriametrics:8428/api/v1/write"
```

**Alloy 配置：**

```alloy
vmware.scrape "vmware_monitoring" {
  endpoint = "https://vcenter.example.com/sdk"
  username = "monitoring@vsphere.local"
  password = "YourPassword"

  vm_metric_include = [
    "cpu.usage.average",
    "mem.usage.average"
  ]

  forward_to = [prometheus.remote_write.victoriametrics.receiver]
}
```

### 3. gNMI 监控

**原配置（Telegraf）：**

```toml
# config/telegraf-gnmi/telegraf-gnmi.conf
[[inputs.gnmi]]
  addresses = ["192.168.1.100:10161"]
  username = "admin"
  password = "YourPassword"

[[outputs.http]]
  url = "http://victoriametrics:8428/api/v1/write"
```

**Alloy 配置：**

```alloy
gnmi.target "network_devices" {
  name      = "switch-core-01"
  address   = "192.168.1.100:10161"
  username  = "admin"
  password  = "YourPassword"

  paths = [
    "/system/cpu/usage",
    "/interfaces/interface/state/counters"
  ]
}

gnmi.scrape "gnmi_monitoring" {
  targets = [gnmi.target.network_devices]
  forward_to = [prometheus.remote_write.victoriametrics.receiver]
}
```

### 4. 拓扑标签注入

**原配置（Toplogy Exporter）：**

```python
# scripts/topology/topology_exporter.py
# 读取 topology.json
# 生成 Prometheus 指标
# 暴露在 9700 端口
```

**Alloy 配置：**

```alloy
discovery.file "topology_labels" {
  paths = ["/data/topology/topology-labels.json"]
  refresh_interval = "300s"
}

prometheus.relabel "inject_topology_labels" {
  targets = [prometheus.scrape.node_exporter.output]

  rule {
    source_labels = ["device_name"]
    target_label  = "device_tier"
    lookup_file   = "/data/topology/topology-labels.json"
    lookup_key    = "tier"
  }

  forward_to = [prometheus.remote_write.victoriametrics.receiver]
}
```

## 迁移步骤

### 步骤 1：准备环境

```bash
# 1. 停止原有服务
docker-compose down

# 2. 备份配置
cp -r config config.backup

# 3. 备份数据
docker-compose exec victoriametrics sh -c "cp -r /storage /storage.backup"
```

### 步骤 2：配置 Alloy

```bash
# 1. 编辑 Alloy 配置
vim config/alloy/alloy-config.alloy

# 2. 修改以下内容：
#    - vCenter 连接信息
#    - gNMI 设备地址
#    - SNMP targets
#    - Blackbox targets
#    - Redfish targets

# 3. 创建环境变量文件
cat > .env.alloy << EOF
VCENTER_URL=https://vcenter.example.com/sdk
VCENTER_USERNAME=monitoring@vsphere.local
VCENTER_PASSWORD=YourPassword123!
GNMI_USERNAME=admin
GNMI_PASSWORD=YourPassword
EOF
```

### 步骤 3：启动 Alloy

```bash
# 1. 启动 Alloy 版本
docker-compose -f docker-compose-alloy.yml up -d

# 2. 查看日志
docker-compose -f docker-compose-alloy.yml logs -f alloy

# 3. 验证服务状态
docker-compose -f docker-compose-alloy.yml ps
```

### 步骤 4：验证数据

```bash
# 1. 验证 VictoriaMetrics 数据
curl http://localhost:8428/metrics | grep up

# 2. 验证 Loki 日志
curl -G http://localhost:3100/loki/api/v1/query \
  --data-urlencode 'query={job="syslog"}'

# 3. 访问 Grafana
open http://localhost:3000

# 4. 检查 Alloy 自监控
curl http://localhost:12345/metrics | grep alloy
```

### 步骤 5：对比验证

```bash
# 1. 启动原版本（并行运行）
docker-compose -f docker-compose.yaml up -d

# 2. 对比指标数据
# 在 Grafana 中创建对比面板，比较新旧版本的指标

# 3. 验证告警规则
# 确认所有告警规则正常工作

# 4. 验证拓扑标签
# 确认拓扑标签正确注入
```

## 优势和注意事项

### 优势

1. **简化架构**
   - 减少容器数量（17 → 9）
   - 统一配置文件
   - 降低维护成本

2. **节省资源**
   - 内存使用降低 44%
   - 减少网络开销
   - 降低磁盘 I/O

3. **统一管理**
   - 单一配置文件
   - 统一日志输出
   - 简化故障排查

4. **原生集成**
   - Grafana 官方支持
   - 与 Loki 无缝集成
   - 更好的性能优化

### 注意事项

1. **学习成本**
   - 需要学习 Alloy 配置语法
   - 配置方式与原有工具不同

2. **功能限制**
   - 不支持 IPMI 协议
   - 不支持 LLDP 发现
   - 不支持告警路由

3. **兼容性**
   - 部分配置需要调整
   - 某些高级功能可能不可用

4. **迁移风险**
   - 需要充分测试
   - 建议先在测试环境验证
   - 保留原配置作为备份

## 推荐方案

### 渐进式迁移

1. **第一阶段**：迁移日志采集
   - 用 Alloy 替代 Promtail + Syslog-NG
   - 验证日志数据完整性

2. **第二阶段**：迁移指标采集
   - 用 Alloy 替代 Telegraf（VMware + gNMI）
   - 验证指标数据准确性

3. **第三阶段**：整合 Exporter
   - 用 Alloy 整合 SNMP/Blackbox/Redfish
   - 验证所有指标正常

4. **第四阶段**：全面部署
   - 停止旧版本
   - 完全切换到 Alloy
   - 监控运行状态

### 推荐配置

**生产环境推荐**：
- 保留原架构（稳定可靠）
- 测试环境使用 Alloy（验证可行性）
- 逐步迁移，降低风险

**测试环境推荐**：
- 直接使用 Alloy
- 验证所有功能
- 积累运维经验

## 总结

Grafana Alloy 是一个强大的统一遥测收集器，可以显著简化监控架构，降低资源消耗和维护成本。但考虑到生产环境的稳定性，建议：

1. **先在测试环境充分验证**
2. **采用渐进式迁移策略**
3. **保留原配置作为备份**
4. **确保所有功能正常后再全面部署**

对于当前项目，Alloy 可以替代 6-8 个组件，节省约 2GB 内存和减少 8 个容器，是一个值得考虑的优化方案。