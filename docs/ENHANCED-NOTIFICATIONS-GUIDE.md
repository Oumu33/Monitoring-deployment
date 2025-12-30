# 增强版告警通知配置指南

## 概述

本指南介绍如何配置和使用增强版告警通知，支持飞书、钉钉、企业微信，并包含自适应预测的详细信息。

## 目录

- [功能特性](#功能特性)
- [文件结构](#文件结构)
- [快速开始](#快速开始)
- [平台配置](#平台配置)
- [模板说明](#模板说明)
- [告警类型](#告警类型)
- [测试验证](#测试验证)

## 功能特性

### 1. 多平台支持
- ✅ 飞书（卡片式、Markdown）
- ✅ 钉钉（Markdown、富文本）
- ✅ 企业微信（卡片式、Markdown）

### 2. 精美的通知模板
- 📊 卡片式布局（飞书、企微）
- 📈 表格化数据展示
- 🎨 颜色标记（严重程度）
- 🔗 可操作链接

### 3. 自适应预测信息
- 🔮 多模型预测对比
- 📊 预测质量评分
- 📅 历史对比数据
- 🔄 季节性分析
- 🎯 自动缓解建议

### 4. 智能路由
- 🎯 基于告警类型的路由
- 🚫 告警抑制规则
- 📋 分级通知策略

## 文件结构

```
config/alertmanager/
├── alertmanager-enhanced.yml      # Alertmanager 配置
├── webhook-adapter-config.yml     # Webhook 适配器配置
├── webhook-router.yml             # Webhook 路由配置
└── templates/
    ├── feishu-card.tmpl           # 飞书卡片模板
    ├── dingtalk-enhanced.tmpl     # 钉钉增强模板
    └── wework-enhanced.tmpl       # 企业微信增强模板

docker-compose-enhanced-notifications.yml  # Docker Compose 配置
```

## 快速开始

### 1. 获取 Webhook URL

#### 飞书
```bash
1. 打开飞书群聊
2. 点击群设置 -> 群机器人 -> 添加机器人 -> 自定义机器人
3. 复制 Webhook URL 和密钥
```

#### 钉钉
```bash
1. 打开钉钉群聊
2. 点击群设置 -> 智能群助手 -> 添加机器人 -> 自定义机器人
3. 设置安全设置（推荐使用加签方式）
4. 复制 Webhook 地址和加签密钥
```

#### 企业微信
```bash
1. 打开企业微信群聊
2. 点击群设置 -> 群机器人 -> 添加机器人
3. 复制 Webhook URL
```

### 2. 配置 Webhook URL

编辑 `config/alertmanager/webhook-adapter-config.yml`：

```yaml
feishu:
  predictive:
    webhook_url: https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_WEBHOOK_URL
    secret: YOUR_SECRET

dingtalk:
  predictive:
    webhook_url: https://oapi.dingtalk.com/robot/send?access_token=YOUR_ACCESS_TOKEN
    secret: YOUR_SECRET

wework:
  predictive:
    webhook_url: https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY
```

### 3. 启动服务

```bash
docker-compose -f docker-compose-enhanced-notifications.yml up -d
```

### 4. 测试告警

```bash
curl -X POST http://localhost:9093/api/v1/alerts \
  -H 'Content-Type: application/json' \
  -d '[{
    "labels": {
      "alertname": "TestPredictiveAlert",
      "severity": "warning",
      "category": "predictive",
      "instance": "test-server"
    },
    "annotations": {
      "summary": "测试预测性告警",
      "description": "这是一条测试预测性告警",
      "prediction_value": "95%",
      "current_value": "80%",
      "prediction_quality": "85%",
      "prediction_confidence": "90%",
      "prediction_method": "adaptive"
    }
  }]'
```

## 平台配置

### 飞书

#### 卡片式通知
```yaml
feishu:
  predictive:
    webhook_url: https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_WEBHOOK_URL
    secret: YOUR_SECRET
    msg_type: interactive
    template: feishu.predictive.alert
```

#### Markdown 通知
```yaml
feishu:
  default:
    webhook_url: https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_WEBHOOK_URL
    secret: YOUR_SECRET
    msg_type: post
    template: feishu.text.content
```

### 钉钉

#### Markdown 通知
```yaml
dingtalk:
  predictive:
    webhook_url: https://oapi.dingtalk.com/robot/send?access_token=YOUR_ACCESS_TOKEN
    secret: YOUR_SECRET
    msg_type: markdown
    template: dingtalk.predictive.content
```

#### ActionCard 通知
```yaml
dingtalk:
  critical:
    webhook_url: https://oapi.dingtalk.com/robot/send?access_token=YOUR_ACCESS_TOKEN
    secret: YOUR_SECRET
    msg_type: actionCard
    template: dingtalk.content
```

### 企业微信

#### 卡片式通知
```yaml
wework:
  predictive:
    webhook_url: https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY
    msg_type: template_card
    template: wework.predictive.card
```

#### Markdown 通知
```yaml
wework:
  default:
    webhook_url: https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY
    msg_type: markdown
    template: wework.content
```

## 模板说明

### 飞书卡片模板

#### 特性
- 🎨 彩色标题（根据严重程度）
- 📊 结构化内容展示
- 🔗 可操作按钮
- 📈 表格化数据

#### 使用
```yaml
feishu:
  predictive:
    template: feishu.predictive.alert
```

### 钉钉增强模板

#### 特性
- 📈 Markdown 格式
- 📊 表格化数据
- 🔗 快速链接
- 🎯 建议操作

#### 使用
```yaml
dingtalk:
  predictive:
    template: dingtalk.predictive.content
```

### 企业微信增强模板

#### 特性
- 📊 卡片式布局
- 🎨 彩色标题
- 🔗 可操作按钮
- 📈 结构化数据

#### 使用
```yaml
wework:
  predictive:
    msg_type: template_card
    template: wework.predictive.card
```

## 告警类型

### 1. 预测性告警

**标签:**
```yaml
category: predictive
subcategory: forecast
priority: P0/P1/P2
```

**注解:**
```yaml
prediction_value: "95%"
current_value: "80%"
prediction_quality: "85%"
prediction_stability: "90%"
prediction_confidence: "92%"
prediction_method: "adaptive"
```

### 2. 根因告警

**标签:**
```yaml
root_cause: "true"
```

**注解:**
```yaml
affected_devices: "5"
affected_vms: "20"
topology_chain: "核心交换机 -> 接入交换机 -> 服务器"
```

### 3. Metrics + Logs 联动告警

**标签:**
```yaml
subcategory: logs
```

**注解:**
```yaml
log_query: '{host="server1"} |~ "error"'
log_query_encoded: '%7Bhost%3D%22server1%22%7D%20%7C~%20%22error%22'
```

### 4. 硬件告警

**标签:**
```yaml
category: hardware
```

**注解:**
```yaml
vendor: "Dell"
model: "PowerEdge R740"
failed_component: "CPU"
```

## 测试验证

### 1. 测试飞书通知

```bash
curl -X POST http://localhost:9093/api/v1/alerts \
  -H 'Content-Type: application/json' \
  -d '[{
    "labels": {
      "alertname": "FeishuTestAlert",
      "severity": "warning",
      "category": "predictive"
    },
    "annotations": {
      "summary": "飞书测试告警",
      "description": "这是一条飞书测试告警"
    }
  }]'
```

### 2. 测试钉钉通知

```bash
curl -X POST http://localhost:9093/api/v1/alerts \
  -H 'Content-Type: application/json' \
  -d '[{
    "labels": {
      "alertname": "DingtalkTestAlert",
      "severity": "warning",
      "category": "predictive"
    },
    "annotations": {
      "summary": "钉钉测试告警",
      "description": "这是一条钉钉测试告警"
    }
  }]'
```

### 3. 测试企业微信通知

```bash
curl -X POST http://localhost:9093/api/v1/alerts \
  -H 'Content-Type: application/json' \
  -d '[{
    "labels": {
      "alertname": "WeworkTestAlert",
      "severity": "warning",
      "category": "predictive"
    },
    "annotations": {
      "summary": "企业微信测试告警",
      "description": "这是一条企业微信测试告警"
    }
  }]'
```

### 4. 测试预测性告警

```bash
curl -X POST http://localhost:9093/api/v1/alerts \
  -H 'Content-Type: application/json' \
  -d '[{
    "labels": {
      "alertname": "PredictiveCPUHighIn1HourEnhanced",
      "severity": "warning",
      "category": "predictive",
      "subcategory": "forecast",
      "instance": "test-server"
    },
    "annotations": {
      "summary": "预测告警: 主机 test-server CPU 使用率将在 1 小时内达到 95%",
      "prediction_value": "95%",
      "current_value": "80%",
      "prediction_quality": "85%",
      "prediction_stability": "90%",
      "prediction_confidence": "92%",
      "prediction_method": "adaptive",
      "linear_prediction": "93%",
      "linear_accuracy": "78%",
      "seasonal_prediction": "94%",
      "seasonal_accuracy": "82%",
      "multivariate_prediction": "96%",
      "multivariate_accuracy": "85%",
      "ensemble_prediction": "94.5%",
      "ensemble_accuracy": "83%",
      "adaptive_accuracy": "87%",
      "history_yesterday": "75%",
      "history_last_week": "72%",
      "history_baseline_7d": "73%",
      "deviation_from_history": "22%",
      "seasonal_trend": "70%",
      "seasonal_seasonal": "5%",
      "seasonal_residual": "3%",
      "seasonal_daily_baseline": "74%",
      "auto_mitigation_suggestions": "建议立即执行: ps aux --sort=-%CPU | head -20\n建议检查是否有新部署的服务",
      "preventive_measures": "启用 CPU 使用率自动告警（阈值 80%）\n配置自动扩容策略",
      "runbook_url": "https://your-wiki.com/runbooks/predictive-cpu-high"
    }
  }]'
```

## 故障排查

### 1. 通知未发送

检查步骤：
```bash
# 1. 查看 Alertmanager 日志
docker logs alertmanager

# 2. 查看 Webhook 适配器日志
docker logs feishu-webhook-adapter
docker logs dingtalk-webhook-adapter
docker logs wework-webhook-adapter

# 3. 测试 Webhook URL
curl -X POST YOUR_WEBHOOK_URL \
  -H 'Content-Type: application/json' \
  -d '{"msgtype":"text","text":{"content":"测试消息"}}'
```

### 2. 模板渲染错误

检查步骤：
```bash
# 1. 验证模板语法
docker exec alertmanager amtool check-config /etc/alertmanager/alertmanager.yml

# 2. 查看模板文件
cat config/alertmanager/templates/feishu-card.tmpl
```

### 3. 路由不匹配

检查步骤：
```bash
# 1. 查看路由配置
cat config/alertmanager/alertmanager-enhanced.yml

# 2. 检查告警标签
curl http://localhost:9093/api/v1/alerts
```

## 最佳实践

### 1. 告警分级
- P0: 紧急，立即处理（5分钟内）
- P1: 重要，尽快处理（30分钟内）
- P2: 警告，关注处理（2小时内）
- P3: 信息，记录即可

### 2. 通知频率
- Critical: 5分钟重复
- Warning: 30分钟重复
- Info: 1小时重复

### 3. 告警抑制
- 根因告警抑制下游告警
- Critical 抑制 Warning
- 预测性告警抑制重复告警

### 4. 模板优化
- 使用表格化数据展示
- 添加可操作链接
- 使用颜色标记严重程度
- 提供清晰的解决建议

## 参考资源

- [Alertmanager 官方文档](https://prometheus.io/docs/alerting/latest/configuration/)
- [飞书开放平台](https://open.feishu.cn/document/ukTMukTMukTM/ucTM5YjL3ETO24yNxkjN)
- [钉钉开放平台](https://open.dingtalk.com/document/robots/custom-robot-access)
- [企业微信开放平台](https://developer.work.weixin.qq.com/document/path/91770)

## 支持

如有问题，请提交 Issue 或联系运维团队。