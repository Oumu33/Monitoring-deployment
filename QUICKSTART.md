# ===================================================================
# 完整监控和可观测性架构 - 快速启动指南
# ===================================================================

## 启动所有服务

```bash
cd /opt/Monitoring

# 1. 构建拓扑发现镜像
docker-compose build topology-discovery

# 2. 启动所有服务
docker-compose up -d

# 3. 查看服务状态
docker-compose ps

# 4. 查看日志
docker-compose logs -f
```

## 访问地址

- **Grafana**: http://localhost:3000 (admin/admin)
- **VictoriaMetrics**: http://localhost:8428
- **Loki**: http://localhost:3100
- **Alertmanager**: http://localhost:9093

## 配置清单

### 1. 网络设备配置 (拓扑发现)

编辑 `config/topology/devices.yml`:

```yaml
devices:
  - name: Switch-Core-01
    host: 192.168.1.100
    snmp_community: public
```

### 2. 网络设备配置 (Syslog)

在设备上配置:

```
# Cisco
logging host YOUR_MONITORING_IP
lldp run

# Arista
logging host YOUR_MONITORING_IP
lldp run
```

### 3. 查看拓扑

浏览器访问 Grafana，导入 Dashboard:
- Network Topology (`config/grafana/dashboards/network-topology.json`)

## 验证

```bash
# 1. 验证拓扑发现
cat data/topology/topology.json

# 2. 验证日志采集
docker-compose logs loki promtail syslog-ng

# 3. 验证指标采集
curl http://localhost:8428/api/v1/query?query=up
```

## 完整架构

```
✅ Metrics: VictoriaMetrics (指标存储)
✅ Logs: Loki (日志存储)
✅ Topology: LLDP Auto-Discovery (拓扑自动发现)
✅ Alerting: Alertmanager (智能告警 + 根因分析)
✅ Visualization: Grafana (统一可视化)
```

恭喜！你已拥有完整的基础设施可观测性平台！
