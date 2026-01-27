#!/usr/bin/env python3
"""
AIOps Insights & Action Service

Implements:
1. Grafana Integration - Push RCA results to Grafana dashboards
2. Alert Enrichment - Add root cause information to Alertmanager notifications
3. Automated Runbooks - Execute predefined recovery playbooks
"""

import os
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import redis
from kafka import KafkaConsumer, KafkaProducer
from neo4j import GraphDatabase
import yaml
import subprocess
from troubleshooting_engine import TroubleshootingEngine
from notification_service import NotificationService, Notification

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
REDIS_HOST = os.environ.get('REDIS_HOST', 'redis')
REDIS_PORT = int(os.environ.get('REDIS_PORT', '6379'))
NEO4J_URI = os.environ.get('NEO4J_URI', 'bolt://neo4j:7687')
NEO4J_USER = os.environ.get('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD', 'password123')
ALERTMANAGER_URL = os.environ.get('ALERTMANAGER_URL', 'http://alertmanager:9093')
GRAFANA_URL = os.environ.get('GRAFANA_URL', 'http://grafana:3000')

# Kafka Topics
TOPIC_RCA_RESULTS = 'aiops.rca_results'
TOPIC_ACTIONS = 'aiops.actions'


class GrafanaIntegration:
    """Integrates with Grafana for visualization"""

    def __init__(self, grafana_url: str, api_key: Optional[str] = None):
        self.grafana_url = grafana_url
        self.api_key = api_key
        self.headers = {}
        if api_key:
            self.headers['Authorization'] = f'Bearer {api_key}'

    def create_annotation(self, text: str, tags: List[str], time_start: int, time_end: Optional[int] = None):
        """
        Create an annotation in Grafana
        """
        annotation = {
            'text': text,
            'tags': tags,
            'time': time_start * 1000  # Convert to milliseconds
        }
        if time_end:
            annotation['timeEnd'] = time_end * 1000

        try:
            response = requests.post(
                f"{self.grafana_url}/api/annotations",
                json=annotation,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            logger.info(f"Created Grafana annotation: {text[:50]}...")
            return response.json()
        except Exception as e:
            logger.error(f"Failed to create Grafana annotation: {e}")
            return None

    def push_rca_to_annotation(self, rca_result: Dict):
        """Push RCA result as Grafana annotation"""
        root_cause = rca_result.get('root_cause', {})
        device = root_cause.get('root_cause_device', 'unknown')
        confidence = root_cause.get('confidence', 0)
        summary = rca_result.get('rca_summary', '')

        tags = ['aiops', 'rca', 'root-cause', device]
        if confidence > 0.8:
            tags.append('high-confidence')

        # Create annotation
        timestamp = int(datetime.fromisoformat(rca_result['timestamp']).timestamp())
        self.create_annotation(
            text=f"AIOps RCA: {summary}",
            tags=tags,
            time_start=timestamp
        )


class AlertEnrichment:
    """Enriches Alertmanager alerts with RCA information"""

    def __init__(self, alertmanager_url: str):
        self.alertmanager_url = alertmanager_url

    def enrich_alert(self, rca_result: Dict):
        """
        Enrich existing alerts with RCA information
        Note: This is a simplified implementation
        """
        try:
            # Get active alerts
            response = requests.get(
                f"{self.alertmanager_url}/api/v1/alerts",
                timeout=10
            )
            response.raise_for_status()
            alerts = response.json().get('data', [])

            # Find matching alerts
            root_cause_device = rca_result.get('root_cause', {}).get('root_cause_device', '')

            for alert in alerts:
                labels = alert.get('labels', {})
                if root_cause_device in labels.get('instance', ''):
                    # Enrich alert with RCA information
                    alert['annotations']['aiops_root_cause'] = json.dumps(rca_result, indent=2)
                    logger.info(f"Enriched alert for {root_cause_device}")

        except Exception as e:
            logger.error(f"Failed to enrich alerts: {e}")


class RunbookExecutor:
    """Executes automated runbooks based on root cause"""

    def __init__(self, runbooks_dir: str = '/app/runbooks'):
        self.runbooks_dir = runbooks_dir
        self.runbooks = self._load_runbooks()

    def _load_runbooks(self) -> Dict:
        """Load runbooks from directory"""
        runbooks = {}
        try:
            if os.path.exists(self.runbooks_dir):
                for filename in os.listdir(self.runbooks_dir):
                    if filename.endswith('.yml') or filename.endswith('.yaml'):
                        filepath = os.path.join(self.runbooks_dir, filename)
                        with open(filepath, 'r') as f:
                            runbook_data = yaml.safe_load(f)
                            runbook_name = filename.replace('.yml', '').replace('.yaml', '')
                            runbooks[runbook_name] = runbook_data
                        logger.info(f"Loaded runbook: {runbook_name}")
        except Exception as e:
            logger.error(f"Error loading runbooks: {e}")

        return runbooks

    def match_runbook(self, rca_result: Dict) -> Optional[Dict]:
        """
        Match a runbook to the RCA result
        """
        root_cause = rca_result.get('root_cause', {})
        anomaly = root_cause.get('root_cause_anomaly', {})
        metric = anomaly.get('metric_name', '')
        device_type = anomaly.get('labels', {}).get('type', '')

        for runbook_name, runbook in self.runbooks.items():
            conditions = runbook.get('conditions', {})

            # Check if runbook conditions match
            match = True
            if 'metric_name' in conditions and conditions['metric_name'] != metric:
                match = False
            if 'device_type' in conditions and conditions['device_type'] != device_type:
                match = False

            if match:
                logger.info(f"Matched runbook: {runbook_name}")
                return runbook

        return None

    def execute_runbook(self, runbook: Dict, context: Dict) -> Dict:
        """
        Execute a runbook
        """
        steps = runbook.get('steps', [])
        results = []

        for i, step in enumerate(steps):
            try:
                step_name = step.get('name', f'step_{i}')
                step_type = step.get('type', 'command')

                logger.info(f"Executing step {i+1}/{len(steps)}: {step_name}")

                if step_type == 'command':
                    result = self._execute_command(step, context)
                elif step_type == 'http_request':
                    result = self._execute_http_request(step, context)
                elif step_type == 'script':
                    result = self._execute_script(step, context)
                else:
                    result = {'status': 'error', 'message': f'Unknown step type: {step_type}'}

                results.append({
                    'step': step_name,
                    'status': result.get('status', 'unknown'),
                    'result': result
                })

                # Stop on failure if configured
                if result.get('status') == 'error' and step.get('stop_on_failure', True):
                    logger.error(f"Step {step_name} failed, stopping execution")
                    break

            except Exception as e:
                logger.error(f"Error executing step {step_name}: {e}")
                results.append({
                    'step': step_name,
                    'status': 'error',
                    'result': {'error': str(e)}
                })

        return {
            'runbook': runbook.get('name', 'unknown'),
            'status': 'completed',
            'steps': results
        }

    def _execute_command(self, step: Dict, context: Dict) -> Dict:
        """Execute a shell command"""
        command = step.get('command', '')
        timeout = step.get('timeout', 30)

        try:
            # Replace placeholders
            command = self._replace_placeholders(command, context)

            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            return {
                'status': 'success' if result.returncode == 0 else 'error',
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
        except subprocess.TimeoutExpired:
            return {'status': 'error', 'message': 'Command timeout'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def _execute_http_request(self, step: Dict, context: Dict) -> Dict:
        """Execute an HTTP request"""
        url = step.get('url', '')
        method = step.get('method', 'GET').upper()
        headers = step.get('headers', {})
        body = step.get('body', {})
        timeout = step.get('timeout', 30)

        try:
            # Replace placeholders
            url = self._replace_placeholders(url, context)
            body = self._replace_placeholders_dict(body, context)

            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=body, headers=headers, timeout=timeout)
            elif method == 'PUT':
                response = requests.put(url, json=body, headers=headers, timeout=timeout)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=timeout)
            else:
                return {'status': 'error', 'message': f'Unknown HTTP method: {method}'}

            return {
                'status': 'success' if response.status_code < 400 else 'error',
                'status_code': response.status_code,
                'response': response.text
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def _execute_script(self, step: Dict, context: Dict) -> Dict:
        """Execute a script file"""
        script_path = step.get('script', '')
        args = step.get('args', [])
        timeout = step.get('timeout', 30)

        try:
            full_path = os.path.join(self.runbooks_dir, script_path)
            if not os.path.exists(full_path):
                return {'status': 'error', 'message': f'Script not found: {full_path}'}

            # Replace placeholders in args
            args = [self._replace_placeholders(arg, context) for arg in args]

            result = subprocess.run(
                ['python', full_path] + args,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            return {
                'status': 'success' if result.returncode == 0 else 'error',
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def _replace_placeholders(self, text: str, context: Dict) -> str:
        """Replace placeholders in text with context values"""
        for key, value in context.items():
            if isinstance(value, str):
                text = text.replace(f'{{{key}}}', value)
        return text

    def _replace_placeholders_dict(self, data: Dict, context: Dict) -> Dict:
        """Replace placeholders in dictionary values"""
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self._replace_placeholders(value, context)
            elif isinstance(value, dict):
                result[key] = self._replace_placeholders_dict(value, context)
            else:
                result[key] = value
        return result


class ActionGenerator:
    """Generates actionable recommendations"""

    def __init__(self):
        pass

    def generate_actions(self, rca_result: Dict) -> List[Dict]:
        """
        Generate actionable recommendations based on RCA result
        """
        actions = []
        root_cause = rca_result.get('root_cause', {})
        anomaly = root_cause.get('root_cause_anomaly', {})
        metric = anomaly.get('metric_name', '')
        device = root_cause.get('root_cause_device', 'unknown')

        # Generate actions based on metric type
        if metric == 'cpu_usage':
            actions.extend(self._generate_cpu_actions(anomaly, device))
        elif metric == 'memory_usage':
            actions.extend(self._generate_memory_actions(anomaly, device))
        elif metric == 'disk_usage':
            actions.extend(self._generate_disk_actions(anomaly, device))
        else:
            actions.append({
                'action': 'investigate',
                'description': f'Investigate {metric} anomaly on {device}',
                'priority': 'medium'
            })

        return actions

    def _generate_cpu_actions(self, anomaly: Dict, device: str) -> List[Dict]:
        """Generate CPU-related actions"""
        actions = []
        severity = anomaly.get('severity', 'medium')

        actions.append({
            'action': 'check_processes',
            'description': f'Check for high CPU processes on {device}',
            'priority': 'high',
            'command': f'top -b -n 1 | head -20'
        })

        if severity == 'high':
            actions.append({
                'action': 'check_load_average',
                'description': f'Check load average on {device}',
                'priority': 'high',
                'command': 'uptime'
            })

        return actions

    def _generate_memory_actions(self, anomaly: Dict, device: str) -> List[Dict]:
        """Generate memory-related actions"""
        actions = []
        severity = anomaly.get('severity', 'medium')

        actions.append({
            'action': 'check_memory_usage',
            'description': f'Check memory usage on {device}',
            'priority': 'high',
            'command': 'free -h'
        })

        if severity == 'high':
            actions.append({
                'action': 'check_swap',
                'description': f'Check swap usage on {device}',
                'priority': 'medium',
                'command': 'swapon --show'
            })

        return actions

    def _generate_disk_actions(self, anomaly: Dict, device: str) -> List[Dict]:
        """Generate disk-related actions"""
        actions = []
        severity = anomaly.get('severity', 'medium')

        actions.append({
            'action': 'check_disk_space',
            'description': f'Check disk space on {device}',
            'priority': 'high',
            'command': 'df -h'
        })

        if severity == 'high':
            actions.append({
                'action': 'cleanup_logs',
                'description': f'Clean up old logs on {device}',
                'priority': 'medium',
                'command': 'find /var/log -type f -name "*.log" -mtime +7 -delete'
            })

        return actions


class InsightsActionService:
    """Main insights and action service"""

    def __init__(self):
        self.redis_client = None
        self.kafka_consumer = None
        self.kafka_producer = None
        self.neo4j_driver = None
        self.running = True

        # Initialize components
        self.grafana = GrafanaIntegration(GRAFANA_URL)
        self.alert_enrichment = AlertEnrichment(ALERTMANAGER_URL)
        self.runbook_executor = RunbookExecutor()
        self.action_generator = ActionGenerator()

        # Initialize troubleshooting engine (will be set after Redis connection)
        self.troubleshooting_engine = None

        # Initialize notification service
        self.notification_service = NotificationService()

    def connect_redis(self):
        """Connect to Redis"""
        try:
            self.redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                decode_responses=True
            )
            self.redis_client.ping()
            logger.info(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")

            # Initialize troubleshooting engine after Redis connection
            self.troubleshooting_engine = TroubleshootingEngine(self.redis_client)
            logger.info("Troubleshooting engine initialized")

            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return False

    def connect_kafka(self):
        """Connect to Kafka"""
        try:
            self.kafka_consumer = KafkaConsumer(
                TOPIC_RCA_RESULTS,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                group_id='insights-action-group',
                auto_offset_reset='latest'
            )

            self.kafka_producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all'
            )

            logger.info(f"Connected to Kafka at {KAFKA_BOOTSTRAP_SERVERS}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            return False

    def connect_neo4j(self):
        """Connect to Neo4j"""
        try:
            self.neo4j_driver = GraphDatabase.driver(
                NEO4J_URI,
                auth=(NEO4J_USER, NEO4J_PASSWORD)
            )
            self.neo4j_driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {NEO4J_URI}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            return False

    def publish_action(self, action: Dict):
        """Publish action to Kafka"""
        try:
            self.kafka_producer.send(TOPIC_ACTIONS, value=action)
            logger.info(f"Published action: {action.get('action', 'unknown')}")
        except Exception as e:
            logger.error(f"Failed to publish action: {e}")

    def process_rca_result(self, rca_result: Dict):
        """Process RCA result and generate insights/actions"""
        try:
            logger.info("=" * 60)
            logger.info("Processing RCA result with troubleshooting engine")
            logger.info("=" * 60)

            # 0. Process with troubleshooting engine (new step)
            logger.info("Step 0: Running troubleshooting engine...")
            root_cause_anomaly = rca_result.get('root_cause', {}).get('root_cause_anomaly', {})

            alert_level = 'medium'
            if root_cause_anomaly and self.troubleshooting_engine:
                troubleshooting_report = self.troubleshooting_engine.process_anomaly(root_cause_anomaly)

                # Add troubleshooting info to RCA result
                rca_result['troubleshooting'] = troubleshooting_report
                alert_level = troubleshooting_report.get('alert_level', 'medium')

                # Log troubleshooting summary
                logger.info(f"Troubleshooting Report:")
                logger.info(f"  Alert Level: {alert_level}")
                logger.info(f"  Escalated: {troubleshooting_report.get('escalated', False)}")
                logger.info(f"  Correlated Logs: {len(troubleshooting_report.get('correlated_logs', []))}")
                logger.info(f"  Historical Issues: {len(troubleshooting_report.get('historical_issues', []))}")
                logger.info(f"  Fix Recommendations: {len(troubleshooting_report.get('fix_recommendations', []))}")

                # Publish troubleshooting report
                self.publish_action({
                    'action': 'troubleshooting_report',
                    'report': troubleshooting_report
                })

                # Check if alert should be escalated
                if troubleshooting_report.get('escalated', False):
                    logger.warning(f"ALERT ESCALATED to {alert_level}!")

                # Include jump links in RCA result
                rca_result['jump_links'] = troubleshooting_report.get('jump_links', {})

            # 1. Push to Grafana with enriched information
            logger.info("Step 1: Pushing to Grafana with troubleshooting info...")
            self.grafana.push_rca_to_annotation(rca_result)

            # 2. Enrich Alertmanager alerts with troubleshooting info
            logger.info("Step 2: Enriching alerts with troubleshooting info...")
            self.alert_enrichment.enrich_alert(rca_result)

            # 3. Generate actions (including troubleshooting recommendations)
            logger.info("Step 3: Generating actions...")
            actions = self.action_generator.generate_actions(rca_result)

            # Add troubleshooting recommendations
            if 'troubleshooting' in rca_result:
                fix_recs = rca_result['troubleshooting'].get('fix_recommendations', [])
                for rec in fix_recs:
                    actions.append({
                        'action': rec.get('action', 'fix'),
                        'description': rec.get('description', rec.get('action', '')),
                        'priority': rec.get('priority', 'medium'),
                        'command': rec.get('command', ''),
                        'type': rec.get('type', 'recommendation')
                    })

            for action in actions:
                self.publish_action(action)
                logger.info(f"Generated action: {action['description']}")

            # 4. Match and execute runbook
            logger.info("Step 4: Checking for runbooks...")
            runbook = self.runbook_executor.match_runbook(rca_result)

            if runbook:
                logger.info(f"Found matching runbook: {runbook.get('name', 'unknown')}")
                context = {
                    'device': rca_result.get('root_cause', {}).get('root_cause_device', ''),
                    'metric': rca_result.get('root_cause', {}).get('root_cause_anomaly', {}).get('metric_name', ''),
                    'timestamp': rca_result.get('timestamp', '')
                }

                execution_result = self.runbook_executor.execute_runbook(runbook, context)
                logger.info(f"Runbook execution result: {execution_result}")

                # Publish action result
                self.publish_action({
                    'action': 'runbook_execution',
                    'runbook': runbook.get('name'),
                    'result': execution_result
                })
            else:
                logger.info("No matching runbook found")

            # 5. Send notifications (new step)
            logger.info("Step 5: Sending notifications...")
            self._send_notifications(rca_result, alert_level)

            logger.info("=" * 60)
            logger.info("RCA result processing completed with troubleshooting")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Error processing RCA result: {e}")

    def _send_notifications(self, rca_result: Dict, alert_level: str):
        """Send notifications based on alert level"""
        try:
            root_cause_anomaly = rca_result.get('root_cause', {}).get('root_cause_anomaly', {})

            # Only send notifications for high and critical alerts
            if alert_level not in ['high', 'critical']:
                logger.info(f"Alert level '{alert_level}' does not require notification")
                return

            # Create notification
            notification = Notification(
                title=f"AIOps 告警 - {root_cause_anomaly.get('metric_name', 'Unknown')}",
                message=rca_result.get('rca_summary', ''),
                severity=root_cause_anomaly.get('severity', 'medium'),
                alert_level=alert_level,
                timestamp=rca_result.get('timestamp', datetime.now().isoformat()),
                anomaly=root_cause_anomaly,
                troubleshooting=rca_result.get('troubleshooting'),
                jump_links=rca_result.get('jump_links'),
                recommendations=rca_result.get('troubleshooting', {}).get('fix_recommendations', [])
            )

            # Send notification
            if alert_level == 'critical':
                results = self.notification_service.send_critical_notification(notification)
            else:
                results = self.notification_service.send_notification(notification)

            # Log results
            for channel, success in results.items():
                if success:
                    logger.info(f"✓ Notification sent to {channel}")
                else:
                    logger.error(f"✗ Failed to send notification to {channel}")

        except Exception as e:
            logger.error(f"Error sending notifications: {e}")

    def run(self):
        """Main insights and action loop"""
        logger.info("Starting Insights & Action Service...")

        # Initialize connections
        if not self.connect_redis():
            return

        if not self.connect_kafka():
            return

        if not self.connect_neo4j():
            return

        logger.info("Insights & Action Service started successfully")

        try:
            for message in self.kafka_consumer:
                if not self.running:
                    break

                rca_result = message.value
                self.process_rca_result(rca_result)

        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        except Exception as e:
            logger.error(f"Fatal error in main loop: {e}")
        finally:
            self.shutdown()

    def shutdown(self):
        """Clean shutdown"""
        logger.info("Shutting down Insights & Action Service...")

        if self.kafka_consumer:
            self.kafka_consumer.close()
            logger.info("Kafka consumer closed")

        if self.kafka_producer:
            self.kafka_producer.close()
            logger.info("Kafka producer closed")

        if self.redis_client:
            self.redis_client.close()
            logger.info("Redis connection closed")

        if self.neo4j_driver:
            self.neo4j_driver.close()
            logger.info("Neo4j connection closed")

        logger.info("Insights & Action Service stopped")


if __name__ == '__main__':
    service = InsightsActionService()
    service.run()