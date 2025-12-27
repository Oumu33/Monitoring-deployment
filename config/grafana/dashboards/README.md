# Grafana Dashboards

此目录用于存放 Grafana 仪表板 JSON 文件。

## 推荐的仪表板

### Node Exporter 仪表板
- **Node Exporter Full**: ID `1860`
  - URL: https://grafana.com/grafana/dashboards/1860
  - 用于监控 Linux 主机的完整仪表板

### VMware 仪表板
- **VMware vSphere - Overview**: ID `11243`
  - URL: https://grafana.com/grafana/dashboards/11243
  - VMware 环境总览仪表板

### SNMP 仪表板
- **SNMP Stats**: ID `11169`
  - URL: https://grafana.com/grafana/dashboards/11169
  - 通用 SNMP 设备监控仪表板

### VictoriaMetrics 仪表板
- **VictoriaMetrics - cluster**: ID `11176`
  - URL: https://grafana.com/grafana/dashboards/11176
  - VictoriaMetrics 集群监控

- **VictoriaMetrics - vmagent**: ID `12683`
  - URL: https://grafana.com/grafana/dashboards/12683
  - vmagent 监控仪表板

## 如何导入仪表板

### 方法1: 通过 Grafana UI 导入
1. 登录 Grafana (http://localhost:3000)
2. 点击左侧菜单 "+" -> "Import"
3. 输入仪表板 ID 或上传 JSON 文件
4. 选择 VictoriaMetrics 数据源
5. 点击 "Import"

### 方法2: 将 JSON 文件放置到此目录
1. 从 Grafana 官网下载仪表板 JSON 文件
2. 将 JSON 文件复制到此目录
3. Grafana 会自动加载新的仪表板(约10秒后)

## 自定义仪表板

你可以在 Grafana UI 中创建自定义仪表板,然后:
1. 点击仪表板右上角的设置图标
2. 选择 "JSON Model"
3. 复制 JSON 内容
4. 保存为 `.json` 文件到此目录
