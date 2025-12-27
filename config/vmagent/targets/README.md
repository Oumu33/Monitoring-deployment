# 文件服务发现配置目录

本目录用于存放 Prometheus 文件服务发现（File Service Discovery）的配置文件。

## 工作原理

vmagent 每 30 秒自动读取此目录下的 JSON 文件，发现新的监控目标。

**关键优势**:
- ✅ 修改 JSON 文件后 **30 秒自动生效，无需重启 vmagent**
- ✅ 支持动态添加/删除监控目标
- ✅ 支持自定义标签分组管理

## 文件格式

每个 JSON 文件格式如下：

```json
[
  {
    "targets": [
      "192.168.1.100",
      "192.168.1.101"
    ],
    "labels": {
      "device_type": "switch",
      "device_tier": "core",
      "location": "datacenter-1",
      "priority": "critical"
    }
  }
]
```

## 配置文件说明

### core-switches.json
核心交换机配置，用于 ICMP Ping 探测。

**示例**:
```json
[
  {
    "targets": ["192.168.1.100"],
    "labels": {
      "device_name": "core-switch-1",
      "device_type": "switch",
      "device_tier": "core",
      "priority": "critical"
    }
  }
]
```

### esxi-hosts.json
ESXi 主机配置，用于 ICMP Ping 探测。

**示例**:
```json
[
  {
    "targets": ["192.168.2.10"],
    "labels": {
      "device_name": "esxi-01",
      "device_type": "esxi",
      "cluster": "production",
      "priority": "critical"
    }
  }
]
```

### websites.json
网站监控配置，用于 HTTP/HTTPS 探测。

**示例**:
```json
[
  {
    "targets": ["https://www.company.com"],
    "labels": {
      "service_name": "company-website",
      "service_type": "http",
      "priority": "critical"
    }
  }
]
```

## 如何添加新设备

### 方法 1: 直接编辑 JSON 文件

```bash
# 编辑对应的 JSON 文件
vim config/vmagent/targets/core-switches.json

# 添加新的 IP 到 targets 数组
[
  {
    "targets": [
      "192.168.1.100",
      "192.168.1.101",  # 新增
      "192.168.1.102"   # 新增
    ],
    "labels": {
      "device_type": "switch",
      "priority": "critical"
    }
  }
]

# 保存文件，等待 30 秒自动生效
```

### 方法 2: 使用 jq 命令批量添加

```bash
# 添加单个设备
jq '.[0].targets += ["192.168.1.110"]' \
  config/vmagent/targets/core-switches.json > temp.json
mv temp.json config/vmagent/targets/core-switches.json
```

### 方法 3: 创建新的分组

```bash
# 创建接入层交换机配置
cat > config/vmagent/targets/access-switches.json <<'EOF'
[
  {
    "targets": [
      "192.168.1.110",
      "192.168.1.111",
      "192.168.1.112"
    ],
    "labels": {
      "device_type": "switch",
      "device_tier": "access",
      "location": "floor-1",
      "priority": "warning"
    }
  }
]
EOF
```

## 标签使用建议

### 推荐的标签

- **device_name**: 设备名称（唯一标识）
- **device_type**: 设备类型（switch/router/esxi/server）
- **device_tier**: 设备层级（core/distribution/access）
- **location**: 地理位置（datacenter-1/floor-2/branch）
- **priority**: 告警优先级（critical/warning/info）
- **cluster**: 集群名称（适用于虚拟化环境）

### 按优先级分组

```json
// 核心设备 - critical
{
  "targets": ["192.168.1.1", "192.168.1.100"],
  "labels": {
    "device_tier": "core",
    "priority": "critical"
  }
}

// 接入设备 - warning
{
  "targets": ["192.168.1.110", "192.168.1.111"],
  "labels": {
    "device_tier": "access",
    "priority": "warning"
  }
}

// 测试设备 - info（不告警）
{
  "targets": ["192.168.99.10"],
  "labels": {
    "device_tier": "lab",
    "priority": "info"
  }
}
```

## 验证配置

### 检查 JSON 格式

```bash
# 验证 JSON 格式是否正确
jq . config/vmagent/targets/core-switches.json
```

### 查看当前监控目标

```bash
# 查询 vmagent 当前的采集目标
curl http://localhost:8429/api/v1/targets | jq '.data.activeTargets[] | select(.labels.device_type=="switch")'
```

### 查看生效情况

```bash
# 修改 JSON 后，等待 30 秒
sleep 30

# 查询新目标是否被发现
curl http://localhost:8429/api/v1/targets | jq '.data.activeTargets[].discoveredLabels.__address__'
```

## 最佳实践

### 1. 按设备类型分文件

```
targets/
├── core-switches.json       # 核心交换机
├── access-switches.json     # 接入交换机
├── routers.json             # 路由器
├── esxi-hosts.json          # ESXi 主机
├── databases.json           # 数据库服务器
└── websites.json            # 网站监控
```

### 2. 使用有意义的标签

```json
{
  "targets": ["192.168.1.100"],
  "labels": {
    "device_name": "core-switch-dc1-01",  // 清晰的命名
    "device_type": "switch",
    "vendor": "cisco",                     // 设备厂商
    "model": "catalyst-9300",              // 设备型号
    "location": "datacenter-1-rack-A01",   // 精确位置
    "owner": "network-team",               // 责任团队
    "priority": "critical"
  }
}
```

### 3. 定期备份配置

```bash
# 备份 targets 配置
tar czf targets-backup-$(date +%Y%m%d).tar.gz config/vmagent/targets/
```

### 4. 版本控制

```bash
# 配置文件纳入 Git 管理
git add config/vmagent/targets/*.json
git commit -m "Add new monitoring targets"
```

## 常见问题

### Q: 修改 JSON 后多久生效？
A: 默认 30 秒自动重新加载，无需重启 vmagent。

### Q: JSON 格式错误会怎样？
A: vmagent 会忽略格式错误的文件，不影响其他正常的配置。建议用 `jq` 验证格式。

### Q: 可以删除设备吗？
A: 可以，直接从 targets 数组中删除 IP 即可，30 秒后自动移除。

### Q: 支持通配符吗？
A: 支持。在 prometheus.yml 中可以使用 `*.json` 匹配所有 JSON 文件。

### Q: 如何临时禁用某个设备？
A: 有两种方式：
1. 从 targets 数组中删除
2. 添加标签 `disabled: "true"`，然后在告警规则中过滤

## 进阶：自动化脚本

### 从 Excel 批量生成

参考 `scripts/generate-targets.py` 脚本，可以从 Excel 批量生成配置。

### 从 CMDB 同步

参考 `scripts/sync-from-cmdb.py` 脚本，可以从 CMDB 定时同步设备信息。

### API 自动注册

参考 `scripts/register-device.py` 脚本，可以提供 API 接口自动注册新设备。

## 相关文档

- [Prometheus File-based Service Discovery](https://prometheus.io/docs/prometheus/latest/configuration/configuration/#file_sd_config)
- [监控系统主文档](../../README.md)
- [Blackbox 监控示例](../../examples/blackbox-monitoring-examples.yml)
