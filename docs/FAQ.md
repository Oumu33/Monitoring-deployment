# 常见问题 FAQ

## 部署相关

### Q1: 系统最低配置要求是什么？

**A:**
- CPU: 2 核心以上
- 内存: 4GB 以上（推荐 8GB）
- 磁盘: 20GB 以上可用空间
- 操作系统: Linux (Ubuntu 20.04+, CentOS 7+, Debian 10+)
- Docker: 20.10+
- Docker Compose: 2.0+

### Q2: 如何修改服务端口？

**A:** 编辑 `docker-compose.yaml` 文件，修改对应服务的 `ports` 配置:

```yaml
services:
  grafana:
    ports:
      - "3001:3000"  # 将 Grafana 端口改为 3001
```

然后重启服务: `docker-compose restart grafana`

### Q3: 首次部署后无法访问 Grafana？

**A:** 检查以下几点:
1. 确认服务已启动: `docker-compose ps`
2. 检查防火墙: `sudo ufw allow 3000` (Ubuntu) 或 `sudo firewall-cmd --add-port=3000/tcp --permanent` (CentOS)
3. 查看日志: `docker-compose logs grafana`

### Q4: 如何修改 Grafana 管理员密码？

**A:**
1. 编辑 `.env` 文件，修改 `GRAFANA_ADMIN_PASSWORD`
2. 重启 Grafana: `docker-compose restart grafana`
3. 或者在 Grafana UI 中修改: Profile -> Change Password

## 监控采集相关

### Q5: 添加了监控目标但没有数据？

**A:** 按以下步骤排查:

1. 检查 vmagent 采集状态:
   ```bash
   curl http://localhost:8429/targets
   ```

2. 确认目标地址可访问:
   ```bash
   curl http://目标IP:端口/metrics
   ```

3. 检查 vmagent 日志:
   ```bash
   docker-compose logs vmagent
   ```

4. 验证配置文件语法:
   ```bash
   make config-check
   ```

### Q6: SNMP 监控无法采集数据？

**A:** 常见问题:

1. **交换机 SNMP 未启用**: 登录交换机启用 SNMP v2c 或 v3
2. **Community string 错误**: 检查 `prometheus.yml` 中的 community 配置
3. **防火墙阻拦**: 确保监控服务器可以访问交换机的 UDP 161 端口
4. **SNMP 配置文件缺失**: 下载官方配置文件:
   ```bash
   make download-snmp-config
   ```

测试 SNMP 连接:
```bash
snmpwalk -v2c -c public 交换机IP sysDescr
```

### Q7: VMware Exporter 报错 "Permission denied"？

**A:**
1. 确认 vCenter 用户有只读权限
2. 检查 `.env` 文件中的 VMware 配置:
   - VSPHERE_HOST
   - VSPHERE_USER
   - VSPHERE_PASSWORD
3. 如果使用自签名证书，设置 `VSPHERE_IGNORE_SSL=True`

## 告警相关

### Q8: 告警规则不触发？

**A:** 检查步骤:

1. 确认规则已加载:
   ```bash
   curl http://localhost:8880/api/v1/rules
   ```

2. 查看规则评估状态:
   访问 http://localhost:8880 查看 vmalert UI

3. 检查 vmalert 日志:
   ```bash
   docker-compose logs vmalert
   ```

4. 手动测试查询:
   在 VictoriaMetrics UI (http://localhost:8428) 中测试告警规则的 PromQL 表达式

### Q9: 告警通知不发送？

**A:**

1. 检查 Alertmanager 状态:
   ```bash
   curl http://localhost:9093/-/healthy
   ```

2. 查看当前告警:
   ```bash
   curl http://localhost:9093/api/v1/alerts
   ```

3. 检查邮件配置(SMTP):
   - 确认 SMTP 服务器地址正确
   - 验证用户名和密码
   - 检查防火墙是否阻拦 SMTP 端口 (25/465/587)

4. 发送测试告警:
   ```bash
   make test-alert
   ```

### Q10: 如何临时屏蔽某个告警？

**A:** 在 Alertmanager UI (http://localhost:9093) 中:
1. 点击 "Silences"
2. 点击 "New Silence"
3. 填写匹配条件（如 `alertname=HostDown`）
4. 设置静默时间
5. 点击 "Create"

## 性能优化

### Q11: VictoriaMetrics 占用内存过高？

**A:** 优化方案:

1. 限制内存使用:
   在 `docker-compose.yaml` 中添加:
   ```yaml
   victoriametrics:
     command:
       - "--memory.allowedPercent=60"
   ```

2. 减少数据保留时间:
   ```yaml
   - "--retentionPeriod=6"  # 从12个月改为6个月
   ```

3. 减少采集频率:
   编辑 `config/vmagent/prometheus.yml`，增大 `scrape_interval`

### Q12: 如何减少磁盘占用？

**A:**

1. 调整数据保留策略（见 Q11）
2. 定期清理旧备份:
   ```bash
   find ./backup -type d -mtime +30 -exec rm -rf {} \;
   ```
3. 压缩 Docker 日志:
   在 `docker-compose.yaml` 中添加:
   ```yaml
   logging:
     driver: "json-file"
     options:
       max-size: "10m"
       max-file: "3"
   ```

### Q13: 大量监控目标导致 vmagent 卡顿？

**A:**

1. 使用文件服务发现代替 static_configs
2. 增加 vmagent 内存限制:
   ```yaml
   vmagent:
     deploy:
       resources:
         limits:
           memory: 2G
   ```
3. 分批采集，设置不同的 `scrape_interval`
4. 对不重要的目标使用更长的采集间隔

## 数据管理

### Q14: 如何迁移到新服务器？

**A:**

1. 在旧服务器上备份:
   ```bash
   ./scripts/backup.sh
   ```

2. 将备份文件和配置复制到新服务器

3. 在新服务器上部署:
   ```bash
   git clone <repository>
   cd Monitoring-deployment
   make setup
   ```

4. 恢复数据:
   ```bash
   ./scripts/restore.sh /path/to/backup
   ```

### Q15: 如何删除特定时间范围的数据？

**A:** VictoriaMetrics 支持删除指定时间范围的数据:

```bash
curl -X POST 'http://localhost:8428/api/v1/admin/tsdb/delete_series?match[]={job="old-job"}&start=2024-01-01T00:00:00Z&end=2024-01-31T23:59:59Z'
```

### Q16: 如何查看当前数据大小？

**A:**

```bash
# 查看 Docker volume 大小
docker run --rm -v monitoring-deployment_vmdata:/data alpine du -sh /data

# 或使用 Makefile
make show-metrics-count
```

## 安全相关

### Q17: 如何启用 HTTPS？

**A:** 推荐使用 Nginx 或 Traefik 反向代理:

1. 使用 Nginx 示例:
   ```nginx
   server {
       listen 443 ssl;
       server_name monitoring.example.com;

       ssl_certificate /path/to/cert.pem;
       ssl_certificate_key /path/to/key.pem;

       location / {
           proxy_pass http://localhost:3000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

2. 使用 Let's Encrypt 自动证书:
   ```bash
   certbot --nginx -d monitoring.example.com
   ```

### Q18: 如何限制访问 IP？

**A:**

方法 1 - 防火墙:
```bash
# 只允许特定 IP 访问
sudo ufw allow from 192.168.1.0/24 to any port 3000
```

方法 2 - Nginx 反向代理:
```nginx
location / {
    allow 192.168.1.0/24;
    deny all;
    proxy_pass http://localhost:3000;
}
```

### Q19: 如何修改 SNMP community string？

**A:** 在 `config/vmagent/prometheus.yml` 中修改:

```yaml
params:
  module: [if_mib]
  auth: [my_community]  # 修改这里
```

然后在 `config/snmp-exporter/snmp.yml` 中添加认证配置（或使用 SNMPv3）。

## 故障恢复

### Q20: 服务突然停止运行怎么办？

**A:**

1. 查看服务状态:
   ```bash
   docker-compose ps
   ```

2. 查看停止原因:
   ```bash
   docker-compose logs <service-name>
   ```

3. 尝试重启:
   ```bash
   docker-compose restart
   ```

4. 如果重启失败，检查磁盘空间:
   ```bash
   df -h
   ```

5. 检查是否 OOM (内存不足):
   ```bash
   dmesg | grep -i "out of memory"
   ```

### Q21: 数据丢失如何恢复？

**A:**

1. 从最近的备份恢复:
   ```bash
   ./scripts/restore.sh ./backup/最新备份目录
   ```

2. 如果没有备份，检查 Docker volume 是否还存在:
   ```bash
   docker volume ls | grep monitoring
   ```

3. 如果 volume 还在，只需重新启动服务:
   ```bash
   docker-compose up -d
   ```

### Q22: 误删除了 Docker volume 怎么办？

**A:**

不幸的是，Docker volume 一旦删除无法恢复。这就是为什么要定期备份的原因。建议:

1. 设置定时备份任务:
   ```bash
   # 添加到 crontab
   0 2 * * * cd /opt/Monitoring && ./scripts/backup.sh
   ```

2. 异地备份:
   将备份文件同步到其他服务器或云存储

## 升级相关

### Q23: 如何升级到新版本？

**A:**

1. 备份当前数据:
   ```bash
   make backup
   ```

2. 更新代码:
   ```bash
   git pull origin main
   ```

3. 更新 Docker 镜像:
   ```bash
   make update-images
   ```

4. 重启服务:
   ```bash
   make restart
   ```

5. 验证升级:
   ```bash
   make health
   ```

### Q24: 升级后配置文件冲突怎么办？

**A:**

1. 查看差异:
   ```bash
   git diff config/
   ```

2. 手动合并配置:
   - 保留自定义配置
   - 应用新版本的改进

3. 或者重命名旧配置，使用新配置:
   ```bash
   mv config config.old
   git checkout config
   # 然后手动迁移自定义配置
   ```

## 其他问题

### Q25: 如何导出 Grafana 仪表板？

**A:**

方法 1 - 通过 UI:
1. 打开仪表板
2. 点击设置图标 -> JSON Model
3. 复制 JSON 内容并保存

方法 2 - 通过 API:
```bash
curl -H "Authorization: Bearer <API_KEY>" \
  http://localhost:3000/api/dashboards/uid/<DASHBOARD_UID> | \
  jq '.dashboard' > dashboard.json
```

### Q26: 如何批量导入 Grafana 仪表板？

**A:**

1. 将仪表板 JSON 文件放到 `config/grafana/dashboards/` 目录
2. Grafana 会自动加载（约10秒后）
3. 或者重启 Grafana: `make restart-grafana`

### Q27: 监控系统本身需要监控吗？

**A:** 是的！系统已内置监控系统自身的告警规则（`config/vmalert/alerts/system-alerts.yml`），包括:
- VictoriaMetrics 宕机
- vmagent 宕机
- vmalert 宕机
- Alertmanager 宕机
- 存储空间不足
- 采集缓冲区满

建议将这些告警发送到独立的通知渠道。

### Q28: 如何查看完整的配置文档？

**A:** 查看以下文档:
- README.md - 完整部署文档
- docs/SWITCH-MONITORING.md - 交换机监控详细配置
- examples/ - 各种配置示例
- 官方文档:
  - [VictoriaMetrics](https://docs.victoriametrics.com/)
  - [vmagent](https://docs.victoriametrics.com/vmagent.html)
  - [vmalert](https://docs.victoriametrics.com/vmalert.html)

---

## 需要更多帮助？

如果以上FAQ没有解决你的问题:

1. 查看 [GitHub Issues](https://github.com/Oumu33/Monitoring-deployment/issues)
2. 提交新的 Issue 描述问题
3. 提供必要的日志和配置信息

**日志收集命令:**
```bash
# 收集所有服务日志
docker-compose logs > monitoring-logs.txt

# 执行健康检查
./scripts/health-check.sh > health-check.txt

# 打包日志和配置
tar czf monitoring-debug.tar.gz monitoring-logs.txt health-check.txt config/
```
