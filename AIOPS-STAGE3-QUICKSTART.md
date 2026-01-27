# AIOps 第三阶段快速启动指南

本指南将帮助你快速启动和验证 AIOps 第三阶段的自动化分析系统。

## 前置条件

确保你已经完成了第一和第二阶段的部署：

```bash
# 检查 Stage 1 和 Stage 2 服务
docker ps | grep -E "victoriametrics|loki|tempo|neo4j"
```

如果这些服务都在运行，你可以继续。

## 🚀 快速启动（3 步完成）

### 步骤 1: 启动服务

```bash
cd /opt/Monitoring-deployment-main
./scripts/start-aiops.sh
```

这个脚本会自动：
- ✅ 检查前置依赖
- ✅ 构建 Docker 镜像
- ✅ 启动所有 Stage 3 服务
- ✅ 等待服务就绪
- ✅ 显示访问信息

### 步骤 2: 验证服务

```bash
./scripts/test-aiops.sh
```

这个脚本会自动：
- ✅ 检查所有容器状态
- ✅ 验证服务端点
- ✅ 检查 Kafka Topics
- ✅ 验证 Redis 和 Neo4j
- ✅ 测试数据流

### 步骤 3: 监控数据流

等待 1-2 分钟让系统收集数据，然后查看 Kafka 消息：

```bash
# 查看指标数据
docker exec -it kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic aiops.metrics --from-beginning --timeout-ms 5000

# 查看异常数据
docker exec -it kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic aiops.anomalies --from-beginning --timeout-ms 5000
```

## 📊 访问界面

启动成功后，你可以访问以下界面：

| 服务 | URL | 用户名 | 密码 |
|------|-----|--------|------|
| Grafana | http://localhost:3000 | admin | admin |
| Neo4j Browser | http://localhost:7474 | neo4j | password123 |
| Flink UI | http://localhost:8081 | - | - |

## 🔍 验证功能

### 1. 查看 Grafana 注解

1. 打开 Grafana: http://localhost:3000
2. 进入任何仪表盘
3. 点击时间轴上方的 "Annotations"
4. 查找 AIOps 相关的注解

### 2. 查看 Neo4j 图谱

1. 打开 Neo4j Browser: http://localhost:7474
2. 登录后执行查询：
   ```cypher
   MATCH (n) RETURN n
   ```
3. 查看设备和它们的关系

### 3. 查看服务日志

```bash
# 查看数据摄入日志
docker-compose -f docker-compose-aiops.yml logs -f data-ingestion

# 查看异常检测日志
docker-compose -f docker-compose-aiops.yml logs -f anomaly-detection

# 查看根因分析日志
docker-compose -f docker-compose-aiops.yml logs -f root-cause-analysis

# 查看洞察与行动日志
docker-compose -f docker-compose-aiops.yml logs -f insights-action
```

## 🧪 模拟异常测试

如果你想测试异常检测功能，可以：

### 方法 1: 生成测试数据

```bash
# 推送高 CPU 使用率的测试数据
echo '{"metric_name":"cpu_usage","labels":{"instance":"test-server"},"values":[[1234567890,95.0]],"timestamp":"2026-01-27T12:00:00"}' | \
  docker exec -i kafka kafka-console-producer --bootstrap-server localhost:9092 --topic aiops.metrics
```

### 方法 2: 生成追踪数据

```bash
# 请求 hello-app 生成追踪
for i in {1..50}; do
  curl http://localhost:5001/
  sleep 0.2
done
```

## 🛠 常用命令

### 启动/停止

```bash
# 启动 Stage 3
./scripts/start-aiops.sh

# 停止 Stage 3
./scripts/stop-aiops.sh

# 启动所有阶段（1+2+3）
docker-compose -f docker-compose.yaml \
              -f docker-compose-traces.yml \
              -f docker-compose-aiops.yml \
              up -d --build
```

### 查看状态

```bash
# 查看服务状态
docker-compose -f docker-compose-aiops.yml ps

# 查看所有日志
docker-compose -f docker-compose-aiops.yml logs

# 查看特定服务日志
docker-compose -f docker-compose-aiops.yml logs data-ingestion
```

### Kafka 操作

```bash
# 列出所有 Topics
docker exec -it kafka kafka-topics --list --bootstrap-server localhost:9092

# 创建 Topic
docker exec -it kafka kafka-topics --create --bootstrap-server localhost:9092 --topic test-topic

# 消费 Topic
docker exec -it kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic aiops.metrics --from-beginning

# 查看Topic 详情
docker exec -it kafka kafka-topics --describe --bootstrap-server localhost:9092 --topic aiops.metrics
```

### Redis 操作

```bash
# 连接 Redis
docker exec -it redis redis-cli

# 查看所有键
docker exec -it redis redis-cli KEYS '*'

# 查看特定键
docker exec -it redis redis-cli GET "your-key"
```

## 📁 重要文件

| 文件/目录 | 说明 |
|-----------|------|
| `docker-compose-aiops.yml` | Stage 3 服务定义 |
| `scripts/aiops/data_ingestion.py` | 数据摄入服务 |
| `scripts/aiops/anomaly_detection.py` | 异常检测服务 |
| `scripts/aiops/root_cause_analysis.py` | 根因分析服务 |
| `scripts/aiops/insights_action.py` | 洞察与行动服务 |
| `scripts/aiops/runbooks/` | 自动化 Runbook |
| `scripts/aiops/config/aiops.yml` | AIOps 配置文件 |
| `scripts/start-aiops.sh` | 启动脚本 |
| `scripts/stop-aiops.sh` | 停止脚本 |
| `scripts/test-aiops.sh` | 测试脚本 |

## 🔧 配置调整

### 调整数据采集间隔

编辑 `docker-compose-aiops.yml`：

```yaml
data-ingestion:
  environment:
    - INGESTION_INTERVAL=60s  # 从 30s 改为 60s
```

### 调整异常检测阈值

编辑 `docker-compose-aiops.yml`：

```yaml
anomaly-detection:
  environment:
    - ANOMALY_THRESHOLD=3.0  # 从 2.0 改为 3.0
```

### 启用自动 Runbook 执行

编辑 `docker-compose-aiops.yml`：

```yaml
insights-action:
  environment:
    - AUTO_EXECUTE_RUNBOOK=true  # 自动执行匹配的 Runbook
```

修改后需要重启服务：

```bash
docker-compose -f docker-compose-aiops.yml restart <service-name>
```

## 🐛 故障排查

### 问题：服务启动失败

```bash
# 查看详细日志
docker-compose -f docker-compose-aiops.yml logs

# 检查端口占用
netstat -tulpn | grep -E '9092|6379|7474|7687|8081'

# 重启服务
docker-compose -f docker-compose-aiops.yml restart
```

### 问题：没有数据流入 Kafka

```bash
# 检查数据摄入服务日志
docker-compose -f docker-compose-aiops.yml logs data-ingestion

# 确认前置服务运行
docker ps | grep -E "victoriametrics|loki|tempo"
```

### 问题：异常未检测到

```bash
# 检查异常检测服务日志
docker-compose -f docker-compose-aiops.yml logs anomaly-detection

# 手动推送测试数据
echo '{"metric_name":"cpu_usage","labels":{"instance":"test-server"},"values":[[1234567890,95.0]]}' | \
  docker exec -i kafka kafka-console-producer --bootstrap-server localhost:9092 --topic aiops.metrics
```

## 📚 进一步学习

- **完整文档:** 查看 `docs/AIOPS-TRACING-PROTOTYPE.md`
- **配置说明:** 查看 `scripts/aiops/config/aiops.yml`
- **Runbook 示例:** 查看 `scripts/aiops/runbooks/` 目录

## 🎉 下一步

1. **监控系统运行:** 定期查看服务日志和 Grafana 仪表盘
2. **优化配置:** 根据实际业务调整检测参数和阈值
3. **添加规则:** 创建自定义的异常检测规则
4. **扩展 Runbook:** 添加更多自动化修复剧本
5. **集成告警:** 配置告警通知和响应流程

## 💡 提示

- 首次启动可能需要几分钟来下载 Docker 镜像
- 系统需要 1-2 分钟才能开始收集和检测数据
- 查看 Grafana 注解来确认 RCA 结果是否被推送
- 定期检查服务日志以确保系统正常运行

## 🆘 获取帮助

如果遇到问题：

1. 查看服务日志
2. 运行测试脚本: `./scripts/test-aiops.sh`
3. 查看完整文档: `docs/AIOPS-TRACING-PROTOTYPE.md`
4. 检查 GitHub Issues

---

祝你使用愉快！🚀