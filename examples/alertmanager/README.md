# Alertmanager 告警通知配置示例

本文件包含多种告警通知渠道的配置示例。

## 支持的通知渠道

1. **Email (邮件)**
2. **WeChat Work (企业微信)**
3. **DingTalk (钉钉)**
4. **Slack**
5. **Webhook (自定义)**
6. **Telegram**
7. **PagerDuty**

## 使用方法

1. 选择适合你的通知渠道配置
2. 复制到 `config/alertmanager/alertmanager.yml`
3. 修改相关参数（API Key、Webhook URL 等）
4. 重启 Alertmanager: `docker-compose restart alertmanager`

## 配置示例文件

- `email-notification.yml` - 邮件通知配置
- `wechat-notification.yml` - 企业微信机器人通知
- `dingtalk-notification.yml` - 钉钉机器人通知
- `slack-notification.yml` - Slack 通知
- `telegram-notification.yml` - Telegram 通知
- `multi-channel.yml` - 多渠道组合配置

## 测试告警通知

```bash
# 发送测试告警
curl -H "Content-Type: application/json" -d '[{
  "labels": {
    "alertname": "TestAlert",
    "severity": "warning"
  },
  "annotations": {
    "summary": "This is a test alert"
  }
}]' http://localhost:9093/api/v1/alerts
```
