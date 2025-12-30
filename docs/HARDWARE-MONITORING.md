# 服务器硬件监控配置指南

## 目录
- [概述](#概述)
- [架构设计](#架构设计)
- [Redfish 监控配置](#redfish-监控配置)
- [IPMI 监控配置](#ipmi-监控配置)
- [监控指标说明](#监控指标说明)
- [告警配置](#告警配置)
- [故障排查](#故障排查)

---

## 概述

本监控系统采用 **Redfish + IPMI 双轨制**策略监控物理服务器硬件：

- **Redfish Exporter**: 统一监控支持 Redfish API 的新服务器（推荐）
- **IPMI Exporter**: 兜底监控不支持 Redfish 的老服务器

### 监控能力

✅ **温度监控**: CPU 温度、主板温度、内存温度
✅ **风扇监控**: 风扇转速、风扇状态
✅ **电源监控**: 电源状态、冗余电源健康
✅ **RAID 监控**: 控制器状态、磁盘阵列健康
✅ **硬盘监控**: SMART 数据、硬盘故障预测
✅ **内存监控**: 内存错误、ECC 校验
✅ **网卡监控**: 网卡状态、链路状态
✅ **固件监控**: BIOS 版本、固件版本
✅ **事件日志**: 硬件告警事件

---

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                    硬件监控架构                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  新服务器 (Redfish API)                                      │
│   ├─ Dell iDRAC 9+ ────┐                                    │
│   ├─ HPE iLO 4/5/6 ────┤                                    │
│   ├─ Supermicro ───────┼──> Redfish Exporter ──┐           │
│   ├─ Lenovo XClarity ──┘                        │           │
│                                                  v           │
│  老服务器 (IPMI)                            vmagent         │
│   ├─ Dell R710 ────────┐                        │           │
│   ├─ HP DL380 G6 ──────┼──> IPMI Exporter ──────┘          │
│   └─ 其他老服务器 ─────┘                        │           │
│                                                  v           │
│                                         VictoriaMetrics      │
│                                                  │           │
│                                                  v           │
│                                              vmalert         │
│                                                  │           │
│                                                  v           │
│                                              Grafana         │
└─────────────────────────────────────────────────────────────┘
```

### 技术选型对比

| 特性 | Redfish | IPMI |
|------|---------|------|
| **协议** | RESTful API + JSON | 文本协议 |
| **发布时间** | 2015 年 | 1998 年 |
| **安全性** | ✅ 高（HTTPS + 现代认证） | ⚠️ 低（明文传输） |
| **功能** | ✅ 强大（完整的硬件信息） | ⚠️ 有限 |
| **厂商支持** | ✅ 统一标准 | ⚠️ 各厂商实现不一 |
| **推荐度** | ⭐⭐⭐⭐⭐ | ⭐⭐ (仅兜底) |

---

## Redfish 监控配置

### 1. 检查服务器支持情况

```bash
# 测试 Dell iDRAC Redfish API
curl -k -u root:calvin https://192.168.1.100/redfish/v1/

# 测试 HPE iLO Redfish API
curl -k -u Administrator:password https://192.168.1.110/redfish/v1/

# 如果返回 JSON 数据，说明支持 Redfish
```

**支持 Redfish 的服务器**:
- **Dell**: iDRAC 7/8/9（2012 年后的服务器）
- **HPE**: iLO 4/5/6（Gen9 及以后）
- **Supermicro**: X10/X11/X12 系列主板（需要更新固件）
- **Lenovo**: XClarity Controller（ThinkSystem 系列）
- **Cisco**: CIMC（UCS C 系列）

### 📦 预配置服务器列表

本平台已预配置主流服务器的硬件监控模板，新服务器部署时只需修改密码和 IP 即可：

#### Dell PowerEdge（14代及以后）
| 型号 | 说明 | 配置名称 |
|------|------|---------|
| R740 | 2U 双路服务器 | `dell-r740-01`, `dell-r740-02` |
| R740xd | 2U 大容量存储 | `dell-r740xd-01` |
| R640 | 1U 双路服务器 | `dell-r640-01` |
| R750 | 2U 双路服务器 | `dell-r750-01` |
| R750xa | 2U GPU 服务器 | `dell-r750xa-01` |
| R840 | 2U 四路服务器 | `dell-r840-01` |
| R940 | 4U 四路服务器 | `dell-r940-01` |
| C6420 | 2U 多节点服务器 | `dell-c6420-01` |
| C6525 | 2U 多节点服务器 | `dell-c6525-01` |

**默认凭据**: `root / calvin`

#### HPE ProLiant（Gen9 及以后）
| 型号 | 说明 | 配置名称 |
|------|------|---------|
| DL360 Gen10 | 1U 双路服务器 | `hpe-dl360-gen10-01`, `hpe-dl360-gen10-02` |
| DL380 Gen10 | 2U 双路服务器 | `hpe-dl380-gen10-01`, `hpe-dl380-gen10-02` |
| DL360 Gen11 | 1U 双路服务器 | `hpe-dl360-gen11-01` |
| DL380 Gen11 | 2U 双路服务器 | `hpe-dl380-gen11-01` |
| DL385 Gen10 | 2U AMD 服务器 | `hpe-dl385-gen10-01` |
| DL560 Gen10 | 4U 四路服务器 | `hpe-dl560-gen10-01` |
| BL460c Gen10 | 刀片服务器 | `hpe-bl460c-gen10-01` |
| Synergy 480 | Synergy 刀片 | `hpe-synergy-480-gen10-01` |

**默认凭据**: `Administrator / password`

#### Supermicro 服务器
| 型号 | 说明 | 配置名称 |
|------|------|---------|
| 6029P-TRT | 2U 双路服务器 | `supermicro-6029p-01`, `supermicro-6029p-02` |
| 613P-TN12P | 1U 双路服务器 | `supermicro-613-01` |
| 614U-TN12P | 1U 双路服务器 | `supermicro-614-01` |
| 615P-TN12P | 1U 双路服务器 | `supermicro-615-01` |
| 616U-TN12P | 1U 双路服务器 | `supermicro-616-01` |

**默认凭据**: `ADMIN / ADMIN`

#### Lenovo ThinkSystem
| 型号 | 说明 | 配置名称 |
|------|------|---------|
| SR650 | 2U 双路服务器 | `lenovo-sr650-01`, `lenovo-sr650-02` |
| SR630 | 1U 双路服务器 | `lenovo-sr630-01` |
| SR850 | 4U 四路服务器 | `lenovo-sr850-01` |
| SR950 | 4U 四路服务器 | `lenovo-sr950-01` |
| SN550 | 2U 存储服务器 | `lenovo-sn550-01` |

**默认凭据**: `USERID / PASSW0RD`

#### Fujitsu PRIMERGY
| 型号 | 说明 | 配置名称 |
|------|------|---------|
| RX2540 M6 | 2U 双路服务器 | `fujitsu-rx2540-01` |
| RX4770 M6 | 4U 四路服务器 | `fujitsu-rx4770-01` |

**默认凭据**: `admin / admin`

### 🔧 快速添加新服务器

1. 在 `config/redfish-exporter/redfish.yml` 中复制对应厂商的配置模板
2. 修改 `host_address`（BMC IP 地址）
3. 修改 `password`（修改为实际密码）
4. 重启 Redfish Exporter：
   ```bash
   docker-compose restart redfish-exporter
   ```
5. 验证采集：
   ```bash
   curl http://localhost:9610/redfish?target=dell-r740-01
   ```

### 2. 配置 Redfish Exporter

编辑 `config/redfish-exporter/redfish.yml`:

```yaml
hosts:
  # Dell 服务器
  dell-server-01:
    username: "root"
    password: "calvin"              # 修改为实际密码
    host_address: "192.168.1.100"   # iDRAC IP
    insecure_skip_verify: true      # 如果使用自签名证书

  dell-server-02:
    username: "root"
    password: "your-password"
    host_address: "192.168.1.101"

  # HPE 服务器
  hpe-server-01:
    username: "Administrator"
    password: "your-ilo-password"
    host_address: "192.168.1.110"
    insecure_skip_verify: true
```

### 3. 配置 Prometheus 采集

编辑 `config/vmagent/prometheus.yml`，在 `redfish-hardware` 任务中添加目标：

```yaml
- job_name: 'redfish-hardware'
  static_configs:
    - targets:
      - dell-server-01
      - dell-server-02
      - hpe-server-01
```

**重要**: targets 中的名称必须与 `redfish.yml` 中的主机名完全一致。

### 4. 启动服务

```bash
# 启动 Redfish Exporter
docker-compose up -d redfish-exporter

# 查看日志
docker-compose logs -f redfish-exporter

# 验证采集
curl http://localhost:9610/redfish?target=dell-server-01
```

---

## IPMI 监控配置

### 1. 检查 IPMI 支持

```bash
# 安装 ipmitool（用于测试）
apt-get install ipmitool  # Ubuntu/Debian
yum install ipmitool      # CentOS/RHEL

# 测试 IPMI 连接
ipmitool -I lanplus -H 192.168.2.10 -U ADMIN -P ADMIN sensor

# 查看传感器数据
ipmitool -I lanplus -H 192.168.2.10 -U ADMIN -P ADMIN sdr list
```

### 2. 配置 IPMI 监控目标

编辑 `config/vmagent/prometheus.yml`，在 `ipmi-hardware` 任务中添加：

```yaml
- job_name: 'ipmi-hardware'
  static_configs:
    - targets: ['192.168.2.10']      # IPMI IP 地址
      labels:
        instance: 'old-server-01'
        device_class: 'server'
        monitoring_method: 'ipmi'

    - targets: ['192.168.2.11']
      labels:
        instance: 'old-server-02'
        device_class: 'server'
        monitoring_method: 'ipmi'
```

### 3. IPMI 认证配置

IPMI Exporter 使用 HTTP Basic Auth 传递 IPMI 凭据：

```yaml
# 方式 1: URL 中包含凭据（不推荐，安全性差）
- targets: ['192.168.2.10']
  params:
    module: [default]
  basic_auth:
    username: 'ADMIN'
    password: 'ADMIN'

# 方式 2: 使用环境变量（推荐）
# 在 docker-compose.yaml 中配置
```

### 4. 启动服务

```bash
# 启动 IPMI Exporter
docker-compose up -d ipmi-exporter

# 验证采集
curl 'http://localhost:9290/ipmi?target=192.168.2.10&module=default'
```

---

## 监控指标说明

### Redfish 关键指标

| 指标名称 | 说明 | 示例值 |
|---------|------|--------|
| `redfish_thermal_temperatures_reading_celsius` | 温度传感器读数 | 45.0 |
| `redfish_thermal_fans_reading_rpm` | 风扇转速 | 3600 |
| `redfish_power_powersupplies_state` | 电源状态 | 1 (正常) |
| `redfish_memory_health_state` | 内存健康状态 | 1 (正常) |
| `redfish_storage_health_state` | 存储健康状态 | 1 (正常) |
| `redfish_system_health_state` | 系统整体健康 | 1 (正常) |

**状态值说明**:
- `1` = 正常 (OK)
- `0` = 告警 (Warning/Critical)

### 预配置告警规则

本平台已预配置完整的硬件监控告警规则（`config/vmalert/alerts/hardware-alerts.yml`）：

#### 系统健康告警
- `HardwareSystemHealthCritical` - 系统整体健康状态异常（P0）

#### CPU 温度告警
- `HardwareCPUTemperatureWarning` - CPU 温度超过 80°C（P2）
- `HardwareCPUTemperatureCritical` - CPU 温度超过 90°C（P0）

#### 内存告警
- `HardwareMemoryECCWarnings` - 检测到内存 ECC 错误（P2）
- `HardwareMemoryHealthCritical` - 内存健康状态异常（P0）

#### 磁盘告警
- `HardwareDiskTemperatureWarning` - 磁盘温度超过 55°C（P2）
- `HardwareDiskTemperatureCritical` - 磁盘温度超过 65°C（P0）
- `HardwareDiskPredictFailure` - 磁盘预测即将故障（P1）
- `HardwareDiskMediaErrors` - 磁盘出现媒体错误（P1）
- `HardwareDiskHealthCritical` - 磁盘健康状态异常（P0）

#### 风扇告警
- `HardwareFanSpeedLow` - 风扇转速低于 1000 RPM（P2）
- `HardwareFanFailed` - 风扇故障（P0）

#### 电源告警
- `HardwarePowerSupplyFailed` - 电源供应故障（P0）
- `HardwarePowerConsumptionHigh` - 功耗超过 800W（P2）

#### 温度告警
- `HardwareInletTemperatureWarning` - 进风口温度超过 30°C（P2）
- `HardwareExhaustTemperatureWarning` - 出风口温度超过 45°C（P2）

#### 其他硬件告警
- `HardwareRAIDControllerFailed` - RAID 控制器状态异常（P0）
- `HardwareNetworkInterfaceFailed` - 网络接口状态异常（P2）
- `HardwareBMCDown` - BMC/iDRAC/iLO 不可达（P2）

#### IPMI 告警（老服务器）
- `IPMISensorFailed` - IPMI 传感器故障（P2）
- `IPMITemperatureHigh` - IPMI 温度过高（P2）
- `IPMIFanFailed` - IPMI 风扇故障（P0）
- `IPMIPowerSupplyFailed` - IPMI 电源故障（P0）

### IPMI 关键指标

| 指标名称 | 说明 | 单位 |
|---------|------|------|
| `ipmi_temperature_celsius` | 温度传感器 | °C |
| `ipmi_fan_speed_rpm` | 风扇转速 | RPM |
| `ipmi_power_state` | 电源状态 | 布尔值 |
| `ipmi_voltage_volts` | 电压 | V |
| `ipmi_current_amperes` | 电流 | A |

---

## 告警配置

创建硬件告警规则 `config/vmalert/alerts/hardware-alerts.yml`:

```yaml
groups:
  - name: hardware_alerts
    interval: 60s
    rules:

      # CPU 温度过高
      - alert: HighCPUTemperature
        expr: |
          redfish_thermal_temperatures_reading_celsius{sensor_name=~".*CPU.*"} > 80
        for: 5m
        labels:
          severity: warning
          category: hardware
        annotations:
          summary: "CPU 温度过高: {{ $labels.instance }}"
          description: "{{ $labels.sensor_name }} 温度 {{ $value }}°C，超过阈值 80°C"

      # 风扇故障
      - alert: FanFailure
        expr: |
          redfish_thermal_fans_state == 0
        for: 1m
        labels:
          severity: critical
          category: hardware
        annotations:
          summary: "风扇故障: {{ $labels.instance }}"
          description: "{{ $labels.fan_name }} 故障，请立即检查"

      # 电源故障
      - alert: PowerSupplyFailure
        expr: |
          redfish_power_powersupplies_state == 0
        for: 1m
        labels:
          severity: critical
          category: hardware
        annotations:
          summary: "电源故障: {{ $labels.instance }}"
          description: "{{ $labels.power_supply_name }} 故障"

      # RAID 降级
      - alert: RAIDDegraded
        expr: |
          redfish_storage_health_state == 0
        for: 5m
        labels:
          severity: critical
          category: hardware
        annotations:
          summary: "RAID 降级: {{ $labels.instance }}"
          description: "存储控制器健康状态异常，可能有硬盘故障"

      # IPMI 温度告警
      - alert: IPMIHighTemperature
        expr: |
          ipmi_temperature_celsius > 85
        for: 5m
        labels:
          severity: warning
          category: hardware
        annotations:
          summary: "IPMI 温度过高: {{ $labels.instance }}"
          description: "{{ $labels.sensor }} 温度 {{ $value }}°C"
```

重启 vmalert 使告警生效:

```bash
docker-compose restart vmalert
```

---

## Grafana 仪表板

### 推荐的仪表板

1. **Redfish Hardware Monitoring**
   - 导入方式: Grafana → Import → 上传 JSON
   - 位置: `config/grafana/dashboards/redfish-hardware.json`（需自行创建）

2. **IPMI Server Hardware**
   - Grafana Dashboard ID: 11530
   - 导入: Grafana → Import → 输入 `11530`

### 关键监控面板

- **温度趋势图**: 所有传感器温度
- **风扇转速**: 实时转速和状态
- **电源状态**: 冗余电源健康
- **RAID 状态**: 控制器和硬盘健康
- **硬件事件日志**: 最近的硬件告警

---

## 故障排查

### Redfish Exporter 无法连接

**问题**: `connection refused` 或 `timeout`

```bash
# 1. 检查 iDRAC/iLO IP 是否可达
ping 192.168.1.100

# 2. 测试 Redfish API
curl -k -u root:calvin https://192.168.1.100/redfish/v1/

# 3. 检查凭据
# Dell iDRAC 默认: root / calvin
# HPE iLO 默认: Administrator / (查看服务器标签)

# 4. 检查防火墙
# Redfish 使用 HTTPS (443 端口)
```

**解决方案**:
- 确认 iDRAC/iLO 网络配置正确
- 检查 `insecure_skip_verify: true` 是否设置（自签名证书）
- 验证用户名密码

### IPMI Exporter 无数据

**问题**: 采集不到 IPMI 数据

```bash
# 1. 测试 IPMI 连接
ipmitool -I lanplus -H 192.168.2.10 -U ADMIN -P ADMIN sensor

# 2. 检查 IPMI 是否启用
# 进入 BIOS → IPMI Configuration → Enable

# 3. 检查网络模式
# 如果容器无法访问 IPMI，尝试 host 模式
```

编辑 `docker-compose.yaml`:

```yaml
ipmi-exporter:
  network_mode: host  # 使用主机网络
```

### 指标数据异常

**问题**: 温度显示 `-1` 或 `N/A`

**原因**: 传感器未启用或硬件不支持

**解决方案**:
- 检查 BIOS 中传感器是否启用
- 某些虚拟机不支持硬件传感器
- 过滤掉无效传感器数据

---

## 最佳实践

### 1. 只读账号

为监控创建只读账号，避免使用管理员账号：

**Dell iDRAC**:
```
用户名: monitoring
权限: Login, Read-Only
```

**HPE iLO**:
```
用户名: monitoring
权限: Login, Virtual Media
```

### 2. 监控频率

硬件监控不需要太频繁：

```yaml
scrape_interval: 60s  # 推荐
scrape_timeout: 30s
```

### 3. 标签规范

统一使用标签便于管理：

```yaml
labels:
  device_class: 'server'
  monitoring_method: 'redfish'  # 或 'ipmi'
  priority: 'P0'                # P0/P1/P2
  datacenter: 'dc1'
  rack: 'A-01'
```

### 4. 安全建议

- ✅ 修改默认密码
- ✅ 使用独立的管理网络
- ✅ 启用 HTTPS（Redfish）
- ✅ 定期更新固件
- ❌ 不要将密码提交到 Git

---

## 参考资料

- [Redfish 标准官网](https://www.dmtf.org/standards/redfish)
- [Redfish Exporter GitHub](https://github.com/jenningsloy318/redfish_exporter)
- [IPMI Exporter GitHub](https://github.com/prometheus-community/ipmi_exporter)
- [Dell iDRAC Redfish API 文档](https://www.dell.com/support/manuals/idrac)
- [HPE iLO Redfish API 文档](https://hewlettpackard.github.io/ilo-rest-api-docs/)

---

## 下一步

- [ ] 配置实际的服务器信息
- [ ] 测试 Redfish/IPMI 连接
- [ ] 导入 Grafana 仪表板
- [ ] 配置硬件告警规则
- [ ] 设置告警通知

如有问题，请参考 [FAQ](FAQ.md) 或提交 Issue。
