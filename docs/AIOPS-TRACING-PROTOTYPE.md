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