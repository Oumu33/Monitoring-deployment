#!/usr/bin/env python3
"""
AIOps Notification Service

Integrates with multiple notification channels:
- DingTalk (钉钉)
- Feishu (飞书)
- WeCom (企业微信)
"""

import os
import json
import logging
import requests
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class Notification:
    """Notification data structure"""
    title: str
    message: str
    severity: str
    alert_level: str
    timestamp: str
    anomaly: Dict
    troubleshooting: Optional[Dict] = None
    jump_links: Optional[Dict] = None
    recommendations: Optional[List[Dict]] = None


class DingTalkNotifier:
    """DingTalk notification integration"""

    def __init__(self, webhook_url: str, secret: Optional[str] = None):
        self.webhook_url = webhook_url
        self.secret = secret

    def send_notification(self, notification: Notification) -> bool:
        """
        Send notification to DingTalk
        """
        try:
            # Build message
            message = self._build_message(notification)

            # Add signature if secret is provided
            if self.secret:
                message = self._add_signature(message)

            # Send request
            response = requests.post(
                self.webhook_url,
                json=message,
                timeout=10
            )
            response.raise_for_status()

            result = response.json()
            if result.get('errcode') == 0:
                logger.info("DingTalk notification sent successfully")
                return True
            else:
                logger.error(f"DingTalk notification failed: {result.get('errmsg')}")
                return False

        except Exception as e:
            logger.error(f"Error sending DingTalk notification: {e}")
            return False

    def _build_message(self, notification: Notification) -> Dict:
        """Build DingTalk message format"""
        # Determine color based on severity
        color_map = {
            'critical': '#FF0000',  # Red
            'high': '#FF6600',      # Orange
            'medium': '#FFCC00',    # Yellow
            'low': '#00CC00',       # Green
            'info': '#00CCFF'       # Blue
        }
        color = color_map.get(notification.alert_level, '#00CCFF')

        # Build markdown content
        markdown = f"""## {notification.title}

**级别:** {notification.alert_level.upper()}
**时间:** {notification.timestamp}
**指标:** {notification.anomaly.get('metric_name', 'N/A')}
**原因:** {notification.anomaly.get('reason', 'N/A')}

---

### 异常详情
- **严重程度:** {notification.severity}
- **评分:** {notification.anomaly.get('score', 0):.2f}
- **设备:** {notification.anomaly.get('labels', {}).get('instance', 'N/A')}

"""

        # Add troubleshooting info if available
        if notification.troubleshooting:
            markdown += "### 排错信息\n"

            # Add correlated logs
            logs = notification.troubleshooting.get('correlated_logs', [])
            if logs:
                markdown += f"**相关日志:** {len(logs)} 条\n"

            # Add historical issues
            history = notification.troubleshooting.get('historical_issues', [])
            if history:
                markdown += f"**历史问题:** {len(history)} 次在30天内发生\n"

            # Add recommendations
            recs = notification.troubleshooting.get('fix_recommendations', [])
            if recs:
                markdown += "\n### 修复建议\n"
                for i, rec in enumerate(recs[:3], 1):
                    priority = rec.get('priority', 'medium').upper()
                    action = rec.get('action', 'N/A')
                    desc = rec.get('description', '')
                    markdown += f"{i}. **[{priority}]** {action}: {desc}\n"

        # Add jump links if available
        if notification.jump_links:
            markdown += "\n### 快速链接\n"
            if 'grafana_dashboard' in notification.jump_links:
                markdown += f"- [Grafana仪表盘]({notification.jump_links['grafana_dashboard']})\n"
            if 'loki_logs' in notification.jump_links:
                markdown += f"- [Loki日志]({notification.jump_links['loki_logs']})\n"
            if 'alertmanager' in notification.jump_links:
                markdown += f"- [告警管理]({notification.jump_links['alertmanager']})\n"

        markdown += "\n---\n*Powered by AIOps*"

        # Build DingTalk message
        return {
            "msgtype": "markdown",
            "markdown": {
                "title": notification.title,
                "text": markdown
            },
            "at": {
                "isAtAll": notification.alert_level == 'critical'
            }
        }

    def _add_signature(self, message: Dict) -> Dict:
        """Add signature for secure webhook"""
        import hmac
        import hashlib
        import base64
        import time

        timestamp = str(int(time.time() * 1000))
        sign_str = f"{timestamp}\n{self.secret}"
        sign = hmac.new(
            self.secret.encode('utf-8'),
            sign_str.encode('utf-8'),
            hashlib.sha256
        ).digest()
        signature = base64.b64encode(sign).decode('utf-8')

        message['timestamp'] = timestamp
        message['sign'] = signature

        return message


class FeishuNotifier:
    """Feishu (Lark) notification integration"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send_notification(self, notification: Notification) -> bool:
        """
        Send notification to Feishu
        """
        try:
            # Build message
            message = self._build_message(notification)

            # Send request
            response = requests.post(
                self.webhook_url,
                json=message,
                timeout=10
            )
            response.raise_for_status()

            result = response.json()
            if result.get('StatusCode') == 0:
                logger.info("Feishu notification sent successfully")
                return True
            else:
                logger.error(f"Feishu notification failed: {result.get('msg')}")
                return False

        except Exception as e:
            logger.error(f"Error sending Feishu notification: {e}")
            return False

    def _build_message(self, notification: Notification) -> Dict:
        """Build Feishu message format"""
        # Determine color based on severity
        color_map = {
            'critical': 'red',
            'high': 'orange',
            'medium': 'yellow',
            'low': 'green',
            'info': 'blue'
        }
        color = color_map.get(notification.alert_level, 'blue')

        # Build card content
        elements = [
            {
                "tag": "div",
                "text": {
                    "content": f"**级别:** {notification.alert_level.upper()}",
                    "tag": "lark_md"
                }
            },
            {
                "tag": "div",
                "text": {
                    "content": f"**时间:** {notification.timestamp}",
                    "tag": "lark_md"
                }
            },
            {
                "tag": "div",
                "text": {
                    "content": f"**指标:** {notification.anomaly.get('metric_name', 'N/A')}",
                    "tag": "lark_md"
                }
            },
            {
                "tag": "div",
                "text": {
                    "content": f"**原因:** {notification.anomaly.get('reason', 'N/A')}",
                    "tag": "lark_md"
                }
            },
            {
                "tag": "hr"
            },
            {
                "tag": "div",
                "text": {
                    "content": "**异常详情**",
                    "tag": "lark_md"
                }
            },
            {
                "tag": "div",
                "text": {
                    "content": f"• 严重程度: {notification.severity}",
                    "tag": "lark_md"
                }
            },
            {
                "tag": "div",
                "text": {
                    "content": f"• 评分: {notification.anomaly.get('score', 0):.2f}",
                    "tag": "lark_md"
                }
            },
            {
                "tag": "div",
                "text": {
                    "content": f"• 设备: {notification.anomaly.get('labels', {}).get('instance', 'N/A')}",
                    "tag": "lark_md"
                }
            }
        ]

        # Add troubleshooting info if available
        if notification.troubleshooting:
            elements.append({"tag": "hr"})
            elements.append({
                "tag": "div",
                "text": {
                    "content": "**排错信息**",
                    "tag": "lark_md"
                }
            })

            # Add correlated logs
            logs = notification.troubleshooting.get('correlated_logs', [])
            if logs:
                elements.append({
                    "tag": "div",
                    "text": {
                        "content": f"• 相关日志: {len(logs)} 条",
                        "tag": "lark_md"
                    }
                })

            # Add historical issues
            history = notification.troubleshooting.get('historical_issues', [])
            if history:
                elements.append({
                    "tag": "div",
                    "text": {
                        "content": f"• 历史问题: {len(history)} 次",
                        "tag": "lark_md"
                    }
                })

            # Add recommendations
            recs = notification.troubleshooting.get('fix_recommendations', [])
            if recs:
                elements.append({
                    "tag": "div",
                    "text": {
                        "content": "**修复建议**",
                        "tag": "lark_md"
                    }
                })
                for i, rec in enumerate(recs[:3], 1):
                    priority = rec.get('priority', 'medium').upper()
                    action = rec.get('action', 'N/A')
                    elements.append({
                        "tag": "div",
                        "text": {
                            "content": f"{i}. **[{priority}]** {action}",
                            "tag": "lark_md"
                        }
                    })

        # Add jump links if available
        if notification.jump_links:
            elements.append({"tag": "hr"})
            elements.append({
                "tag": "div",
                "text": {
                    "content": "**快速链接**",
                    "tag": "lark_md"
                }
            })

            if 'grafana_dashboard' in notification.jump_links:
                elements.append({
                    "tag": "a",
                    "text": {
                        "content": "Grafana仪表盘",
                        "tag": "lark_md"
                    },
                    "href": notification.jump_links['grafana_dashboard']
                })
            if 'loki_logs' in notification.jump_links:
                elements.append({
                    "tag": "a",
                    "text": {
                        "content": "Loki日志",
                        "tag": "lark_md"
                    },
                    "href": notification.jump_links['loki_logs']
                })

        # Build Feishu card
        return {
            "msg_type": "interactive",
            "card": {
                "config": {
                    "wide_screen_mode": True
                },
                "header": {
                    "template": color,
                    "title": {
                        "content": notification.title,
                        "tag": "plain_text"
                    }
                },
                "elements": elements
            }
        }


class WeComNotifier:
    """WeChat Work (企业微信) notification integration"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send_notification(self, notification: Notification) -> bool:
        """
        Send notification to WeChat Work
        """
        try:
            # Build message
            message = self._build_message(notification)

            # Send request
            response = requests.post(
                self.webhook_url,
                json=message,
                timeout=10
            )
            response.raise_for_status()

            result = response.json()
            if result.get('errcode') == 0:
                logger.info("WeChat Work notification sent successfully")
                return True
            else:
                logger.error(f"WeChat Work notification failed: {result.get('errmsg')}")
                return False

        except Exception as e:
            logger.error(f"Error sending WeChat Work notification: {e}")
            return False

    def _build_message(self, notification: Notification) -> Dict:
        """Build WeChat Work message format"""
        # Build markdown content
        markdown = f"""## {notification.title}

> **级别:** {notification.alert_level.upper()}
> **时间:** {notification.timestamp}
> **指标:** {notification.anomaly.get('metric_name', 'N/A')}
> **原因:** {notification.anomaly.get('reason', 'N/A')}

---

**异常详情**
- 严重程度: {notification.severity}
- 评分: {notification.anomaly.get('score', 0):.2f}
- 设备: {notification.anomaly.get('labels', {}).get('instance', 'N/A')}
"""

        # Add troubleshooting info if available
        if notification.troubleshooting:
            markdown += "\n**排错信息**\n"

            logs = notification.troubleshooting.get('correlated_logs', [])
            if logs:
                markdown += f"- 相关日志: {len(logs)} 条\n"

            history = notification.troubleshooting.get('historical_issues', [])
            if history:
                markdown += f"- 历史问题: {len(history)} 次\n"

            recs = notification.troubleshooting.get('fix_recommendations', [])
            if recs:
                markdown += "\n**修复建议**\n"
                for i, rec in enumerate(recs[:3], 1):
                    priority = rec.get('priority', 'medium').upper()
                    action = rec.get('action', 'N/A')
                    markdown += f"{i}. **[{priority}]** {action}\n"

        markdown += "\n---\n*Powered by AIOps*"

        return {
            "msgtype": "markdown",
            "markdown": {
                "content": markdown
            }
        }


class NotificationService:
    """Main notification service"""

    def __init__(self):
        self.notifiers = []
        self._initialize_notifiers()

    def _initialize_notifiers(self):
        """Initialize notification channels from environment variables"""
        # DingTalk
        dingtalk_webhook = os.environ.get('DINGTALK_WEBHOOK_URL')
        dingtalk_secret = os.environ.get('DINGTALK_SECRET')
        if dingtalk_webhook:
            self.notifiers.append({
                'name': 'DingTalk',
                'notifier': DingTalkNotifier(dingtalk_webhook, dingtalk_secret),
                'enabled': True
            })
            logger.info("DingTalk notifier initialized")

        # Feishu
        feishu_webhook = os.environ.get('FEISHU_WEBHOOK_URL')
        if feishu_webhook:
            self.notifiers.append({
                'name': 'Feishu',
                'notifier': FeishuNotifier(feishu_webhook),
                'enabled': True
            })
            logger.info("Feishu notifier initialized")

        # WeChat Work
        wecom_webhook = os.environ.get('WECOM_WEBHOOK_URL')
        if wecom_webhook:
            self.notifiers.append({
                'name': 'WeChat Work',
                'notifier': WeComNotifier(wecom_webhook),
                'enabled': True
            })
            logger.info("WeChat Work notifier initialized")

        if not self.notifiers:
            logger.warning("No notification channels configured")

    def send_notification(self, notification: Notification) -> Dict[str, bool]:
        """
        Send notification to all enabled channels
        Returns a dict mapping channel names to success status
        """
        results = {}

        for channel in self.notifiers:
            if channel['enabled']:
                try:
                    success = channel['notifier'].send_notification(notification)
                    results[channel['name']] = success
                except Exception as e:
                    logger.error(f"Error sending to {channel['name']}: {e}")
                    results[channel['name']] = False

        return results

    def send_critical_notification(self, notification: Notification):
        """Send critical notification with higher priority"""
        # Critical notifications are sent to all channels immediately
        results = self.send_notification(notification)

        # Log failures
        for channel, success in results.items():
            if not success:
                logger.error(f"Failed to send critical notification to {channel}")

        return results


if __name__ == '__main__':
    # Test notification service
    service = NotificationService()

    test_notification = Notification(
        title="AIOps 告警测试",
        message="这是一条测试告警消息",
        severity="high",
        alert_level="high",
        timestamp=datetime.now().isoformat(),
        anomaly={
            'metric_name': 'cpu_usage',
            'reason': 'CPU usage high: 95.50%',
            'severity': 'high',
            'score': 0.85,
            'labels': {'instance': 'test-server:9100'}
        }
    )

    results = service.send_notification(test_notification)
    print(f"Notification results: {results}")