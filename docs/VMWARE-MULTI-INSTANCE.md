# 多 VMware 集群监控 - 实战配置指南

## 原理说明

**重要**: vmware-exporter 本身确实是单用户单连接！

```
1个 vmware-exporter 容器 = 1个 vSphere 用户 = 连接1个 vCenter
```

**解决方案**: 部署多个 vmware-exporter 容器实例

```
容器1 (端口9272) → 用户monitor-dc1 → vCenter DC1
容器2 (端口9273) → 用户monitor-dc2 → vCenter DC2
容器3 (端口9274) → 用户monitor-branch → vCenter Branch
```

---

## 场景一: 监控 2 个数据中心的 vCenter

### 第一步: 在两个 vCenter 上创建监控用户

**vCenter DC1:**
```
用户名: monitoring@vsphere.local
密码: Password123!
权限: 只读 (Read-only)
```

**vCenter DC2:**
```
用户名: monitoring@vsphere.local  # 可以同名
密码: Password456!
权限: 只读 (Read-only)
```

### 第二步: 修改 .env 文件

```bash
# 数据中心1
VSPHERE_DC1_HOST=vcenter-dc1.company.com
VSPHERE_DC1_USER=monitoring@vsphere.local
VSPHERE_DC1_PASSWORD=Password123!

# 数据中心2
VSPHERE_DC2_HOST=vcenter-dc2.company.com
VSPHERE_DC2_USER=monitoring@vsphere.local
VSPHERE_DC2_PASSWORD=Password456!

# SSL 配置
VSPHERE_IGNORE_SSL=True
```

### 第三步: 修改 docker-compose.yaml

在 `docker-compose.yaml` 中添加两个 vmware-exporter 容器：

```yaml
services:
  # 原有的单个 vmware-exporter 可以删除或注释

  # ===== 数据中心1 VMware Exporter =====
  vmware-exporter-dc1:
    image: pryorda/vmware_exporter:latest
    container_name: vmware-exporter-dc1
    ports:
      - "9272:9272"  # 第一个实例用9272端口
    environment:
      - VSPHERE_HOST=${VSPHERE_DC1_HOST}
      - VSPHERE_USER=${VSPHERE_DC1_USER}
      - VSPHERE_PASSWORD=${VSPHERE_DC1_PASSWORD}
      - VSPHERE_IGNORE_SSL=${VSPHERE_IGNORE_SSL:-True}
    restart: unless-stopped
    networks:
      - monitoring

  # ===== 数据中心2 VMware Exporter =====
  vmware-exporter-dc2:
    image: pryorda/vmware_exporter:latest
    container_name: vmware-exporter-dc2
    ports:
      - "9273:9272"  # 第二个实例用9273端口 (主机端口不同!)
    environment:
      - VSPHERE_HOST=${VSPHERE_DC2_HOST}
      - VSPHERE_USER=${VSPHERE_DC2_USER}
      - VSPHERE_PASSWORD=${VSPHERE_DC2_PASSWORD}
      - VSPHERE_IGNORE_SSL=${VSPHERE_IGNORE_SSL:-True}
    restart: unless-stopped
    networks:
      - monitoring
```

**关键点**:
- 容器名不同: `vmware-exporter-dc1` vs `vmware-exporter-dc2`
- **主机端口映射不同**: `9272:9272` vs `9273:9272`
- 容器内端口都是 9272，但映射到主机的端口不同

### 第四步: 配置 vmagent 采集

编辑 `config/vmagent/prometheus.yml`:

```yaml
scrape_configs:
  # 数据中心1 VMware 监控
  - job_name: 'vmware-dc1'
    static_configs:
      - targets: ['vmware-exporter-dc1:9272']  # Docker 容器名:容器端口
        labels:
          datacenter: 'dc1'
          location: 'beijing'
          env: 'production'
    scrape_interval: 60s
    scrape_timeout: 50s

  # 数据中心2 VMware 监控
  - job_name: 'vmware-dc2'
    static_configs:
      - targets: ['vmware-exporter-dc2:9272']  # Docker 容器名:容器端口
        labels:
          datacenter: 'dc2'
          location: 'shanghai'
          env: 'production'
    scrape_interval: 60s
    scrape_timeout: 50s
```

**注意**: 在 Docker 网络内部，使用容器名访问，端口都是 9272

### 第五步: 启动服务

```bash
# 停止旧服务
docker-compose down

# 启动新配置
docker-compose up -d

# 验证容器状态
docker ps | grep vmware-exporter

# 应该看到两个容器:
# vmware-exporter-dc1  0.0.0.0:9272->9272/tcp
# vmware-exporter-dc2  0.0.0.0:9273->9272/tcp
```

### 第六步: 验证采集

```bash
# 测试 DC1 exporter
curl http://localhost:9272/metrics | grep vmware_vm_power_state

# 测试 DC2 exporter
curl http://localhost:9273/metrics | grep vmware_vm_power_state

# 验证 vmagent 采集状态
curl http://localhost:8429/targets | grep vmware
```

---

## 场景二: 单个 vCenter 的多租户监控（权限隔离）

**需求**: 同一个 vCenter，但不同部门只能看到自己的虚拟机

### 架构说明

```
同一个 vCenter: vcenter.company.com
├── 资源池: Finance (财务部虚拟机)
│   └── 监控用户: monitoring-finance@vsphere.local (只能看财务部VM)
├── 资源池: Development (研发部虚拟机)
│   └── 监控用户: monitoring-dev@vsphere.local (只能看研发部VM)
└── 资源池: Operations (运维部虚拟机)
    └── 监控用户: monitoring-ops@vsphere.local (只能看运维部VM)

部署3个 vmware-exporter 容器:
├── vmware-exporter-finance (端口9272) → monitoring-finance用户
├── vmware-exporter-dev (端口9273) → monitoring-dev用户
└── vmware-exporter-ops (端口9274) → monitoring-ops用户
```

### 第一步: 在 vCenter 中配置权限

**为财务部创建监控用户:**

1. 登录 vCenter Web Client
2. 菜单 → 管理 → 单点登录 → 用户和组
3. 添加用户: `monitoring-finance@vsphere.local`
4. 导航到 "财务部" 资源池
5. 右键 → 添加权限
   - 用户: `monitoring-finance@vsphere.local`
   - 角色: `只读` (Read-only)
   - ✅ 勾选 "传播到子对象"
6. 保存

**重复以上步骤为研发部和运维部创建用户:**
- `monitoring-dev@vsphere.local` → 只对 "研发部" 资源池只读
- `monitoring-ops@vsphere.local` → 只对 "运维部" 资源池只读

### 第二步: 配置环境变量

`.env` 文件:

```bash
# 同一个 vCenter，但使用不同的用户
VSPHERE_HOST=vcenter.company.com

# 财务部监控用户
VSPHERE_FINANCE_USER=monitoring-finance@vsphere.local
VSPHERE_FINANCE_PASSWORD=FinancePass123!

# 研发部监控用户
VSPHERE_DEV_USER=monitoring-dev@vsphere.local
VSPHERE_DEV_PASSWORD=DevPass123!

# 运维部监控用户
VSPHERE_OPS_USER=monitoring-ops@vsphere.local
VSPHERE_OPS_PASSWORD=OpsPass123!

VSPHERE_IGNORE_SSL=True
```

### 第三步: 部署 3 个 vmware-exporter 容器

`docker-compose.yaml`:

```yaml
services:
  # 财务部 VMware 监控
  vmware-exporter-finance:
    image: pryorda/vmware_exporter:latest
    container_name: vmware-exporter-finance
    ports:
      - "9272:9272"
    environment:
      - VSPHERE_HOST=${VSPHERE_HOST}
      - VSPHERE_USER=${VSPHERE_FINANCE_USER}
      - VSPHERE_PASSWORD=${VSPHERE_FINANCE_PASSWORD}
      - VSPHERE_IGNORE_SSL=${VSPHERE_IGNORE_SSL}
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
      - VSPHERE_HOST=${VSPHERE_HOST}
      - VSPHERE_USER=${VSPHERE_DEV_USER}
      - VSPHERE_PASSWORD=${VSPHERE_DEV_PASSWORD}
      - VSPHERE_IGNORE_SSL=${VSPHERE_IGNORE_SSL}
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
      - VSPHERE_HOST=${VSPHERE_HOST}
      - VSPHERE_USER=${VSPHERE_OPS_USER}
      - VSPHERE_PASSWORD=${VSPHERE_OPS_PASSWORD}
      - VSPHERE_IGNORE_SSL=${VSPHERE_IGNORE_SSL}
    restart: unless-stopped
    networks:
      - monitoring
```

### 第四步: 配置 vmagent

`config/vmagent/prometheus.yml`:

```yaml
scrape_configs:
  # 财务部虚拟机监控
  - job_name: 'vmware-finance'
    static_configs:
      - targets: ['vmware-exporter-finance:9272']
        labels:
          tenant: 'finance'
          department: '财务部'
    scrape_interval: 60s

  # 研发部虚拟机监控
  - job_name: 'vmware-dev'
    static_configs:
      - targets: ['vmware-exporter-dev:9272']
        labels:
          tenant: 'development'
          department: '研发部'
    scrape_interval: 60s

  # 运维部虚拟机监控
  - job_name: 'vmware-ops'
    static_configs:
      - targets: ['vmware-exporter-ops:9272']
        labels:
          tenant: 'operations'
          department: '运维部'
    scrape_interval: 60s
```

### 第五步: 验证权限隔离

```bash
# 启动服务
docker-compose up -d

# 测试财务部 exporter（应该只能看到财务部的虚拟机）
curl http://localhost:9272/metrics | grep vmware_vm_name

# 测试研发部 exporter（应该只能看到研发部的虚拟机）
curl http://localhost:9273/metrics | grep vmware_vm_name

# 测试运维部 exporter（应该只能看到运维部的虚拟机）
curl http://localhost:9274/metrics | grep vmware_vm_name
```

---

## 场景三: 为什么需要多个容器？

### 错误理解 ❌

```
一个 vmware-exporter 容器可以连接多个 vCenter？
→ 不行！一个容器只能连接一个 vCenter
```

### 正确理解 ✅

```
想监控 N 个 vCenter = 部署 N 个 vmware-exporter 容器

监控 3 个 vCenter:
  ├── vmware-exporter-dc1 (9272端口)
  ├── vmware-exporter-dc2 (9273端口)
  └── vmware-exporter-dc3 (9274端口)
```

### 为什么这样设计？

因为 vmware-exporter 是通过 **环境变量** 配置的：

```yaml
environment:
  - VSPHERE_HOST=vcenter.company.com  # 只能配置一个
  - VSPHERE_USER=monitoring           # 只能配置一个用户
  - VSPHERE_PASSWORD=password         # 只能配置一个密码
```

**一个容器 = 一组环境变量 = 一个 vCenter 连接**

---

## 端口映射详解

### Docker 网络模式

```yaml
vmware-exporter-dc1:
  ports:
    - "9272:9272"
    #  ^^^^  ^^^^
    #  主机  容器
    #  端口  端口
```

**解释:**
- 容器内端口: 固定是 `9272` (vmware-exporter 监听端口)
- 主机端口: 可以自定义，避免冲突

**多实例端口映射:**
```yaml
vmware-exporter-dc1:
  ports:
    - "9272:9272"  # 主机9272 → 容器9272

vmware-exporter-dc2:
  ports:
    - "9273:9272"  # 主机9273 → 容器9272 (容器内都是9272)

vmware-exporter-dc3:
  ports:
    - "9274:9272"  # 主机9274 → 容器9272
```

### 访问方式对比

| 访问方式 | 地址 | 说明 |
|---------|------|------|
| 外部访问 DC1 | `http://192.168.1.100:9272` | 使用主机IP + 主机端口 |
| 外部访问 DC2 | `http://192.168.1.100:9273` | 使用主机IP + 主机端口 |
| vmagent 访问 DC1 | `http://vmware-exporter-dc1:9272` | Docker网络内用容器名 |
| vmagent 访问 DC2 | `http://vmware-exporter-dc2:9272` | Docker网络内用容器名 |

---

## 常见问题

### Q1: 可以让所有容器都用 9272 端口吗？

**A**: 不行！会端口冲突。

```yaml
# ❌ 错误 - 端口冲突
vmware-exporter-dc1:
  ports: - "9272:9272"
vmware-exporter-dc2:
  ports: - "9272:9272"  # 错误！9272已被占用
```

```yaml
# ✅ 正确 - 主机端口不同
vmware-exporter-dc1:
  ports: - "9272:9272"
vmware-exporter-dc2:
  ports: - "9273:9272"  # 主机端口不同，容器端口可以相同
```

### Q2: 可以只部署一个 vmware-exporter，通过配置文件指定多个 vCenter 吗？

**A**: 不可以。vmware-exporter 不支持多 vCenter 配置。必须部署多个容器实例。

### Q3: 如果我有 10 个 vCenter，需要部署 10 个容器吗？

**A**: 是的。但可以优化：

```yaml
# 使用 docker-compose scale（不推荐，配置复杂）
# 或使用 Kubernetes DaemonSet（推荐大规模部署）
```

对于 10+ 个 vCenter，建议：
1. 使用配置管理工具（Ansible/Terraform）
2. 或考虑使用 Kubernetes 部署

### Q4: 容器太多会不会占用很多资源？

**A**: vmware-exporter 很轻量：

```yaml
单个容器资源消耗:
  CPU: ~0.1-0.3 核
  内存: ~200-500 MB

10 个容器总消耗:
  CPU: ~1-3 核
  内存: ~2-5 GB
```

可以通过资源限制优化：

```yaml
vmware-exporter-dc1:
  deploy:
    resources:
      limits:
        cpus: '0.5'
        memory: 512M
```

---

## 完整示例：监控 2 个 vCenter

创建文件 `docker-compose-multi-vcenter.yml`:

```yaml
version: '3.8'

services:
  # 保留原有的其他服务（victoriametrics, vmagent等）...

  # vCenter 1 (主数据中心)
  vmware-exporter-dc1:
    image: pryorda/vmware_exporter:latest
    container_name: vmware-exporter-dc1
    ports:
      - "9272:9272"
    environment:
      - VSPHERE_HOST=vcenter-dc1.company.com
      - VSPHERE_USER=monitoring@vsphere.local
      - VSPHERE_PASSWORD=Password123!
      - VSPHERE_IGNORE_SSL=True
    restart: unless-stopped
    networks:
      - monitoring

  # vCenter 2 (灾备数据中心)
  vmware-exporter-dc2:
    image: pryorda/vmware_exporter:latest
    container_name: vmware-exporter-dc2
    ports:
      - "9273:9272"
    environment:
      - VSPHERE_HOST=vcenter-dc2.company.com
      - VSPHERE_USER=monitoring@vsphere.local
      - VSPHERE_PASSWORD=Password456!
      - VSPHERE_IGNORE_SSL=True
    restart: unless-stopped
    networks:
      - monitoring

networks:
  monitoring:
    driver: bridge
```

部署：

```bash
# 停止现有服务
docker-compose down

# 使用新配置启动
docker-compose -f docker-compose-multi-vcenter.yml up -d

# 验证
docker ps | grep vmware-exporter
curl http://localhost:9272/healthz  # DC1
curl http://localhost:9273/healthz  # DC2
```

---

## 总结

**核心概念:**
- ✅ 1 个 vmware-exporter 容器 = 1 个 vSphere 用户连接
- ✅ 监控 N 个 vCenter = 部署 N 个容器
- ✅ 权限隔离 = 不同用户 + 不同容器
- ✅ 主机端口不能冲突，但容器内端口都是 9272

**最佳实践:**
1. 为每个 vCenter 创建专用监控账号
2. 使用有意义的容器名 (vmware-exporter-dc1, vmware-exporter-finance)
3. 使用标签区分不同环境 (datacenter, tenant, location)
4. 设置合理的资源限制
5. 定期验证权限和采集状态
