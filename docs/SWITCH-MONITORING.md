# 交换机监控配置指南

## 交换机告警规则说明

我已经为你创建了专门的交换机告警规则文件 `switch-alerts.yml`，包含 30+ 条交换机专用告警规则。

## 告警规则分类

### 1. 设备健康告警
- **SwitchDown**: 交换机无法访问
- **SwitchHighCPU**: CPU 使用率过高 (>80%)
- **SwitchCriticalCPU**: CPU 使用率严重过高 (>95%)
- **SwitchHighMemory**: 内存使用率过高 (>85%)
- **SwitchRebooted**: 交换机最近重启

### 2. 硬件告警
- **SwitchHighTemperature**: 温度过高 (>60°C)
- **SwitchCriticalTemperature**: 温度严重过高 (>70°C)
- **SwitchFanFailure**: 风扇故障
- **SwitchPowerSupplyFailure**: 电源故障

### 3. 端口状态告警
- **SwitchTrunkPortDown**: Trunk 端口下线
- **SwitchUplinkPortDown**: 上联端口下线
- **SwitchPortFlapping**: 端口状态频繁变化（抖动）
- **SwitchVLANInterfaceDown**: VLAN 接口下线

### 4. 端口性能告警
- **SwitchPortInputErrors**: 端口输入错误率过高
- **SwitchPortOutputErrors**: 端口输出错误率过高
- **SwitchPortInputDiscards**: 端口输入丢包率过高
- **SwitchPortOutputDiscards**: 端口输出丢包率过高
- **SwitchPortCRCErrors**: CRC 错误率过高
- **SwitchPortCollisions**: 端口冲突检测
- **SwitchPortHighInboundTraffic**: 入向带宽利用率过高 (>85%)
- **SwitchPortHighOutboundTraffic**: 出向带宽利用率过高 (>85%)

### 5. 网络协议告警
- **SwitchFrequentSTPChanges**: STP 拓扑变化频繁
- **SwitchMACTableNearFull**: MAC 地址表接近满

### 6. 安全告警
- **SwitchPortSecurityViolation**: 端口安全违规
- **SwitchConfigurationChanged**: 配置已变更但未保存

### 7. 高级功能告警
- **SwitchPOEPortOverload**: PoE 端口功率过载
- **SwitchStackMemberDown**: 堆叠成员离线

## 需要的 SNMP MIB 支持

不同的告警规则需要不同的 MIB 支持。以下是推荐配置：

### 基础监控（所有交换机必须）
- **IF-MIB**: 接口状态和流量
  - ifOperStatus (端口状态)
  - ifInErrors, ifOutErrors (错误统计)
  - ifInDiscards, ifOutDiscards (丢包统计)
  - ifHCInOctets, ifHCOutOctets (64位流量计数器)
  - ifHighSpeed (接口速率)

- **HOST-RESOURCES-MIB**: CPU 和内存
  - hrProcessorLoad (CPU 使用率)
  - hrStorageUsed, hrStorageSize (内存使用)

- **SNMPv2-MIB**: 系统信息
  - sysUpTime (运行时间)
  - sysDescr (系统描述)

### Cisco 交换机专用
- **CISCO-ENVMON-MIB**: 环境监控
  - ciscoEnvMonTemperatureStatusValue (温度)
  - ciscoEnvMonFanState (风扇状态)
  - ciscoEnvMonSupplyState (电源状态)

- **CISCO-CONFIG-MAN-MIB**: 配置管理
  - ccmHistoryRunningLastChanged (配置变更时间)
  - ccmHistoryRunningLastSaved (配置保存时间)

- **CISCO-STACK-MIB**: 堆叠管理
  - cswSwitchState (堆叠成员状态)

- **CISCO-PORT-SECURITY-MIB**: 端口安全
  - cpsIfPortSecurityViolations (安全违规计数)

### 通用标准 MIB
- **BRIDGE-MIB**: 交换机桥接功能
  - dot1dStpTopChanges (STP 拓扑变化)
  - dot1dTpLearnedEntryDiscards (MAC 表丢弃)

- **EtherLike-MIB**: 以太网统计
  - dot3StatsFCSErrors (CRC/FCS 错误)

- **POWER-ETHERNET-MIB**: PoE 功能
  - pethPsePortPower (端口功率)
  - pethPsePortPowerLimit (功率限制)

## SNMP Exporter 配置

### 方法 1: 使用官方预生成配置（推荐）

官方配置文件已包含大部分常见交换机的 MIB 定义：

```bash
cd config/snmp-exporter
wget https://github.com/prometheus/snmp_exporter/releases/latest/download/snmp.yml
```

### 方法 2: 生成自定义配置

如果需要监控特定的 OID 或自定义配置，可以使用 generator 工具：

1. 创建 `generator.yml` 配置文件:

```yaml
modules:
  # Cisco 交换机完整监控
  cisco_switch:
    walk:
      - 1.3.6.1.2.1.1              # SNMPv2-MIB::system
      - 1.3.6.1.2.1.2              # IF-MIB::interfaces
      - 1.3.6.1.2.1.31             # IF-MIB::ifXTable
      - 1.3.6.1.4.1.9.9.13         # CISCO-ENVMON-MIB
      - 1.3.6.1.4.1.9.9.109        # CISCO-PORT-SECURITY-MIB
      - 1.3.6.1.4.1.9.9.500        # CISCO-STACK-MIB
      - 1.3.6.1.2.1.25.3           # HOST-RESOURCES-MIB::hrDevice
      - 1.3.6.1.2.1.17             # BRIDGE-MIB
      - 1.3.6.1.2.1.105            # POWER-ETHERNET-MIB
    lookups:
      - source_indexes: [ifIndex]
        lookup: ifAlias
      - source_indexes: [ifIndex]
        lookup: ifDescr
    overrides:
      ifAlias:
        ignore: true
      ifDescr:
        ignore: true
      ifType:
        type: EnumAsInfo
```

2. 使用 generator 生成配置:

```bash
docker run --rm -v "${PWD}:/opt" prom/snmp-generator generate
```

## vmagent 采集配置

### 基础配置

在 `config/vmagent/prometheus.yml` 中配置交换机采集：

```yaml
- job_name: 'cisco-switches'
  static_configs:
    - targets:
      - 192.168.1.100  # 核心交换机
      - 192.168.1.101  # 汇聚交换机
      - 192.168.1.102  # 接入交换机
  metrics_path: /snmp
  params:
    module: [cisco_ios]  # 或 if_mib
  relabel_configs:
    - source_labels: [__address__]
      target_label: __param_target
    - source_labels: [__param_target]
      target_label: instance
    - target_label: __address__
      replacement: snmp-exporter:9116
  scrape_interval: 60s
  scrape_timeout: 50s
```

### 区分不同类型的交换机

```yaml
# 核心交换机
- job_name: 'core-switches'
  static_configs:
    - targets: ['192.168.1.100', '192.168.1.101']
      labels:
        switch_role: 'core'
        location: 'datacenter'
  metrics_path: /snmp
  params:
    module: [cisco_ios]
  relabel_configs:
    - source_labels: [__address__]
      target_label: __param_target
    - source_labels: [__param_target]
      target_label: instance
    - target_label: __address__
      replacement: snmp-exporter:9116

# 接入交换机
- job_name: 'access-switches'
  static_configs:
    - targets: ['192.168.1.110', '192.168.1.111', '192.168.1.112']
      labels:
        switch_role: 'access'
        location: 'office'
  metrics_path: /snmp
  params:
    module: [if_mib]  # 接入交换机可能只需要基础监控
  relabel_configs:
    - source_labels: [__address__]
      target_label: __param_target
    - source_labels: [__param_target]
      target_label: instance
    - target_label: __address__
      replacement: snmp-exporter:9116
```

### 端口别名标注

为了让告警更易读，建议在交换机上配置端口描述：

```cisco
interface GigabitEthernet1/0/1
 description Uplink-to-Core-SW1
```

这样告警中的 `ifAlias` 标签会显示 "Uplink-to-Core-SW1"，便于识别。

## 交换机 SNMP 配置

### Cisco IOS/IOS-XE 配置示例

```cisco
! 配置 SNMP community (v2c)
snmp-server community public RO

! 配置 SNMP v3 (更安全，推荐)
snmp-server group monitoring-group v3 priv
snmp-server user monitoring monitoring-group v3 auth sha AuthPass123 priv aes 128 PrivPass123

! 启用 SNMP traps (可选)
snmp-server enable traps cpu threshold
snmp-server enable traps envmon
snmp-server enable traps port-security

! 限制 SNMP 访问源
access-list 99 permit 192.168.1.0 0.0.0.255
snmp-server community public RO 99
```

### 华为交换机配置示例

```huawei
# SNMP v2c
snmp-agent community read public

# SNMP v3
snmp-agent group v3 monitoring privacy
snmp-agent usm-user v3 monitoring monitoring simple-auth-password AuthPass123 private-auth-password PrivPass123

# ACL 限制
acl number 2000
 rule 5 permit source 192.168.1.0 0.0.0.255
snmp-agent community read public acl 2000
```

### H3C 交换机配置示例

```h3c
# SNMP v2c
snmp-agent community read public

# SNMP v3
snmp-agent group v3 monitoring privacy
snmp-agent usm-user v3 monitoring monitoring authentication-mode sha AuthPass123 privacy-mode aes128 PrivPass123
```

## 测试 SNMP 连接

### 测试基本连接

```bash
# SNMP v2c
snmpwalk -v2c -c public 192.168.1.100 sysDescr

# SNMP v3
snmpwalk -v3 -l authPriv -u monitoring -a SHA -A AuthPass123 -x AES -X PrivPass123 192.168.1.100 sysDescr
```

### 测试关键 OID

```bash
# 测试 CPU
snmpwalk -v2c -c public 192.168.1.100 1.3.6.1.2.1.25.3.3.1.2

# 测试温度 (Cisco)
snmpwalk -v2c -c public 192.168.1.100 1.3.6.1.4.1.9.9.13.1.3

# 测试接口状态
snmpwalk -v2c -c public 192.168.1.100 ifOperStatus
```

### 使用 SNMP Exporter 测试

```bash
# 测试采集
curl 'http://localhost:9116/snmp?target=192.168.1.100&module=cisco_ios'
```

## 常见厂商 SNMP 模块选择

| 厂商 | 推荐模块 | 说明 |
|------|----------|------|
| Cisco Catalyst | `cisco_ios` | 适用于大部分 Catalyst 交换机 |
| Cisco Nexus | `cisco_nxos` | Nexus 数据中心交换机 |
| 华为 | `if_mib` + 自定义 | 使用通用 IF-MIB 或生成自定义配置 |
| H3C | `if_mib` + 自定义 | 类似华为 |
| Juniper | `juniper_ex` | EX 系列交换机 |
| Aruba | `aruba_switch` | Aruba 交换机 |
| Dell/Force10 | `if_mib` | 使用通用模块 |
| HP/Aruba | `aruba_switch` 或 `if_mib` | 根据型号选择 |

## Grafana 仪表板推荐

导入以下仪表板 ID 到 Grafana:

- **11169**: SNMP Stats - 通用 SNMP 设备监控
- **11202**: Cisco SNMP - Cisco 交换机专用
- **14431**: Network Interfaces via SNMP - 接口详细监控

## 故障排查

### 1. 无法采集数据

```bash
# 检查 SNMP 连通性
snmpwalk -v2c -c public <交换机IP> sysDescr

# 检查 SNMP Exporter 日志
docker logs snmp-exporter

# 测试 SNMP Exporter
curl 'http://localhost:9116/snmp?target=<交换机IP>&module=if_mib'
```

### 2. 某些指标缺失

- 检查交换机型号是否支持该 MIB
- 验证 SNMP community 或用户权限
- 查看交换机 SNMP 配置是否启用相关 trap

### 3. CPU/内存指标不准确

不同厂商的 CPU/内存 OID 可能不同:
- Cisco IOS: `cpmCPUTotal5minRev`
- 通用: `hrProcessorLoad`
- 可能需要自定义配置

### 4. 温度/风扇/电源指标缺失

这些是厂商特定的 MIB,需要:
- 使用厂商专用的 SNMP 模块
- 或者使用 generator 工具生成包含厂商 MIB 的配置

## 性能优化建议

1. **采集间隔**: 交换机监控建议使用 60s 采集间隔
2. **超时设置**: 设置 scrape_timeout 为 50s (略小于 scrape_interval)
3. **并发控制**: 如果交换机较多,可以分批采集
4. **选择性监控**: 核心交换机监控所有指标,接入交换机只监控基础指标

## 安全建议

1. 使用 SNMP v3 替代 v2c
2. 配置 ACL 限制 SNMP 访问源
3. 使用只读 community/用户
4. 定期更换 SNMP 密码
5. 禁用不必要的 SNMP trap

## 参考资源

- [Cisco SNMP OID Reference](https://www.cisco.com/c/en/us/support/docs/ip/simple-network-management-protocol-snmp/13713-snmp-oid.html)
- [SNMP Exporter Generator](https://github.com/prometheus/snmp_exporter/tree/main/generator)
- [Prometheus SNMP Best Practices](https://prometheus.io/docs/guides/snmp-exporter/)
