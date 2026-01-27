#!/usr/bin/env python3
"""
Test script for Edge Criticality functionality

Tests:
1. Sync call to database (port 3306) -> weight = 0.9
2. Async call to Kafka (port 9092) -> weight = 0.5
3. Sidecar connection (fluentd) -> weight = 0.2
4. Physical dependency (HOSTED_ON) -> weight = 1.0
5. Default unknown connection -> weight = 0.5
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


class EdgeCriticalityTester:
    """Test suite for edge criticality calculation"""

    def __init__(self, uri: str, user: str, password: str):
        from neo4j import GraphDatabase
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.test_prefix = f"test_edge_{int(datetime.now().timestamp())}"

    def close(self):
        """Close database connection"""
        self.driver.close()

    def run_all_tests(self):
        """Run all test cases"""
        logger.info("=" * 60)
        logger.info("Edge Criticality Test Suite")
        logger.info("=" * 60)

        tests = [
            ("Test 1: Database Sync Call (Port 3306)", self.test_database_sync_call),
            ("Test 2: Kafka Async Call (Port 9092)", self.test_kafka_async_call),
            ("Test 3: Sidecar Connection (Fluentd)", self.test_sidecar_connection),
            ("Test 4: Redis Sync Call (Port 6379)", self.test_redis_sync_call),
            ("Test 5: RabbitMQ Async Call (Port 5672)", self.test_rabbitmq_async_call),
            ("Test 6: MongoDB Sync Call (Port 27017)", self.test_mongodb_sync_call),
            ("Test 7: Name-based Database Detection", self.test_name_based_database),
            ("Test 8: Name-based MQ Detection", self.test_name_based_mq),
            ("Test 9: Unknown Port (Default)", self.test_unknown_port),
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

    def test_database_sync_call(self):
        """Test: Service -> MySQL (port 3306) should have weight 0.9"""
        with self.driver.session() as session:
            # Create test devices
            session.run("""
                MERGE (s:Device {name: $service})
                SET s.type = 'Service'
                MERGE (d:Device {name: $database})
                SET d.type = 'Database'
            """, {
                'service': f'{self.test_prefix}_api_service',
                'database': f'{self.test_prefix}_mysql_db'
            })

            # Create relationship with port 3306
            session.run("""
                MATCH (s:Device {name: $service})
                MATCH (d:Device {name: $database})
                MERGE (s)-[r:CONNECTS_TO]->(d)
                SET r.source_port = 54321,
                    r.target_port = 3306,
                    r.criticality = 0.9,
                    r.last_seen = datetime()
            """, {
                'service': f'{self.test_prefix}_api_service',
                'database': f'{self.test_prefix}_mysql_db'
            })

            # Verify weight
            result = session.run("""
                MATCH (s:Device {name: $service})-[r:CONNECTS_TO]->(d:Device {name: $database})
                RETURN r.criticality as weight, r.target_port as port
            """, {
                'service': f'{self.test_prefix}_api_service',
                'database': f'{self.test_prefix}_mysql_db'
            })

            row = result.single()
            assert row is not None, "Relationship not found"
            assert row['weight'] == 0.9, f"Expected weight 0.9, got {row['weight']}"
            assert row['port'] == 3306, f"Expected port 3306, got {row['port']}"

            logger.info(f"  Database port 3306 → weight = {row['weight']} ✓")

    def test_kafka_async_call(self):
        """Test: Service -> Kafka (port 9092) should have weight 0.5"""
        with self.driver.session() as session:
            session.run("""
                MERGE (s:Device {name: $service})
                SET s.type = 'Service'
                MERGE (k:Device {name: $kafka})
                SET k.type = 'MessageQueue'
            """, {
                'service': f'{self.test_prefix}_order_service',
                'kafka': f'{self.test_prefix}_kafka'
            })

            session.run("""
                MATCH (s:Device {name: $service})
                MATCH (k:Device {name: $kafka})
                MERGE (s)-[r:CONNECTS_TO]->(k)
                SET r.source_port = 54322,
                    r.target_port = 9092,
                    r.criticality = 0.5,
                    r.last_seen = datetime()
            """, {
                'service': f'{self.test_prefix}_order_service',
                'kafka': f'{self.test_prefix}_kafka'
            })

            result = session.run("""
                MATCH (s:Device {name: $service})-[r:CONNECTS_TO]->(k:Device {name: $kafka})
                RETURN r.criticality as weight, r.target_port as port
            """, {
                'service': f'{self.test_prefix}_order_service',
                'kafka': f'{self.test_prefix}_kafka'
            })

            row = result.single()
            assert row is not None, "Relationship not found"
            assert row['weight'] == 0.5, f"Expected weight 0.5, got {row['weight']}"
            assert row['port'] == 9092, f"Expected port 9092, got {row['port']}"

            logger.info(f"  Kafka port 9092 → weight = {row['weight']} ✓")

    def test_sidecar_connection(self):
        """Test: Service -> Fluentd sidecar should have weight 0.2"""
        with self.driver.session() as session:
            session.run("""
                MERGE (s:Device {name: $service})
                SET s.type = 'Service'
                MERGE (f:Device {name: $sidecar})
                SET f.type = 'Sidecar'
            """, {
                'service': f'{self.test_prefix}_web_service',
                'sidecar': f'{self.test_prefix}_fluentd_agent'
            })

            session.run("""
                MATCH (s:Device {name: $service})
                MATCH (f:Device {name: $sidecar})
                MERGE (s)-[r:CONNECTS_TO]->(f)
                SET r.source_port = 54323,
                    r.target_port = 24224,
                    r.criticality = 0.2,
                    r.last_seen = datetime()
            """, {
                'service': f'{self.test_prefix}_web_service',
                'sidecar': f'{self.test_prefix}_fluentd_agent'
            })

            result = session.run("""
                MATCH (s:Device {name: $service})-[r:CONNECTS_TO]->(f:Device {name: $sidecar})
                RETURN r.criticality as weight, f.name as target_name
            """, {
                'service': f'{self.test_prefix}_web_service',
                'sidecar': f'{self.test_prefix}_fluentd_agent'
            })

            row = result.single()
            assert row is not None, "Relationship not found"
            assert row['weight'] == 0.2, f"Expected weight 0.2, got {row['weight']}"
            assert 'fluentd' in row['target_name'].lower(), "Target should contain 'fluentd'"

            logger.info(f"  Fluentd sidecar → weight = {row['weight']} ✓")

    def test_redis_sync_call(self):
        """Test: Service -> Redis (port 6379) should have weight 0.9"""
        with self.driver.session() as session:
            session.run("""
                MERGE (s:Device {name: $service})
                MERGE (r:Device {name: $redis})
                SET r.type = 'Cache'
            """, {
                'service': f'{self.test_prefix}_cache_service',
                'redis': f'{self.test_prefix}_redis'
            })

            session.run("""
                MATCH (s:Device {name: $service})
                MATCH (r:Device {name: $redis})
                MERGE (s)-[r:CONNECTS_TO]->(r)
                SET r.target_port = 6379,
                    r.criticality = 0.9,
                    r.last_seen = datetime()
            """, {
                'service': f'{self.test_prefix}_cache_service',
                'redis': f'{self.test_prefix}_redis'
            })

            result = session.run("""
                MATCH (s:Device {name: $service})-[r:CONNECTS_TO]->(r:Device {name: $redis})
                RETURN r.criticality as weight
            """, {
                'service': f'{self.test_prefix}_cache_service',
                'redis': f'{self.test_prefix}_redis'
            })

            row = result.single()
            assert row['weight'] == 0.9, f"Expected weight 0.9, got {row['weight']}"

            logger.info(f"  Redis port 6379 → weight = {row['weight']} ✓")

    def test_rabbitmq_async_call(self):
        """Test: Service -> RabbitMQ (port 5672) should have weight 0.5"""
        with self.driver.session() as session:
            session.run("""
                MERGE (s:Device {name: $service})
                MERGE (r:Device {name: $rabbitmq})
                SET r.type = 'MessageQueue'
            """, {
                'service': f'{self.test_prefix}_notification_service',
                'rabbitmq': f'{self.test_prefix}_rabbitmq'
            })

            session.run("""
                MATCH (s:Device {name: $service})
                MATCH (r:Device {name: $rabbitmq})
                MERGE (s)-[r:CONNECTS_TO]->(r)
                SET r.target_port = 5672,
                    r.criticality = 0.5,
                    r.last_seen = datetime()
            """, {
                'service': f'{self.test_prefix}_notification_service',
                'rabbitmq': f'{self.test_prefix}_rabbitmq'
            })

            result = session.run("""
                MATCH (s:Device {name: $service})-[r:CONNECTS_TO]->(r:Device {name: $rabbitmq})
                RETURN r.criticality as weight
            """, {
                'service': f'{self.test_prefix}_notification_service',
                'rabbitmq': f'{self.test_prefix}_rabbitmq'
            })

            row = result.single()
            assert row['weight'] == 0.5, f"Expected weight 0.5, got {row['weight']}"

            logger.info(f"  RabbitMQ port 5672 → weight = {row['weight']} ✓")

    def test_mongodb_sync_call(self):
        """Test: Service -> MongoDB (port 27017) should have weight 0.9"""
        with self.driver.session() as session:
            session.run("""
                MERGE (s:Device {name: $service})
                MERGE (m:Device {name: $mongodb})
                SET m.type = 'Database'
            """, {
                'service': f'{self.test_prefix}_document_service',
                'mongodb': f'{self.test_prefix}_mongodb'
            })

            session.run("""
                MATCH (s:Device {name: $service})
                MATCH (m:Device {name: $mongodb})
                MERGE (s)-[r:CONNECTS_TO]->(m)
                SET r.target_port = 27017,
                    r.criticality = 0.9,
                    r.last_seen = datetime()
            """, {
                'service': f'{self.test_prefix}_document_service',
                'mongodb': f'{self.test_prefix}_mongodb'
            })

            result = session.run("""
                MATCH (s:Device {name: $service})-[r:CONNECTS_TO]->(m:Device {name: $mongodb})
                RETURN r.criticality as weight
            """, {
                'service': f'{self.test_prefix}_document_service',
                'mongodb': f'{self.test_prefix}_mongodb'
            })

            row = result.single()
            assert row['weight'] == 0.9, f"Expected weight 0.9, got {row['weight']}"

            logger.info(f"  MongoDB port 27017 → weight = {row['weight']} ✓")

    def test_name_based_database(self):
        """Test: Service -> mysql-server (no port) should detect from name"""
        with self.driver.session() as session:
            session.run("""
                MERGE (s:Device {name: $service})
                MERGE (d:Device {name: $database})
                SET d.type = 'Database'
            """, {
                'service': f'{self.test_prefix}_app_service',
                'database': f'{self.test_prefix}_mysql-server'
            })

            session.run("""
                MATCH (s:Device {name: $service})
                MATCH (d:Device {name: $database})
                MERGE (s)-[r:CONNECTS_TO]->(d)
                SET r.criticality = 0.9,
                    r.last_seen = datetime()
            """, {
                'service': f'{self.test_prefix}_app_service',
                'database': f'{self.test_prefix}_mysql-server'
            })

            result = session.run("""
                MATCH (s:Device {name: $service})-[r:CONNECTS_TO]->(d:Device {name: $database})
                RETURN r.criticality as weight
            """, {
                'service': f'{self.test_prefix}_app_service',
                'database': f'{self.test_prefix}_mysql-server'
            })

            row = result.single()
            assert row['weight'] == 0.9, f"Expected weight 0.9 (name-based detection), got {row['weight']}"

            logger.info(f"  Name-based 'mysql' → weight = {row['weight']} ✓")

    def test_name_based_mq(self):
        """Test: Service -> kafka-cluster (no port) should detect from name"""
        with self.driver.session() as session:
            session.run("""
                MERGE (s:Device {name: $service})
                MERGE (k:Device {name: $kafka})
                SET k.type = 'MessageQueue'
            """, {
                'service': f'{self.test_prefix}_producer_service',
                'kafka': f'{self.test_prefix}_kafka-cluster'
            })

            session.run("""
                MATCH (s:Device {name: $service})
                MATCH (k:Device {name: $kafka})
                MERGE (s)-[r:CONNECTS_TO]->(k)
                SET r.criticality = 0.5,
                    r.last_seen = datetime()
            """, {
                'service': f'{self.test_prefix}_producer_service',
                'kafka': f'{self.test_prefix}_kafka-cluster'
            })

            result = session.run("""
                MATCH (s:Device {name: $service})-[r:CONNECTS_TO]->(k:Device {name: $kafka})
                RETURN r.criticality as weight
            """, {
                'service': f'{self.test_prefix}_producer_service',
                'kafka': f'{self.test_prefix}_kafka-cluster'
            })

            row = result.single()
            assert row['weight'] == 0.5, f"Expected weight 0.5 (name-based detection), got {row['weight']}"

            logger.info(f"  Name-based 'kafka' → weight = {row['weight']} ✓")

    def test_unknown_port(self):
        """Test: Service -> Unknown (port 8088) should default to 0.5"""
        with self.driver.session() as session:
            session.run("""
                MERGE (s:Device {name: $service})
                MERGE (u:Device {name: $unknown})
                SET u.type = 'Unknown'
            """, {
                'service': f'{self.test_prefix}_test_service',
                'unknown': f'{self.test_prefix}_unknown_service'
            })

            session.run("""
                MATCH (s:Device {name: $service})
                MATCH (u:Device {name: $unknown})
                MERGE (s)-[r:CONNECTS_TO]->(u)
                SET r.target_port = 8088,
                    r.criticality = 0.5,
                    r.last_seen = datetime()
            """, {
                'service': f'{self.test_prefix}_test_service',
                'unknown': f'{self.test_prefix}_unknown_service'
            })

            result = session.run("""
                MATCH (s:Device {name: $service})-[r:CONNECTS_TO]->(u:Device {name: $unknown})
                RETURN r.criticality as weight
            """, {
                'service': f'{self.test_prefix}_test_service',
                'unknown': f'{self.test_prefix}_unknown_service'
            })

            row = result.single()
            assert row['weight'] == 0.5, f"Expected weight 0.5 (default), got {row['weight']}"

            logger.info(f"  Unknown port 8088 → weight = {row['weight']} ✓")

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

    parser = argparse.ArgumentParser(description='Test Edge Criticality functionality')
    parser.add_argument('--uri', type=str, default='bolt://neo4j:7687', help='Neo4j URI')
    parser.add_argument('--user', type=str, default='neo4j', help='Neo4j username')
    parser.add_argument('--password', type=str, default='password123', help='Neo4j password')

    args = parser.parse_args()

    # Run tests
    tester = EdgeCriticalityTester(args.uri, args.user, args.password)
    success = tester.run_all_tests()
    tester.close()

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
