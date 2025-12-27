# 使用 Telegraf 替代 vmware-exporter 监控多 vCenter

## 为什么选择 Telegraf？

**核心优势:**
- ✅ **单实例支持多 vCenter** - 一个配置文件配置多个 vCenter
- ✅ 资源消耗更低 - 一个进程处理所有 vCenter
- ✅ 更灵活的数据采集 - 支持自定义采集间隔、过滤
- ✅ 原生支持多种输出 - VictoriaMetrics, InfluxDB, Prometheus等

**对比 vmware-exporter:**
```
vmware-exporter 方案:
  3个vCenter = 3个容器 = 3个进程 = 600-1500MB 内存

Telegraf 方案:
  3个vCenter = 1个容器 = 1个进程 = 200-400MB 内存
```

---

## 快速开始

### 第一步: 修改 docker-compose.yaml

**删除或注释原有的 vmware-exporter 配置**，添加 Telegraf:

```yaml
services:
  # 其他服务保持不变...

  # ===== Telegraf - 多 vCenter 监控 =====
  telegraf-vmware:
    image: telegraf:latest
    container_name: telegraf-vmware
    volumes:
      - ./config/telegraf/telegraf.conf:/etc/telegraf/telegraf.conf:ro
    environment:
      - HOST_PROC=/host/proc
      - HOST_SYS=/host/sys
      - HOST_ETC=/host/etc
    restart: unless-stopped
    networks:
      - monitoring
```

### 第二步: 创建 Telegraf 配置文件

创建 `config/telegraf/telegraf.conf`:

```toml
# Telegraf 全局配置
[agent]
  interval = "60s"
  round_interval = true
  metric_batch_size = 1000
  metric_buffer_limit = 10000
  collection_jitter = "0s"
  flush_interval = "10s"
  flush_jitter = "0s"
  precision = ""
  hostname = ""
  omit_hostname = false

# ===== 输出到 VictoriaMetrics =====
[[outputs.http]]
  url = "http://victoriametrics:8428/api/v1/write"
  data_format = "prometheusremotewrite"

  [outputs.http.headers]
    Content-Type = "application/x-protobuf"
    Content-Encoding = "snappy"
    X-Prometheus-Remote-Write-Version = "0.1.0"

# ===== 监控 vCenter DC1 =====
[[inputs.vsphere]]
  ## vCenter 连接信息
  vcenters = ["https://vcenter-dc1.company.com/sdk"]
  username = "monitoring@vsphere.local"
  password = "Password123!"

  ## 数据中心过滤
  # datacenters = ["DC1"]

  ## 集群过滤
  # clusters = ["Cluster1", "Cluster2"]

  ## 采集间隔
  interval = "60s"

  ## 超时设置
  timeout = "60s"

  ## SSL 配置
  insecure_skip_verify = true

  ## 采集对象
  vm_metric_include = [
    "cpu.usage.average",
    "cpu.ready.summation",
    "mem.usage.average",
    "net.usage.average",
    "disk.usage.average"
  ]

  host_metric_include = [
    "cpu.usage.average",
    "cpu.coreUtilization.average",
    "mem.usage.average",
    "disk.usage.average",
    "net.usage.average"
  ]

  ## 添加自定义标签
  [inputs.vsphere.tags]
    datacenter = "dc1"
    location = "beijing"
    env = "production"

# ===== 监控 vCenter DC2 =====
[[inputs.vsphere]]
  vcenters = ["https://vcenter-dc2.company.com/sdk"]
  username = "monitoring@vsphere.local"
  password = "Password456!"

  interval = "60s"
  timeout = "60s"
  insecure_skip_verify = true

  vm_metric_include = [
    "cpu.usage.average",
    "mem.usage.average",
    "net.usage.average",
    "disk.usage.average"
  ]

  host_metric_include = [
    "cpu.usage.average",
    "mem.usage.average",
    "disk.usage.average"
  ]

  [inputs.vsphere.tags]
    datacenter = "dc2"
    location = "shanghai"
    env = "production"

# ===== 监控 vCenter Branch (分支机构) =====
[[inputs.vsphere]]
  vcenters = ["https://vcenter-branch.company.com/sdk"]
  username = "monitoring@vsphere.local"
  password = "BranchPass123!"

  ## 分支机构采集间隔可以更长
  interval = "120s"
  timeout = "100s"
  insecure_skip_verify = true

  ## 分支机构只采集关键指标
  vm_metric_include = [
    "cpu.usage.average",
    "mem.usage.average"
  ]

  host_metric_include = [
    "cpu.usage.average",
    "mem.usage.average"
  ]

  [inputs.vsphere.tags]
    datacenter = "branch"
    location = "remote"
    env = "production"
```

### 第三步: 创建配置目录

```bash
mkdir -p config/telegraf
```

### 第四步: 启动服务

```bash
# 停止旧的 vmware-exporter (如果有)
docker stop vmware-exporter vmware-exporter-dc1 vmware-exporter-dc2 2>/dev/null

# 启动 Telegraf
docker-compose up -d telegraf-vmware

# 查看日志
docker logs -f telegraf-vmware
```

### 第五步: 验证数据采集

```bash
# 在 VictoriaMetrics 中查询 VMware 指标
curl 'http://localhost:8428/api/v1/query?query=vsphere_vm_cpu_usage_average' | jq

# 或在 Grafana 中查询
vsphere_vm_cpu_usage_average{datacenter="dc1"}
```

---

## 完整配置示例

### 单 vCenter 多租户场景

如果是同一个 vCenter，不同权限的用户：

```toml
# 财务部虚拟机监控
[[inputs.vsphere]]
  vcenters = ["https://vcenter.company.com/sdk"]
  username = "monitoring-finance@vsphere.local"
  password = "FinancePass!"

  ## 只采集财务部资源池的虚拟机
  resource_pools = ["Finance"]

  interval = "60s"
  insecure_skip_verify = true

  [inputs.vsphere.tags]
    tenant = "finance"
    department = "财务部"

# 研发部虚拟机监控
[[inputs.vsphere]]
  vcenters = ["https://vcenter.company.com/sdk"]
  username = "monitoring-dev@vsphere.local"
  password = "DevPass!"

  resource_pools = ["Development"]

  interval = "60s"
  insecure_skip_verify = true

  [inputs.vsphere.tags]
    tenant = "development"
    department = "研发部"

# 运维部虚拟机监控
[[inputs.vsphere]]
  vcenters = ["https://vcenter.company.com/sdk"]
  username = "monitoring-ops@vsphere.local"
  password = "OpsPass!"

  resource_pools = ["Operations"]

  interval = "60s"
  insecure_skip_verify = true

  [inputs.vsphere.tags]
    tenant = "operations"
    department = "运维部"
```

---

## Telegraf 配置详解

### 关键参数说明

```toml
[[inputs.vsphere]]
  ## vCenter 地址（必需）
  vcenters = ["https://vcenter.example.com/sdk"]

  ## 认证信息（必需）
  username = "monitoring@vsphere.local"
  password = "password"

  ## 采集间隔（可选，默认60s）
  interval = "60s"

  ## 超时时间（可选，默认20s）
  timeout = "60s"

  ## 跳过 SSL 验证（可选，默认false）
  insecure_skip_verify = true

  ## 数据中心过滤（可选）
  # datacenters = ["DC1", "DC2"]

  ## 集群过滤（可选）
  # clusters = ["Cluster1"]

  ## 主机过滤（可选）
  # hosts = ["esxi1.example.com"]

  ## 虚拟机过滤（可选）
  # vms = ["vm1", "vm2"]

  ## 资源池过滤（可选）
  # resource_pools = ["Finance", "Development"]

  ## 虚拟机指标（可选）
  vm_metric_include = [
    "cpu.usage.average",
    "cpu.ready.summation",
    "mem.usage.average",
    "net.usage.average",
    "disk.usage.average",
    "disk.read.average",
    "disk.write.average"
  ]

  ## 主机指标（可选）
  host_metric_include = [
    "cpu.usage.average",
    "cpu.coreUtilization.average",
    "mem.usage.average",
    "disk.usage.average",
    "net.usage.average"
  ]

  ## 数据存储指标（可选）
  datastore_metric_include = [
    "disk.used.latest",
    "disk.capacity.latest"
  ]

  ## 添加自定义标签（可选）
  [inputs.vsphere.tags]
    datacenter = "dc1"
    env = "production"
    location = "beijing"
```

### 可采集的指标

**虚拟机指标:**
- `cpu.usage.average` - CPU 使用率
- `cpu.ready.summation` - CPU 就绪时间
- `mem.usage.average` - 内存使用率
- `disk.usage.average` - 磁盘使用率
- `net.usage.average` - 网络使用率
- `disk.read.average` - 磁盘读取
- `disk.write.average` - 磁盘写入

**ESXi 主机指标:**
- `cpu.usage.average` - CPU 使用率
- `cpu.coreUtilization.average` - CPU 核心利用率
- `mem.usage.average` - 内存使用率
- `disk.usage.average` - 磁盘使用率
- `net.usage.average` - 网络使用率

**数据存储指标:**
- `disk.used.latest` - 已使用空间
- `disk.capacity.latest` - 总容量

---

## 性能对比

### 资源消耗对比（监控3个 vCenter）

| 指标 | vmware-exporter×3 | Telegraf×1 |
|------|------------------|------------|
| 容器数量 | 3 个 | 1 个 |
| CPU 使用 | 0.3-0.9 核 | 0.2-0.5 核 |
| 内存使用 | 600-1500 MB | 200-400 MB |
| 网络连接 | 3 个持久连接 | 3 个持久连接 |
| 端口占用 | 9272, 9273, 9274 | 无（内部输出） |

### 配置复杂度对比

**vmware-exporter:**
```yaml
# 需要3个容器定义
vmware-exporter-dc1:
  ports: ["9272:9272"]
  environment: [...]

vmware-exporter-dc2:
  ports: ["9273:9272"]
  environment: [...]

vmware-exporter-dc3:
  ports: ["9274:9272"]
  environment: [...]

# vmagent 需要3个采集任务
- job_name: 'vmware-dc1'
  targets: ['vmware-exporter-dc1:9272']
- job_name: 'vmware-dc2'
  targets: ['vmware-exporter-dc2:9272']
- job_name: 'vmware-dc3'
  targets: ['vmware-exporter-dc3:9272']
```

**Telegraf:**
```yaml
# 只需要1个容器定义
telegraf-vmware:
  volumes: ['./config/telegraf/telegraf.conf']

# 配置文件中定义多个 vCenter
[[inputs.vsphere]]
  vcenters = ["dc1"]
[[inputs.vsphere]]
  vcenters = ["dc2"]
[[inputs.vsphere]]
  vcenters = ["dc3"]
```

---

## 告警规则配置

Telegraf 输出的指标名称与 vmware-exporter 不同，需要修改告警规则。

### 指标名称对照

| vmware-exporter | Telegraf | 说明 |
|----------------|----------|------|
| `vmware_vm_power_state` | `vsphere_vm_power_state` | 虚拟机电源状态 |
| `vmware_vm_cpu_usage` | `vsphere_vm_cpu_usage_average` | CPU 使用率 |
| `vmware_vm_mem_usage` | `vsphere_vm_mem_usage_average` | 内存使用率 |
| `vmware_host_cpu_usage` | `vsphere_host_cpu_usage_average` | 主机 CPU |
| `vmware_datastore_capacity_size` | `vsphere_datastore_disk_capacity_latest` | 数据存储容量 |

### 修改告警规则

编辑 `config/vmalert/alerts/vmware-alerts.yml`:

```yaml
groups:
  - name: vmware-telegraf-alerts
    interval: 60s
    rules:
      # 虚拟机宕机
      - alert: VMDown
        expr: vsphere_vm_power_state == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "虚拟机 {{ $labels.moid }} 已关机"
          description: "数据中心 {{ $labels.datacenter }} 的虚拟机已关机"

      # 虚拟机 CPU 过高
      - alert: VMHighCPU
        expr: vsphere_vm_cpu_usage_average > 85
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "虚拟机 CPU 使用率过高"
          description: "CPU 使用率: {{ $value }}%"

      # ESXi 主机 CPU 过高
      - alert: ESXiHighCPU
        expr: vsphere_host_cpu_usage_average > 90
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "ESXi 主机 CPU 使用率过高"
          description: "CPU 使用率: {{ $value }}%"

      # 数据存储空间不足
      - alert: DatastoreLowSpace
        expr: (vsphere_datastore_disk_used_latest / vsphere_datastore_disk_capacity_latest) * 100 > 85
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "数据存储空间不足"
          description: "已使用 {{ $value }}%"
```

---

## 从 vmware-exporter 迁移到 Telegraf

### 迁移步骤

**1. 备份现有配置**
```bash
./scripts/backup.sh
```

**2. 停止 vmware-exporter**
```bash
docker stop $(docker ps -q --filter "name=vmware-exporter")
```

**3. 部署 Telegraf**
```bash
# 创建配置目录
mkdir -p config/telegraf

# 复制配置模板
cp examples/telegraf/telegraf-vsphere.conf config/telegraf/telegraf.conf

# 编辑配置，添加你的 vCenter 信息
vim config/telegraf/telegraf.conf

# 启动 Telegraf
docker-compose up -d telegraf-vmware
```

**4. 验证数据采集**
```bash
# 查看日志
docker logs -f telegraf-vmware

# 查询指标
curl 'http://localhost:8428/api/v1/query?query=vsphere_vm_cpu_usage_average'
```

**5. 更新告警规则**
```bash
# 修改告警规则中的指标名称
vim config/vmalert/alerts/vmware-alerts.yml

# 重载告警规则
make reload-vmalert
```

**6. 验证告警**
```bash
# 查看告警规则状态
curl http://localhost:8880/api/v1/rules
```

**7. 清理旧容器**
```bash
docker rm $(docker ps -aq --filter "name=vmware-exporter")
```

---

## 优缺点对比

### Telegraf 优点
- ✅ **单实例支持多 vCenter** - 配置简单
- ✅ **资源消耗更低** - 一个进程处理所有
- ✅ **更灵活的过滤** - 支持资源池、集群、主机过滤
- ✅ **更多输出选项** - 支持多种时序数据库
- ✅ **更丰富的指标** - 可以自定义采集的指标

### Telegraf 缺点
- ❌ 指标名称不同 - 需要修改告警规则
- ❌ 配置复杂度略高 - TOML 配置格式
- ❌ 社区仪表板较少 - Grafana 仪表板需要自己调整

### vmware-exporter 优点
- ✅ 配置简单 - 环境变量即可
- ✅ 社区仪表板多 - Grafana 有现成的
- ✅ 专注 VMware - 只做一件事

### vmware-exporter 缺点
- ❌ **不支持多 vCenter** - 必须多实例
- ❌ 资源消耗高 - 多个进程
- ❌ 配置繁琐 - 需要多个容器定义

---

## 推荐方案

### 场景 1: 监控 1-2 个 vCenter
**推荐**: vmware-exporter
- 配置简单
- 资源消耗可接受
- 有现成的 Grafana 仪表板

### 场景 2: 监控 3 个以上 vCenter
**推荐**: **Telegraf**
- 单实例配置
- 资源消耗明显降低
- 配置集中管理

### 场景 3: 大规模环境 (10+ vCenter)
**推荐**: Telegraf + 分布式部署
- 按地域部署多个 Telegraf 实例
- 每个实例监控本地区的 vCenter
- 降低网络延迟

---

## 完整 Docker Compose 配置

创建文件 `docker-compose-telegraf.yml`:

```yaml
version: '3.8'

services:
  # 保留其他服务 (victoriametrics, vmagent, grafana...)

  # ===== Telegraf - VMware 监控 =====
  telegraf-vmware:
    image: telegraf:latest
    container_name: telegraf-vmware
    volumes:
      - ./config/telegraf/telegraf.conf:/etc/telegraf/telegraf.conf:ro
    restart: unless-stopped
    networks:
      - monitoring
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

networks:
  monitoring:
    driver: bridge
```

---

## 总结

**如果你不想部署多个 vmware-exporter，强烈推荐使用 Telegraf！**

**核心优势:**
- 1️⃣ **单实例配置多个 vCenter** - 解决你的痛点
- 2️⃣ **资源消耗更低** - 省内存省CPU
- 3️⃣ **配置更灵活** - 支持更多过滤选项

**快速开始:**
```bash
# 1. 创建 Telegraf 配置
mkdir -p config/telegraf
vim config/telegraf/telegraf.conf  # 添加多个 vCenter

# 2. 启动 Telegraf
docker-compose up -d telegraf-vmware

# 3. 验证
docker logs -f telegraf-vmware
```

这样就不需要部署多个容器了！
