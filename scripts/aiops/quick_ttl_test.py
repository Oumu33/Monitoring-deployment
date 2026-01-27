#!/usr/bin/env python3
"""
Quick TTL Test - Verify Graph Cleaner functionality

This script:
1. Inserts a test Pod with last_seen = 2 days ago
2. Inserts a test Pod with last_seen = 5 minutes ago
3. Runs Graph Cleaner dry-run
4. Verifies expired node is identified
5. Runs actual cleanup
6. Verifies expired node is deleted, active node preserved
"""

import sys
import logging
from datetime import datetime, timedelta

sys.path.insert(0, '/opt/Monitoring-deployment-main/scripts/aiops')

from neo4j import GraphDatabase
from graph_cleaner import GraphCleaner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_quick_test():
    """Run quick TTL verification test"""
    logger.info("=" * 60)
    logger.info("Quick TTL Test - Graph Cleaner Verification")
    logger.info("=" * 60)

    # Configuration
    uri = os.environ.get('NEO4J_URI', 'bolt://neo4j:7687')
    user = os.environ.get('NEO4J_USER', 'neo4j')
    password = os.environ.get('NEO4J_PASSWORD', 'password123')

    # Connect to Neo4j
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        logger.info(f"✓ Connected to Neo4j at {uri}")
    except Exception as e:
        logger.error(f"✗ Failed to connect to Neo4j: {e}")
        return False

    try:
        with driver.session() as session:
            # Step 1: Insert expired Pod (2 days ago)
            expired_pod_urn = 'test:pod:expired:demo'
            logger.info("\nStep 1: Inserting expired Pod (2 days ago)...")
            session.run("""
                MERGE (p:Pod {urn: $urn})
                SET p.name = $name,
                    p.namespace = $namespace,
                    p.last_seen = $last_seen,
                    p.status = 'Running',
                    p.created_at = datetime() - duration('P2D')
            """, {
                'urn': expired_pod_urn,
                'name': 'test-pod-expired',
                'namespace': 'test',
                'last_seen': datetime.now() - timedelta(days=2)
            })
            logger.info(f"✓ Inserted expired Pod: {expired_pod_urn}")

            # Step 2: Insert active Pod (5 minutes ago)
            active_pod_urn = 'test:pod:active:demo'
            logger.info("\nStep 2: Inserting active Pod (5 minutes ago)...")
            session.run("""
                MERGE (p:Pod {urn: $urn})
                SET p.name = $name,
                    p.namespace = $namespace,
                    p.last_seen = $last_seen,
                    p.status = 'Running',
                    p.created_at = datetime() - duration('PT10M')
            """, {
                'urn': active_pod_urn,
                'name': 'test-pod-active',
                'namespace': 'test',
                'last_seen': datetime.now() - timedelta(minutes=5)
            })
            logger.info(f"✓ Inserted active Pod: {active_pod_urn}")

            # Verify both pods exist
            logger.info("\nVerifying both pods exist...")
            result = session.run("""
                MATCH (p:Pod)
                WHERE p.urn IN [$urn1, $urn2]
                RETURN p.urn as urn, p.last_seen as last_seen, p.name as name
                ORDER BY p.last_seen DESC
            """, {'urn1': expired_pod_urn, 'urn2': active_pod_urn})

            pods = list(result)
            assert len(pods) == 2, f"Expected 2 pods, found {len(pods)}"

            for pod in pods:
                hours_ago = (datetime.now() - pod['last_seen']).total_seconds() / 3600
                logger.info(f"  • {pod['name']}: last_seen = {hours_ago:.1f} hours ago")

        # Step 3: Initialize Graph Cleaner
        logger.info("\nStep 3: Initializing Graph Cleaner...")
        cleaner = GraphCleaner(uri, user, password)
        cleaner.connect()
        logger.info("✓ Graph Cleaner initialized")

        # Step 4: Dry run cleanup
        logger.info("\nStep 4: Running dry-run cleanup...")
        dry_run_stats = cleaner.run_cleanup_for_label('Pod', ttl_hours=24, dry_run=True)
        logger.info(f"✓ Dry run identified {dry_run_stats['deleted_count']} expired Pod(s)")

        assert dry_run_stats['deleted_count'] == 1, \
            f"Expected 1 expired Pod in dry run, got {dry_run_stats['deleted_count']}"

        # Step 5: Verify dry run didn't delete anything
        logger.info("\nStep 5: Verifying dry run didn't delete anything...")
        with driver.session() as session:
            result = session.run("""
                MATCH (p:Pod)
                WHERE p.urn IN [$urn1, $urn2]
                RETURN count(p) as count
            """, {'urn1': expired_pod_urn, 'urn2': active_pod_urn})

            count = result.single()['count']
            assert count == 2, f"Dry run should not delete pods, found {count} instead of 2"
            logger.info("✓ Both pods still exist (dry run didn't delete)")

        # Step 6: Run actual cleanup
        logger.info("\nStep 6: Running actual cleanup...")
        actual_stats = cleaner.run_cleanup_for_label('Pod', ttl_hours=24, dry_run=False)
        logger.info(f"✓ Actual cleanup deleted {actual_stats['deleted_count']} expired Pod(s)")

        assert actual_stats['deleted_count'] == 1, \
            f"Expected to delete 1 expired Pod, got {actual_stats['deleted_count']}"

        # Step 7: Verify expired pod deleted, active pod preserved
        logger.info("\nStep 7: Verifying cleanup results...")
        with driver.session() as session:
            # Check expired pod is deleted
            result = session.run("""
                MATCH (p:Pod {urn: $urn})
                RETURN count(p) as count
            """, {'urn': expired_pod_urn})

            expired_count = result.single()['count']
            assert expired_count == 0, "Expired Pod should be deleted"
            logger.info("✓ Expired Pod successfully deleted")

            # Check active pod is preserved
            result = session.run("""
                MATCH (p:Pod {urn: $urn})
                RETURN p.name as name, p.status as status
            """, {'urn': active_pod_urn})

            active_pod = result.single()
            assert active_pod is not None, "Active Pod should still exist"
            logger.info(f"✓ Active Pod preserved: {active_pod['name']} (status: {active_pod['status']})")

        # Step 8: Cleanup test data
        logger.info("\nStep 8: Cleaning up test data...")
        with driver.session() as session:
            result = session.run("""
                MATCH (p:Pod)
                WHERE p.urn IN [$urn1, $urn2]
                DETACH DELETE p
                RETURN count(p) as count
            """, {'urn1': expired_pod_urn, 'urn2': active_pod_urn})

            logger.info(f"✓ Cleaned up {result.single()['count']} test pod(s)")

        logger.info("\n" + "=" * 60)
        logger.info("✅ ALL TESTS PASSED!")
        logger.info("=" * 60)
        logger.info("\nSummary:")
        logger.info("  • Expired Pod (2 days old) was correctly identified")
        logger.info("  • Dry run didn't delete any nodes")
        logger.info("  • Actual cleanup deleted expired Pod")
        logger.info("  • Active Pod (5 minutes old) was preserved")
        logger.info("\nGraph Cleaner TTL mechanism is working correctly! 🎉")

        return True

    except AssertionError as e:
        logger.error(f"\n✗ TEST FAILED: {e}")
        return False
    except Exception as e:
        logger.error(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        cleaner.close()
        driver.close()


if __name__ == '__main__':
    import os
    success = run_quick_test()
    sys.exit(0 if success else 1)
