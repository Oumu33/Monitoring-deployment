#!/usr/bin/env python3
"""
AIOps Root Cause Analysis Service

Implements:
1. Graph Dependency Analysis - Neo4j queries and graph algorithms
2. Causal Inference - Event correlation and anomaly propagation
3. Root Cause Localization - Heuristic rules and ML-based inference
"""

import os
import json
import logging
import networkx as nx
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
import redis
from kafka import KafkaConsumer, KafkaProducer
from neo4j import GraphDatabase
from collections import defaultdict, deque

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
CORRELATION_WINDOW = int(os.environ.get('CORRELATION_WINDOW', '600'))  # 10 minutes
MAX_GRAPH_DEPTH = int(os.environ.get('MAX_GRAPH_DEPTH', '5'))

# Kafka Topics
TOPIC_ANOMALIES = 'aiops.anomalies'
TOPIC_RCA_RESULTS = 'aiops.rca_results'


class GraphDependencyAnalyzer:
    """Analyzes dependencies in the infrastructure graph"""

    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver

    def get_upstream_dependencies(self, node_name: str, max_depth: int = 3) -> List[Dict]:
        """
        Get upstream dependencies (devices/services that this node depends on)
        """
        query = f"""
        MATCH (target:Device {{name: $node_name}})
        MATCH (target)<-[:CONNECTS_TO*1..{max_depth}]-(source:Device)
        RETURN source.name AS name, source.ip AS ip, source.type AS type,
               length(path) AS distance, path AS path
        ORDER BY distance ASC
        """
        with self.driver.session() as session:
            result = session.run(query, node_name=node_name)
            return [record.data() for record in result]

    def get_downstream_dependencies(self, node_name: str, max_depth: int = 3) -> List[Dict]:
        """
        Get downstream dependencies (devices/services that depend on this node)
        """
        query = f"""
        MATCH (source:Device {{name: $node_name}})
        MATCH (source)-[:CONNECTS_TO*1..{max_depth}]->(target:Device)
        RETURN target.name AS name, target.ip AS ip, target.type AS type,
               length(path) AS distance, path AS path
        ORDER BY distance ASC
        """
        with self.driver.session() as session:
            result = session.run(query, node_name=node_name)
            return [record.data() for record in result]

    def get_shortest_path(self, source: str, target: str) -> Optional[List[Dict]]:
        """
        Get shortest path between two devices
        """
        query = """
        MATCH path = shortestPath(
            (a:Device {name: $source})-[:CONNECTS_TO*]-(b:Device {name: $target})
        )
        RETURN [node IN nodes(path) | {
            name: node.name,
            ip: node.ip,
            type: node.type
        }] AS path
        """
        with self.driver.session() as session:
            result = session.run(query, source=source, target=target)
            record = result.single()
            return record['path'] if record else None

    def get_centrality_metrics(self) -> Dict[str, Dict]:
        """
        Calculate centrality metrics for all devices
        - Degree centrality: Number of connections
        - Betweenness centrality: How often a node appears on shortest paths
        - Closeness centrality: Average distance to all other nodes
        """
        # Get all nodes and edges
        query = """
        MATCH (d:Device)
        OPTIONAL MATCH (d)-[r:CONNECTS_TO]->(other:Device)
        WITH d, count(r) AS degree
        RETURN d.name AS name, d.ip AS ip, d.type AS type, degree
        """
        with self.driver.session() as session:
            result = session.run(query)
            nodes = []
            for record in result:
                nodes.append({
                    'name': record['name'],
                    'ip': record['ip'],
                    'type': record['type'],
                    'degree': record['degree']
                })

        # Build NetworkX graph
        G = nx.Graph()
        for node in nodes:
            G.add_node(node['name'], **node)

        # Add edges
        query = """
        MATCH (a:Device)-[r:CONNECTS_TO]->(b:Device)
        RETURN a.name AS source, b.name AS target
        """
        with self.driver.session() as session:
            result = session.run(query)
            for record in result:
                G.add_edge(record['source'], record['target'])

        # Calculate centrality metrics
        metrics = {}
        degree_cent = nx.degree_centrality(G)
        betweenness_cent = nx.betweenness_centrality(G)
        closeness_cent = nx.closeness_centrality(G)

        for node_name in G.nodes():
            metrics[node_name] = {
                'degree_centrality': degree_cent.get(node_name, 0),
                'betweenness_centrality': betweenness_cent.get(node_name, 0),
                'closeness_centrality': closeness_cent.get(node_name, 0)
            }

        return metrics

    def find_critical_path(self, start_node: str, end_node: str) -> Optional[List[str]]:
        """
        Find critical path considering centrality metrics
        """
        # Get centrality metrics
        centrality = self.get_centrality_metrics()

        # Build weighted graph (inverse of betweenness centrality)
        query = """
        MATCH (a:Device)-[r:CONNECTS_TO]->(b:Device)
        RETURN a.name AS source, b.name AS target
        """
        with self.driver.session() as session:
            result = session.run(query)

        G = nx.DiGraph()
        for record in result:
            weight = 1.0 / (centrality.get(record['source'], {}).get('betweenness_centrality', 0.01) + 0.01)
            G.add_edge(record['source'], record['target'], weight=weight)

        try:
            path = nx.shortest_path(G, source=start_node, target=end_node, weight='weight')
            return path
        except nx.NetworkXNoPath:
            return None

    def get_device_neighbors(self, device_name: str) -> Dict[str, List[str]]:
        """
        Get all neighbors of a device (both upstream and downstream)
        """
        query = """
        MATCH (d:Device {name: $device_name})
        OPTIONAL MATCH (d)-[r_out:CONNECTS_TO]->(downstream:Device)
        OPTIONAL MATCH (d)<-[r_in:CONNECTS_TO]-(upstream:Device)
        WITH d,
             collect(DISTINCT downstream.name) AS downstream_neighbors,
             collect(DISTINCT upstream.name) AS upstream_neighbors
        RETURN downstream_neighbors, upstream_neighbors
        """
        with self.driver.session() as session:
            result = session.run(query, device_name=device_name)
            record = result.single()
            if record:
                return {
                    'downstream': record['downstream_neighbors'],
                    'upstream': record['upstream_neighbors']
                }
            return {'downstream': [], 'upstream': []}


class EventCorrelator:
    """Correlates events based on temporal and spatial proximity"""

    def __init__(self, correlation_window: int = 600):
        self.correlation_window = correlation_window  # seconds
        self.event_buffer = []
        self.redis_client = None

    def connect_redis(self, host: str, port: int):
        """Connect to Redis for persistence"""
        try:
            self.redis_client = redis.Redis(host=host, port=port, decode_responses=True)
            self.redis_client.ping()
            logger.info(f"EventCorrelator connected to Redis at {host}:{port}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")

    def add_event(self, event: Dict):
        """Add an event to the buffer"""
        event['timestamp'] = datetime.fromisoformat(event['timestamp'])
        self.event_buffer.append(event)

        # Keep only events within correlation window
        cutoff_time = datetime.now() - timedelta(seconds=self.correlation_window)
        self.event_buffer = [
            e for e in self.event_buffer
            if e['timestamp'] > cutoff_time
        ]

    def correlate_events(self, new_event: Dict) -> List[Dict]:
        """
        Find correlated events with the new event
        """
        new_event_time = datetime.fromisoformat(new_event['timestamp'])
        correlated = []

        for event in self.event_buffer:
            time_diff = abs((new_event_time - event['timestamp']).total_seconds())

            if time_diff <= self.correlation_window:
                correlation_score = self._calculate_correlation_score(new_event, event, time_diff)
                if correlation_score > 0.5:  # Threshold for correlation
                    correlated.append({
                        'event': event,
                        'score': correlation_score,
                        'time_diff': time_diff
                    })

        return sorted(correlated, key=lambda x: x['score'], reverse=True)

    def _calculate_correlation_score(self, event1: Dict, event2: Dict, time_diff: float) -> float:
        """Calculate correlation score between two events"""
        score = 0.0

        # Temporal proximity (closer = higher score)
        temporal_score = 1.0 - (time_diff / self.correlation_window)
        score += temporal_score * 0.4

        # Same metric type
        if event1.get('metric_name') == event2.get('metric_name'):
            score += 0.3

        # Same device (instance)
        labels1 = event1.get('labels', {})
        labels2 = event2.get('labels', {})
        if labels1.get('instance') == labels2.get('instance'):
            score += 0.3

        return score


class AnomalyPropagationAnalyzer:
    """Analyzes how anomalies propagate through the dependency graph"""

    def __init__(self, graph_analyzer: GraphDependencyAnalyzer):
        self.graph_analyzer = graph_analyzer

    def find_propagation_chain(self, anomaly: Dict, direction: str = 'both') -> List[Dict]:
        """
        Find propagation chain for an anomaly
        direction: 'upstream', 'downstream', or 'both'
        """
        device_name = anomaly.get('labels', {}).get('instance', '').split(':')[0]

        propagation_chain = []

        if direction in ['upstream', 'both']:
            upstream = self.graph_analyzer.get_upstream_dependencies(device_name, max_depth=MAX_GRAPH_DEPTH)
            for node in upstream:
                propagation_chain.append({
                    'direction': 'upstream',
                    'device': node['name'],
                    'distance': node['distance'],
                    'type': node['type']
                })

        if direction in ['downstream', 'both']:
            downstream = self.graph_analyzer.get_downstream_dependencies(device_name, max_depth=MAX_GRAPH_DEPTH)
            for node in downstream:
                propagation_chain.append({
                    'direction': 'downstream',
                    'device': node['name'],
                    'distance': node['distance'],
                    'type': node['type']
                })

        return propagation_chain

    def find_propagation_source(self, anomalies: List[Dict]) -> Optional[Dict]:
        """
        Find the likely source of anomaly propagation
        """
        # Build propagation chains for all anomalies
        all_chains = []
        for anomaly in anomalies:
            chain = self.find_propagation_chain(anomaly, direction='upstream')
            all_chains.append({
                'anomaly': anomaly,
                'chain': chain
            })

        # Find common upstream nodes
        upstream_counts = defaultdict(int)
        for chain_data in all_chains:
            for node in chain_data['chain']:
                if node['direction'] == 'upstream':
                    upstream_counts[node['device']] += 1

        if not upstream_counts:
            return None

        # Return the most common upstream node
        most_common_device = max(upstream_counts.items(), key=lambda x: x[1])
        return {
            'device': most_common_device[0],
            'occurrence_count': most_common_device[1]
        }


class RootCauseInferenceEngine:
    """Infers root causes using heuristic rules and ML"""

    def __init__(self, graph_analyzer: GraphDependencyAnalyzer):
        self.graph_analyzer = graph_analyzer

    def infer_root_cause(self, anomalies: List[Dict]) -> Dict:
        """
        Infer root cause from a set of anomalies
        """
        if not anomalies:
            return {}

        # Get centrality metrics
        centrality = self.graph_analyzer.get_centrality_metrics()

        # Score each potential root cause
        candidates = []

        for anomaly in anomalies:
            device = anomaly.get('labels', {}).get('instance', '').split(':')[0]

            # Get centrality score
            device_centrality = centrality.get(device, {})
            centrality_score = (
                device_centrality.get('betweenness_centrality', 0) * 0.5 +
                device_centrality.get('degree_centrality', 0) * 0.3 +
                device_centrality.get('closeness_centrality', 0) * 0.2
            )

            # Get anomaly severity
            severity = anomaly.get('severity', 'medium')
            severity_score = {'low': 0.3, 'medium': 0.6, 'high': 1.0}.get(severity, 0.5)

            # Get anomaly score
            anomaly_score = anomaly.get('score', 0.5)

            # Combined score
            combined_score = centrality_score * 0.4 + severity_score * 0.3 + anomaly_score * 0.3

            candidates.append({
                'device': device,
                'anomaly': anomaly,
                'centrality_score': centrality_score,
                'severity_score': severity_score,
                'anomaly_score': anomaly_score,
                'combined_score': combined_score
            })

        # Sort by combined score
        candidates.sort(key=lambda x: x['combined_score'], reverse=True)

        if not candidates:
            return {}

        top_candidate = candidates[0]

        # Generate root cause explanation
        explanation = self._generate_explanation(top_candidate, candidates[:5])

        return {
            'root_cause_device': top_candidate['device'],
            'root_cause_anomaly': top_candidate['anomaly'],
            'confidence': top_candidate['combined_score'],
            'explanation': explanation,
            'candidates': candidates[:5]
        }

    def _generate_explanation(self, top_candidate: Dict, all_candidates: List[Dict]) -> str:
        """Generate human-readable explanation"""
        device = top_candidate['device']
        anomaly = top_candidate['anomaly']

        anomaly_type = anomaly.get('anomaly_type', 'unknown')
        metric = anomaly.get('metric_name', 'unknown metric')
        reason = anomaly.get('reason', '')

        explanation = (
            f"Root cause identified on device '{device}' based on:\n"
            f"- Anomaly type: {anomaly_type}\n"
            f"- Affected metric: {metric}\n"
            f"- Detection reason: {reason}\n"
            f"- Centrality score: {top_candidate['centrality_score']:.3f} (network position)\n"
            f"- Severity: {top_candidate['severity_score']:.3f}\n"
            f"- Anomaly score: {top_candidate['anomaly_score']:.3f}\n"
            f"- Overall confidence: {top_candidate['combined_score']:.3f}"
        )

        return explanation


class RootCauseAnalysisService:
    """Main RCA service"""

    def __init__(self):
        self.redis_client = None
        self.kafka_consumer = None
        self.kafka_producer = None
        self.neo4j_driver = None
        self.running = True

        # Initialize components
        self.graph_analyzer = None
        self.event_correlator = EventCorrelator(correlation_window=CORRELATION_WINDOW)
        self.propagation_analyzer = None
        self.inference_engine = None

        # Anomaly buffer
        self.anomaly_buffer = []

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
                TOPIC_ANOMALIES,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                group_id='rca-group',
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

            # Initialize components
            self.graph_analyzer = GraphDependencyAnalyzer(self.neo4j_driver)
            self.propagation_analyzer = AnomalyPropagationAnalyzer(self.graph_analyzer)
            self.inference_engine = RootCauseInferenceEngine(self.graph_analyzer)

            return True
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            return False

    def publish_rca_result(self, rca_result: Dict):
        """Publish RCA result to Kafka"""
        try:
            self.kafka_producer.send(TOPIC_RCA_RESULTS, value=rca_result)
            logger.info(f"Published RCA result: {rca_result.get('root_cause_device', 'unknown')}")
        except Exception as e:
            logger.error(f"Failed to publish RCA result: {e}")

    def process_anomaly(self, anomaly: Dict):
        """Process a single anomaly"""
        try:
            # Add to event correlator
            self.event_correlator.add_event(anomaly)

            # Add to anomaly buffer
            self.anomaly_buffer.append(anomaly)

            # Keep only anomalies within correlation window
            cutoff_time = datetime.now() - timedelta(seconds=CORRELATION_WINDOW)
            self.anomaly_buffer = [
                a for a in self.anomaly_buffer
                if datetime.fromisoformat(a['timestamp']) > cutoff_time
            ]

            # Find correlated events
            correlated = self.event_correlator.correlate_events(anomaly)

            if correlated:
                logger.info(f"Found {len(correlated)} correlated events for anomaly")

                # If we have multiple correlated anomalies, perform RCA
                if len(correlated) >= 2:
                    correlated_anomalies = [anomaly] + [c['event'] for c in correlated]

                    # Find propagation source
                    propagation_source = self.propagation_analyzer.find_propagation_source(
                        correlated_anomalies
                    )

                    # Infer root cause
                    root_cause = self.inference_engine.infer_root_cause(correlated_anomalies)

                    # Build RCA result
                    rca_result = {
                        'timestamp': datetime.now().isoformat(),
                        'trigger_anomaly': anomaly,
                        'correlated_anomalies': correlated_anomalies,
                        'propagation_source': propagation_source,
                        'root_cause': root_cause,
                        'rca_summary': self._generate_rca_summary(anomaly, correlated_anomalies, root_cause)
                    }

                    self.publish_rca_result(rca_result)

        except Exception as e:
            logger.error(f"Error processing anomaly: {e}")

    def _generate_rca_summary(self, trigger_anomaly: Dict, correlated: List[Dict], root_cause: Dict) -> str:
        """Generate RCA summary"""
        if not root_cause:
            return f"RCA incomplete: Insufficient correlated events (found {len(correlated)} anomalies)"

        device = root_cause.get('root_cause_device', 'unknown')
        confidence = root_cause.get('confidence', 0)

        summary = (
            f"Root Cause Analysis completed:\n"
            f"- Trigger: {trigger_anomaly.get('summary', 'unknown')}\n"
            f"- Correlated anomalies: {len(correlated)}\n"
            f"- Root cause device: {device}\n"
            f"- Confidence: {confidence:.2%}\n"
            f"- Explanation: {root_cause.get('explanation', 'N/A')}"
        )

        return summary

    def run(self):
        """Main RCA loop"""
        logger.info("Starting Root Cause Analysis Service...")

        # Initialize connections
        if not self.connect_redis():
            return

        if not self.connect_kafka():
            return

        if not self.connect_neo4j():
            return

        logger.info("Root Cause Analysis Service started successfully")

        try:
            for message in self.kafka_consumer:
                if not self.running:
                    break

                anomaly = message.value
                self.process_anomaly(anomaly)

        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        except Exception as e:
            logger.error(f"Fatal error in main loop: {e}")
        finally:
            self.shutdown()

    def shutdown(self):
        """Clean shutdown"""
        logger.info("Shutting down Root Cause Analysis Service...")

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

        logger.info("Root Cause Analysis Service stopped")


if __name__ == '__main__':
    service = RootCauseAnalysisService()
    service.run()
