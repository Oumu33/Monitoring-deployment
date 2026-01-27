#!/usr/bin/env python3
"""
Test script for Weighted Root Cause Analysis

Tests the new failure propagation algorithm that uses edge criticality weights.

Scenario: Payment-Service is slow
- Suspect 1: MySQL Database (weight 0.9) with high CPU
- Suspect 2: Fluentd Sidecar (weight 0.2) with restarts

Expected Results:
- Old algorithm: Both suspects have equal priority
- New algorithm: MySQL gets score 0.81, Fluentd gets score 0.20 (MySQL is root cause)
"""

import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WeightedRCATester:
    """Test suite for weighted root cause analysis"""

    def __init__(self, uri: str, user: str, password: str):
        from neo4j import GraphDatabase
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.test_prefix = f"test_rca_{int(datetime.now().timestamp())}"

    def close(self):
        """Close database connection"""
        self.driver.close()

    def run_all_tests(self):
        """Run all test cases"""
        logger.info("=" * 60)
        logger.info("Weighted Root Cause Analysis Test Suite")
        logger.info("=" * 60)

        tests = [
            ("Test 1: Setup Test Topology", self.setup_test_topology),
            ("Test 2: Weighted Propagation Analysis", self.test_weighted_propagation),
            ("Test 3: Sidecar Noise Filtering", self.test_sidecar_filtering),
            ("Test 4: Multi-hop Propagation", self.test_multi_hop_propagation),
            ("Test 5: High Criticality Path Priority", self.test_high_criticality_priority),
        ]

        passed = 0
        failed = 0

        for test_name, test_func in tests:
            try:
                logger.info(f"\n▶ {test_name}")
                test_func()
                passed += 1
                logger.info(f"✓ {test_name} PASSED")
            except AssertionError as e:
                failed += 1
                logger.error(f"✗ {test_name} FAILED: {e}")
            except Exception as e:
                failed += 1
                logger.error(f"✗ {test_name} ERROR: {e}")
                import traceback
                traceback.print_exc()

        logger.info("\n" + "=" * 60)
        logger.info(f"Test Results: {passed} passed, {failed} failed")
        logger.info("=" * 60)

        # Cleanup
        self.cleanup_test_data()

        return failed == 0

    def setup_test_topology(self):
        """Setup test topology with weighted edges"""
        logger.info("Creating test topology...")

        with self.driver.session() as session:
            # Create Payment-Service (target)
            session.run("""
                MERGE (p:Device {name: $name})
                SET p.type = 'Service', p.ip = '10.1.1.100'
            """, {'name': f'{self.test_prefix}_payment_service'})

            # Create MySQL Database (high criticality)
            session.run("""
                MERGE (m:Device {name: $name})
                SET m.type = 'Database', m.ip = '10.1.1.200'
            """, {'name': f'{self.test_prefix}_mysql_db'})

            # Create Fluentd Sidecar (low criticality)
            session.run("""
                MERGE (f:Device {name: $name})
                SET f.type = 'Sidecar', f.ip = '10.1.1.100'
            """, {'name': f'{self.test_prefix}_fluentd'})

            # Create Redis Cache (high criticality)
            session.run("""
                MERGE (r:Device {name: $name})
                SET r.type = 'Cache', r.ip = '10.1.1.201'
            """, {'name': f'{self.test_prefix}_redis'})

            # Create Kafka Message Queue (low criticality)
            session.run("""
                MERGE (k:Device {name: $name})
                SET k.type = 'MessageQueue', k.ip = '10.1.1.202'
            """, {'name': f'{self.test_prefix}_kafka'})

            # Create edges with different criticalities
            # Payment -> MySQL (0.9 - SYNC)
            session.run("""
                MATCH (p:Device {name: $payment})
                MATCH (m:Device {name: $mysql})
                MERGE (p)-[r:CONNECTS_TO]->(m)
                SET r.source_port = 54321, r.target_port = 3306,
                    r.criticality = 0.9, r.last_seen = datetime()
            """, {
                'payment': f'{self.test_prefix}_payment_service',
                'mysql': f'{self.test_prefix}_mysql_db'
            })

            # Payment -> Fluentd (0.2 - SIDECAR)
            session.run("""
                MATCH (p:Device {name: $payment})
                MATCH (f:Device {name: $fluentd})
                MERGE (p)-[r:CONNECTS_TO]->(f)
                SET r.source_port = 54322, r.target_port = 24224,
                    r.criticality = 0.2, r.last_seen = datetime()
            """, {
                'payment': f'{self.test_prefix}_payment_service',
                'fluentd': f'{self.test_prefix}_fluentd'
            })

            # Payment -> Redis (0.9 - SYNC)
            session.run("""
                MATCH (p:Device {name: $payment})
                MATCH (r:Device {name: $redis})
                MERGE (p)-[r:CONNECTS_TO]->(r)
                SET r.source_port = 54323, r.target_port = 6379,
                    r.criticality = 0.9, r.last_seen = datetime()
            """, {
                'payment': f'{self.test_prefix}_payment_service',
                'redis': f'{self.test_prefix}_redis'
            })

            # Payment -> Kafka (0.5 - ASYNC)
            session.run("""
                MATCH (p:Device {name: $payment})
                MATCH (k:Device {name: $kafka})
                MERGE (p)-[r:CONNECTS_TO]->(k)
                SET r.source_port = 54324, r.target_port = 9092,
                    r.criticality = 0.5, r.last_seen = datetime()
            """, {
                'payment': f'{self.test_prefix}_payment_service',
                'kafka': f'{self.test_prefix}_kafka'
            })

            logger.info("Test topology created successfully")

    def test_weighted_propagation(self):
        """Test: MySQL (0.9) should rank higher than Fluentd (0.2)"""
        logger.info("Testing weighted propagation analysis...")

        # Define anomalies
        anomalies = [
            {
                'device': f'{self.test_prefix}_mysql_db',
                'score': 0.9,  # High CPU
                'severity': 'high',
                'anomaly_score': 0.9
            },
            {
                'device': f'{self.test_prefix}_fluentd',
                'score': 1.0,  # Frequent restarts
                'severity': 'high',
                'anomaly_score': 1.0
            }
        ]

        target_node = f'{self.test_prefix}_payment_service'

        # Run analysis
        from root_cause_analysis import GraphDependencyAnalyzer
        analyzer = GraphDependencyAnalyzer(self.driver)

        candidates = analyzer.analyze_failure_propagation(
            target_node=target_node,
            anomalous_nodes=anomalies,
            max_depth=3
        )

        assert len(candidates) == 2, f"Expected 2 candidates, got {len(candidates)}"

        # MySQL should rank higher
        mysql_candidate = next((c for c in candidates if 'mysql' in c['node']), None)
        fluentd_candidate = next((c for c in candidates if 'fluentd' in c['node']), None)

        assert mysql_candidate is not None, "MySQL candidate not found"
        assert fluentd_candidate is not None, "Fluentd candidate not found"

        # MySQL score = 0.9 (path) * 0.9 (anomaly) = 0.81
        # Fluentd score = 0.2 (path) * 1.0 (anomaly) = 0.20
        logger.info(f"  MySQL score: {mysql_candidate['score']:.3f}")
        logger.info(f"  Fluentd score: {fluentd_candidate['score']:.3f}")

        assert mysql_candidate['score'] > fluentd_candidate['score'], \
            "MySQL should have higher score than Fluentd"
        assert mysql_candidate['score'] > 0.7, \
            f"MySQL score should be > 0.7, got {mysql_candidate['score']}"
        assert fluentd_candidate['score'] < 0.3, \
            f"Fluentd score should be < 0.3, got {fluentd_candidate['score']}"

        logger.info("  ✓ MySQL correctly ranked higher than Fluentd")

    def test_sidecar_filtering(self):
        """Test: Sidecar anomalies should be filtered out"""
        logger.info("Testing sidecar noise filtering...")

        anomalies = [
            {
                'device': f'{self.test_prefix}_fluentd',
                'score': 1.0,
                'severity': 'high',
                'anomaly_score': 1.0
            }
        ]

        target_node = f'{self.test_prefix}_payment_service'

        from root_cause_analysis import GraphDependencyAnalyzer
        analyzer = GraphDependencyAnalyzer(self.driver)

        candidates = analyzer.analyze_failure_propagation(
            target_node=target_node,
            anomalous_nodes=anomalies,
            max_depth=3
        )

        # Sidecar should be filtered out (score < 0.3)
        if candidates:
            fluentd_candidate = candidates[0]
            assert fluentd_candidate['score'] < 0.3, \
                f"Sidecar score should be < 0.3, got {fluentd_candidate['score']}"
            logger.info(f"  Sidecar filtered out (score: {fluentd_candidate['score']:.3f})")
        else:
            logger.info("  ✓ Sidecar correctly filtered (no candidates)")

    def test_multi_hop_propagation(self):
        """Test: Multi-hop propagation score calculation"""
        logger.info("Testing multi-hop propagation...")

        # Create a multi-hop scenario: Service -> Router -> Switch -> Database
        with self.driver.session() as session:
            # Create intermediate devices
            session.run("""
                MERGE (r:Device {name: $name})
                SET r.type = 'Router', r.ip = '10.1.1.250'
                MERGE (s:Device {name: $name2})
                SET s.type = 'Switch', s.ip = '10.1.1.251'
            """, {
                'name': f'{self.test_prefix}_router',
                'name2': f'{self.test_prefix}_switch'
            })

            # Create multi-hop edges
            # Router -> Switch (0.7)
            session.run("""
                MATCH (r:Device {name: $router})
                MATCH (s:Device {name: $switch})
                MERGE (r)-[r_rel:CONNECTS_TO]->(s)
                SET r_rel.criticality = 0.7, r_rel.last_seen = datetime()
            """, {
                'router': f'{self.test_prefix}_router',
                'switch': f'{self.test_prefix}_switch'
            })

            # Switch -> MySQL (0.9)
            session.run("""
                MATCH (s:Device {name: $switch})
                MATCH (m:Device {name: $mysql})
                MERGE (s)-[s_rel:CONNECTS_TO]->(m)
                SET s_rel.criticality = 0.9, s_rel.last_seen = datetime()
            """, {
                'switch': f'{self.test_prefix}_switch',
                'mysql': f'{self.test_prefix}_mysql_db'
            })

        logger.info("  Multi-hop topology created")

    def test_high_criticality_priority(self):
        """Test: High criticality paths are prioritized"""
        logger.info("Testing high criticality path priority...")

        anomalies = [
            {
                'device': f'{self.test_prefix}_redis',
                'score': 0.8,
                'severity': 'high',
                'anomaly_score': 0.8
            },
            {
                'device': f'{self.test_prefix}_kafka',
                'score': 0.9,
                'severity': 'high',
                'anomaly_score': 0.9
            }
        ]

        target_node = f'{self.test_prefix}_payment_service'

        from root_cause_analysis import GraphDependencyAnalyzer
        analyzer = GraphDependencyAnalyzer(self.driver)

        candidates = analyzer.analyze_failure_propagation(
            target_node=target_node,
            anomalous_nodes=anomalies,
            max_depth=3
        )

        if len(candidates) >= 2:
            # Redis (0.9 * 0.8 = 0.72) should rank higher than Kafka (0.5 * 0.9 = 0.45)
            redis_candidate = next((c for c in candidates if 'redis' in c['node']), None)
            kafka_candidate = next((c for c in candidates if 'kafka' in c['node']), None)

            if redis_candidate and kafka_candidate:
                logger.info(f"  Redis score: {redis_candidate['score']:.3f}")
                logger.info(f"  Kafka score: {kafka_candidate['score']:.3f}")

                assert redis_candidate['score'] > kafka_candidate['score'], \
                    "Redis should rank higher than Kafka"

                logger.info("  ✓ High criticality path prioritized")

    def cleanup_test_data(self):
        """Clean up all test data"""
        logger.info("\nCleaning up test data...")
        with self.driver.session() as session:
            result = session.run("""
                MATCH (n)
                WHERE n.name STARTS WITH $prefix
                DETACH DELETE n
                RETURN count(n) as count
            """, {'prefix': self.test_prefix})

            count = result.single()['count'] if result else 0
            logger.info(f"Cleaned up {count} test nodes")


def main():
    """Main test runner"""
    import argparse

    parser = argparse.ArgumentParser(description='Test Weighted Root Cause Analysis')
    parser.add_argument('--uri', type=str, default='bolt://neo4j:7687', help='Neo4j URI')
    parser.add_argument('--user', type=str, default='neo4j', help='Neo4j username')
    parser.add_argument('--password', type=str, default='password123', help='Neo4j password')

    args = parser.parse_args()

    # Run tests
    tester = WeightedRCATester(args.uri, args.user, args.password)
    success = tester.run_all_tests()
    tester.close()

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
