# VictoriaMetrics 监控系统性能调优指南

## 概述

本指南提供针对不同规模监控环境的性能调优配置，帮助优化资源使用、提升查询性能、降低存储成本。

## 场景分类

### 小型环境 (< 50 台主机，< 100 万时间序列)
### 中型环境 (50-200 台主机，100 万 - 500 万时间序列)
### 大型环境 (> 200 台主机，> 500 万时间序列)

---

## 一、VictoriaMetrics 性能调优

### 小型环境配置

```yaml
victoriametrics:
  image: victoriametrics/victoria-metrics:latest
  container_name: victoriametrics
  command:
    - "--storageDataPath=/storage"
    - "--httpListenAddr=:8428"
    - "--retentionPeriod=12"          # 12个月保留期
    - "--memory.allowedPercent=60"    # 限制内存使用60%
    - "--search.maxQueryDuration=30s" # 最大查询时间30秒
    - "--search.maxConcurrentRequests=8" # 最大并发查询数
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 4G
      reservations:
        cpus: '1'
        memory: 2G
```

### 中型环境配置

```yaml
victoriametrics:
  image: victoriametrics/victoria-metrics:latest
  container_name: victoriametrics
  command:
    - "--storageDataPath=/storage"
    - "--httpListenAddr=:8428"
    - "--retentionPeriod=6"           # 降低保留期到6个月
    - "--memory.allowedPercent=70"
    - "--search.maxQueryDuration=60s"
    - "--search.maxConcurrentRequests=16"
    - "--dedup.minScrapeInterval=30s" # 去重优化
    - "--search.maxSamplesPerQuery=1e8" # 单次查询最大样本数
    - "--search.maxSeries=1e6"        # 最大序列数
  deploy:
    resources:
      limits:
        cpus: '4'
        memory: 8G
      reservations:
        cpus: '2'
        memory: 4G
  volumes:
    - vmdata:/storage
    - /mnt/fast-ssd:/storage  # 使用SSD存储
```

### 大型环境配置

```yaml
victoriametrics:
  image: victoriametrics/victoria-metrics:latest
  container_name: victoriametrics
  command:
    - "--storageDataPath=/storage"
    - "--httpListenAddr=:8428"
    - "--retentionPeriod=3"           # 3个月保留期
    - "--memory.allowedPercent=80"
    - "--search.maxQueryDuration=120s"
    - "--search.maxConcurrentRequests=32"
    - "--dedup.minScrapeInterval=1m"
    - "--search.maxSamplesPerQuery=2e8"
    - "--search.maxSeries=5e6"
    - "--cacheExpireDuration=30m"     # 缓存过期时间
    - "--maxInsertRequestSize=32MB"   # 增大批量写入大小
    - "--search.maxPointsPerTimeseries=30000" # 每个序列最大点数
  deploy:
    resources:
      limits:
        cpus: '8'
        memory: 16G
      reservations:
        cpus: '4'
        memory: 8G
  volumes:
    - /mnt/nvme-ssd:/storage  # 使用NVMe SSD
```

### VictoriaMetrics 参数详解

| 参数 | 说明 | 推荐值 |
|------|------|--------|
| `--retentionPeriod` | 数据保留时间 | 小型:12月, 中型:6月, 大型:3月 |
| `--memory.allowedPercent` | 允许使用的内存百分比 | 60-80% |
| `--search.maxQueryDuration` | 单次查询最大时间 | 30s-120s |
| `--search.maxConcurrentRequests` | 最大并发查询数 | 8-32 |
| `--dedup.minScrapeInterval` | 去重时间间隔 | 等于或略大于采集间隔 |
| `--search.maxSamplesPerQuery` | 单次查询最大样本数 | 1e8-2e8 |
| `--cacheExpireDuration` | 缓存过期时间 | 30m |

---

## 二、vmagent 性能调优

### 小型环境配置

```yaml
vmagent:
  image: victoriametrics/vmagent:latest
  container_name: vmagent
  command:
    - "--promscrape.config=/etc/prometheus/prometheus.yml"
    - "--remoteWrite.url=http://victoriametrics:8428/api/v1/write"
    - "--remoteWrite.maxBlockSize=8MB"     # 批量写入块大小
    - "--remoteWrite.maxRowsPerBlock=10000" # 每块最大行数
    - "--remoteWrite.flushInterval=5s"      # 刷新间隔
    - "--memory.allowedPercent=60"
  deploy:
    resources:
      limits:
        cpus: '1'
        memory: 1G
      reservations:
        cpus: '0.5'
        memory: 512M
```

### 中型环境配置

```yaml
vmagent:
  image: victoriametrics/vmagent:latest
  container_name: vmagent
  command:
    - "--promscrape.config=/etc/prometheus/prometheus.yml"
    - "--remoteWrite.url=http://victoriametrics:8428/api/v1/write"
    - "--remoteWrite.maxBlockSize=16MB"
    - "--remoteWrite.maxRowsPerBlock=20000"
    - "--remoteWrite.flushInterval=10s"
    - "--remoteWrite.queues=4"              # 并发写入队列数
    - "--memory.allowedPercent=70"
    - "--promscrape.maxScrapeSize=32MB"     # 单次抓取最大大小
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 2G
      reservations:
        cpus: '1'
        memory: 1G
```

### 大型环境配置

```yaml
vmagent:
  image: victoriametrics/vmagent:latest
  container_name: vmagent
  command:
    - "--promscrape.config=/etc/prometheus/prometheus.yml"
    - "--remoteWrite.url=http://victoriametrics:8428/api/v1/write"
    - "--remoteWrite.maxBlockSize=32MB"
    - "--remoteWrite.maxRowsPerBlock=50000"
    - "--remoteWrite.flushInterval=15s"
    - "--remoteWrite.queues=8"
    - "--remoteWrite.maxDiskUsagePerURL=10GB" # 磁盘缓冲区大小
    - "--memory.allowedPercent=80"
    - "--promscrape.maxScrapeSize=64MB"
    - "--promscrape.streamParse=true"        # 流式解析
  deploy:
    resources:
      limits:
        cpus: '4'
        memory: 4G
      reservations:
        cpus: '2'
        memory: 2G
```

### vmagent 采集间隔优化

```yaml
scrape_configs:
  # 关键服务 - 高频采集
  - job_name: 'critical-services'
    scrape_interval: 15s
    scrape_timeout: 10s

  # 普通服务 - 标准采集
  - job_name: 'normal-services'
    scrape_interval: 30s
    scrape_timeout: 25s

  # 低优先级服务 - 低频采集
  - job_name: 'low-priority'
    scrape_interval: 60s
    scrape_timeout: 50s

  # VMware 监控 - 最低频采集
  - job_name: 'vmware'
    scrape_interval: 120s
    scrape_timeout: 100s

  # SNMP 设备 - 低频采集
  - job_name: 'snmp'
    scrape_interval: 300s  # 5分钟
    scrape_timeout: 240s
```

---

## 三、Grafana 性能调优

### 基础配置

```yaml
grafana:
  image: grafana/grafana:latest
  environment:
    # 性能相关
    - GF_DATABASE_MAX_OPEN_CONNS=100
    - GF_DATABASE_MAX_IDLE_CONNS=10
    - GF_DATAPROXY_TIMEOUT=60
    - GF_DATAPROXY_KEEP_ALIVE_SECONDS=60
    - GF_DATAPROXY_MAX_IDLE_CONNECTIONS=100
    # 缓存配置
    - GF_REMOTE_CACHE_TYPE=redis  # 可选
    - GF_RENDERING_CONCURRENT_RENDER_LIMIT=5
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 2G
      reservations:
        cpus: '1'
        memory: 1G
```

### 仪表板查询优化

**最佳实践:**

1. **使用变量减少查询数量**
```
变量: $interval = auto
查询: rate(metric[$interval])
```

2. **限制时间范围**
```
# 避免查询过长时间范围
默认时间范围: 最近6小时
最大时间范围: 7天
```

3. **使用下采样**
```promql
# 长时间查询使用降采样
rate(metric[5m])[1h:1m]  # 1小时降采样为1分钟间隔
```

4. **优化聚合查询**
```promql
# 不推荐 - 查询所有实例再聚合
avg(node_cpu_seconds_total)

# 推荐 - 按标签聚合
avg by(instance)(node_cpu_seconds_total)
```

---

## 四、Alertmanager 性能调优

```yaml
alertmanager:
  image: prom/alertmanager:latest
  command:
    - "--config.file=/etc/alertmanager/alertmanager.yml"
    - "--storage.path=/alertmanager"
    - "--data.retention=120h"        # 保留5天
    - "--alerts.gc-interval=30m"     # 清理间隔
    - "--cluster.settle-timeout=30s" # 集群稳定超时
  deploy:
    resources:
      limits:
        cpus: '1'
        memory: 512M
      reservations:
        cpus: '0.5'
        memory: 256M
```

---

## 五、系统级优化

### 1. 磁盘 I/O 优化

**使用 SSD/NVMe:**
```yaml
volumes:
  vmdata:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /mnt/nvme-ssd/vmdata
```

**文件系统优化:**
```bash
# XFS 推荐配置
mkfs.xfs -f -i size=512 -n size=8192 /dev/nvme0n1

# 挂载选项
mount -o noatime,nodiratime,nobarrier /dev/nvme0n1 /mnt/vmdata
```

**添加到 /etc/fstab:**
```
/dev/nvme0n1  /mnt/vmdata  xfs  noatime,nodiratime,nobarrier  0  0
```

### 2. 网络优化

**TCP 参数调优:**
```bash
# 添加到 /etc/sysctl.conf
net.core.somaxconn = 32768
net.core.netdev_max_backlog = 16384
net.ipv4.tcp_max_syn_backlog = 8192
net.ipv4.tcp_slow_start_after_idle = 0
net.ipv4.tcp_tw_reuse = 1

# 应用配置
sysctl -p
```

### 3. 内存优化

**调整内存参数:**
```bash
# vm.swappiness - 降低swap使用
vm.swappiness = 10

# vm.dirty_ratio - 脏页刷新比例
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5
```

### 4. 文件描述符限制

```bash
# 添加到 /etc/security/limits.conf
* soft nofile 65536
* hard nofile 65536
* soft nproc 32768
* hard nproc 32768

# 验证
ulimit -n
```

### 5. Docker 容器优化

**日志限制:**
```yaml
services:
  victoriametrics:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

**共享内存:**
```yaml
services:
  victoriametrics:
    shm_size: '2gb'  # 增加共享内存
```

---

## 六、监控自身性能

### 添加性能监控仪表板

导入 Grafana 仪表板:
- **VictoriaMetrics**: ID `11176`
- **vmagent**: ID `12683`
- **Grafana**: ID `3590`

### 关键性能指标

**VictoriaMetrics:**
```promql
# 写入速率
rate(vm_rows_inserted_total[5m])

# 查询性能
histogram_quantile(0.99, rate(vm_request_duration_seconds_bucket[5m]))

# 内存使用
process_resident_memory_bytes

# 磁盘使用
vm_data_size_bytes
```

**vmagent:**
```promql
# 采集成功率
sum(up) / count(up) * 100

# 丢弃样本数
rate(vmagent_remotewrite_dropped_rows_total[5m])

# 队列长度
vmagent_remotewrite_pending_data_bytes
```

---

## 七、常见性能问题排查

### 问题 1: 查询缓慢

**诊断:**
```bash
# 查看慢查询
curl http://localhost:8428/api/v1/status/top_queries

# 查看活动查询
curl http://localhost:8428/api/v1/status/active_queries
```

**解决方案:**
1. 限制查询时间范围
2. 增加 `search.maxConcurrentRequests`
3. 优化 PromQL 查询
4. 使用下采样

### 问题 2: 内存占用高

**诊断:**
```bash
# 查看内存统计
curl http://localhost:8428/metrics | grep process_resident_memory

# 查看缓存使用
curl http://localhost:8428/metrics | grep vm_cache
```

**解决方案:**
1. 降低 `memory.allowedPercent`
2. 减少保留时间 `retentionPeriod`
3. 限制并发查询数
4. 清理不需要的时间序列

### 问题 3: 磁盘空间增长快

**诊断:**
```bash
# 查看数据大小
docker exec victoriametrics du -sh /storage

# 查看时间序列数量
curl http://localhost:8428/api/v1/status/tsdb
```

**解决方案:**
1. 减少保留时间
2. 降低采集频率
3. 删除不需要的指标
4. 启用去重 `dedup.minScrapeInterval`

### 问题 4: vmagent 丢弃数据

**诊断:**
```bash
# 查看丢弃统计
curl http://localhost:8429/metrics | grep dropped

# 查看队列状态
curl http://localhost:8429/metrics | grep pending
```

**解决方案:**
1. 增大 `remoteWrite.maxBlockSize`
2. 增加 `remoteWrite.queues`
3. 增大 `remoteWrite.maxDiskUsagePerURL`
4. 优化 VictoriaMetrics 写入性能

---

## 八、性能基准测试

### 小型环境基准

- **主机数量**: 50台
- **时间序列**: 100万
- **采集间隔**: 30s
- **每秒写入**: 3.3万样本/s
- **存储需求**: ~50GB/月
- **CPU**: 2核
- **内存**: 4GB

### 中型环境基准

- **主机数量**: 200台
- **时间序列**: 500万
- **采集间隔**: 30s
- **每秒写入**: 16.6万样本/s
- **存储需求**: ~250GB/月
- **CPU**: 4核
- **内存**: 8GB

### 大型环境基准

- **主机数量**: 1000台
- **时间序列**: 2000万
- **采集间隔**: 30s
- **每秒写入**: 66.6万样本/s
- **存储需求**: ~1TB/月
- **CPU**: 8核
- **内存**: 16GB

---

## 九、成本优化建议

### 1. 分层存储策略

```yaml
# 热数据 (最近7天) - SSD
# 温数据 (7-30天) - HDD
# 冷数据 (>30天) - 对象存储/归档
```

### 2. 降采样策略

```yaml
# 原始数据保留7天
# 5分钟聚合保留30天
# 1小时聚合保留1年
```

### 3. 选择性采集

```yaml
# 只采集必要的指标
metric_relabel_configs:
  - source_labels: [__name__]
    regex: 'node_(cpu|memory|disk|network).*'
    action: keep
```

### 4. 资源限制

```yaml
# 为所有服务设置资源限制
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 2G
```

---

## 十、完整优化配置示例

参考文件:
- `examples/performance/docker-compose-optimized.yml`
- `examples/performance/prometheus-optimized.yml`
- `examples/performance/sysctl-optimization.conf`

使用优化配置:
```bash
# 应用系统优化
sudo cp examples/performance/sysctl-optimization.conf /etc/sysctl.d/99-monitoring.conf
sudo sysctl -p /etc/sysctl.d/99-monitoring.conf

# 使用优化的 docker-compose
cp examples/performance/docker-compose-optimized.yml docker-compose.yml

# 重启服务
make restart
```
