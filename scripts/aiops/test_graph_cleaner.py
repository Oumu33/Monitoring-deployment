#!/usr/bin/env python3
"""
Test script for Graph Cleaner TTL functionality

Tests:
1. Insert test nodes with different last_seen timestamps
2. Run Graph Cleaner (dry-run)
3. Verify expired nodes are identified correctly
4. Run actual cleanup
5. Verify expired nodes are deleted
6. Verify active nodes are preserved
"""

import sys
import time
import logging
from datetime import datetime, timedelta

sys.path.insert(0, '/opt/Monitoring-deployment-main/scripts/aiops')

from neo4j import GraphDatabase
from graph_cleaner import GraphCleaner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GraphCleanerTester:
    """Test suite for Graph Cleaner"""

    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.cleaner = GraphCleaner(uri, user, password)
        self.test_prefix = f"test_ttl_{int(time.time())}"

    def __enter__(self):
        self.cleaner.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.clean_up_test_data()
        self.cleaner.close()
        self.driver.close()

    def run_all_tests(self):
        """Run all test cases"""
        logger.info("=" * 60)
        logger.info("Graph Cleaner TTL Test Suite")
        logger.info("=" * 60)

        tests = [
            ("Test 1: Insert Test Nodes", self.test_insert_nodes),
            ("Test 2: Dry Run Cleanup", self.test_dry_run),
            ("Test 3: Actual Cleanup", self.test_actual_cleanup),
            ("Test 4: Verify Active Nodes Preserved", self.test_verify_active_nodes),
            ("Test 5: Batch Deletion Performance", self.test_batch_deletion),
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

        logger.info("\n" + "=" * 60)
        logger.info(f"Test Results: {passed} passed, {failed} failed")
        logger.info("=" * 60)

        return failed == 0

    def test_insert_nodes(self):
        """Insert test nodes with different last_seen timestamps"""
        logger.info("Inserting test nodes...")

        with self.driver.session() as session:
            # Insert expired Pod (2 days ago)
            session.run("""
                MERGE (p:Pod {urn: $urn})
                SET p.name = $name,
                    p.namespace = $namespace,
                    p.last_seen = $last_seen,
                    p.status = 'Running'
            """, {
                'urn': f'{self.test_prefix}_pod_expired_01',
                'name': 'test-pod-expired-01',
                'namespace': 'test',
                'last_seen': datetime.now() - timedelta(days=2)
            })

            # Insert another expired Pod (3 days ago)
            session.run("""
                MERGE (p:Pod {urn: $urn})
                SET p.name = $name,
                    p.namespace = $namespace,
                    p.last_seen = $last_seen,
                    p.status = 'Running'
            """, {
                'urn': f'{self.test_prefix}_pod_expired_02',
                'name': 'test-pod-expired-02',
                'namespace': 'test',
                'last_seen': datetime.now() - timedelta(days=3)
            })

            # Insert active Pod (recent)
            session.run("""
                MERGE (p:Pod {urn: $urn})
                SET p.name = $name,
                    p.namespace = $namespace,
                    p.last_seen = $last_seen,
                    p.status = 'Running'
            """, {
                'urn': f'{self.test_prefix}_pod_active_01',
                'name': 'test-pod-active-01',
                'namespace': 'test',
                'last_seen': datetime.now() - timedelta(minutes=5)
            })

            # Insert expired Service (40 days ago)
            session.run("""
                MERGE (s:Service {urn: $urn})
                SET s.name = $name,
                    s.namespace = $namespace,
                    s.last_seen = $last_seen,
                    s.cluster_ip = '10.0.0.1'
            """, {
                'urn': f'{self.test_prefix}_service_expired_01',
                'name': 'test-service-expired-01',
                'namespace': 'test',
                'last_seen': datetime.now() - timedelta(days=40)
            })

            # Insert active Service (recent)
            session.run("""
                MERGE (s:Service {urn: $urn})
                SET s.name = $name,
                    s.namespace = $namespace,
                    s.last_seen = $last_seen,
                    s.cluster_ip = '10.0.0.2'
            """, {
                'urn': f'{self.test_prefix}_service_active_01',
                'name': 'test-service-active-01',
                'namespace': 'test',
                'last_seen': datetime.now() - timedelta(minutes=10)
            })

            # Verify all nodes were inserted
            result = session.run("""
                MATCH (n)
                WHERE n.urn STARTS WITH $prefix
                RETURN count(n) as count
            """, {'prefix': self.test_prefix})
            count = result.single()['count']

            assert count == 5, f"Expected 5 test nodes, got {count}"
            logger.info(f"Inserted {count} test nodes")

    def test_dry_run(self):
        """Test dry run cleanup (should not delete anything)"""
        logger.info("Running dry-run cleanup...")

        # Get node count before dry run
        with self.driver.session() as session:
            before_count = session.run("""
                MATCH (n:Pod)
                WHERE n.urn STARTS WITH $prefix
                RETURN count(n) as count
            """, {'prefix': self.test_prefix}).single()['count']

        # Run dry run
        stats = self.cleaner.run_cleanup_for_label('Pod', ttl_hours=24, dry_run=True)

        # Verify no nodes were actually deleted
        with self.driver.session() as session:
            after_count = session.run("""
                MATCH (n:Pod)
                WHERE n.urn STARTS WITH $prefix
                RETURN count(n) as count
            """, {'prefix': self.test_prefix}).single()['count']

        assert before_count == after_count, "Dry run should not delete any nodes"
        assert stats['deleted_count'] == 2, f"Expected 2 expired Pods, got {stats['deleted_count']}"
        logger.info(f"Dry run identified {stats['deleted_count']} expired Pods (none deleted)")

    def test_actual_cleanup(self):
        """Test actual cleanup (should delete expired nodes)"""
        logger.info("Running actual cleanup...")

        # Get node count before cleanup
        with self.driver.session() as session:
            before_count = session.run("""
                MATCH (n:Pod)
                WHERE n.urn STARTS WITH $prefix
                RETURN count(n) as count
            """, {'prefix': self.test_prefix}).single()['count']

        # Run actual cleanup
        stats = self.cleaner.run_cleanup_for_label('Pod', ttl_hours=24, dry_run=False)

        # Verify expired nodes were deleted
        with self.driver.session() as session:
            after_count = session.run("""
                MATCH (n:Pod)
                WHERE n.urn STARTS WITH $prefix
                RETURN count(n) as count
            """, {'prefix': self.test_prefix}).single()['count']

        assert before_count == 3, f"Expected 3 Pods before cleanup, got {before_count}"
        assert after_count == 1, f"Expected 1 Pod after cleanup, got {after_count}"
        assert stats['deleted_count'] == 2, f"Expected to delete 2 Pods, got {stats['deleted_count']}"
        logger.info(f"Deleted {stats['deleted_count']} expired Pods, kept {after_count} active Pods")

    def test_verify_active_nodes(self):
        """Verify active nodes are preserved"""
        logger.info("Verifying active nodes are preserved...")

        with self.driver.session() as session:
            # Check active Pod still exists
            result = session.run("""
                MATCH (p:Pod {urn: $urn})
                RETURN p.name as name, p.status as status
            """, {'urn': f'{self.test_prefix}_pod_active_01'})

            pod = result.single()
            assert pod is not None, "Active Pod should still exist"
            assert pod['name'] == 'test-pod-active-01', "Active Pod name should match"
            logger.info(f"Active Pod preserved: {pod['name']} (status: {pod['status']})")

            # Check active Service still exists
            result = session.run("""
                MATCH (s:Service {urn: $urn})
                RETURN s.name as name, s.cluster_ip as ip
            """, {'urn': f'{self.test_prefix}_service_active_01'})

            service = result.single()
            assert service is not None, "Active Service should still exist"
            assert service['name'] == 'test-service-active-01', "Active Service name should match"
            logger.info(f"Active Service preserved: {service['name']} (IP: {service['ip']})")

            # Check expired Pod is deleted
            result = session.run("""
                MATCH (p:Pod {urn: $urn})
                RETURN count(p) as count
            """, {'urn': f'{self.test_prefix}_pod_expired_01'})

            count = result.single()['count']
            assert count == 0, "Expired Pod should be deleted"
            logger.info("Expired Pod successfully deleted")

    def test_batch_deletion(self):
        """Test batch deletion performance with many nodes"""
        logger.info("Testing batch deletion with 1500 nodes...")

        with self.driver.session() as session:
            # Insert 1500 expired Pods
            batch_size = 100
            for i in range(15):  # 15 batches of 100 = 1500 nodes
                queries = []
                for j in range(batch_size):
                    idx = i * batch_size + j
                    queries.append({
                        'urn': f'{self.test_prefix}_batch_pod_{idx}',
                        'name': f'batch-pod-{idx}',
                        'namespace': 'test',
                        'last_seen': datetime.now() - timedelta(days=5)
                    })

                # Batch insert
                session.run("""
                    UNWIND $data AS row
                    MERGE (p:Pod {urn: row.urn})
                    SET p.name = row.name,
                        p.namespace = row.namespace,
                        p.last_seen = row.last_seen,
                        p.status = 'Running'
                """, {'data': queries})

                logger.info(f"Inserted batch {i+1}/15 ({(i+1)*batch_size} nodes)")

            # Verify insertion
            result = session.run("""
                MATCH (p:Pod)
                WHERE p.urn STARTS WITH $prefix
                RETURN count(p) as count
            """, {'prefix': f'{self.test_prefix}_batch_pod'})
            count = result.single()['count']
            assert count == 1500, f"Expected 1500 batch Pods, got {count}"
            logger.info(f"Inserted {count} batch Pods")

        # Run cleanup and measure time
        start_time = time.time()
        stats = self.cleaner.run_cleanup_for_label('Pod', ttl_hours=24, dry_run=False)
        elapsed_time = time.time() - start_time

        assert stats['deleted_count'] == 1500, f"Expected to delete 1500 batch Pods, got {stats['deleted_count']}"
        logger.info(f"Deleted {stats['deleted_count']} batch Pods in {elapsed_time:.2f}s")

        # Performance check: should complete in reasonable time
        assert elapsed_time < 30, f"Batch deletion took too long: {elapsed_time:.2f}s"
        logger.info(f"✓ Batch deletion performance acceptable: {elapsed_time:.2f}s")

    def clean_up_test_data(self):
        """Clean up all test data"""
        logger.info("Cleaning up test data...")

        with self.driver.session() as session:
            result = session.run("""
                MATCH (n)
                WHERE n.urn STARTS WITH $prefix
                DETACH DELETE n
                RETURN count(n) as count
            """, {'prefix': self.test_prefix})

            count = result.single()['count'] if result else 0
            logger.info(f"Cleaned up {count} test nodes")


def main():
    """Main test runner"""
    import argparse

    parser = argparse.ArgumentParser(description='Test Graph Cleaner TTL functionality')
    parser.add_argument('--uri', type=str, default='bolt://neo4j:7687', help='Neo4j URI')
    parser.add_argument('--user', type=str, default='neo4j', help='Neo4j username')
    parser.add_argument('--password', type=str, default='password123', help='Neo4j password')

    args = parser.parse_args()

    # Run tests
    with GraphCleanerTester(args.uri, args.user, args.password) as tester:
        success = tester.run_all_tests()

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())