# AIOps 通知服务配置指南

本文档介绍如何配置AIOps的通知服务，支持钉钉、飞书和企业微信。

## 支持的通知渠道

✅ **钉钉 (DingTalk)**
- 支持Markdown格式
- 支持@所有人（仅Critical级别）
- 支持加签验证

✅ **飞书 (Feishu/Lark)**
- 支持富文本卡片
- 支持颜色标记
- 支持快速链接

✅ **企业微信 (WeChat Work)**
- 支持Markdown格式
- 支持快速链接

## 配置步骤

### 1. 获取钉钉Webhook

1. 在钉钉群中，点击右上角"..."
2. 选择"群机器人" → "自定义机器人"
3. 输入机器人名称，选择安全设置
4. 如果选择"加签"，复制生成的密钥
5. 复制Webhook地址

**示例Webhook:**
```
https://oapi.dingtalk.com/robot/send?access_token=abc123def456
```

### 2. 获取飞书Webhook

1. 在飞书群中，点击右上角"..."
2. 选择"群机器人" → "添加机器人"
3. 选择"自定义机器人"
4. 输入机器人名称
5. 复制Webhook地址

**示例Webhook:**
```
https://open.feishu.cn/open-apis/bot/v2/hook/abc123def456
```

### 3. 获取企业微信Webhook

1. 在企业微信群中，点击右上角"..."
2. 选择"群机器人" → "添加机器人"
3. 输入机器人名称
4. 复制Webhook地址

**示例Webhook:**
```
https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=abc123-def456
```

## 配置方法

### 方法一：直接修改docker-compose.yml

编辑 `docker-compose-aiops.yml`，找到 `insights-action` 服务的 `environment` 部分：

```yaml
insights-action:
  environment:
    # ... 其他配置 ...
    # 取消以下行的注释并填写你的webhook
    - DINGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN
    - DINGTALK_SECRET=YOUR_SECRET
    - FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_HOOK
    - WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY
```

### 方法二：使用环境变量文件

1. 复制配置示例：
```bash
cp .env.aiops.notification .env.aiops
```

2. 编辑 `.env.aiops` 文件，填写你的webhook：
```bash
# 钉钉
DINGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN
DINGTALK_SECRET=YOUR_SECRET

# 飞书
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_HOOK

# 企业微信
WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY
```

3. 在 `docker-compose-aiops.yml` 中添加：
```yaml
insights-action:
  env_file:
    - .env.aiops
```

### 方法三：使用Docker Secret（推荐用于生产环境）

1. 创建secret：
```bash
echo "https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN" | docker secret create dingtalk_webhook -
echo "YOUR_SECRET" | docker secret create dingtalk_secret -
```

2. 在 `docker-compose-aiops.yml` 中使用：
```yaml
insights-action:
  secrets:
    - dingtalk_webhook
    - dingtalk_secret
  environment:
    - DINGTALK_WEBHOOK_URL_FILE=/run/secrets/dingtalk_webhook
    - DINGTALK_SECRET_FILE=/run/secrets/dingtalk_secret

secrets:
  dingtalk_webhook:
    external: true
  dingtalk_secret:
    external: true
```

## 重启服务

配置完成后，重启 `insights-action` 服务：

```bash
docker-compose -f docker-compose-aiops.yml restart insights-action
```

查看日志确认配置成功：

```bash
docker-compose -f docker-compose-aiops.yml logs -f insights-action
```

你应该看到类似这样的日志：
```
INFO - DingTalk notifier initialized
INFO - Feishu notifier initialized
```

## 测试通知

### 测试钉钉

```bash
curl -X POST "https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "msgtype": "text",
    "text": {
      "content": "测试通知：AIOps通知配置成功"
    }
  }'
```

### 测试飞书

```bash
curl -X POST "https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_HOOK" \
  -H 'Content-Type: application/json' \
  -d '{
    "msg_type": "text",
    "content": {
      "text": "测试通知：AIOps通知配置成功"
    }
  }'
```

### 测试企业微信

```bash
curl -X POST "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "msgtype": "text",
    "text": {
      "content": "测试通知：AIOps通知配置成功"
    }
  }'
```

## 通知级别

AIOps会根据告警的严重程度发送不同级别的通知：

| 级别 | 触发条件 | 通知行为 |
|------|---------|---------|
| **Critical** | 服务宕机、连接拒绝、HTTP 5xx | 立即发送所有渠道，@所有人 |
| **High** | CPU>90%、内存>95%、磁盘>90% | 发送所有渠道 |
| **Medium** | CPU>80%、响应时间>5s | 可选发送 |
| **Low** | 一般异常 | 不发送 |

## 通知内容示例

### Critical级别

```
## AIOps 告警 - service_down

**级别:** CRITICAL
**时间:** 2026-01-27T12:00:00
**指标:** service_down
**原因:** Service nginx is not running

---

### 异常详情
- **严重程度:** critical
- **评分:** 1.00
- **设备:** web-server-01:9100

### 排错信息
**相关日志:** 5 条
**历史问题:** 2 次在30天内发生

### 修复建议
1. **[CRITICAL]** 立即重启服务
2. **[HIGH]** 检查服务配置
3. **[MEDIUM]** 查看错误日志

### 快速链接
- [Grafana仪表盘](http://localhost:3000/...)
- [Loki日志](http://localhost:3100/...)
- [告警管理](http://localhost:9093/#/alerts)

---
*Powered by AIOps*
```

## 故障排查

### 问题1：通知未发送

**检查步骤：**

1. 查看服务日志：
```bash
docker-compose -f docker-compose-aiops.yml logs insights-action | grep -i notification
```

2. 检查环境变量：
```bash
docker exec -it insights-action env | grep -E 'DINGTALK|FEISHU|WECOM'
```

3. 测试webhook是否可访问：
```bash
curl -X POST "YOUR_WEBHOOK_URL" \
  -H 'Content-Type: application/json' \
  -d '{"msgtype":"text","text":{"content":"测试"}}'
```

### 问题2：钉钉加签失败

**解决方案：**

1. 确认 `DINGTALK_SECRET` 已正确配置
2. 检查secret是否包含特殊字符
3. 尝试使用不带加签的webhook

### 问题3：飞书卡片显示异常

**解决方案：**

1. 检查webhook URL是否正确
2. 确认飞书机器人权限
3. 查看飞书群机器人设置

### 问题4：企业微信通知失败

**解决方案：**

1. 检查webhook URL是否正确
2. 确认企业微信群机器人未被禁用
3. 检查消息格式是否正确

## 最佳实践

1. **生产环境：**
   - 使用Docker Secret存储敏感信息
   - 配置多个通知渠道作为备份
   - 启用加签验证（钉钉）

2. **测试环境：**
   - 可以只配置一个通知渠道
   - 使用较低的告警阈值进行测试

3. **安全建议：**
   - 不要在代码中硬编码webhook URL
   - 定期轮换webhook token
   - 限制机器人权限

## 下一步

配置完成后，你可以：

1. 查看通知效果
2. 调整告警阈值
3. 自定义通知模板
4. 配置通知时间窗口（避免夜间通知）

## 获取帮助

如果遇到问题：

1. 查看服务日志：`docker-compose -f docker-compose-aiops.yml logs insights-action`
2. 查看快速启动指南：`AIOPS-STAGE3-QUICKSTART.md`
3. 查看完整文档：`docs/AIOPS-TRACING-PROTOTYPE.md`

---

祝你配置成功！🎉