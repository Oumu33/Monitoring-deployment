# 监控目标配置示例

这个目录包含各种监控场景的配置示例，帮助你快速配置不同类型的监控目标。

## 使用方法

1. 根据你的需求选择合适的示例文件
2. 复制相关配置到 `config/vmagent/prometheus.yml`
3. 修改 IP 地址、端口等参数
4. 重启 vmagent: `docker-compose restart vmagent`

## 示例文件说明

- `linux-servers.yml` - Linux 服务器监控配置
- `cisco-switches.yml` - Cisco 交换机监控配置
- `vmware-vcenter.yml` - VMware vCenter 监控配置
- `databases.yml` - 数据库监控配置（MySQL, PostgreSQL, Redis 等）
- `web-services.yml` - Web 服务监控配置（HTTP 探测）
- `custom-metrics.yml` - 自定义应用监控配置

## 注意事项

- 所有示例中的 IP 地址都需要替换为实际地址
- 根据网络环境调整 `scrape_interval` 和 `scrape_timeout`
- 确保目标服务器已安装并运行相应的 exporter
- 使用标签 (`labels`) 对监控目标进行分类管理
