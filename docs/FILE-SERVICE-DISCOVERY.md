# 文件服务发现快速指南

## 🎉 已启用文件服务发现！

现在你可以通过编辑 JSON 文件来管理监控目标，**无需重启 vmagent**！

## 📁 配置文件位置

```
config/vmagent/targets/
├── core-switches.json   # 核心交换机（已创建示例）
├── esxi-hosts.json      # ESXi 主机（已创建示例）
├── websites.json        # 网站监控（已创建示例）
└── README.md            # 详细使用说明
```

## 🚀 快速开始

### 1. 重启 vmagent（仅需一次）

```bash
# 使配置生效
docker-compose restart vmagent

# 查看日志确认启动成功
docker logs -f vmagent
```

### 2. 添加你的第一个监控目标

**示例：添加核心交换机**

```bash
# 编辑核心交换机配置
vim config/vmagent/targets/core-switches.json
```

将示例 IP 改成你的实际 IP：

```json
[
  {
    "targets": [
      "192.168.1.100"  # 改成你的交换机 IP
    ],
    "labels": {
      "device_name": "core-switch-1",
      "device_type": "switch",
      "device_tier": "core",
      "location": "datacenter-1",
      "priority": "critical"
    }
  }
]
```

保存文件后，**等待 30 秒自动生效**！

### 3. 验证监控目标是否生效

```bash
# 等待 30 秒
sleep 30

# 查看 vmagent 采集目标
curl http://localhost:8429/api/v1/targets | jq

# 或者查看特定类型的目标
curl http://localhost:8429/api/v1/targets | \
  jq '.data.activeTargets[] | select(.labels.device_type=="switch")'
```

## 📝 常见操作

### 添加新设备

**方法 1：编辑现有文件**

```bash
vim config/vmagent/targets/core-switches.json

# 在 targets 数组中添加新 IP
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
```

**方法 2：创建新分组**

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

# 30 秒后自动发现新配置文件！
```

### 删除设备

```bash
# 从 targets 数组中删除 IP
vim config/vmagent/targets/core-switches.json

# 或者删除整个配置文件
rm config/vmagent/targets/old-devices.json

# 30 秒后自动移除
```

### 添加网站监控

```bash
# 编辑网站配置
vim config/vmagent/targets/websites.json

[
  {
    "targets": [
      "https://www.company.com",
      "http://oa.company.local",
      "https://api.company.com"
    ],
    "labels": {
      "service_type": "http",
      "priority": "critical"
    }
  }
]
```

## 🏷️ 推荐的标签

使用有意义的标签可以方便后续查询和告警：

```json
{
  "targets": ["192.168.1.100"],
  "labels": {
    "device_name": "core-switch-dc1-01",  // 设备名称
    "device_type": "switch",               // 设备类型
    "device_tier": "core",                 // 网络层级
    "vendor": "cisco",                     // 设备厂商
    "location": "datacenter-1",            // 地理位置
    "priority": "critical"                 // 告警优先级
  }
}
```

### 按优先级分组

```json
// 核心设备 - critical（立即告警）
{
  "targets": ["192.168.1.1", "192.168.1.100"],
  "labels": {
    "device_tier": "core",
    "priority": "critical"
  }
}

// 接入设备 - warning（延迟告警）
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

## ✅ 验证配置

### 检查 JSON 格式

```bash
# 验证 JSON 格式是否正确
jq . config/vmagent/targets/core-switches.json

# 如果输出格式化的 JSON，说明格式正确
# 如果报错，说明 JSON 格式有问题
```

### 查看当前所有监控目标

```bash
# 查看所有活跃的采集目标
curl http://localhost:8429/api/v1/targets | jq '.data.activeTargets[].labels'

# 统计目标数量
curl http://localhost:8429/api/v1/targets | \
  jq '.data.activeTargets | length'
```

### 按设备类型查询

```bash
# 查看所有交换机
curl http://localhost:8429/api/v1/targets | \
  jq '.data.activeTargets[] | select(.labels.device_type=="switch")'

# 查看所有 ESXi 主机
curl http://localhost:8429/api/v1/targets | \
  jq '.data.activeTargets[] | select(.labels.device_type=="esxi")'
```

## 🎯 实际场景示例

### 场景 1：监控所有核心网络设备

```bash
cat > config/vmagent/targets/core-network.json <<'EOF'
[
  {
    "targets": [
      "192.168.1.1",    # 核心路由器
      "192.168.1.100",  # 核心交换机 1
      "192.168.1.101"   # 核心交换机 2
    ],
    "labels": {
      "device_tier": "core",
      "location": "datacenter-1",
      "priority": "critical"
    }
  }
]
EOF
```

### 场景 2：监控 VMware 环境

```bash
cat > config/vmagent/targets/vmware-infra.json <<'EOF'
[
  {
    "targets": [
      "192.168.2.5",   # vCenter
      "192.168.2.10",  # ESXi-01
      "192.168.2.11",  # ESXi-02
      "192.168.2.12"   # ESXi-03
    ],
    "labels": {
      "device_type": "vmware",
      "cluster": "production",
      "priority": "critical"
    }
  }
]
EOF
```

### 场景 3：监控业务系统

```bash
cat > config/vmagent/targets/business-apps.json <<'EOF'
[
  {
    "targets": [
      "https://www.company.com",
      "https://api.company.com",
      "http://oa.company.local",
      "http://jenkins.company.local"
    ],
    "labels": {
      "service_type": "http",
      "environment": "production",
      "priority": "critical"
    }
  }
]
EOF
```

## ⚡ 高级技巧

### 使用 jq 批量添加设备

```bash
# 批量添加多个 IP
jq '.[0].targets += ["192.168.1.102", "192.168.1.103"]' \
  config/vmagent/targets/core-switches.json > temp.json
mv temp.json config/vmagent/targets/core-switches.json
```

### 从文本文件批量导入

```bash
# 准备 IP 列表
cat > ips.txt <<EOF
192.168.1.110
192.168.1.111
192.168.1.112
EOF

# 生成 JSON 配置
python3 << 'PYTHON'
import json

with open('ips.txt') as f:
    ips = [line.strip() for line in f if line.strip()]

config = [{
    "targets": ips,
    "labels": {
        "device_type": "switch",
        "device_tier": "access",
        "priority": "warning"
    }
}]

with open('config/vmagent/targets/new-switches.json', 'w') as f:
    json.dump(config, f, indent=2)

print(f"✅ 已导入 {len(ips)} 台设备")
PYTHON
```

## 🔧 故障排查

### 问题 1：修改后没有生效

**解决方法**：

```bash
# 1. 检查 JSON 格式
jq . config/vmagent/targets/your-file.json

# 2. 查看 vmagent 日志
docker logs vmagent | tail -50

# 3. 等待足够时间（默认 30 秒）
sleep 30

# 4. 手动重启 vmagent
docker-compose restart vmagent
```

### 问题 2：JSON 格式错误

```bash
# 使用 jq 验证格式
jq . config/vmagent/targets/core-switches.json

# 如果报错，检查:
# - 是否有多余的逗号
# - 括号是否匹配
# - 引号是否配对
```

### 问题 3：设备没有被监控

```bash
# 查看采集目标状态
curl http://localhost:8429/api/v1/targets | \
  jq '.data.activeTargets[] | {instance: .labels.instance, health: .health}'

# 检查设备是否可达
ping 192.168.1.100
```

## 📚 更多资源

- [详细使用文档](config/vmagent/targets/README.md)
- [Blackbox 监控示例](examples/blackbox-monitoring-examples.yml)
- [主文档](README.md)

## 🎉 总结

**文件服务发现的核心优势**:

1. ✅ **修改配置 30 秒自动生效，无需重启**
2. ✅ 支持动态添加/删除监控目标
3. ✅ 配置文件化，易于版本控制
4. ✅ 支持批量管理和自动化
5. ✅ 零额外组件，维护简单

**现在开始使用吧！** 🚀
