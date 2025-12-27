# VMware 多集群监控方案对比

## 快速决策

| 场景 | 推荐方案 | 原因 |
|------|---------|------|
| 1-2 个 vCenter | vmware-exporter | 配置简单，社区支持好 |
| 3+ 个 vCenter | **Telegraf** | 单实例，资源节省 |
| 需要自定义采集指标 | **Telegraf** | 更灵活的指标选择 |
| 已有 Prometheus 生态 | vmware-exporter | 兼容性好，仪表板多 |
| 资源受限环境 | **Telegraf** | 内存占用低 70% |

---

## 方案一: 多个 vmware-exporter 容器

### 架构
```
3 个 vCenter = 3 个容器
├── vmware-exporter-dc1 (端口 9272)
├── vmware-exporter-dc2 (端口 9273)
└── vmware-exporter-dc3 (端口 9274)
```

### 优点 ✅
- 配置超简单 - 只需环境变量
- 社区支持好 - Grafana 仪表板丰富
- 专注 VMware - 只做监控这一件事
- 故障隔离好 - 一个容器挂了不影响其他

### 缺点 ❌
- 资源消耗高 - 3 个 vCenter = 600-1500MB 内存
- 配置分散 - 每个容器独立配置
- 端口管理复杂 - 需要手动分配端口

### 资源消耗
```
单个容器:
  CPU: ~0.1-0.3 核
  内存: ~200-500 MB

3 个容器总计:
  CPU: ~0.3-0.9 核
  内存: ~600-1500 MB
  端口: 9272, 9273, 9274
```

### 适用场景
- 监控 1-2 个 vCenter
- 需要完全隔离的监控实例
- 团队熟悉 Prometheus 生态
- 不关心资源消耗

### 配置文件
- 参考: `docs/VMWARE-MULTI-INSTANCE.md`
- 示例: `examples/multi-vmware-cluster.yml`

---

## 方案二: 单个 Telegraf 实例（推荐）

### 架构
```
3 个 vCenter = 1 个容器
└── telegraf-vmware
    ├── vCenter DC1
    ├── vCenter DC2
    └── vCenter DC3
```

### 优点 ✅
- **单实例多 vCenter** - 配置集中管理
- **资源消耗低** - 内存节省 70%
- 采集更灵活 - 支持资源池、集群过滤
- 配置更强大 - 可自定义采集间隔和指标
- 原生支持多种输出 - VictoriaMetrics/InfluxDB/Prometheus

### 缺点 ❌
- 配置复杂度高 - TOML 格式，学习成本
- 指标名称不同 - 需要修改告警规则 (`vsphere_*` vs `vmware_*`)
- 社区仪表板少 - Grafana 仪表板需要自己调整
- 单点故障 - 一个容器挂了全部 vCenter 监控失效

### 资源消耗
```
单个 Telegraf 容器监控 3 个 vCenter:
  CPU: ~0.2-0.5 核
  内存: ~200-400 MB
  端口: 无需暴露（内部输出）

节省:
  内存: 70% ↓
  CPU: 30% ↓
  容器数: 66% ↓
```

### 适用场景
- 监控 3+ 个 vCenter
- 资源受限环境
- 需要灵活的指标采集策略
- 接受一定配置复杂度

### 配置文件
- 参考: `docs/TELEGRAF-VMWARE.md`
- 示例: `examples/telegraf/telegraf-vsphere.conf`

---

## 详细对比

### 配置复杂度

**vmware-exporter (简单)**:
```yaml
# docker-compose.yaml
vmware-exporter-dc1:
  environment:
    - VSPHERE_HOST=vcenter1.com
    - VSPHERE_USER=monitor
    - VSPHERE_PASSWORD=pass123
```

**Telegraf (复杂但强大)**:
```toml
# telegraf.conf
[[inputs.vsphere]]
  vcenters = ["https://vcenter1.com/sdk"]
  username = "monitor@vsphere.local"
  password = "pass123"

  # 可以过滤集群
  clusters = ["Cluster1", "Cluster2"]

  # 可以自定义指标
  vm_metric_include = [
    "cpu.usage.average",
    "mem.usage.average"
  ]
```

### 指标名称对比

| vmware-exporter | Telegraf | 说明 |
|----------------|----------|------|
| `vmware_vm_power_state` | `vsphere_vm_power_state` | 虚拟机电源状态 |
| `vmware_vm_cpu_usage` | `vsphere_vm_cpu_usage_average` | CPU 使用率 |
| `vmware_vm_mem_usage` | `vsphere_vm_mem_usage_average` | 内存使用率 |
| `vmware_host_cpu_usage` | `vsphere_host_cpu_usage_average` | 主机 CPU |
| `vmware_datastore_capacity_size` | `vsphere_datastore_disk_capacity_latest` | 存储容量 |

**注意**: 如果从 vmware-exporter 迁移到 Telegraf，需要修改所有告警规则！

### 功能对比

| 功能 | vmware-exporter | Telegraf |
|-----|----------------|----------|
| 单实例多 vCenter | ❌ 不支持 | ✅ 支持 |
| 资源池过滤 | ❌ 不支持 | ✅ 支持 |
| 集群过滤 | ❌ 不支持 | ✅ 支持 |
| 自定义采集间隔 | ❌ 全局配置 | ✅ 每个 vCenter 独立配置 |
| 自定义指标选择 | ❌ 采集所有 | ✅ 精细控制 |
| 自定义标签 | ❌ 不支持 | ✅ 支持任意标签 |
| Grafana 仪表板 | ✅ 丰富 | ⚠️ 需自己调整 |
| 输出格式 | Prometheus | 多种格式 |

---

## 迁移指南

### 从 vmware-exporter 迁移到 Telegraf

**步骤 1: 备份**
```bash
./scripts/backup.sh
```

**步骤 2: 停止 vmware-exporter**
```bash
docker stop $(docker ps -q --filter "name=vmware-exporter")
```

**步骤 3: 部署 Telegraf**
```bash
# 创建配置目录
mkdir -p config/telegraf

# 复制配置模板
cp examples/telegraf/telegraf-vsphere.conf config/telegraf/telegraf.conf

# 编辑配置
vim config/telegraf/telegraf.conf

# 启动 Telegraf
docker-compose up -d telegraf-vmware
```

**步骤 4: 更新告警规则**
```bash
# 修改所有告警规则文件
sed -i 's/vmware_/vsphere_/g' config/vmalert/alerts/vmware-alerts.yml

# 重载告警规则
make reload-vmalert
```

**步骤 5: 验证**
```bash
# 查看 Telegraf 日志
docker logs -f telegraf-vmware

# 查询指标
curl 'http://localhost:8428/api/v1/query?query=vsphere_vm_cpu_usage_average'
```

---

## 成本对比

### 监控 5 个 vCenter 的成本

**vmware-exporter 方案**:
```
容器数: 5 个
总内存: ~1-2.5 GB
总 CPU: ~0.5-1.5 核
端口: 9272-9276 (5个)
配置文件: 5 个容器定义 + 5 个采集任务
```

**Telegraf 方案**:
```
容器数: 1 个
总内存: ~300-500 MB
总 CPU: ~0.3-0.7 核
端口: 0 个（内部输出）
配置文件: 1 个配置文件
```

**节省**:
- 内存: 节省 70-80%
- CPU: 节省 40-50%
- 运维复杂度: ↓↓↓

---

## 推荐决策树

```
开始
  │
  ├─ 监控几个 vCenter？
  │   ├─ 1-2 个 → vmware-exporter
  │   └─ 3+ 个 → 继续
  │
  ├─ 资源是否受限？
  │   ├─ 是 → Telegraf
  │   └─ 否 → 继续
  │
  ├─ 是否需要灵活的指标采集？
  │   ├─ 是 → Telegraf
  │   └─ 否 → 继续
  │
  ├─ 团队是否熟悉 Prometheus 生态？
  │   ├─ 是，需要现成仪表板 → vmware-exporter
  │   └─ 否，愿意自定义 → Telegraf
  │
  └─ 默认推荐 → Telegraf（更现代，更高效）
```

---

## 实际案例

### 案例 1: 小型环境（2 个 vCenter）
**选择**: vmware-exporter
**原因**:
- 配置简单，10 分钟部署完成
- 有现成的 Grafana 仪表板
- 资源消耗可接受（~400MB）

### 案例 2: 中型环境（5 个 vCenter）
**选择**: Telegraf
**原因**:
- 节省内存 1.5GB（重要）
- 配置集中管理
- 支持按集群过滤，减少不必要的采集

### 案例 3: 大型环境（10+ 个 vCenter）
**选择**: Telegraf + 分布式部署
**架构**:
```
北京机房: Telegraf 实例 1 → 监控北京 3 个 vCenter
上海机房: Telegraf 实例 2 → 监控上海 4 个 vCenter
深圳机房: Telegraf 实例 3 → 监控深圳 3 个 vCenter
```
**原因**:
- 降低网络延迟
- 故障隔离
- 每个实例仍然节省大量资源

---

## 总结

**如果你不确定，推荐使用 Telegraf！**

理由:
1. **更现代** - Telegraf 是 InfluxData 的官方产品，持续维护
2. **更高效** - 资源消耗显著降低
3. **更灵活** - 支持更多高级功能
4. **更简洁** - 单实例管理所有 vCenter

**唯一的代价**:
- 初次配置需要 30 分钟熟悉 TOML 格式
- 需要自己调整 Grafana 仪表板（或使用我们提供的模板）

**快速开始**:
```bash
# 查看 Telegraf 完整文档
cat docs/TELEGRAF-VMWARE.md

# 使用示例配置
cp examples/telegraf/telegraf-vsphere.conf config/telegraf/telegraf.conf
vim config/telegraf/telegraf.conf  # 修改你的 vCenter 信息
docker-compose up -d telegraf-vmware
```

---

## 参考文档

- [Telegraf 方案详细文档](./TELEGRAF-VMWARE.md)
- [多实例 vmware-exporter 方案](./VMWARE-MULTI-INSTANCE.md)
- [多 vCenter 监控配置](./MULTI-VMWARE.md)
