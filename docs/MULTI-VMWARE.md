# VMware 多集群监控配置指南

## 概述

本指南详细说明如何监控多个 VMware vCenter 环境，包括多数据中心、多租户、单用户权限隔离等场景。

## 场景一：多数据中心监控

### 架构说明

```
┌─────────────────────────────────────────────────────────────┐
│                    监控系统 (VictoriaMetrics)                │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  vmware-exporter-dc1 ──┐                                    │
│  vmware-exporter-dc2 ──┼──> vmagent ──> VictoriaMetrics    │
│  vmware-exporter-branch─┤                                    │
│  vmware-exporter-dev ───┘                                    │
│                                                               │
└─────────────────────────────────────────────────────────────┘
         │           │           │           │
         ▼           ▼           ▼           ▼
    vCenter-DC1  vCenter-DC2  vCenter-BR  vCenter-DEV
    (主数据中心)  (灾备中心)   (分支)      (开发测试)
```

### 部署步骤

#### 1. 配置环境变量

复制多 vCenter 环境变量模板:
```bash
cp examples/multi-vmware.env.example .env-multi-vcenter
```

编辑 `.env` 文件，添加所有 vCenter 的配置:
```bash
# 主数据中心
VSPHERE_DC1_HOST=vcenter-dc1.example.com
VSPHERE_DC1_USER=monitoring@vsphere.local
VSPHERE_DC1_PASSWORD=your-password

# 灾备数据中心
VSPHERE_DC2_HOST=vcenter-dc2.example.com
VSPHERE_DC2_USER=monitoring@vsphere.local
VSPHERE_DC2_PASSWORD=your-password

# ... 更多 vCenter
```

#### 2. 修改 docker-compose.yaml

将 `examples/multi-vmware-cluster.yml` 中的配置合并到 `docker-compose.yaml`:

```yaml
services:
  # 保留原有的单 VMware Exporter 或删除

  # 添加多个 VMware Exporter
  vmware-exporter-dc1:
    image: pryorda/vmware_exporter:latest
    container_name: vmware-exporter-dc1
    ports:
      - "9272:9272"
    environment:
      - VSPHERE_HOST=${VSPHERE_DC1_HOST}
      - VSPHERE_USER=${VSPHERE_DC1_USER}
      - VSPHERE_PASSWORD=${VSPHERE_DC1_PASSWORD}
      - VSPHERE_IGNORE_SSL=True
    restart: unless-stopped
    networks:
      - monitoring
```

#### 3. 配置 vmagent 采集

编辑 `config/vmagent/prometheus.yml`:

```yaml
scrape_configs:
  # 主数据中心 VMware
  - job_name: 'vmware-dc1'
    static_configs:
      - targets: ['vmware-exporter-dc1:9272']
        labels:
          datacenter: 'dc1'
          location: 'main'
          env: 'production'
    scrape_interval: 60s
    scrape_timeout: 50s

  # 灾备数据中心 VMware
  - job_name: 'vmware-dc2'
    static_configs:
      - targets: ['vmware-exporter-dc2:9272']
        labels:
          datacenter: 'dc2'
          location: 'backup'
          env: 'production'
    scrape_interval: 60s
    scrape_timeout: 50s

  # 分支机构 VMware (采集间隔更长)
  - job_name: 'vmware-branch'
    static_configs:
      - targets: ['vmware-exporter-branch:9272']
        labels:
          datacenter: 'branch'
          location: 'remote'
          env: 'production'
    scrape_interval: 120s
    scrape_timeout: 100s

  # 开发测试环境 VMware (采集间隔最长)
  - job_name: 'vmware-dev'
    static_configs:
      - targets: ['vmware-exporter-dev:9272']
        labels:
          datacenter: 'dev'
          location: 'office'
          env: 'development'
    scrape_interval: 300s
    scrape_timeout: 240s
```

#### 4. 启动服务

```bash
docker-compose up -d
```

#### 5. 验证采集

```bash
# 查看采集目标状态
curl http://localhost:8429/targets | grep vmware

# 或使用 Makefile
make show-targets | grep vmware
```

## 场景二：单 vCenter 多租户监控

### 需求说明

在同一个 vCenter 中，为不同部门/租户创建独立的监控用户，每个用户只能监控自己的虚拟机。

### 架构说明

```
                    vCenter (单个)
                         │
        ┌────────────────┼────────────────┐
        │                │                │
  Resource Pool A   Resource Pool B  Resource Pool C
  (财务部虚拟机)      (研发部虚拟机)     (运维部虚拟机)
        │                │                │
        ▼                ▼                ▼
 monitoring-finance  monitoring-dev  monitoring-ops
  (只读财务资源)       (只读研发资源)   (只读运维资源)
        │                │                │
        └────────────────┴────────────────┘
                         │
                    vmagent (统一采集)
```

### 配置步骤

#### 1. 在 vCenter 中创建监控用户

为每个部门创建专用监控账号:

```
用户: monitoring-finance@vsphere.local
权限: 只读 "Finance" 文件夹/资源池

用户: monitoring-dev@vsphere.local
权限: 只读 "Development" 文件夹/资源池

用户: monitoring-ops@vsphere.local
权限: 只读 "Operations" 文件夹/资源池
```

**权限配置步骤:**

1. 登录 vCenter Web Client
2. 导航到具体的文件夹/资源池
3. 右键 -> 添加权限
4. 添加用户: `monitoring-finance@vsphere.local`
5. 角色: `Monitoring-ReadOnly` (自定义只读角色)
6. 勾选 "传播到子对象"
7. 确认保存

#### 2. 部署多个 VMware Exporter 实例

编辑 `docker-compose.yaml`:

```yaml
services:
  # 财务部 VMware 监控
  vmware-exporter-finance:
    image: pryorda/vmware_exporter:latest
    container_name: vmware-exporter-finance
    ports:
      - "9272:9272"
    environment:
      - VSPHERE_HOST=vcenter.example.com
      - VSPHERE_USER=monitoring-finance@vsphere.local
      - VSPHERE_PASSWORD=${VSPHERE_FINANCE_PASSWORD}
      - VSPHERE_IGNORE_SSL=True
    labels:
      - "tenant=finance"
    restart: unless-stopped
    networks:
      - monitoring

  # 研发部 VMware 监控
  vmware-exporter-dev:
    image: pryorda/vmware_exporter:latest
    container_name: vmware-exporter-dev
    ports:
      - "9273:9272"
    environment:
      - VSPHERE_HOST=vcenter.example.com
      - VSPHERE_USER=monitoring-dev@vsphere.local
      - VSPHERE_PASSWORD=${VSPHERE_DEV_PASSWORD}
      - VSPHERE_IGNORE_SSL=True
    labels:
      - "tenant=development"
    restart: unless-stopped
    networks:
      - monitoring

  # 运维部 VMware 监控
  vmware-exporter-ops:
    image: pryorda/vmware_exporter:latest
    container_name: vmware-exporter-ops
    ports:
      - "9274:9272"
    environment:
      - VSPHERE_HOST=vcenter.example.com
      - VSPHERE_USER=monitoring-ops@vsphere.local
      - VSPHERE_PASSWORD=${VSPHERE_OPS_PASSWORD}
      - VSPHERE_IGNORE_SSL=True
    labels:
      - "tenant=operations"
    restart: unless-stopped
    networks:
      - monitoring
```

#### 3. 配置 vmagent 采集

```yaml
scrape_configs:
  # 财务部虚拟机监控
  - job_name: 'vmware-tenant-finance'
    static_configs:
      - targets: ['vmware-exporter-finance:9272']
        labels:
          tenant: 'finance'
          department: 'finance'
          vcenter: 'main'
    scrape_interval: 60s

  # 研发部虚拟机监控
  - job_name: 'vmware-tenant-dev'
    static_configs:
      - targets: ['vmware-exporter-dev:9272']
        labels:
          tenant: 'development'
          department: 'engineering'
          vcenter: 'main'
    scrape_interval: 60s

  # 运维部虚拟机监控
  - job_name: 'vmware-tenant-ops'
    static_configs:
      - targets: ['vmware-exporter-ops:9272']
        labels:
          tenant: 'operations'
          department: 'it'
          vcenter: 'main'
    scrape_interval: 60s
```

#### 4. 配置租户隔离告警

创建 `config/vmalert/alerts/vmware-tenant-alerts.yml`:

```yaml
groups:
  - name: vmware-tenant-alerts
    interval: 60s
    rules:
      # 财务部虚拟机告警
      - alert: FinanceVMDown
        expr: vmware_vm_power_state{tenant="finance"} == 0
        for: 2m
        labels:
          severity: critical
          tenant: finance
        annotations:
          summary: "财务部虚拟机 {{ $labels.vm_name }} 已关机"
          description: "请联系财务部确认"

      # 研发部虚拟机 CPU 过高
      - alert: DevVMHighCPU
        expr: vmware_vm_cpu_usage{tenant="development"} > 85
        for: 10m
        labels:
          severity: warning
          tenant: development
        annotations:
          summary: "研发部虚拟机 {{ $labels.vm_name }} CPU 使用率过高"
          description: "当前 CPU 使用率: {{ $value }}%"
```

#### 5. Grafana 多租户视图

在 Grafana 中创建不同租户的仪表板，使用变量过滤:

```
变量名: tenant
查询: label_values(vmware_vm_power_state, tenant)
类型: Query

面板查询示例:
vmware_vm_cpu_usage{tenant="$tenant"}
```

## 场景三：混合监控（多 vCenter + 多租户）

### 复杂环境示例

```
DC1 vCenter
  ├── Resource Pool: Production
  │   ├── monitoring-prod-user (生产环境监控)
  │   └── vmware-exporter-dc1-prod
  └── Resource Pool: Testing
      ├── monitoring-test-user (测试环境监控)
      └── vmware-exporter-dc1-test

DC2 vCenter
  ├── Resource Pool: DR-Production
  │   └── vmware-exporter-dc2-prod
  └── Resource Pool: DR-Testing
      └── vmware-exporter-dc2-test
```

### 环境变量配置

```bash
# DC1 生产环境
VSPHERE_DC1_PROD_HOST=vcenter-dc1.example.com
VSPHERE_DC1_PROD_USER=monitoring-prod@vsphere.local
VSPHERE_DC1_PROD_PASSWORD=password1

# DC1 测试环境
VSPHERE_DC1_TEST_HOST=vcenter-dc1.example.com
VSPHERE_DC1_TEST_USER=monitoring-test@vsphere.local
VSPHERE_DC1_TEST_PASSWORD=password2

# DC2 生产环境
VSPHERE_DC2_PROD_HOST=vcenter-dc2.example.com
VSPHERE_DC2_PROD_USER=monitoring-prod@vsphere.local
VSPHERE_DC2_PROD_PASSWORD=password3

# DC2 测试环境
VSPHERE_DC2_TEST_HOST=vcenter-dc2.example.com
VSPHERE_DC2_TEST_USER=monitoring-test@vsphere.local
VSPHERE_DC2_TEST_PASSWORD=password4
```

## VMware 用户权限配置详解

### 最小权限原则

监控用户只需要**只读**权限，以下是详细的权限配置:

#### 1. 创建自定义角色 "Monitoring-ReadOnly"

**必需权限:**
```
Global
  ├── Diagnostics
  ├── Health
  ├── Licenses (查看)
  └── Settings (查看)

Datastore
  └── Browse datastore

Host
  ├── Configuration (查看)
  └── Local operations (查看)

Network
  └── Assign network

Resource
  └── Assign virtual machine to resource pool (查看)

Virtual Machine
  ├── Change Configuration (查看)
  ├── Interaction (查看)
  ├── Inventory (查看)
  ├── Provisioning (查看)
  └── State (查看所有状态)

vApp
  └── View OVF environment
```

#### 2. 分配权限

**全局权限（推荐）:**
```
对象: vCenter Server
用户: monitoring@vsphere.local
角色: Monitoring-ReadOnly
传播: 是
```

**细粒度权限（多租户场景）:**
```
对象: 数据中心 -> 特定文件夹/资源池
用户: monitoring-finance@vsphere.local
角色: Monitoring-ReadOnly
传播: 是（仅限该文件夹及子对象）
```

### 验证权限

使用 PowerCLI 验证用户权限:

```powershell
# 连接 vCenter
Connect-VIServer -Server vcenter.example.com -User monitoring@vsphere.local

# 列出可见的虚拟机
Get-VM

# 测试是否可以修改（应该失败）
Get-VM "test-vm" | Set-VM -Name "new-name"  # 应返回权限错误
```

## 性能优化建议

### 1. 采集间隔优化

```yaml
# 生产环境 - 60秒
- job_name: 'vmware-production'
  scrape_interval: 60s
  scrape_timeout: 50s

# 测试环境 - 120秒
- job_name: 'vmware-testing'
  scrape_interval: 120s
  scrape_timeout: 100s

# 分支/远程站点 - 300秒
- job_name: 'vmware-branch'
  scrape_interval: 300s
  scrape_timeout: 240s
```

### 2. VMware Exporter 性能调优

在 `docker-compose.yaml` 中添加资源限制:

```yaml
vmware-exporter-dc1:
  deploy:
    resources:
      limits:
        cpus: '1'
        memory: 1G
      reservations:
        cpus: '0.5'
        memory: 512M
```

### 3. 并发采集优化

如果有大量虚拟机，可以增加 VMware Exporter 的并发数:

```yaml
vmware-exporter-dc1:
  environment:
    - VSPHERE_COLLECT_VSAN=False  # 如果不使用 vSAN
    - VSPHERE_COLLECT_ONLY=vms,hosts,datastores  # 只采集需要的对象
```

## 故障排查

### 问题 1: VMware Exporter 无法连接 vCenter

**检查清单:**
```bash
# 1. 测试网络连接
ping vcenter.example.com
telnet vcenter.example.com 443

# 2. 验证用户名密码
# 尝试用浏览器登录 vCenter

# 3. 查看 Exporter 日志
docker logs vmware-exporter-dc1

# 4. 检查 SSL 证书
# 如果是自签名证书，确保 VSPHERE_IGNORE_SSL=True
```

### 问题 2: 只能看到部分虚拟机

**原因:** 用户权限不足

**解决:**
1. 检查用户在 vCenter 中的权限范围
2. 确认权限已传播到子对象
3. 验证资源池/文件夹的权限设置

### 问题 3: 采集缓慢或超时

**优化方案:**
```yaml
# 增加超时时间
scrape_timeout: 120s

# 减少采集频率
scrape_interval: 300s

# 限制采集对象
environment:
  - VSPHERE_COLLECT_ONLY=vms,hosts
```

## 最佳实践

1. **安全性**
   - 为每个 vCenter 创建专用监控账号
   - 使用最小权限原则
   - 定期轮换密码
   - 启用 vCenter 审计日志

2. **可靠性**
   - 多个 Exporter 实例分散负载
   - 设置合理的采集超时
   - 监控 Exporter 自身健康状态

3. **可维护性**
   - 使用统一的命名规范
   - 通过标签区分不同环境/租户
   - 文档化每个监控用户的权限范围

4. **成本优化**
   - 非关键环境使用更长采集间隔
   - 只采集必要的指标
   - 定期清理不需要的历史数据

## 参考配置示例

完整配置示例文件:
- `examples/multi-vmware-cluster.yml` - 多集群 Docker Compose 配置
- `examples/multi-vmware.env.example` - 环境变量配置
- `config/vmalert/alerts/vmware-tenant-alerts.yml` - 租户告警规则
