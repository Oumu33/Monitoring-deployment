#!/usr/bin/env python3
"""
AIOps Troubleshooting Engine

Implements advanced troubleshooting capabilities:
- Multi-level alerting
- Auto-jump to relevant resources
- Log correlation
- Historical issue tracking
- Similar fault detection
- Fix recommendations
"""

import os
import json
import logging
import redis
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
REDIS_HOST = os.environ.get('REDIS_HOST', 'redis')
REDIS_PORT = int(os.environ.get('REDIS_PORT', '6379'))
GRAFANA_URL = os.environ.get('GRAFANA_URL', 'http://grafana:3000')
LOKI_URL = os.environ.get('LOKI_URL', 'http://loki:3100')
VICTORIAMETRICS_URL = os.environ.get('VICTORIAMETRICS_URL', 'http://victoriametrics:8428')


class AlertLevel:
    """Alert severity levels"""
    CRITICAL = 'critical'
    HIGH = 'high'
    MEDIUM = 'medium'
    LOW = 'low'
    INFO = 'info'


class MultiLevelAlertManager:
    """Manages multi-level alerting with escalation"""

    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.alert_history = {}

    def determine_alert_level(self, anomaly: Dict) -> str:
        """
        Determine alert level based on anomaly characteristics
        """
        severity = anomaly.get('severity', 'medium')
        score = anomaly.get('score', 0.5)
        metric_name = anomaly.get('metric_name', '')

        # Critical conditions
        if severity == 'critical':
            return AlertLevel.CRITICAL

        # High severity or very high score
        if severity == 'high' or score > 0.8:
            return AlertLevel.HIGH

        # Service down or connection refused
        if any(keyword in metric_name.lower() for keyword in ['service_down', 'connection_refused']):
            return AlertLevel.CRITICAL

        # HTTP 5xx errors
        if 'http_5xx' in metric_name.lower():
            return AlertLevel.HIGH

        # Resource exhaustion
        if any(keyword in metric_name.lower() for keyword in ['cpu', 'memory', 'disk']):
            if score > 0.7:
                return AlertLevel.HIGH
            elif score > 0.5:
                return AlertLevel.MEDIUM

        # Default to medium
        return AlertLevel.MEDIUM

    def escalate_alert(self, anomaly: Dict, current_level: str) -> Tuple[str, bool]:
        """
        Check if alert should be escalated
        Returns (new_level, should_escalate)
        """
        # Check if this is a recurring issue
        alert_key = self._get_alert_key(anomaly)
        occurrence_count = self._get_occurrence_count(alert_key)

        # Escalate if issue persists
        if occurrence_count >= 5 and current_level != AlertLevel.CRITICAL:
            return AlertLevel.CRITICAL, True
        elif occurrence_count >= 3 and current_level == AlertLevel.MEDIUM:
            return AlertLevel.HIGH, True

        return current_level, False

    def _get_alert_key(self, anomaly: Dict) -> str:
        """Generate unique key for alert"""
        metric = anomaly.get('metric_name', '')
        labels = anomaly.get('labels', {})
        instance = labels.get('instance', 'unknown')
        return f"{metric}:{instance}"

    def _get_occurrence_count(self, alert_key: str) -> int:
        """Get occurrence count from Redis"""
        try:
            key = f"alert:occurrences:{alert_key}"
            count = self.redis_client.incr(key)
            self.redis_client.expire(key, 3600)  # Expire after 1 hour
            return count
        except Exception as e:
            logger.error(f"Error getting occurrence count: {e}")
            return 1


class AutoJumpNavigator:
    """Provides auto-jump capabilities to relevant resources"""

    def __init__(self):
        self.grafana_url = GRAFANA_URL
        self.loki_url = LOKI_URL
        self.victoriametrics_url = VICTORIAMETRICS_URL

    def generate_jump_links(self, anomaly: Dict) -> Dict[str, str]:
        """
        Generate jump links to relevant resources
        """
        links = {}
        metric_name = anomaly.get('metric_name', '')
        labels = anomaly.get('labels', {})
        instance = labels.get('instance', '')
        timestamp = anomaly.get('timestamp', '')

        # Grafana dashboard link
        links['grafana_dashboard'] = self._generate_grafana_link(metric_name, instance, timestamp)

        # Loki logs link
        links['loki_logs'] = self._generate_loki_link(instance, timestamp)

        # VictoriaMetrics explorer link
        links['vm_explorer'] = self._generate_vm_link(metric_name, instance, timestamp)

        # Grafana Explore link
        links['grafana_explore'] = self._generate_explore_link(metric_name, instance, timestamp)

        # Alertmanager link
        links['alertmanager'] = f"{self.grafana_url.replace('3000', '9093')}/#/alerts"

        return links

    def _generate_grafana_link(self, metric: str, instance: str, timestamp: str) -> str:
        """Generate Grafana dashboard link"""
        # Convert timestamp to epoch
        try:
            ts = datetime.fromisoformat(timestamp).timestamp()
            epoch_ms = int(ts * 1000)
        except:
            epoch_ms = int(datetime.now().timestamp() * 1000)

        dashboard_map = {
            'cpu_usage': 'd/system-overview',
            'memory_usage': 'd/system-overview',
            'disk_usage': 'd/system-overview',
            'network_in': 'd/network-overview',
            'network_out': 'd/network-overview',
            'http_5xx_errors': 'd/logs-explorer',
            'response_time': 'd/logs-explorer'
        }

        dashboard = dashboard_map.get(metric, 'd/system-overview')
        return f"{self.grafana_url}{dashboard}?from={epoch_ms - 300000}&to={epoch_ms + 60000}"

    def _generate_loki_link(self, instance: str, timestamp: str) -> str:
        """Generate Loki logs link"""
        try:
            ts = datetime.fromisoformat(timestamp).timestamp()
            epoch_ns = int(ts * 1000000000)
        except:
            epoch_ns = int(datetime.now().timestamp() * 1000000000)

        query = f'{{instance="{instance}"}}'
        return f"{self.loki_url}/graph?g0.expr={query}&g0.start={epoch_ns - 600000000000}&g0.end={epoch_ns + 60000000000}"

    def _generate_vm_link(self, metric: str, instance: str, timestamp: str) -> str:
        """Generate VictoriaMetrics explorer link"""
        query = f'{metric}{{instance="{instance}"}}'
        return f"{self.victoriametrics_url}/graph?g0.expr={query}&g0.tab=0"

    def _generate_explore_link(self, metric: str, instance: str, timestamp: str) -> str:
        """Generate Grafana Explore link"""
        query = f'{metric}{{instance="{instance}"}}'
        return f"{self.grafana_url}/explore?left=%5B%7B%22datasource%22%3A%22victoriametrics%22%2C%22queries%22%3A%5B%7B%22refId%22%3A%22A%22%2C%22expr%22%3A%22{query}%22%2C%22range%22%3Atrue%7D%5D%7D%5D"


class LogCorrelator:
    """Correlates logs with anomalies"""

    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.loki_url = LOKI_URL

    def correlate_logs(self, anomaly: Dict, time_window: int = 600) -> List[Dict]:
        """
        Find correlated logs for the anomaly
        time_window: seconds before/after the anomaly
        """
        try:
            labels = anomaly.get('labels', {})
            instance = labels.get('instance', '')
            metric_name = anomaly.get('metric_name', '')
            timestamp = anomaly.fromisoformat(anomaly.get('timestamp', datetime.now().isoformat()))

            # Calculate time range
            start_time = timestamp - timedelta(seconds=time_window)
            end_time = timestamp + timedelta(seconds=time_window // 2)

            # Build Loki query based on anomaly type
            query = self._build_log_query(instance, metric_name)

            # Query Loki
            logs = self._query_loki(query, start_time, end_time)

            # Filter and rank logs
            correlated_logs = self._filter_and_rank_logs(logs, anomaly)

            return correlated_logs

        except Exception as e:
            logger.error(f"Error correlating logs: {e}")
            return []

    def _build_log_query(self, instance: str, metric_name: str) -> str:
        """Build Loki query based on anomaly type"""
        base_query = f'{{instance="{instance}"}}'

        # Add error/warning filters based on metric type
        if 'cpu' in metric_name.lower():
            base_query += ' |~ `(?i)(error|exception|failed|timeout)`'
        elif 'memory' in metric_name.lower():
            base_query += ' |~ `(?i)(oom|out of memory|allocation failed)`'
        elif 'disk' in metric_name.lower():
            base_query += ' |~ `(?i)(disk full|no space|write error)`'
        elif 'network' in metric_name.lower():
            base_query += ' |~ `(?i)(connection refused|timeout|network unreachable)`'
        elif 'http' in metric_name.lower():
            base_query += ' |~ `(?i)(5\\d\\d|internal server error|service unavailable)`'

        return base_query

    def _query_loki(self, query: str, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Query Loki for logs"""
        try:
            params = {
                'query': query,
                'start': start_time.isoformat() + 'Z',
                'end': end_time.isoformat() + 'Z',
                'limit': '100'
            }

            response = requests.get(
                f"{self.loki_url}/loki/api/v1/query_range",
                params=params,
                timeout=30
            )
            response.raise_for_status()

            result = response.json()
            logs = []

            if result.get('status') == 'success':
                for stream in result.get('data', {}).get('result', []):
                    for value in stream.get('values', []):
                        logs.append({
                            'timestamp': value[0],
                            'log_line': value[1],
                            'labels': stream.get('stream', {})
                        })

            return logs

        except Exception as e:
            logger.error(f"Error querying Loki: {e}")
            return []

    def _filter_and_rank_logs(self, logs: List[Dict], anomaly: Dict) -> List[Dict]:
        """Filter and rank logs by relevance"""
        metric_name = anomaly.get('metric_name', '')
        severity = anomaly.get('severity', 'medium')

        scored_logs = []

        for log in logs:
            score = 0.0
            log_line = log.get('log_line', '').lower()

            # Check for error keywords
            if any(keyword in log_line for keyword in ['error', 'exception', 'failed']):
                score += 0.5

            # Check for specific error patterns
            if metric_name in log_line:
                score += 0.3

            # Check for severity indicators
            if 'critical' in log_line or 'fatal' in log_line:
                score += 0.4
            elif 'warning' in log_line or 'warn' in log_line:
                score += 0.2

            if score > 0.3:
                log['relevance_score'] = score
                scored_logs.append(log)

        # Sort by relevance score
        scored_logs.sort(key=lambda x: x['relevance_score'], reverse=True)

        return scored_logs[:20]  # Return top 20


class HistoricalIssueTracker:
    """Tracks historical issues and patterns"""

    def __init__(self, redis_client):
        self.redis_client = redis_client

    def store_anomaly(self, anomaly: Dict):
        """Store anomaly in history"""
        try:
            alert_key = self._get_alert_key(anomaly)
            history_key = f"history:{alert_key}"

            # Add to Redis list
            entry = {
                'timestamp': anomaly.get('timestamp'),
                'metric_name': anomaly.get('metric_name'),
                'severity': anomaly.get('severity'),
                'score': anomaly.get('score'),
                'reason': anomaly.get('reason', '')
            }

            self.redis_client.lpush(history_key, json.dumps(entry))
            self.redis_client.expire(history_key, 86400 * 30)  # Keep for 30 days

            # Trim to last 100 entries
            self.redis_client.ltrim(history_key, 0, 99)

        except Exception as e:
            logger.error(f"Error storing anomaly: {e}")

    def get_historical_issues(self, anomaly: Dict, days: int = 30) -> List[Dict]:
        """Get historical issues for this type of anomaly"""
        try:
            alert_key = self._get_alert_key(anomaly)
            history_key = f"history:{alert_key}"

            # Get all entries
            entries = self.redis_client.lrange(history_key, 0, -1)
            history = [json.loads(entry) for entry in entries]

            # Filter by date range
            cutoff_date = datetime.now() - timedelta(days=days)
            filtered = [
                entry for entry in history
                if datetime.fromisoformat(entry['timestamp']) > cutoff_date
            ]

            return filtered

        except Exception as e:
            logger.error(f"Error getting historical issues: {e}")
            return []

    def find_similar_issues(self, anomaly: Dict) -> List[Dict]:
        """Find similar historical issues"""
        try:
            metric_name = anomaly.get('metric_name', '')
            labels = anomaly.get('labels', {})

            # Search for similar issues in Redis
            pattern = f"history:*:{metric_name}"
            keys = self.redis_client.keys(pattern)

            similar_issues = []

            for key in keys:
                entries = self.redis_client.lrange(key, 0, 9)  # Get last 10
                for entry in entries:
                    issue = json.loads(entry)
                    similar_issues.append(issue)

            return similar_issues[:10]

        except Exception as e:
            logger.error(f"Error finding similar issues: {e}")
            return []

    def _get_alert_key(self, anomaly: Dict) -> str:
        """Generate unique key for alert"""
        metric = anomaly.get('metric_name', '')
        labels = anomaly.get('labels', {})
        instance = labels.get('instance', 'unknown')
        return f"{metric}:{instance}"


class FixRecommender:
    """Recommends fixes based on anomaly and historical data"""

    def __init__(self, historical_tracker: HistoricalIssueTracker):
        self.historical_tracker = historical_tracker

    def recommend_fixes(self, anomaly: Dict, historical_issues: List[Dict]) -> List[Dict]:
        """Recommend fixes for the anomaly"""
        recommendations = []
        metric_name = anomaly.get('metric_name', '')
        severity = anomaly.get('severity', 'medium')

        # General recommendations based on metric type
        recommendations.extend(self._get_metric_specific_recommendations(metric_name, severity))

        # Recommendations based on historical patterns
        recommendations.extend(self._get_historical_recommendations(historical_issues))

        # Recommendations based on severity
        recommendations.extend(self._get_severity_recommendations(severity))

        return recommendations

    def _get_metric_specific_recommendations(self, metric: str, severity: str) -> List[Dict]:
        """Get recommendations specific to the metric type"""
        recommendations = []

        if 'cpu' in metric.lower():
            recommendations.extend([
                {
                    'action': 'Check running processes',
                    'priority': 'high',
                    'command': 'top -b -n 1 | head -20'
                },
                {
                    'action': 'Kill high CPU processes',
                    'priority': 'medium',
                    'command': 'ps aux --sort=-%cpu | awk "NR>1 && $3>80 {print $2}" | xargs -r kill -15'
                },
                {
                    'action': 'Check for runaway processes',
                    'priority': 'medium',
                    'command': 'ps aux --sort=-pcpu | head -10'
                }
            ])

        elif 'memory' in metric.lower():
            recommendations.extend([
                {
                    'action': 'Clear page cache',
                    'priority': 'high',
                    'command': 'sync && echo 3 > /proc/sys/vm/drop_caches'
                },
                {
                    'action': 'Kill high memory processes',
                    'priority': 'medium',
                    'command': 'ps aux --sort=-%mem | awk "NR>1 && $4>50 {print $2}" | xargs -r kill -15'
                },
                {
                    'action': 'Check for memory leaks',
                    'priority': 'low',
                    'command': 'smem -k -c name,pss | head -20'
                }
            ])

        elif 'disk' in metric.lower():
            recommendations.extend([
                {
                    'action': 'Clean old logs',
                    'priority': 'high',
                    'command': 'find /var/log -type f -name "*.log" -mtime +7 -delete'
                },
                {
                    'action': 'Clean apt cache',
                    'priority': 'medium',
                    'command': 'apt-get autoremove -y && apt-get clean'
                },
                {
                    'action': 'Find large files',
                    'priority': 'medium',
                    'command': 'find / -type f -size +100M -exec ls -lh {} + 2>/dev/null | head -20'
                }
            ])

        elif 'network' in metric.lower():
            recommendations.extend([
                {
                    'action': 'Check network interfaces',
                    'priority': 'high',
                    'command': 'ip addr show'
                },
                {
                    'action': 'Check active connections',
                    'priority': 'medium',
                    'command': 'ss -s'
                },
                {
                    'action': 'Check network errors',
                    'priority': 'medium',
                    'command': 'ip -s link show'
                }
            ])

        elif 'http' in metric.lower():
            recommendations.extend([
                {
                    'action': 'Check web server status',
                    'priority': 'high',
                    'command': 'systemctl status nginx apache2'
                },
                {
                    'action': 'Check web server error logs',
                    'priority': 'high',
                    'command': 'tail -100 /var/log/nginx/error.log'
                },
                {
                    'action': 'Check backend service status',
                    'priority': 'medium',
                    'command': 'systemctl status {backend_service}'
                }
            ])

        return recommendations

    def _get_historical_recommendations(self, historical_issues: List[Dict]) -> List[Dict]:
        """Get recommendations based on historical issues"""
        recommendations = []

        if not historical_issues:
            return recommendations

        # Check if issue is recurring
        if len(historical_issues) >= 3:
            recommendations.append({
                'action': 'Recurring issue detected - implement permanent fix',
                'priority': 'critical',
                'description': f'This issue has occurred {len(historical_issues)} times in the past. Consider root cause analysis.',
                'type': 'recurring'
            })

        return recommendations

    def _get_severity_recommendations(self, severity: str) -> List[Dict]:
        """Get recommendations based on severity"""
        recommendations = []

        if severity == 'critical':
            recommendations.extend([
                {
                    'action': 'Immediate escalation required',
                    'priority': 'critical',
                    'description': 'This is a critical issue requiring immediate attention'
                },
                {
                    'action': 'Notify on-call engineer',
                    'priority': 'critical',
                    'description': 'Escalate to on-call team immediately'
                }
            ])

        elif severity == 'high':
            recommendations.append({
                'action': 'Urgent attention required',
                'priority': 'high',
                'description': 'This is a high-priority issue'
            })

        return recommendations


class TroubleshootingEngine:
    """Main troubleshooting engine"""

    def __init__(self, redis_client):
        self.redis_client = redis_client

        # Initialize components
        self.alert_manager = MultiLevelAlertManager(redis_client)
        self.navigator = AutoJumpNavigator()
        self.log_correlator = LogCorrelator(redis_client)
        self.history_tracker = HistoricalIssueTracker(redis_client)
        self.fix_recommender = FixRecommender(self.history_tracker)

    def process_anomaly(self, anomaly: Dict) -> Dict:
        """
        Process anomaly and generate troubleshooting information
        """
        try:
            # Store anomaly in history
            self.history_tracker.store_anomaly(anomaly)

            # Determine alert level
            alert_level = self.alert_manager.determine_alert_level(anomaly)

            # Check for escalation
            new_level, should_escalate = self.alert_manager.escalate_alert(anomaly, alert_level)
            if should_escalate:
                alert_level = new_level

            # Generate jump links
            jump_links = self.navigator.generate_jump_links(anomaly)

            # Correlate logs
            correlated_logs = self.log_correlator.correlate_logs(anomaly)

            # Get historical issues
            historical_issues = self.history_tracker.get_historical_issues(anomaly)

            # Find similar issues
            similar_issues = self.history_tracker.find_similar_issues(anomaly)

            # Recommend fixes
            fix_recommendations = self.fix_recommender.recommend_fixes(anomaly, historical_issues)

            # Build troubleshooting report
            report = {
                'timestamp': datetime.now().isoformat(),
                'anomaly': anomaly,
                'alert_level': alert_level,
                'escalated': should_escalate,
                'jump_links': jump_links,
                'correlated_logs': correlated_logs[:10],  # Top 10 logs
                'historical_issues': historical_issues[:5],  # Last 5 issues
                'similar_issues': similar_issues[:5],  # Top 5 similar issues
                'fix_recommendations': fix_recommendations,
                'summary': self._generate_summary(anomaly, alert_level, correlated_logs, historical_issues)
            }

            return report

        except Exception as e:
            logger.error(f"Error processing anomaly: {e}")
            return {
                'error': str(e),
                'anomaly': anomaly
            }

    def _generate_summary(self, anomaly: Dict, alert_level: str, logs: List[Dict], history: List[Dict]) -> str:
        """Generate troubleshooting summary"""
        metric = anomaly.get('metric_name', 'unknown')
        severity = anomaly.get('severity', 'medium')
        reason = anomaly.get('reason', 'No reason provided')

        summary = f"[{alert_level.upper()}] {metric} anomaly detected: {reason}\n"
        summary += f"Severity: {severity}\n"

        if logs:
            summary += f"\nFound {len(logs)} correlated log entries\n"

        if history:
            summary += f"\nThis issue has occurred {len(history)} times in the past 30 days\n"

        return summary


if __name__ == '__main__':
    # Test the troubleshooting engine
    import redis

    redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
    engine = TroubleshootingEngine(redis_client)

    # Test anomaly
    test_anomaly = {
        'timestamp': datetime.now().isoformat(),
        'metric_name': 'cpu_usage',
        'labels': {'instance': 'test-server:9100'},
        'severity': 'high',
        'score': 0.85,
        'reason': 'CPU usage high: 95.50%'
    }

    report = engine.process_anomaly(test_anomaly)
    print(json.dumps(report, indent=2))
