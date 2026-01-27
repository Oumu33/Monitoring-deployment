#!/usr/bin/env python3
"""
AIOps Data Ingestion Service

Real-time data collection from:
- VictoriaMetrics (Metrics)
- Loki (Logs)
- Tempo (Traces)

Pushes data to Kafka topics for downstream processing.
"""

import os
import time
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import redis
from kafka import KafkaProducer

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
VICTORIAMETRICS_URL = os.environ.get('VICTORIAMETRICS_URL', 'http://victoriametrics:8428')
LOKI_URL = os.environ.get('LOKI_URL', 'http://loki:3100')
TEMPO_URL = os.environ.get('TEMPO_URL', 'http://tempo:3200')
INGESTION_INTERVAL = int(os.environ.get('INGESTION_INTERVAL', '30'))

# Kafka Topics
TOPIC_METRICS = 'aiops.metrics'
TOPIC_LOGS = 'aiops.logs'
TOPIC_TRACES = 'aiops.traces'
TOPIC_EVENTS = 'aiops.events'


class DataIngestionService:
    """Main data ingestion service"""

    def __init__(self):
        self.redis_client = None
        self.kafka_producer = None
        self.running = True

    def connect_redis(self):
        """Connect to Redis for caching"""
        try:
            self.redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                decode_responses=True
            )
            self.redis_client.ping()
            logger.info(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return False

    def connect_kafka(self):
        """Connect to Kafka for message publishing"""
        try:
            self.kafka_producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all',
                retries=3
            )
            logger.info(f"Connected to Kafka at {KAFKA_BOOTSTRAP_SERVERS}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            return False

    def publish_to_kafka(self, topic: str, data: Dict):
        """Publish data to Kafka topic"""
        try:
            future = self.kafka_producer.send(topic, value=data)
            future.get(timeout=10)
            logger.debug(f"Published to {topic}: {data.get('timestamp', data.get('time'))}")
        except Exception as e:
            logger.error(f"Failed to publish to {topic}: {e}")

    # ==================== Metrics Ingestion ====================

    def collect_victoriametrics_metrics(self):
        """
        Collect metrics from VictoriaMetrics
        Focus on system metrics (CPU, memory, disk, network)
        """
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=5)

            # Query key system metrics
            queries = {
                'cpu_usage': 'avg by (instance) (100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100))',
                'memory_usage': 'avg by (instance) ((node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100)',
                'disk_usage': 'avg by (instance, mountpoint) ((node_filesystem_size_bytes - node_filesystem_avail_bytes) / node_filesystem_size_bytes * 100)',
                'network_in': 'sum by (instance) (rate(node_network_receive_bytes_total[5m]))',
                'network_out': 'sum by (instance) (rate(node_network_transmit_bytes_total[5m]))'
            }

            metrics_data = []

            for metric_name, query in queries.items():
                try:
                    params = {
                        'query': query,
                        'start': start_time.timestamp(),
                        'end': end_time.timestamp(),
                        'step': '1m'
                    }

                    response = requests.get(
                        f"{VICTORIAMETRICS_URL}/api/v1/query_range",
                        params=params,
                        timeout=30
                    )
                    response.raise_for_status()

                    result = response.json()
                    if result.get('status') == 'success':
                        for metric in result.get('data', {}).get('result', []):
                            metric_info = {
                                'metric_name': metric_name,
                                'labels': metric.get('metric', {}),
                                'values': metric.get('values', []),
                                'timestamp': datetime.now().isoformat(),
                                'source': 'victoriametrics'
                            }
                            metrics_data.append(metric_info)

                            # Publish to Kafka
                            self.publish_to_kafka(TOPIC_METRICS, metric_info)

                except Exception as e:
                    logger.error(f"Failed to collect metric {metric_name}: {e}")

            logger.info(f"Collected {len(metrics_data)} metrics from VictoriaMetrics")
            return metrics_data

        except Exception as e:
            logger.error(f"Error collecting VictoriaMetrics data: {e}")
            return []

    # ==================== Logs Ingestion ====================

    def collect_loki_logs(self):
        """
        Collect error/warning logs from Loki
        """
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=5)

            # Query for error and warning logs
            query = '{level=~"error|warn|warning"}'

            params = {
                'query': query,
                'start': start_time.isoformat() + 'Z',
                'end': end_time.isoformat() + 'Z',
                'limit': '100'
            }

            response = requests.get(
                f"{LOKI_URL}/loki/api/v1/query_range",
                params=params,
                timeout=30
            )
            response.raise_for_status()

            result = response.json()
            logs_data = []

            if result.get('status') == 'success':
                for stream in result.get('data', {}).get('result', []):
                    stream_labels = stream.get('stream', {})
                    for value in stream.get('values', []):
                        log_entry = {
                            'timestamp': value[0],
                            'log_line': value[1],
                            'labels': stream_labels,
                            'source': 'loki',
                            'collected_at': datetime.now().isoformat()
                        }
                        logs_data.append(log_entry)

                        # Publish to Kafka
                        self.publish_to_kafka(TOPIC_LOGS, log_entry)

            logger.info(f"Collected {len(logs_data)} error/warning logs from Loki")
            return logs_data

        except Exception as e:
            logger.error(f"Error collecting Loki logs: {e}")
            return []

    # ==================== Traces Ingestion ====================

    def collect_tempo_traces(self):
        """
        Collect recent traces from Tempo
        """
        try:
            # Search for traces in the last 5 minutes
            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=5)

            params = {
                'start': int(start_time.timestamp() * 1000000),  # microseconds
                'end': int(end_time.timestamp() * 1000000),
                'minDuration': '1000000',  # 1ms minimum
                'limit': 50
            }

            response = requests.get(
                f"{TEMPO_URL}/api/search",
                params=params,
                timeout=30
            )

            if response.status_code == 200:
                traces = response.json()
                traces_data = []

                for trace in traces.get('traces', []):
                    trace_id = trace.get('traceID')
                    if trace_id:
                        # Get trace details
                        trace_detail = self._get_trace_detail(trace_id)
                        if trace_detail:
                            traces_data.append(trace_detail)
                            self.publish_to_kafka(TOPIC_TRACES, trace_detail)

                logger.info(f"Collected {len(traces_data)} traces from Tempo")
                return traces_data
            else:
                logger.warning(f"Tempo search failed: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Error collecting Tempo traces: {e}")
            return []

    def _get_trace_detail(self, trace_id: str) -> Optional[Dict]:
        """Get detailed information about a specific trace"""
        try:
            response = requests.get(
                f"{TEMPO_URL}/api/traces/{trace_id}",
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            if data and 'batches' in data:
                spans = []
                total_duration = 0

                for batch in data.get('batches', []):
                    for span in batch.get('spans', []):
                        span_info = {
                            'span_id': span.get('spanID'),
                            'parent_span_id': span.get('parentSpanID'),
                            'operation': span.get('operationName'),
                            'service': span.get('process', {}).get('serviceName'),
                            'start_time': span.get('startTime'),
                            'duration': span.get('duration'),
                            'tags': span.get('tags', {})
                        }
                        spans.append(span_info)
                        total_duration = max(total_duration, span.get('duration', 0))

                return {
                    'trace_id': trace_id,
                    'spans': spans,
                    'total_duration': total_duration,
                    'span_count': len(spans),
                    'source': 'tempo',
                    'collected_at': datetime.now().isoformat()
                }

        except Exception as e:
            logger.error(f"Error getting trace detail {trace_id}: {e}")

        return None

    # ==================== Main Loop ====================

    def run(self):
        """Main ingestion loop"""
        logger.info("Starting Data Ingestion Service...")

        # Initialize connections
        if not self.connect_redis():
            logger.error("Failed to connect to Redis. Retrying...")
            return

        if not self.connect_kafka():
            logger.error("Failed to connect to Kafka. Retrying...")
            return

        logger.info("Data Ingestion Service started successfully")

        try:
            while self.running:
                cycle_start = time.time()

                logger.info("=" * 60)
                logger.info("Starting new data collection cycle")
                logger.info("=" * 60)

                # Collect metrics
                self.collect_victoriametrics_metrics()

                # Collect logs
                self.collect_loki_logs()

                # Collect traces
                self.collect_tempo_traces()

                # Calculate sleep time
                cycle_duration = time.time() - cycle_start
                sleep_time = max(0, INGESTION_INTERVAL - cycle_duration)

                logger.info(f"Cycle completed in {cycle_duration:.2f}s. Sleeping for {sleep_time:.2f}s...")
                time.sleep(sleep_time)

        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        except Exception as e:
            logger.error(f"Fatal error in main loop: {e}")
        finally:
            self.shutdown()

    def shutdown(self):
        """Clean shutdown"""
        logger.info("Shutting down Data Ingestion Service...")

        if self.kafka_producer:
            self.kafka_producer.close()
            logger.info("Kafka producer closed")

        if self.redis_client:
            self.redis_client.close()
            logger.info("Redis connection closed")

        logger.info("Data Ingestion Service stopped")


if __name__ == '__main__':
    service = DataIngestionService()
    service.run()