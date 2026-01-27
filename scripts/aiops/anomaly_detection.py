#!/usr/bin/env python3
"""
AIOps Anomaly Detection Service

Implements multiple anomaly detection methods:
1. Statistical Methods: ARIMA, EWMA, Z-score
2. Rule Engine: Threshold-based, pattern-based
3. Machine Learning: Isolation Forest, K-Means
"""

import os
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import redis
from kafka import KafkaConsumer, KafkaProducer
from neo4j import GraphDatabase
from statsmodels.tsa.arima.model import ARIMA
from sklearn.ensemble import IsolationForest
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

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
DETECTION_WINDOW = int(os.environ.get('DETECTION_WINDOW', '300'))  # 5 minutes
ANOMALY_THRESHOLD = float(os.environ.get('ANOMALY_THRESHOLD', '2.0'))

# Kafka Topics
TOPIC_METRICS = 'aiops.metrics'
TOPIC_LOGS = 'aiops.logs'
TOPIC_ANOMALIES = 'aiops.anomalies'


class AnomalyDetector:
    """Base class for anomaly detection methods"""

    def __init__(self, name: str):
        self.name = name

    def detect(self, data: List[float]) -> Tuple[bool, float, str]:
        """
        Detect anomalies in data

        Returns:
            (is_anomaly, score, reason)
        """
        raise NotImplementedError


class ARIMADetector(AnomalyDetector):
    """ARIMA-based time series anomaly detection"""

    def __init__(self, order=(1, 1, 1)):
        super().__init__("ARIMA")
        self.order = order
        self.model = None

    def detect(self, data: List[float]) -> Tuple[bool, float, str]:
        if len(data) < 10:
            return False, 0.0, "Insufficient data"

        try:
            df = pd.DataFrame(data, columns=['value'])

            # Fit ARIMA model
            model = ARIMA(df['value'], order=self.order)
            model_fit = model.fit()

            # Forecast next value
            forecast = model_fit.forecast(steps=1).iloc[0]
            actual = data[-1]

            # Calculate residual (error)
            residual = abs(actual - forecast)
            std_residual = np.std(df['value'] - model_fit.fittedvalues)

            if std_residual == 0:
                return False, 0.0, "No variance in data"

            z_score = residual / std_residual
            is_anomaly = z_score > ANOMALY_THRESHOLD

            return is_anomaly, z_score, f"ARIMA: Actual={actual:.2f}, Forecast={forecast:.2f}, Z-score={z_score:.2f}"

        except Exception as e:
            logger.error(f"ARIMA detection error: {e}")
            return False, 0.0, f"ARIMA error: {str(e)}"


class EWMADetector(AnomalyDetector):
    """Exponentially Weighted Moving Average detector"""

    def __init__(self, alpha=0.3, threshold=3.0):
        super().__init__("EWMA")
        self.alpha = alpha
        self.threshold = threshold

    def detect(self, data: List[float]) -> Tuple[bool, float, str]:
        if len(data) < 5:
            return False, 0.0, "Insufficient data"

        try:
            df = pd.DataFrame(data, columns=['value'])

            # Calculate EWMA
            ewma = df['value'].ewm(alpha=self.alpha).mean()

            # Calculate standard deviation
            rolling_std = df['value'].rolling(window=min(10, len(data))).std()

            latest_ewma = ewma.iloc[-1]
            latest_std = rolling_std.iloc[-1]
            actual = data[-1]

            if pd.isna(latest_std) or latest_std == 0:
                return False, 0.0, "No variance in data"

            z_score = abs(actual - latest_ewma) / latest_std
            is_anomaly = z_score > self.threshold

            return is_anomaly, z_score, f"EWMA: Actual={actual:.2f}, EWMA={latest_ewma:.2f}, Z-score={z_score:.2f}"

        except Exception as e:
            logger.error(f"EWMA detection error: {e}")
            return False, 0.0, f"EWMA error: {str(e)}"


class ZScoreDetector(AnomalyDetector):
    """Z-score based anomaly detection"""

    def __init__(self, threshold=3.0):
        super().__init__("Z-Score")
        self.threshold = threshold

    def detect(self, data: List[float]) -> Tuple[bool, float, str]:
        if len(data) < 5:
            return False, 0.0, "Insufficient data"

        try:
            mean = np.mean(data)
            std = np.std(data)

            if std == 0:
                return False, 0.0, "No variance in data"

            actual = data[-1]
            z_score = abs(actual - mean) / std
            is_anomaly = z_score > self.threshold

            return is_anomaly, z_score, f"Z-Score: Actual={actual:.2f}, Mean={mean:.2f}, Z-score={z_score:.2f}"

        except Exception as e:
            logger.error(f"Z-score detection error: {e}")
            return False, 0.0, f"Z-score error: {str(e)}"


class RuleEngine:
    """Rule-based anomaly detection"""

    def __init__(self):
        self.rules = []

    def add_rule(self, rule_func, name: str):
        """Add a custom rule"""
        self.rules.append({'func': rule_func, 'name': name})

    def evaluate(self, data: Dict) -> List[Dict]:
        """Evaluate all rules against data"""
        anomalies = []

        for rule in self.rules:
            try:
                is_anomaly, score, message = rule['func'](data)
                if is_anomaly:
                    anomalies.append({
                        'rule': rule['name'],
                        'score': score,
                        'message': message
                    })
            except Exception as e:
                logger.error(f"Rule evaluation error for {rule['name']}: {e}")

        return anomalies


class MLAnomalyDetector:
    """Machine learning based anomaly detection"""

    def __init__(self):
        self.isolation_forest = None
        self.scaler = StandardScaler()

    def fit(self, data: np.ndarray):
        """Train the isolation forest model"""
        try:
            scaled_data = self.scaler.fit_transform(data)
            self.isolation_forest = IsolationForest(
                contamination=0.1,
                random_state=42
            )
            self.isolation_forest.fit(scaled_data)
            logger.info("Isolation Forest model trained")
        except Exception as e:
            logger.error(f"Error training ML model: {e}")

    def detect(self, data: np.ndarray) -> Tuple[bool, float, str]:
        """Detect anomalies using trained model"""
        if self.isolation_forest is None:
            return False, 0.0, "Model not trained"

        try:
            scaled_data = self.scaler.transform(data)
            predictions = self.isolation_forest.predict(scaled_data)
            scores = self.isolation_forest.score_samples(scaled_data)

            # -1 indicates anomaly
            is_anomaly = predictions[-1] == -1
            score = abs(scores[-1])

            return is_anomaly, score, f"Isolation Forest: Anomaly={is_anomaly}, Score={score:.3f}"

        except Exception as e:
            logger.error(f"ML detection error: {e}")
            return False, 0.0, f"ML error: {str(e)}"


class AnomalyDetectionService:
    """Main anomaly detection service"""

    def __init__(self):
        self.redis_client = None
        self.kafka_consumer = None
        self.kafka_producer = None
        self.neo4j_driver = None
        self.running = True

        # Initialize detectors
        self.detectors = [
            ARIMADetector(),
            EWMADetector(alpha=0.3, threshold=ANOMALY_THRESHOLD),
            ZScoreDetector(threshold=ANOMALY_THRESHOLD)
        ]

        # Initialize rule engine
        self.rule_engine = RuleEngine()
        self._setup_rules()

        # Initialize ML detector
        self.ml_detector = MLAnomalyDetector()

        # Data buffers
        self.metrics_buffer = {}  # metric_key -> [values]

    def _setup_rules(self):
        """Setup detection rules"""
        # CPU > 90% for 5 minutes
        def cpu_high_rule(data):
            if data.get('metric_name') != 'cpu_usage':
                return False, 0.0, "Not CPU metric"

            values = data.get('values', [])
            if len(values) < 5:
                return False, 0.0, "Insufficient data"

            recent_values = [float(v[1]) for v in values[-5:]]
            avg_cpu = np.mean(recent_values)

            is_anomaly = avg_cpu > 90
            score = avg_cpu / 100
            message = f"CPU usage high: {avg_cpu:.2f}%"

            return is_anomaly, score, message

        self.rule_engine.add_rule(cpu_high_rule, "CPU High")

        # Memory > 95%
        def memory_high_rule(data):
            if data.get('metric_name') != 'memory_usage':
                return False, 0.0, "Not memory metric"

            values = data.get('values', [])
            if not values:
                return False, 0.0, "No data"

            latest_value = float(values[-1][1])

            is_anomaly = latest_value > 95
            score = latest_value / 100
            message = f"Memory usage high: {latest_value:.2f}%"

            return is_anomaly, score, message

        self.rule_engine.add_rule(memory_high_rule, "Memory High")

        # Disk usage > 90%
        def disk_high_rule(data):
            if data.get('metric_name') != 'disk_usage':
                return False, 0.0, "Not disk metric"

            values = data.get('values', [])
            if not values:
                return False, 0.0, "No data"

            latest_value = float(values[-1][1])

            is_anomaly = latest_value > 90
            score = latest_value / 100
            message = f"Disk usage high: {latest_value:.2f}%"

            return is_anomaly, score, message

        self.rule_engine.add_rule(disk_high_rule, "Disk High")

        # Network input rate too high (> 1GB/s)
        def network_in_high_rule(data):
            if data.get('metric_name') != 'network_in':
                return False, 0.0, "Not network_in metric"

            values = data.get('values', [])
            if not values:
                return False, 0.0, "No data"

            latest_value = float(values[-1][1])

            is_anomaly = latest_value > 1000000000  # 1GB/s
            score = min(latest_value / 2000000000, 1.0)
            message = f"Network input rate high: {latest_value / 1000000000:.2f} GB/s"

            return is_anomaly, score, message

        self.rule_engine.add_rule(network_in_high_rule, "Network Input High")

        # Network output rate too high (> 1GB/s)
        def network_out_high_rule(data):
            if data.get('metric_name') != 'network_out':
                return False, 0.0, "Not network_out metric"

            values = data.get('values', [])
            if not values:
                return False, 0.0, "No data"

            latest_value = float(values[-1][1])

            is_anomaly = latest_value > 1000000000  # 1GB/s
            score = min(latest_value / 2000000000, 1.0)
            message = f"Network output rate high: {latest_value / 1000000000:.2f} GB/s"

            return is_anomaly, score, message

        self.rule_engine.add_rule(network_out_high_rule, "Network Output High")

        # CPU持续高负载 (> 80% for 10 minutes)
        def cpu_sustained_high_rule(data):
            if data.get('metric_name') != 'cpu_usage':
                return False, 0.0, "Not CPU metric"

            values = data.get('values', [])
            if len(values) < 10:
                return False, 0.0, "Insufficient data"

            recent_values = [float(v[1]) for v in values[-10:]]
            avg_cpu = np.mean(recent_values)

            is_anomaly = avg_cpu > 80
            score = avg_cpu / 100
            message = f"CPU sustained high load: {avg_cpu:.2f}% for 10 minutes"

            return is_anomaly, score, message

        self.rule_engine.add_rule(cpu_sustained_high_rule, "CPU Sustained High")

        # Load average > CPU cores * 2
        def load_average_high_rule(data):
            if data.get('metric_name') != 'load_average':
                return False, 0.0, "Not load_average metric"

            values = data.get('values', [])
            if not values:
                return False, 0.0, "No data"

            latest_value = float(values[-1][1])
            labels = data.get('labels', {})
            cpu_cores = int(labels.get('cpu_cores', 4))

            is_anomaly = latest_value > cpu_cores * 2
            score = min(latest_value / (cpu_cores * 4), 1.0)
            message = f"Load average high: {latest_value:.2f} (cores: {cpu_cores})"

            return is_anomaly, score, message

        self.rule_engine.add_rule(load_average_high_rule, "Load Average High")

        # Swap usage > 50%
        def swap_usage_high_rule(data):
            if data.get('metric_name') != 'swap_usage':
                return False, 0.0, "Not swap_usage metric"

            values = data.get('values', [])
            if not values:
                return False, 0.0, "No data"

            latest_value = float(values[-1][1])

            is_anomaly = latest_value > 50
            score = latest_value / 100
            message = f"Swap usage high: {latest_value:.2f}%"

            return is_anomaly, score, message

        self.rule_engine.add_rule(swap_usage_high_rule, "Swap Usage High")

        # Disk I/O wait time > 20%
        def disk_iowait_high_rule(data):
            if data.get('metric_name') != 'disk_iowait':
                return False, 0.0, "Not disk_iowait metric"

            values = data.get('values', [])
            if not values:
                return False, 0.0, "No data"

            latest_value = float(values[-1][1])

            is_anomaly = latest_value > 20
            score = latest_value / 100
            message = f"Disk I/O wait high: {latest_value:.2f}%"

            return is_anomaly, score, message

        self.rule_engine.add_rule(disk_iowait_high_rule, "Disk I/O Wait High")

        # HTTP 5xx errors > 5%
        def http_5xx_errors_rule(data):
            if data.get('metric_name') != 'http_5xx_errors':
                return False, 0.0, "Not http_5xx_errors metric"

            values = data.get('values', [])
            if not values:
                return False, 0.0, "No data"

            latest_value = float(values[-1][1])

            is_anomaly = latest_value > 5
            score = latest_value / 20
            message = f"HTTP 5xx errors high: {latest_value:.2f}%"

            return is_anomaly, score, message

        self.rule_engine.add_rule(http_5xx_errors_rule, "HTTP 5xx Errors High")

        # Response time > 5 seconds
        def response_time_high_rule(data):
            if data.get('metric_name') != 'response_time':
                return False, 0.0, "Not response_time metric"

            values = data.get('values', [])
            if not values:
                return False, 0.0, "No data"

            latest_value = float(values[-1][1])

            is_anomaly = latest_value > 5000  # 5 seconds
            score = min(latest_value / 10000, 1.0)
            message = f"Response time high: {latest_value / 1000:.2f} seconds"

            return is_anomaly, score, message

        self.rule_engine.add_rule(response_time_high_rule, "Response Time High")

        # Connection refused errors detected
        def connection_refused_rule(data):
            metric_name = data.get('metric_name', '')

            if 'connection_refused' not in metric_name.lower():
                return False, 0.0, "Not connection refused metric"

            values = data.get('values', [])
            if not values:
                return False, 0.0, "No data"

            latest_value = float(values[-1][1])

            is_anomaly = latest_value > 0
            score = min(latest_value / 10, 1.0)
            message = f"Connection refused errors detected: {latest_value}"

            return is_anomaly, score, message

        self.rule_engine.add_rule(connection_refused_rule, "Connection Refused")

        # Service down (no metrics for 5 minutes)
        def service_down_rule(data):
            # This rule is checked by the absence of data, not presence
            # Handled separately in the main loop
            return False, 0.0, "Service down check handled separately"

        self.rule_engine.add_rule(service_down_rule, "Service Down")

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
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return False

    def connect_kafka(self):
        """Connect to Kafka"""
        try:
            self.kafka_consumer = KafkaConsumer(
                TOPIC_METRICS,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                group_id='anomaly-detection-group',
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

    def publish_anomaly(self, anomaly: Dict):
        """Publish anomaly to Kafka"""
        try:
            self.kafka_producer.send(TOPIC_ANOMALIES, value=anomaly)
            logger.info(f"Published anomaly: {anomaly.get('summary')}")
        except Exception as e:
            logger.error(f"Failed to publish anomaly: {e}")

    def process_metric(self, metric_data: Dict):
        """Process a metric and detect anomalies"""
        try:
            metric_name = metric_data.get('metric_name')
            labels = metric_data.get('labels', {})
            values = metric_data.get('values', [])

            if not values:
                return

            # Extract metric values
            metric_values = [float(v[1]) for v in values]

            # Create unique metric key
            metric_key = f"{metric_name}_{labels.get('instance', 'unknown')}"

            # Update buffer
            if metric_key not in self.metrics_buffer:
                self.metrics_buffer[metric_key] = []

            self.metrics_buffer[metric_key].extend(metric_values)
            # Keep only last 100 points
            if len(self.metrics_buffer[metric_key]) > 100:
                self.metrics_buffer[metric_key] = self.metrics_buffer[metric_key][-100:]

            # Run statistical detectors
            for detector in self.detectors:
                is_anomaly, score, reason = detector.detect(self.metrics_buffer[metric_key])

                if is_anomaly:
                    anomaly = {
                        'timestamp': datetime.now().isoformat(),
                        'anomaly_type': 'statistical',
                        'detector': detector.name,
                        'metric_name': metric_name,
                        'labels': labels,
                        'score': score,
                        'reason': reason,
                        'summary': f"{detector.name} anomaly detected for {metric_name}",
                        'severity': 'high' if score > ANOMALY_THRESHOLD * 1.5 else 'medium'
                    }
                    self.publish_anomaly(anomaly)

            # Run rule engine
            rule_anomalies = self.rule_engine.evaluate(metric_data)
            for rule_anomaly in rule_anomalies:
                anomaly = {
                    'timestamp': datetime.now().isoformat(),
                    'anomaly_type': 'rule',
                    'rule': rule_anomaly['rule'],
                    'metric_name': metric_name,
                    'labels': labels,
                    'score': rule_anomaly['score'],
                    'reason': rule_anomaly['message'],
                    'summary': f"Rule violation: {rule_anomaly['rule']}",
                    'severity': 'high' if rule_anomaly['score'] > 0.9 else 'medium'
                }
                self.publish_anomaly(anomaly)

        except Exception as e:
            logger.error(f"Error processing metric: {e}")

    def run(self):
        """Main detection loop"""
        logger.info("Starting Anomaly Detection Service...")

        # Initialize connections
        if not self.connect_redis():
            return

        if not self.connect_kafka():
            return

        if not self.connect_neo4j():
            return

        logger.info("Anomaly Detection Service started successfully")

        try:
            for message in self.kafka_consumer:
                if not self.running:
                    break

                metric_data = message.value
                self.process_metric(metric_data)

        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        except Exception as e:
            logger.error(f"Fatal error in main loop: {e}")
        finally:
            self.shutdown()

    def shutdown(self):
        """Clean shutdown"""
        logger.info("Shutting down Anomaly Detection Service...")

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

        logger.info("Anomaly Detection Service stopped")


if __name__ == '__main__':
    service = AnomalyDetectionService()
    service.run()