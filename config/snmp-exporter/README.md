# SNMP Exporter 配置说明

## 快速开始

SNMP Exporter 需要一个配置文件来定义如何从 SNMP 设备获取指标。

### 使用官方预生成的配置文件(推荐)

最简单的方法是使用 Prometheus 官方预生成的配置文件:

```bash
cd config/snmp-exporter
wget https://github.com/prometheus/snmp_exporter/releases/latest/download/snmp.yml
```

这个文件包含了大多数常见网络设备的 MIB 定义。

### 支持的设备和 MIB 模块

官方配置文件包含以下常用模块:

- `if_mib`: 网络接口监控(通用)
- `cisco_*`: Cisco 设备专用模块
- `juniper_*`: Juniper 设备专用模块
- `apc_ups`: APC UPS 设备
- `ddwrt`: DD-WRT 路由器
- `paloalto_*`: Palo Alto 防火墙
- `synology`: 群晖 NAS
- 更多...

### 配置 vmagent 使用不同的模块

在 `config/vmagent/prometheus.yml` 中,修改 SNMP 采集任务:

```yaml
- job_name: 'snmp-cisco-switches'
  static_configs:
    - targets:
      - 192.168.1.100  # Cisco 交换机 IP
  metrics_path: /snmp
  params:
    module: [cisco_ios]  # 使用 cisco_ios 模块
  relabel_configs:
    - source_labels: [__address__]
      target_label: __param_target
    - source_labels: [__param_target]
      target_label: instance
    - target_label: __address__
      replacement: snmp-exporter:9116
```

### 生成自定义配置(高级)

如果需要监控特殊设备或自定义 OID,可以使用 snmp_exporter generator:

1. 安装 generator 工具
```bash
git clone https://github.com/prometheus/snmp_exporter.git
cd snmp_exporter/generator
```

2. 编辑 `generator.yml` 配置文件

3. 生成配置
```bash
make generate
```

4. 将生成的 `snmp.yml` 复制到此目录

## SNMP 版本配置

### SNMP v2c (推荐用于内网设备)

在 vmagent 配置中添加:
```yaml
params:
  module: [if_mib]
  auth: [public_v2]  # community string
```

### SNMP v3 (更安全)

需要在 snmp.yml 中配置认证信息:
```yaml
auths:
  secure_v3:
    version: 3
    username: monitoring
    password: password123
    auth_protocol: SHA
    priv_protocol: AES
    priv_password: privpassword123
    security_level: authPriv
```

## 测试 SNMP 连接

使用 snmpwalk 命令测试设备连接:

```bash
# SNMP v2c
snmpwalk -v2c -c public 192.168.1.100 1.3.6.1.2.1.2.2.1.8

# SNMP v3
snmpwalk -v3 -l authPriv -u monitoring -a SHA -A password123 -x AES -X privpassword123 192.168.1.100 1.3.6.1.2.1.2.2.1.8
```

## 常见问题

### 1. 超时错误
- 检查网络连接
- 增加 scrape_timeout 时间
- 确认 SNMP community string 正确

### 2. 没有数据
- 确认设备支持对应的 MIB
- 检查 OID 是否正确
- 查看 snmp-exporter 日志: `docker logs snmp-exporter`

### 3. 性能问题
- 减少 walk 的 OID 范围
- 增加 scrape_interval
- 使用更具体的 MIB 模块

## 参考资源

- SNMP Exporter 官方文档: https://github.com/prometheus/snmp_exporter
- MIB 浏览器: http://www.oidview.com/mibs/0/md-0-1.html
- Prometheus SNMP 最佳实践: https://prometheus.io/docs/guides/snmp-exporter/
