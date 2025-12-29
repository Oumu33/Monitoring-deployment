# ===================================================================
# LLDP 拓扑自动发现系统
# ===================================================================

## 系统架构

```
网络设备 (LLDP 启用)
    ↓ SNMP
Topology Discovery 容器 (Python)
    ├→ 采集 LLDP 邻居信息
    ├→ 生成拓扑关系图
    ├→ 计算网络层级 (Core/Aggregation/Access)
    ├→ 自动生成 Prometheus 标签
    └→ 生成 Grafana 可视化数据
        ↓
VictoriaMetrics (指标 + 拓扑标签)
        ↓
Grafana (Node Graph 拓扑可视化)
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

# 构建拓扑发现镜像
docker-compose build topology-discovery

# 启动拓扑发现服务
docker-compose up -d topology-discovery

# 查看日志
docker-compose logs -f topology-discovery
```

### 4. 验证拓扑数据

```bash
# 查看生成的拓扑文件
cat data/topology/topology.json

# 查看 Prometheus 标签
cat data/topology/labels.json

# 查看 Grafana 图数据
cat data/topology/graph.json
```

### 5. 在 Grafana 中查看拓扑

1. 登录 Grafana: http://localhost:3000
2. 导入 Dashboard: `config/grafana/dashboards/network-topology.json`
3. 查看自动生成的网络拓扑图

---

## 自动化特性

### ✅ 自动发现

- **LLDP 邻居采集**: 每 5 分钟自动采集所有设备的 LLDP 信息
- **拓扑关系生成**: 自动构建设备连接关系
- **层级计算**: 根据连接数量自动判断设备层级（核心/汇聚/接入）

### ✅ 自动标签

拓扑发现自动为每个设备生成标签：

```json
{
  "device_name": "Server-01",
  "device_type": "server",
  "device_tier": "access",
  "connected_switch": "Switch-Access-01",
  "connected_port": "Gi0/1",
  "topology_discovered": "true"
}
```

这些标签会自动添加到 Prometheus 指标中，用于：
- **告警关联**: Alertmanager 根据拓扑抑制连锁告警
- **根因分析**: 自动识别故障影响范围
- **可视化**: Grafana 展示设备间关系

### ✅ 自动可视化

- **Node Graph**: Grafana 自动渲染网络拓扑图
- **实时更新**: 拓扑变化自动反映在图中
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
      "vendor": "cisco"
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
  "updated": "2025-12-29T10:00:00"
}
```

### 2. labels.json（Prometheus 标签）

```json
[
  {
    "targets": ["192.168.1.100:9100"],
    "labels": {
      "device_name": "Switch-Core-01",
      "device_tier": "core",
      "connected_switch": "Switch-Access-01",
      "topology_discovered": "true"
    }
  }
]
```

### 3. graph.json（Grafana 可视化）

```json
{
  "nodes": [
    {
      "id": "Switch-Core-01",
      "title": "Switch-Core-01",
      "mainStat": "core",
      "secondaryStat": "switch"
    }
  ],
  "edges": [
    {
      "id": "Switch-Core-01-Switch-Access-01",
      "source": "Switch-Core-01",
      "target": "Switch-Access-01",
      "mainStat": "Gi0/1 <-> Gi0/24"
    }
  ]
}
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

### 设备层级判断逻辑

在 `lldp_discovery.py` 中自动计算：

```python
连接数 >= 10  → 核心交换机 (core)
连接数 >= 3   → 汇聚交换机 (aggregation)
连接数 < 3    → 接入交换机 (access)
```

可根据实际网络调整阈值。

---

## 告警关联示例

有了拓扑标签后，Alertmanager 自动根因分析：

**场景**: 核心交换机故障

```
接收到的告警:
1. SwitchDown (Switch-Core-01)         ← 根因
2. SwitchDown (Switch-Access-01)       ← 下游设备
3. SwitchDown (Switch-Access-02)       ← 下游设备
4. HostDown (Server-01)                ← 连接的服务器
5. HostDown (Server-02)                ← 连接的服务器

Alertmanager 处理:
- 检测到 Switch-Core-01 (tier=core) 故障
- 自动抑制所有 tier=access 的交换机告警
- 自动抑制连接到这些交换机的服务器告警

最终发送 1 封邮件:
"核心交换机 Switch-Core-01 故障，影响 2 个接入交换机和 5 台服务器"
```

---

## Grafana 查询示例

### 查看拓扑关系

```promql
# 所有设备及其连接的交换机
up{topology_discovered="true"}

# 核心交换机
up{device_tier="core"}

# 连接到特定交换机的所有设备
up{connected_switch="Switch-Core-01"}
```

### 影响分析

```promql
# 如果 Switch-Core-01 故障，会影响哪些设备？
count by (connected_switch) (up{connected_switch="Switch-Core-01"})
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
# 3. 权限问题 → 确保 data/topology 目录可写
```

### 未发现任何邻居

```bash
# 1. 检查设备 LLDP 状态
# Cisco:
show lldp neighbors

# Arista:
show lldp neighbors

# 2. 手动测试 SNMP
snmpwalk -v2c -c public 192.168.1.100 1.0.8802.1.1.2.1.4.1.1.9

# 3. 检查 Python 脚本
docker-compose exec topology-discovery python3 /scripts/lldp_discovery.py
```

### Grafana 不显示拓扑图

```bash
# 1. 检查拓扑数据是否生成
ls -la data/topology/

# 2. 检查 Prometheus 是否加载了标签
curl 'http://localhost:8428/api/v1/label/__name__/values' | grep topology

# 3. 重新加载 Grafana Dashboard
```

---

## 高级配置

### 集成 VMware 拓扑

在 `lldp_discovery.py` 中可以扩展，通过 VMware API 获取 VM 和 ESXi 的连接关系。

### 集成 DNS/IPAM

可以自动查询 DNS 将 IP 地址解析为主机名。

### 导出到 Netbox

可以将发现的拓扑数据导出到 Netbox CMDB。

---

## 参考资料

- [LLDP MIB 规范](https://www.ieee802.org/1/pages/802.1AB.html)
- [PySNMP 文档](https://pysnmp.readthedocs.io/)
- [Grafana Node Graph](https://grafana.com/docs/grafana/latest/panels-visualizations/visualizations/node-graph/)

---

完全自动化的拓扑发现 = LLDP + 标签自动化 + 可视化
