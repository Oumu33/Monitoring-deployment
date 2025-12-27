# 监控系统部署方案

基于 VictoriaMetrics 的完整监控系统,包含 Linux 主机监控、VMware 虚拟化监控、SNMP 网络设备监控。

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      监控数据流                               │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Node Exporter ──┐                                           │
│  VMware Exporter ┼──> vmagent ──> VictoriaMetrics           │
│  SNMP Exporter ──┘         │             │                   │
│                            │             │                   │
│                            v             v                   │
│                       vmalert ──> Alertmanager               │
│                            │                                 │
│                            v                                 │
│                        Grafana                               │
└─────────────────────────────────────────────────────────────┘
```

## 组件说明

- **VictoriaMetrics**: 时序数据库,存储所有监控指标
- **vmagent**: 指标采集代理,负责从各个 exporter 收集数据
- **vmalert**: 告警规则引擎,评估告警规则并触发告警
- **Alertmanager**: 告警管理和通知分发
- **Grafana**: 数据可视化平台
- **Node Exporter**: Linux 主机指标采集
- **VMware Exporter**: VMware vSphere 环境监控
- **SNMP Exporter**: SNMP 网络设备监控

## 前置要求

- Docker 20.10+
- Docker Compose 2.0+
- 至少 4GB 可用内存
- 至少 20GB 可用磁盘空间

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/Oumu33/Monitoring-deployment.git
cd Monitoring-deployment
```

### 2. 配置环境变量

```bash
cp .env.example .env
vim .env
```

编辑 `.env` 文件,配置以下必要参数:

```bash
# Grafana 管理员账号
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=your-secure-password

# VMware vCenter 连接信息
VSPHERE_HOST=vcenter.example.com
VSPHERE_USER=monitoring@vsphere.local
VSPHERE_PASSWORD=your-vcenter-password
VSPHERE_IGNORE_SSL=True
```

### 3. 下载 SNMP Exporter 配置文件(推荐)

```bash
cd config/snmp-exporter
wget https://github.com/prometheus/snmp_exporter/releases/latest/download/snmp.yml
cd ../..
```

### 4. 配置监控目标

编辑 `config/vmagent/prometheus.yml`,添加你的监控目标:

```yaml
# 添加 Linux 主机
- job_name: 'node-exporter'
  static_configs:
    - targets: ['192.168.1.10:9100']
      labels:
        instance: 'web-server-01'

# 添加 SNMP 设备
- job_name: 'snmp-exporter'
  static_configs:
    - targets:
      - 192.168.1.100  # 交换机 IP
      - 192.168.1.101  # 路由器 IP
```

### 5. 配置告警通知

编辑 `config/alertmanager/alertmanager.yml`,配置邮件通知:

```yaml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@example.com'
  smtp_auth_username: 'alerts@example.com'
  smtp_auth_password: 'your-app-password'
```

### 6. 启动服务

```bash
docker-compose up -d
```

### 7. 验证服务状态

```bash
docker-compose ps
```

所有服务应该处于 `Up` 状态。

## 访问地址

- **Grafana**: http://localhost:3000 (默认账号: admin/admin)
- **VictoriaMetrics**: http://localhost:8428
- **vmalert**: http://localhost:8880
- **Alertmanager**: http://localhost:9093
- **Node Exporter**: http://localhost:9100/metrics
- **SNMP Exporter**: http://localhost:9116/metrics
- **VMware Exporter**: http://localhost:9272/metrics

## 监控目标配置

### Linux 主机监控

在需要监控的 Linux 主机上安装 Node Exporter:

```bash
# 使用 Docker
docker run -d \
  --name=node-exporter \
  --net="host" \
  --pid="host" \
  -v "/:/host:ro,rslave" \
  prom/node-exporter:latest \
  --path.rootfs=/host
```

或者使用系统服务安装,参考: https://github.com/prometheus/node_exporter

### VMware 监控配置

1. 在 vCenter 中创建只读监控账号
2. 在 `.env` 文件中配置 vCenter 连接信息
3. VMware Exporter 会自动发现并监控所有 ESXi 主机和虚拟机

### SNMP 设备监控

1. 确保网络设备开启 SNMP(v2c 或 v3)
2. 在 `config/vmagent/prometheus.yml` 中添加设备 IP
3. 根据设备类型选择合适的 SNMP 模块

详细配置请参考: [config/snmp-exporter/README.md](config/snmp-exporter/README.md)

## Grafana 仪表板

### 推荐的仪表板

登录 Grafana 后,导入以下仪表板(Import -> 输入 ID):

- **Node Exporter Full** (ID: 1860) - Linux 主机监控
- **VMware vSphere - Overview** (ID: 11243) - VMware 环境监控
- **SNMP Stats** (ID: 11169) - SNMP 设备监控
- **VictoriaMetrics - vmagent** (ID: 12683) - vmagent 监控

## 告警配置

系统预配置了以下告警规则:

### 主机告警
- 主机宕机
- CPU 使用率过高 (>80%)
- 内存使用率过高 (>85%)
- 磁盘空间不足 (<15%)
- 磁盘 I/O 等待过高
- 网络接口下线

### VMware 告警
- 虚拟机宕机
- ESXi 主机资源使用率过高
- 数据存储空间不足

### 网络设备告警
- SNMP 设备无法访问
- 网络接口下线
- 接口错误率过高
- 接口流量过高

### 监控系统告警
- 监控组件服务宕机
- 采集目标无法访问
- 存储空间不足

告警规则配置文件位于 `config/vmalert/alerts/` 目录。

## 维护操作

### 查看日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f victoriametrics
docker-compose logs -f vmagent
```

### 重启服务

```bash
# 重启所有服务
docker-compose restart

# 重启特定服务
docker-compose restart vmagent
```

### 更新配置

修改配置文件后,重启相应服务:

```bash
# 更新 vmagent 配置
docker-compose restart vmagent

# 更新告警规则
docker-compose restart vmalert

# 更新 Alertmanager 配置
docker-compose restart alertmanager
```

### 数据备份

```bash
# 备份 VictoriaMetrics 数据
docker run --rm -v monitoring-deployment_vmdata:/source -v $(pwd)/backup:/backup alpine \
  tar czf /backup/vm-data-$(date +%Y%m%d).tar.gz -C /source .

# 备份 Grafana 数据
docker run --rm -v monitoring-deployment_grafana-data:/source -v $(pwd)/backup:/backup alpine \
  tar czf /backup/grafana-data-$(date +%Y%m%d).tar.gz -C /source .
```

### 清理和重置

```bash
# 停止所有服务
docker-compose down

# 删除所有数据(谨慎操作!)
docker-compose down -v

# 重新启动
docker-compose up -d
```

## 性能优化

### VictoriaMetrics 优化

- 数据保留时间: 修改 `docker-compose.yaml` 中的 `--retentionPeriod` 参数
- 内存限制: 添加 `--memory.allowedPercent=60` 限制内存使用

### vmagent 优化

- 减少采集间隔: 修改 `scrape_interval` 为更大的值(如 30s 或 60s)
- 批量写入: 添加 `--remoteWrite.maxBlockSize=8388608` 增加批量大小

### 网络优化

- 将监控组件与监控目标部署在同一网段
- 对于 VMware 监控,建议部署在 vCenter 网络附近
- SNMP 监控使用较长的采集间隔(60s+)

## 故障排查

### 服务无法启动

```bash
# 检查端口占用
netstat -tlnp | grep -E '(3000|8428|9093|9116|9272)'

# 检查 Docker 日志
docker-compose logs
```

### 无法采集数据

1. 检查 vmagent 日志: `docker-compose logs vmagent`
2. 验证目标可达性: `curl http://target:port/metrics`
3. 检查防火墙规则

### 告警不触发

1. 检查 vmalert 日志: `docker-compose logs vmalert`
2. 访问 vmalert UI: http://localhost:8880
3. 验证告警规则语法

### VMware Exporter 报错

1. 检查 vCenter 连接信息
2. 确认监控账号权限
3. 查看详细日志: `docker-compose logs vmware-exporter`

## 目录结构

```
.
├── docker-compose.yaml          # Docker Compose 配置
├── .env.example                 # 环境变量示例
├── .gitignore                   # Git 忽略文件
├── README.md                    # 本文档
└── config/                      # 配置文件目录
    ├── vmagent/
    │   └── prometheus.yml       # vmagent 采集配置
    ├── vmalert/
    │   └── alerts/              # 告警规则
    │       ├── node-alerts.yml
    │       ├── infra-alerts.yml
    │       └── system-alerts.yml
    ├── alertmanager/
    │   └── alertmanager.yml     # Alertmanager 配置
    ├── grafana/
    │   ├── provisioning/        # Grafana 自动配置
    │   │   ├── datasources/     # 数据源配置
    │   │   └── dashboards/      # 仪表板配置
    │   └── dashboards/          # 仪表板 JSON 文件
    └── snmp-exporter/
        ├── snmp.yml             # SNMP 配置
        └── README.md            # SNMP 配置说明
```

## 安全建议

1. **修改默认密码**: 修改 Grafana 管理员密码
2. **限制访问**: 使用防火墙或反向代理限制访问
3. **HTTPS**: 在生产环境中使用 HTTPS
4. **密钥管理**: 不要将密码提交到 Git 仓库
5. **网络隔离**: 将监控系统部署在独立的网络段
6. **定期备份**: 定期备份配置和数据
7. **及时更新**: 定期更新 Docker 镜像

## 扩展功能

### 添加 Blackbox Exporter(HTTP/ICMP 探测)

在 `docker-compose.yaml` 中添加:

```yaml
blackbox-exporter:
  image: prom/blackbox-exporter:latest
  ports:
    - "9115:9115"
  volumes:
    - ./config/blackbox/blackbox.yml:/etc/blackbox/blackbox.yml
  networks:
    - monitoring
```

### 添加 cAdvisor(容器监控)

```yaml
cadvisor:
  image: gcr.io/cadvisor/cadvisor:latest
  ports:
    - "8080:8080"
  volumes:
    - /:/rootfs:ro
    - /var/run:/var/run:ro
    - /sys:/sys:ro
    - /var/lib/docker/:/var/lib/docker:ro
  networks:
    - monitoring
```

## 参考文档

- [VictoriaMetrics 官方文档](https://docs.victoriametrics.com/)
- [vmagent 文档](https://docs.victoriametrics.com/vmagent.html)
- [vmalert 文档](https://docs.victoriametrics.com/vmalert.html)
- [Alertmanager 文档](https://prometheus.io/docs/alerting/latest/alertmanager/)
- [Grafana 文档](https://grafana.com/docs/grafana/latest/)
- [Node Exporter 文档](https://github.com/prometheus/node_exporter)
- [SNMP Exporter 文档](https://github.com/prometheus/snmp_exporter)
- [VMware Exporter 文档](https://github.com/pryorda/vmware_exporter)

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request!

## 联系方式

如有问题,请在 GitHub 仓库提交 Issue。
