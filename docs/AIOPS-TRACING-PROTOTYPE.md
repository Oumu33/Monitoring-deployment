# AIOps 链路追踪原型 - `feature/aiops-prototype` 分支文档

本文档详细说明了在 `feature/aiops-prototype` 分支中引入的新增功能与修改，旨在通过集成分布式链路追踪（Traces）与现有的指标（Metrics）和日志（Logs）监控技术栈，为AIOps解决方案奠定基础。

## 1. 项目目标

该分支的主要目标是扩展现有的监控部署，使其包含：
-   **分布式链路追踪 (Traces):** 使用 Grafana Tempo 作为存储后端，OpenTelemetry Collector 负责数据采集。
-   **追踪数据生成:** 一个通过 OpenTelemetry 插桩的示例微服务 (`hello-app`)，用于生成追踪数据。
-   **跨可观测性集成:** 在 Grafana 内部联通指标、日志和链路，以增强关联分析和故障排查能力。

## 2. 新增组件介绍

### 2.1. Grafana Tempo

-   **用途:** 一个高吞吐、低成本的分布式链路追踪后端。它负责存储从 OpenTelemetry Collector 接收到的追踪数据。
-   **配置:** 在 `docker-compose-traces.yml` 文件中定义。
-   **Grafana 集成:** 通过 `config/grafana/provisioning/datasources/tempo.yml` 文件在 Grafana 中自动配置为数据源，实现了链路的可视化和高级联动功能（例如，从链路跳转到日志，基于指标数据的服务拓扑图等）。

### 2.2. OpenTelemetry Collector

-   **用途:** 一个与供应商无关的代理，用于接收、处理和导出遥测数据（追踪、指标、日志）。在此设置中，它接收来自应用的 OTLP 格式的追踪数据，并将其转发到 Tempo。
-   **配置:** 在 `docker-compose-traces.yml` 中定义，并通过 `config/otel/otel-collector.yml` 进行配置。

### 2.3. 示例应用 (`hello-app`)

-   **用途:** 一个简单的 Python Flask 微服务，通过 OpenTelemetry 进行了插桩，用于演示应用如何生成并导出追踪数据。
-   **位置:** `services/hello-app/` 目录。
-   **组件:** `app.py` (带 OTel 插桩的 Flask 应用), `requirements.txt`, `Dockerfile`。
-   **追踪导出:** 被配置为将追踪数据导出到 `otel-collector` 服务。

## 3. 文件变更详情

### 3.1. 新增文件

-   `docker-compose-traces.yml`: 定义了 `tempo`, `otel-collector`, 和 `hello-app` 服务。
-   `config/otel/otel-collector.yml`: OpenTelemetry Collector 的配置文件。
-   `config/grafana/provisioning/datasources/tempo.yml`: 用于 Grafana 自动配置 Tempo 数据源的文件。
-   `services/hello-app/`:
    -   `app.py`: 已插桩的 Flask 应用代码。
    -   `requirements.txt`: `hello-app` 的 Python 依赖。
    -   `Dockerfile`: 用于构建 `hello-app` 镜像的 Dockerfile。

### 3.2. 修改的文件

-   `docker-compose.yaml`:
    -   **`redfish-exporter` 服务:** 由于原镜像 `jenningsloy318/redfish_exporter:latest` 存在持续的拉取权限问题，已将其替换为 `gportal/redfish_exporter:latest`。
    -   **`promtail` 服务:** 为了解决容器启动时出现的 `read-only file system`（只读文件系统）错误，`network-device-logs` 的卷挂载配置已从只读（`:ro`）更新为可读写（移除了 `:ro` 标记）。

## 4. 部署与验证

### 4.1. 先决条件

-   **Docker 与 Docker Compose:** 确保已安装并正在运行。
-   **网络连接:** 稳定的 Docker Hub 网络连接（或已正确配置的国内镜像加速器）对于首次拉取镜像是至关重要的。
-   **干净的 Docker 环境:** 如果遇到无法解决的持续性问题，请考虑进行一次彻底的环境清理（见下方“已知问题”）。

### 4.2. 如何启动服务

进入项目根目录，并运行以下命令。该命令将构建 `hello-app` 镜像并启动所有在两个 compose 文件中定义的服务。

```bash
docker-compose -f docker-compose.yaml -f docker-compose-traces.yml up -d --build
```

### 4.3. 如何生成追踪数据

当 `hello-app` 服务启动并运行后（暴露在 `localhost:5001`），通过访问其端点来生成追踪数据：

```bash
curl http://localhost:5001/
```
每一次 `curl` 请求都会生成一条新的 Trace。

### 4.4. 如何在 Grafana 中验证

1.  在浏览器中打开 Grafana (通常是 `http://localhost:3000`)。
2.  登录 (默认: `admin/admin`)。
3.  进入左侧菜单的 **"Explore"** (指南针图标) 视图。
4.  在左上角的数据源下拉菜单中，选择 **"Tempo"** 数据源。
5.  点击 **"Run query"** 按钮，即可查看最近的追踪数据。您应该能看到由 `hello-app` 服务（服务名 `hello-app`，操作名 `index-request`）生成的追踪。
6.  您可以点击任意一条追踪，查看其包含的所有 Span 和详细信息。

## 5. 已知问题与故障排查

### 5.1. `docker-compose up` 过程中持续出现网络 `EOF` 错误

这表明访问 Docker Hub 的网络连接不稳定。如果 `dkturbo` 工具（用于配置镜像加速器）未能完全解决此问题，则需要手动干预。

**推荐操作:**
对您的 Docker 环境进行一次彻底清理，以消除任何可能存在的损坏状态，然后重试。

```bash
# 1. 停止并移除本项目定义的所有服务
docker-compose -f docker-compose.yaml -f docker-compose-traces.yml down --volumes

# 2. **关键: 清理所有未使用的 Docker 数据**
#    此命令会移除所有已停止的容器、未使用的网络、悬空镜像以及**所有未被使用的数据卷**。
#    请谨慎操作，因为它会清理所有与本项目无关的数据。
docker system prune -a -f --volumes

# 3. 重启 Docker 服务 (如果 prune 命令没有自动重启的话)
systemctl restart docker

# 4. 重新运行部署命令
docker-compose -f docker-compose.yaml -f docker-compose-traces.yml up -d --build
```

### 5.2. `promtail` 服务出现 `KeyError: 'ContainerConfig'` 或 `read-only file system` 错误

这些错误表明 `promtail` 容器或其在 Docker 元数据中的配置已损坏。执行上述的 `docker system prune` 命令应该可以解决这些问题。

---

本文档为 AIOps 链路追踪原型提供了一份全面的指南。



---



# 阶段二: 构建关系图谱



在完成了第一阶段的数据基础建设后，第二阶段的目标是引入图数据库，将监控对象的实体和它们之间的关系进行结构化存储。



## 新增组件 (阶段二)



### Neo4j (图数据库)



-   **用途:** 存储基础设施的实体关系图谱。节点（Nodes）代表设备（如交换机、服务器），边（Edges）代表它们之间的关系（如 `CONNECTS_TO`）。

-   **配置:** 在新增的 `docker-compose-aiops.yml` 文件中定义。

-   **访问:**

    -   **Web UI:** `http://localhost:7474`

    -   **Bolt 连接:** `bolt://localhost:7687` (客户端使用)

-   **登录:** 默认用户名 `neo4j`，密码 `password123`。



### graph-builder (图谱构建器)



-   **用途:** 一个一次性运行的脚本，负责从项目的配置文件 (`devices.yml`) 和动态数据文件 (`topology.json`) 中读取信息，并将其写入 Neo4j 数据库。

-   **配置:** 在 `docker-compose-aiops.yml` 中定义，作为一个依赖 `neo4j` 的服务。

-   **位置:** `scripts/aiops/`



## 如何启动 (包含阶段二)



要启动包括 Neo4j 在内的所有服务，请在项目根目录运行以下命令，将所有 compose 文件都包含进来：



```bash

# 确保您已解决了网络问题并可以正常拉取镜像

docker-compose -f docker-compose.yaml -f docker-compose-traces.yml -f docker-compose-aiops.yml up -d --build

```



`graph-builder` 服务在成功将数据写入 Neo4j 后会自动退出。



## 如何验证图谱数据



1.  打开 Neo4j 浏览器 `http://localhost:7474`。

2.  使用默认凭据登录 (`neo4j` / `password123`)。首次登录可能需要修改密码，可再次修改为 `password123`。

3.  在顶部的查询框中，输入以下 [Cypher](https://neo4j.com/developer/cypher/) 查询语句，并点击执行按钮（或按 Ctrl+Enter）：



    ```cypher

    MATCH (n) RETURN n

    ```



4.  如果 `graph-builder` 运行成功，您应该能在右侧的图表中看到从 `devices.yml` 导入的设备节点。如果 `topology.json` 也存在，您还能看到连接这些节点的 `CONNECTS_TO` 关系。

---

# 阶段三: 自动化分析（AIOps核心）

在完成了第一阶段的数据基础建设（Metrics + Logs + Traces）和第二阶段的图谱关系构建后，第三阶段的目标是实现自动化根因分析（ARCA）与主动异常检测，让系统从单纯的数据展示，升级为主动识别问题、分析原因并输出可落地的运维洞察。

## 核心目标

- 实现实时数据摄入与预处理
- 实现多维度异常检测（统计学方法 + 规则引擎）
- 实现图谱依赖分析与因果推断
- 实现根因定位与自动化修复建议
- 提供可落地的运维洞察和行动建议

## 新增组件 (阶段三)

### 基础设施组件

#### Apache Kafka
- **用途:** 高吞吐分布式消息系统，用于实时数据流传输
- **配置:** 在 `docker-compose-aiops.yml` 中定义
- **访问:** `localhost:9092`
- **Topics:**
  - `aiops.metrics` - 指标数据
  - `aiops.logs` - 日志数据
  - `aiops.traces` - 链路数据
  - `aiops.events` - 事件数据
  - `aiops.anomalies` - 异常检测结果
  - `aiops.rca_results` - 根因分析结果
  - `aiops.actions` - 执行的行动

#### Zookeeper
- **用途:** Kafka 的依赖服务，用于协调和配置管理
- **配置:** 在 `docker-compose-aiops.yml` 中定义
- **访问:** `localhost:2181`

#### Redis
- **用途:** 内存数据存储，用于缓存和状态管理
- **配置:** 在 `docker-compose-aiops.yml` 中定义
- **访问:** `localhost:6379`

#### Apache Flink
- **用途:** 流处理引擎，用于实时数据处理
- **配置:** 在 `docker-compose-aiops.yml` 中定义
- **组件:**
  - `flink-jobmanager` - 作业管理器
  - `flink-taskmanager` - 任务管理器
- **访问:** `http://localhost:8081` (Flink Web UI)

### 核心服务组件

#### data-ingestion (数据摄入服务)
- **用途:** 实时从 VictoriaMetrics、Loki、Tempo 采集数据并推送到 Kafka
- **配置:** `scripts/aiops/data_ingestion.py`
- **功能:**
  - 从 VictoriaMetrics 采集系统指标（CPU、内存、磁盘、网络）
  - 从 Loki 采集错误和警告日志
  - 从 Tempo 采集分布式追踪数据
  - 将数据格式化并推送到对应的 Kafka Topics

#### anomaly-detection (异常检测服务)
- **用途:** 实时检测数据中的异常
- **配置:** `scripts/aiops/anomaly_detection.py`
- **检测方法:**
  - **统计学方法:**
    - ARIMA - 时间序列异常检测
    - EWMA - 指数加权移动平均
    - Z-Score - 标准分数检测
  - **规则引擎:**
    - CPU > 90% 持续 5 分钟
    - 内存 > 95%
    - 磁盘 > 90%
  - **机器学习:**
    - Isolation Forest - 孤立森林算法
    - K-Means - 聚类分析
- **输出:** 将检测到的异常推送到 `aiops.anomalies` Topic

#### root-cause-analysis (根因分析服务)
- **用途:** 基于图谱和事件关联进行根因定位
- **配置:** `scripts/aiops/root_cause_analysis.py`
- **功能:**
  - **图谱依赖分析:**
    - 查询上游/下游依赖关系
    - 计算最短路径
    - 分析中心性指标（度中心性、介数中心性、接近中心性）
    - 发现关键路径
  - **因果推断:**
    - 事件关联（基于时间和空间的关联）
    - 异常传播链构建
    - 启发式规则推断
  - **根因定位:**
    - 基于中心性评分
    - 基于异常严重程度
    - 基于传播影响范围
- **输出:** 将根因分析结果推送到 `aiops.rca_results` Topic

#### insights-action (洞察与行动服务)
- **用途:** 生成可落地的洞察和自动化行动建议
- **配置:** `scripts/aiops/insights_action.py`
- **功能:**
  - **Grafana 集成:**
    - 创建注解（Annotations）
    - 推送 RCA 结果到 Grafana 仪表盘
  - **告警丰富化:**
    - 向 Alertmanager 告警添加根因信息
    - 提供上下文和修复建议
  - **自动化 Runbooks:**
    - 匹配预定义的 Runbook
    - 执行自动化修复脚本
    - 支持命令、HTTP 请求、脚本执行
- **输出:** 将行动建议推送到 `aiops.actions` Topic

## Runbook 配置

Runbook 是预定义的自动化修复剧本，存储在 `scripts/aiops/runbooks/` 目录：

### 示例 Runbooks

#### cpu_high.yml
- **触发条件:** CPU 使用率 > 90%
- **执行步骤:**
  1. 检查 top 进程
  2. 检查负载平均值
  3. 检查 CPU 核心数
  4. 记录 CPU 使用快照

#### memory_high.yml
- **触发条件:** 内存使用率 > 95%
- **执行步骤:**
  1. 检查内存使用情况
  2. 检查交换分区使用
  3. 检查内存消耗最大的进程
  4. 清理 apt 缓存
  5. 清理页面缓存

#### disk_high.yml
- **触发条件:** 磁盘使用率 > 90%
- **执行步骤:**
  1. 检查磁盘空间
  2. 查找大文件（>100MB）
  3. 清理旧日志（7+ 天）
  4. 清理旧 journal 日志
  5. 清理 apt 缓存和未使用的包

## 如何启动 (包含阶段三)

### 1. 启动前检查

确保第一和第二阶段的服务正在运行：

```bash
# 检查 VictoriaMetrics
docker ps | grep victoriametrics

# 检查 Loki
docker ps | grep loki

# 检查 Tempo
docker ps | grep tempo

# 检查 Neo4j
docker ps | grep neo4j
```

### 2. 使用启动脚本（推荐）

使用提供的启动脚本可以自动完成所有步骤：

```bash
# 启动 AIOps 第三阶段服务
./scripts/start-aiops.sh
```

启动脚本会自动：
- 检查前置依赖
- 构建 Docker 镜像
- 启动所有 Stage 3 服务
- 等待服务就绪
- 显示访问信息和命令

### 3. 手动启动

如果需要手动启动，请执行：

```bash
# 构建 Stage 3 镜像
docker-compose -f docker-compose-aiops.yml build

# 启动 Stage 3 服务
docker-compose -f docker-compose-aiops.yml up -d

# 查看服务状态
docker-compose -f docker-compose-aiops.yml ps
```

### 4. 完整启动（包含所有阶段）

要一次性启动所有三个阶段的服务：

```bash
docker-compose -f docker-compose.yaml \
              -f docker-compose-traces.yml \
              -f docker-compose-aiops.yml \
              up -d --build
```

## 如何验证

### 1. 使用测试脚本（推荐）

```bash
# 运行自动化测试
./scripts/test-aiops.sh
```

测试脚本会检查：
- 所有容器是否正在运行
- 服务端点是否可访问
- Kafka Topics 是否已创建
- Redis 和 Neo4j 连接是否正常
- 数据流是否正常工作

### 2. 手动验证

#### 检查服务状态

```bash
# 查看 Stage 3 服务状态
docker-compose -f docker-compose-aiops.yml ps
```

#### 检查服务日志

```bash
# 查看数据摄入服务日志
docker-compose -f docker-compose-aiops.yml logs -f data-ingestion

# 查看异常检测服务日志
docker-compose -f docker-compose-aiops.yml logs -f anomaly-detection

# 查看根因分析服务日志
docker-compose -f docker-compose-aiops.yml logs -f root-cause-analysis

# 查看洞察与行动服务日志
docker-compose -f docker-compose-aiops.yml logs -f insights-action
```

#### 检查 Kafka Topics

```bash
# 列出所有 Topics
docker exec -it kafka kafka-topics --list --bootstrap-server localhost:9092

# 消费指标数据
docker exec -it kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic aiops.metrics --from-beginning

# 消费异常数据
docker exec -it kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic aiops.anomalies --from-beginning

# 消费 RCA 结果
docker exec -it kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic aiops.rca_results --from-beginning
```

#### 检查 Grafana

1. 打开 Grafana: `http://localhost:3000`
2. 查看 Annotations（注解）是否出现 AIOps 相关标记
3. 查看是否有新的告警被丰富化

#### 检查 Neo4j

1. 打开 Neo4j Browser: `http://localhost:7474`
2. 执行查询查看中心性指标：
   ```cypher
   MATCH (d:Device)
   OPTIONAL MATCH (d)-[r:CONNECTS_TO]->(other:Device)
   WITH d, count(r) AS degree
   RETURN d.name AS name, d.type AS type, degree
   ORDER BY degree DESC
   ```

### 3. 模拟异常测试

为了测试异常检测和根因分析功能，可以模拟一些异常情况：

#### 方法 1: 压力测试（需要额外的服务器）

```bash
# 在监控的服务器上运行压力测试
stress --cpu 8 --timeout 60s
```

这会产生高 CPU 使用率，应该能触发 CPU 异常检测。

#### 方法 2: 使用示例应用

```bash
# 频繁请求 hello-app 生成大量追踪数据
for i in {1..100}; do
  curl http://localhost:5001/
  sleep 0.1
done
```

#### 方法 3: 生成测试数据

可以通过 Kafka 直接推送测试数据：

```bash
# 推送测试指标数据
echo '{"metric_name":"cpu_usage","labels":{"instance":"test-server"},"values":[[1234567890,95.0]],"timestamp":"2026-01-27T12:00:00"}' | \
  docker exec -i kafka kafka-console-producer --bootstrap-server localhost:9092 --topic aiops.metrics
```

## 配置说明

### 环境变量

主要的环境变量在 `docker-compose-aiops.yml` 中配置：

- `KAFKA_BOOTSTRAP_SERVERS` - Kafka 服务器地址
- `REDIS_HOST` / `REDIS_PORT` - Redis 服务器配置
- `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` - Neo4j 数据库配置
- `DETECTION_WINDOW` - 异常检测窗口（秒）
- `ANOMALY_THRESHOLD` - 异常检测阈值
- `CORRELATION_WINDOW` - 事件关联窗口（秒）
- `MAX_GRAPH_DEPTH` - 最大图谱遍历深度

### 配置文件

#### scripts/aiops/config/aiops.yml

这是 AIOps 的主配置文件，包含所有组件的配置：

```yaml
data_ingestion:
  enabled: true
  interval: 30  # 数据采集间隔（秒）

anomaly_detection:
  enabled: true
  detection_window: 300  # 检测窗口（秒）
  anomaly_threshold: 2.0  # 异常阈值

root_cause_analysis:
  enabled: true
  correlation_window: 600  # 关联窗口（秒）
  max_graph_depth: 5  # 最大深度

insights_action:
  enabled: true
  runbooks:
    auto_execute: false  # 是否自动执行 Runbook
```

## 故障排查

### 问题 1: 服务无法启动

**症状:** `docker-compose up` 时某些服务启动失败

**解决方案:**
```bash
# 查看服务日志
docker-compose -f docker-compose-aiops.yml logs <service-name>

# 检查端口冲突
netstat -tulpn | grep -E '9092|6379|7474|7687|8081'

# 重启服务
docker-compose -f docker-compose-aiops.yml restart <service-name>
```

### 问题 2: Kafka Topics 未创建

**症状:** 查询 Topics 时找不到预期的 Topic

**解决方案:**
```bash
# 手动创建 Topics
docker exec -it kafka kafka-topics --create --bootstrap-server localhost:9092 --topic aiops.metrics
docker exec -it kafka kafka-topics --create --bootstrap-server localhost:9092 --topic aiops.logs
docker exec -it kafka kafka-topics --create --bootstrap-server localhost:9092 --topic aiops.traces
docker exec -it kafka kafka-topics --create --bootstrap-server localhost:9092 --topic aiops.anomalies
docker exec -it kafka kafka-topics --create --bootstrap-server localhost:9092 --topic aiops.rca_results
docker exec -it kafka kafka-topics --create --bootstrap-server localhost:9092 --topic aiops.actions
```

### 问题 3: 数据未流入 Kafka

**症状:** Kafka Topics 中没有数据

**解决方案:**
1. 检查数据摄入服务日志
2. 确认 VictoriaMetrics、Loki、Tempo 服务正在运行
3. 检查网络连接
4. 查看数据摄入服务的错误日志

```bash
docker-compose -f docker-compose-aiops.yml logs data-ingestion
```

### 问题 4: 异常未检测到

**症状:** 没有异常被推送到 `aiops.anomalies` Topic

**解决方案:**
1. 检查异常检测服务日志
2. 确认指标数据正在流入 `aiops.metrics` Topic
3. 调整异常检测阈值
4. 检查规则引擎配置

```bash
docker-compose -f docker-compose-aiops.yml logs anomaly-detection
```

### 问题 5: 根因分析未执行

**症状:** 没有 RCA 结果被推送到 `aiops.rca_results` Topic

**解决方案:**
1. 确认有异常数据在 `aiops.anomalies` Topic 中
2. 检查是否有多个相关异常（需要至少 2 个相关异常才触发 RCA）
3. 检查 Neo4j 连接
4. 查看根因分析服务日志

```bash
docker-compose -f docker-compose-aiops.yml logs root-cause-analysis
```

### 问题 6: Runbook 未执行

**症状:** 匹配的 Runbook 没有被自动执行

**解决方案:**
1. 检查 `auto_execute` 配置
2. 确认 Runbook 文件存在且格式正确
3. 查看 Runbook 匹配日志
4. 检查 Runbook 执行权限

```bash
docker-compose -f docker-compose-aiops.yml logs insights-action
```

## 停止服务

### 停止第三阶段服务

```bash
# 使用停止脚本（推荐）
./scripts/stop-aiops.sh

# 或手动停止
docker-compose -f docker-compose-aiops.yml down
```

### 停止所有服务

```bash
docker-compose -f docker-compose.yaml \
              -f docker-compose-traces.yml \
              -f docker-compose-aiops.yml \
              down
```

## 性能优化建议

### 1. 调整数据采集间隔

根据实际需求调整数据采集频率：

```yaml
# 在 docker-compose-aiops.yml 中修改
environment:
  - INGESTION_INTERVAL=60s  # 从 30s 改为 60s
```

### 2. 优化 Kafka 配置

对于高负载环境，调整 Kafka 的分区数和副本数：

```yaml
# 在 docker-compose-aiops.yml 中添加
environment:
  - KAFKA_NUM_PARTITIONS=3
  - KAFKA_REPLICATION_FACTOR=2
```

### 3. 调整异常检测参数

根据实际业务调整检测参数：

```yaml
environment:
  - DETECTION_WINDOW=600  # 增加检测窗口到 10 分钟
  - ANOMALY_THRESHOLD=3.0  # 提高阈值减少误报
```

## 下一步

1. **监控和维护:**
   - 定期检查服务日志
   - 监控 Kafka 消息堆积
   - 检查 Redis 内存使用
   - 监控 Neo4j 性能

2. **优化和调优:**
   - 根据实际情况调整检测参数
   - 添加更多自定义规则
   - 优化 Runbook
   - 增加机器学习模型

3. **扩展功能:**
   - 集成更多数据源
   - 添加更多异常检测算法
   - 实现更复杂的因果推断
   - 支持更多自动化操作

4. **集成和部署:**
   - 与现有运维系统集成
   - 配置告警通知
   - 设置自动化运维流程
   - 编写运维文档

## 总结

第三阶段实现了完整的 AIOps 自动化分析系统，包括：

✅ 实时数据摄入（Metrics + Logs + Traces）
✅ 多维度异常检测（统计学 + 规则 + ML）
✅ 图谱依赖分析（Neo4j + 图算法）
✅ 因果推断与根因定位
✅ 自动化修复建议（Runbooks）
✅ Grafana 集成与告警丰富化

这个系统将前两个阶段的数据基础和图谱关系，转化为智能的运维洞察能力，实现了从被动监控到主动运维的转变。
