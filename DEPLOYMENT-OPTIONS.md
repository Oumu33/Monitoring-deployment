# 按需启动指南

## 📋 启动方案对比

| 方案 | 文件 | 组件 | 适用场景 |
|------|------|------|---------|
| **最小化** | `docker-compose-minimal.yml` | VictoriaMetrics + Grafana | 基础监控，快速开始 |
| **监控采集** | `docker-compose-monitoring.yml` | vmagent + Node Exporter + vmalert + Alertmanager | 添加监控目标，配置告警 |
| **日志聚合** | `docker-compose-logs.yml` | Loki + Promtail + Syslog-NG | 日志收集和分析 |
| **拓扑发现** | `docker-compose-topology.yml` | Topology Discovery + Exporter | 网络拓扑自动发现 |
| **完整版** | `docker-compose.yaml` | 所有组件 | 完整可观测性平台 |
| **多主机** | `docker-compose-multihost.yml` | 分布式部署 | 大规模环境 |

## 🚀 快速开始

### 方案 1：最小化部署（推荐新手）

```bash
# 1. 只启动核心组件（VictoriaMetrics + Grafana）
docker-compose -f docker-compose-minimal.yml up -d

# 2. 访问 Grafana
# http://localhost:3000
# 默认账号：admin / admin
```

**适用场景**：
- 快速测试
- 学习使用
- 小规模环境（< 10 台设备）

### 方案 2：按需添加组件

```bash
# 1. 启动核心组件
docker-compose -f docker-compose-minimal.yml up -d

# 2. 添加监控采集（按需）
docker-compose -f docker-compose-monitoring.yml up -d

# 3. 添加日志聚合（按需）
docker-compose -f docker-compose-logs.yml up -d

# 4. 添加拓扑发现（按需）
docker-compose -f docker-compose-topology.yml up -d
```

**适用场景**：
- 逐步扩展
- 按需部署
- 灵活配置

### 方案 3：完整部署（推荐生产环境）

```bash
# 一键启动所有组件
docker-compose up -d
```

**适用场景**：
- 生产环境
- 完整功能
- 快速部署

## 🔧 多主机部署

### 场景：3 台主机分布式部署

```
Server-1 (192.168.1.10): 核心组件
  - VictoriaMetrics
  - Grafana

Server-2 (192.168.1.20): 监控采集
  - vmagent
  - Node Exporter

Server-3 (192.168.1.30): 日志组件
  - Loki
  - Promtail
```

### 配置指向说明

**关键配置点**：

1. **vmagent 配置**（Server-2）
   ```yaml
   # 指向 Server-1 的 VictoriaMetrics
   remoteWrite.url=http://192.168.1.10:8428/api/v1/write
   ```

2. **Promtail 配置**（Server-3）
   ```yaml
   # 指向 Server-3 的 Loki
   url: http://192.168.1.30:3100/loki/api/v1/push
   ```

3. **Grafana 配置**（Server-1）
   ```yaml
   # VictoriaMetrics 数据源
   url: http://victoriametrics:8428
   
   # Loki 数据源
   url: http://192.168.1.30:3100
   ```

4. **监听地址配置**
   ```yaml
   # VictoriaMetrics（Server-1）
   --httpListenAddr=0.0.0.0:8428  # 监听所有网卡
   
   # Loki（Server-3）
   --httpListenAddr=0.0.0.0:3100  # 监听所有网卡
   ```

### 部署步骤

```bash
# 1. Server-1：启动核心组件
ssh server-1
cd Monitoring-deployment
docker-compose -f docker-compose-minimal.yml up -d

# 2. Server-2：启动监控采集
ssh server-2
cd Monitoring-deployment
# 修改配置文件中的 IP 地址为 192.168.1.10
vim config/vmagent/prometheus.yml
docker-compose -f docker-compose-monitoring.yml up -d

# 3. Server-3：启动日志组件
ssh server-3
cd Monitoring-deployment
docker-compose -f docker-compose-logs.yml up -d

# 4. Server-1：更新 Grafana 数据源配置
ssh server-1
cd Monitoring-deployment
# 添加 Loki 数据源配置
vim config/grafana/provisioning/datasources/loki.yml
docker-compose restart grafana

# 5. 验证连接
# 在 Server-2 上测试
curl http://192.168.1.10:8428/health

# 在 Server-3 上测试
curl http://192.168.1.10:8428/health
```

## 📝 配置文件说明

### 1. 环境变量配置

创建 `.env` 文件：
```bash
# 服务器 IP 地址
VM_SERVER_IP=192.168.1.10
LOKI_SERVER_IP=192.168.1.30
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin
```

在 `docker-compose.yml` 中使用：
```yaml
vmagent:
  command:
    - "--remoteWrite.url=http://${VM_SERVER_IP}:8428/api/v1/write"
```

### 2. 网络配置

确保主机之间网络互通：
```bash
# 测试网络连通性
ping 192.168.1.10
ping 192.168.1.20
ping 192.168.1.30

# 测试端口连通性
telnet 192.168.1.10 8428
telnet 192.168.1.30 3100
```

### 3. 防火墙配置

开放必要的端口：
```bash
# Server-1（核心组件）
- 8428: VictoriaMetrics
- 3000: Grafana

# Server-2（监控采集）
- 8429: vmagent
- 9100: Node Exporter

# Server-3（日志组件）
- 3100: Loki
- 9080: Promtail
```

## 🔍 故障排查

### 常见问题

**问题 1：组件无法连接**

```
# 检查网络连通性
ping <目标主机IP>

# 检查端口是否开放
telnet <目标主机IP> <端口号>

# 检查 Docker 网络配置
docker network inspect monitoring

# 检查容器日志
docker logs <容器名>
```

**问题 2：配置文件路径错误**

```
# 检查配置文件是否存在
ls -la config/vmagent/prometheus.yml

# 检查容器内配置文件
docker exec -it vmagent cat /etc/prometheus/prometheus.yml

# 检查文件权限
chmod 644 config/vmagent/prometheus.yml
```

**问题 3：数据无法写入**

```
# 检查 VictoriaMetrics 是否运行
curl http://192.168.1.10:8428/health

# 检查 vmagent 日志
docker logs vmagent

# 检查网络配置
docker exec -it vmagent ping victoriametrics
```

## 📊 性能优化

### 资源分配

根据实际需求调整资源限制：

```yaml
services:
  victoriametrics:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G

  vmagent:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

## 🎯 最佳实践

1. **从小到大**：先启动最小化版本，逐步添加组件
2. **配置管理**：使用 `.env` 文件管理 IP 地址和密码
3. **网络规划**：提前规划 IP 地址和端口分配
4. **监控监控**：确保监控系统本身的健康状态
5. **备份策略**：定期备份配置文件和数据

## 📚 相关文档

- [完整部署指南](DEPLOYMENT-GUIDE.md)
- [配置文件说明](docs/FILE-SERVICE-DISCOVERY.md)
- [故障排查指南](docs/FAQ.md)