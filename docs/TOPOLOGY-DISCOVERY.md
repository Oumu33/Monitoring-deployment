# ===================================================================
# LLDP 拓扑自动发现系统
# ===================================================================

## 系统架构

```
网络设备 (LLDP 启用)
    ↓ SNMP
Topology Discovery 容器 (Python)
    ├→ 采集 LLDP 邻居信息
    ├→ 生成拓扑关系图 (topology.json)
    ├→ 生成 Prometheus 文件服务发现 (topology-labels.json)
    └→ 自动重载 vmagent 配置
        ↓
Topology Exporter 容器
    ├→ 读取 topology.json
    └→ 暴露 Prometheus 指标 (topology_device_info, topology_connection)
        ↓
vmagent
    ├→ 采集 Topology Exporter 指标
    └→ 从 file_sd 读取拓扑标签
        ↓
VictoriaMetrics (指标 + 拓扑标签)
        ↓
Grafana
    ├→ Node Graph 拓扑可视化
    └→ Device/Connection 详情表格
        ↓
Alertmanager (根据拓扑标签做智能抑制)
```

## 核心组件

### 1. LLDP Discovery (lldp_discovery.py)
- **功能**: 通过 SNMP 采集 LLDP 邻居信息
- **输出**:
  - `/data/topology/topology.json` - 完整拓扑数据
  - `/etc/prometheus/targets/topology-labels.json` - Prometheus file_sd 格式
- **运行**: 每 5 分钟自动运行一次

### 2. Topology Exporter (topology_exporter.py)
- **功能**: 将拓扑数据暴露为 Prometheus 指标
- **端口**: 9700
- **指标**:
  - `topology_device_info{device_name, device_type, device_tier, ...}` - 设备信息
  - `topology_connection{source_device, target_device, source_port, target_port}` - 连接关系
  - `topology_devices_total` - 设备总数
  - `topology_connections_total` - 连接总数
  - `topology_devices_by_tier{tier}` - 按层级统计

### 3. 数据流向

```
LLDP Discovery
    ↓ 生成 topology.json
Topology Exporter
    ↓ 读取 topology.json → 转换为 Prometheus 指标
vmagent
    ↓ 采集指标 → 写入 VictoriaMetrics
VictoriaMetrics
    ↓ 存储指标和标签
Grafana + Alertmanager
    ↓ 查询并使用标签
```

## 快速开始

### 1. 配置设备列表

编辑 `config/topology/devices.yml`:

```yaml
devices:
  - name: Switch-Core-01
    host: 192.168.1.100
    type: switch
    tier: core
    vendor: cisco
    snmp_community: public
```

### 2. 确保设备启用 LLDP

**Cisco**:
```
lldp run
snmp-server community public RO
```

**Arista**:
```
lldp run
snmp-server community public ro
```

**Juniper**:
```
set protocols lldp interface all
set snmp community public authorization read-only
```

### 3. 构建并启动服务

```bash
cd /opt/Monitoring

# 构建拓扑服务镜像
docker-compose build topology-discovery topology-exporter

# 启动所有拓扑服务
docker-compose up -d topology-discovery topology-exporter

# 查看日志
docker-compose logs -f topology-discovery
docker-compose logs -f topology-exporter
```

### 4. 验证拓扑数据

```bash
# 查看生成的拓扑文件
cat data/topology/topology.json

# 查看 Prometheus 标签文件
cat config/vmagent/targets/topology-labels.json

# 访问 Topology Exporter 指标
curl http://localhost:9700/metrics | grep topology
```

### 5. 在 Grafana 中查看拓扑

1. 登录 Grafana: http://localhost:3000
2. 访问 Dashboard: "Network Topology - LLDP Auto-Discovery"
3. 查看:
   - **拓扑图** (Node Graph)
   - **设备统计** (按层级分布)
   - **设备详情表格**
   - **连接详情表格**

---

## 自动化特性

### ✅ 自动发现

- **LLDP 邻居采集**: 每 5 分钟自动采集所有设备的 LLDP 信息
- **拓扑关系生成**: 自动构建设备连接关系图
- **层级计算**: 根据连接数量自动判断设备层级
  - 连接数 ≥ 10 → 核心交换机 (core)
  - 连接数 ≥ 3 → 汇聚交换机 (aggregation)
  - 连接数 < 3 → 接入交换机 (access)

### ✅ 自动标签注入

拓扑发现自动为每个设备生成标签（通过 file_sd）:

```json
{
  "targets": ["192.168.1.100:9100"],
  "labels": {
    "device_name": "Switch-Core-01",
    "device_type": "switch",
    "device_tier": "core",
    "connected_switch": "Switch-Agg-01",
    "connected_switch_port": "Gi0/1",
    "topology_discovered": "true"
  }
}
```

这些标签会自动附加到该设备的所有指标上，用于：
- **告警关联**: Alertmanager 根据拓扑抑制连锁告警
- **根因分析**: 自动识别故障影响范围
- **可视化**: Grafana 展示设备间关系

### ✅ 自动配置重载

每次拓扑发现完成后，自动重载 vmagent 配置：
```bash
curl -X POST http://vmagent:8429/-/reload
```

### ✅ 自动可视化

- **Node Graph**: Grafana 自动渲染网络拓扑图
- **实时更新**: 拓扑变化自动反映在图中（30秒刷新）
- **交互式**: 点击节点查看设备详情

---

## 拓扑数据格式

### 1. topology.json（完整拓扑）

```json
{
  "nodes": {
    "Switch-Core-01": {
      "name": "Switch-Core-01",
      "host": "192.168.1.100",
      "type": "switch",
      "tier": "core",
      "vendor": "cisco",
      "location": "dc1-rack-A01"
    }
  },
  "edges": [
    {
      "source": "Switch-Core-01",
      "target": "Switch-Access-01",
      "source_port": "Gi0/1",
      "target_port": "Gi0/24"
    }
  ],
  "updated": "2025-12-30T10:00:00"
}
```

### 2. topology-labels.json（Prometheus file_sd）

```json
[
  {
    "targets": ["192.168.1.100:9100"],
    "labels": {
      "device_name": "Switch-Core-01",
      "device_tier": "core",
      "connected_switch": "Switch-Access-01",
      "connected_switch_port": "Gi0/1",
      "topology_discovered": "true"
    }
  }
]
```

### 3. Prometheus 指标

```promql
# 设备信息
topology_device_info{device_name="Switch-Core-01",device_type="switch",device_tier="core"} 1

# 连接关系
topology_connection{source_device="Switch-Core-01",target_device="Switch-Access-01"} 1

# 统计信息
topology_devices_total 10
topology_connections_total 15
topology_devices_by_tier{tier="core"} 2
```

---

## 配置说明

### 发现间隔

编辑 `docker-compose.yaml`:

```yaml
topology-discovery:
  environment:
    - DISCOVERY_INTERVAL=300  # 秒（默认 5 分钟）
```

### Exporter 端口

```yaml
topology-exporter:
  environment:
    - EXPORTER_PORT=9700      # 默认 9700
```

### 设备层级判断逻辑

在 `lldp_discovery.py` 中自动计算：

```python
连接数 >= 10  → 核心交换机 (core)
连接数 >= 3   → 汇聚交换机 (aggregation)
连接数 < 3    → 接入交换机 (access)
```

可根据实际网络调整阈值（scripts/topology/lldp_discovery.py:225-230）。

---

## 告警关联示例

有了拓扑标签后，Alertmanager 自动根因分析：

**场景**: 核心交换机故障

```
接收到的告警:
1. SwitchDown (Switch-Core-01, tier=core)         ← 根因
2. SwitchDown (Switch-Access-01, tier=access)     ← 下游设备
3. SwitchDown (Switch-Access-02, tier=access)     ← 下游设备
4. HostDown (Server-01, connected_switch=Access-01) ← 连接的服务器
5. HostDown (Server-02, connected_switch=Access-02) ← 连接的服务器

Alertmanager 处理:
- 检测到 Switch-Core-01 (tier=core) 故障
- 自动抑制所有 tier=access 的交换机告警（规则 12）
- 自动抑制连接到这些交换机的服务器告警（规则 15）

最终发送 1 封邮件:
"核心交换机 Switch-Core-01 故障，影响 2 个接入交换机和 2 台服务器"
```

相关抑制规则：config/alertmanager/alertmanager.yml:337-415

---

## Grafana 查询示例

### 查看拓扑关系

```promql
# 所有设备信息
topology_device_info

# 核心交换机
topology_device_info{device_tier="core"}

# 所有连接关系
topology_connection

# 特定设备的连接
topology_connection{source_device="Switch-Core-01"}
```

### 影响分析

```promql
# 查看拓扑统计
topology_devices_total
topology_connections_total

# 按层级统计设备
sum by (tier) (topology_devices_by_tier)
```

### 关联设备指标

```promql
# 核心交换机的 CPU 使用率
node_cpu_usage{device_tier="core"}

# 连接到特定交换机的所有设备
up{connected_switch="Switch-Core-01"}
```

---

## 故障排查

### 拓扑发现服务无法启动

```bash
# 查看日志
docker-compose logs topology-discovery

# 常见问题:
# 1. SNMP 连接失败 → 检查 devices.yml 中的 IP 和 community
# 2. LLDP 未启用 → 在设备上启用 LLDP
# 3. 权限问题 → 确保 data/topology 和 config/vmagent/targets 目录可写
```

### 未发现任何邻居

```bash
# 1. 检查设备 LLDP 状态
# Cisco:
show lldp neighbors

# 2. 手动测试 SNMP
snmpwalk -v2c -c public 192.168.1.100 1.0.8802.1.1.2.1.4.1.1.9

# 3. 手动运行脚本
docker-compose exec topology-discovery python3 /scripts/lldp_discovery.py
```

### Topology Exporter 不返回数据

```bash
# 1. 检查 exporter 是否运行
docker-compose ps topology-exporter

# 2. 检查日志
docker-compose logs topology-exporter

# 3. 手动访问指标
curl http://localhost:9700/metrics

# 4. 检查 topology.json 是否存在
ls -la data/topology/topology.json
```

### Grafana 不显示拓扑图

```bash
# 1. 检查 VictoriaMetrics 中是否有指标
curl 'http://localhost:8428/api/v1/query?query=topology_device_info'

# 2. 检查 vmagent 是否采集了 topology-exporter
curl 'http://localhost:8429/targets' | grep topology

# 3. 重新加载 Grafana Dashboard
```

### 标签未注入到设备指标

```bash
# 1. 检查 file_sd 文件是否生成
cat config/vmagent/targets/topology-labels.json

# 2. 检查 vmagent 配置
grep -A 5 "topology-labels" config/vmagent/prometheus.yml

# 3. 手动重载 vmagent
curl -X POST http://localhost:8429/-/reload

# 4. 检查设备指标是否有标签
curl 'http://localhost:8428/api/v1/query?query=up{topology_discovered="true"}'
```

---

## 高级配置

### 集成 VMware 拓扑

可以扩展 `lldp_discovery.py`，通过 VMware API 获取 VM 和 ESXi 的连接关系，
并合并到拓扑数据中。

### 集成 DNS/IPAM

可以自动查询 DNS 将 IP 地址解析为主机名，丰富拓扑数据。

### 导出到 Netbox

可以将发现的拓扑数据导出到 Netbox CMDB，实现双向同步。

### 自定义 Exporter 指标

编辑 `scripts/topology/topology_exporter.py`，可以添加更多自定义指标：
- 设备在线状态
- 连接健康度
- 历史拓扑变化

---

## 性能优化

### 资源占用

- **Topology Discovery**: CPU 0.1 核，内存 256 MB（运行时）
- **Topology Exporter**: CPU 0.05 核，内存 128 MB

### 大规模环境

对于超过 500 个设备的环境：

1. **增加发现间隔**:
   ```yaml
   DISCOVERY_INTERVAL=600  # 10 分钟
   ```

2. **并发采集**: 修改 `lldp_discovery.py` 使用多线程并发采集 SNMP

3. **分片发现**: 将设备分组，部署多个 topology-discovery 实例

---

## 参考资料

- [LLDP MIB 规范](https://www.ieee802.org/1/pages/802.1AB.html)
- [PySNMP 文档](https://pysnmp.readthedocs.io/)
- [Grafana Node Graph](https://grafana.com/docs/grafana/latest/panels-visualizations/visualizations/node-graph/)
- [Prometheus File Service Discovery](https://prometheus.io/docs/prometheus/latest/configuration/configuration/#file_sd_config)

---

**完全自动化的拓扑发现 = LLDP + Exporter + 标签注入 + 可视化 + 智能告警**
