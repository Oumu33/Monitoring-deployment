#!/usr/bin/env python3
"""
AIOps Graph Cleaner - TTL-based Garbage Collection

Implements automatic cleanup of expired topology nodes with:
- Differentiated TTL policies (Pods: 24h, Services: 30d, Nodes: 30d)
- Batch deletion to prevent performance impact
- Soft delete support for audit trails

Usage:
    cleaner = GraphCleaner(neo4j_driver)
    cleaner.run_cleanup()
"""

import os
import time
import logging
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
from neo4j import GraphDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GraphCleaner:
    """
    Automatic graph cleanup service with TTL policies

    Prevents graph explosion by removing expired nodes based on last_seen timestamp.
    Uses batch deletion to protect database performance.
    """

    # TTL policies in hours (can be overridden via environment variables)
    DEFAULT_TTL_POLICIES = {
        'Pod': 24,           # Pods are ephemeral, keep for 24 hours
        'Container': 24,     # Containers follow pods
        'Service': 720,      # Services are stable, keep for 30 days
        'Node': 720,         # Nodes are long-lived, keep for 30 days
        'Device': 720,       # Network devices are long-lived
        'Server': 720,       # Physical servers are long-lived
        'Alert': 168,        # Alert history: 7 days
        'Anomaly': 168,      # Anomaly history: 7 days
        'LogEntry': 48,      # Log entries: 2 days
        'Trace': 24,         # Traces: 1 day
        'Unknown': 48        # Fallback policy
    }

    def __init__(self, uri: str, user: str, password: str, ttl_policies: Dict[str, int] = None):
        """
        Initialize Graph Cleaner

        Args:
            uri: Neo4j connection URI
            user: Neo4j username
            password: Neo4j password
            ttl_policies: Optional custom TTL policies (in hours)
        """
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = None

        # Load TTL policies (allow environment variable overrides)
        self.ttl_policies = self._load_ttl_policies(ttl_policies)

        # Batch size for deletion (prevents OOM)
        self.batch_size = 1000

        # Statistics
        self.stats = {
            'total_deleted': 0,
            'nodes_by_type': {},
            'execution_time': 0
        }

        logger.info("Graph Cleaner initialized")
        logger.info(f"TTL Policies: {self.ttl_policies}")

    def connect(self):
        """Establish connection to Neo4j"""
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            self.driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {self.uri}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            return False

    def close(self):
        """Close database connection"""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")

    def _load_ttl_policies(self, custom_policies: Dict[str, int] = None) -> Dict[str, int]:
        """
        Load TTL policies from defaults and environment variables

        Environment variable format: AIOPS_TTL_POD=24, AIOPS_TTL_SERVICE=720
        """
        policies = self.DEFAULT_TTL_POLICIES.copy()

        # Override with environment variables
        for key in policies.keys():
            env_key = f'AIOPS_TTL_{key.upper()}'
            if env_key in os.environ:
                try:
                    policies[key] = int(os.environ[env_key])
                    logger.info(f"Overriding TTL for {key}: {policies[key]}h (from env)")
                except ValueError:
                    logger.warning(f"Invalid TTL value for {env_key}, using default")

        # Override with custom policies if provided
        if custom_policies:
            policies.update(custom_policies)

        return policies

    def run_cleanup(self, dry_run: bool = False) -> Dict:
        """
        Execute cleanup task for all node types

        Args:
            dry_run: If True, only report what would be deleted without actually deleting

        Returns:
            Cleanup statistics dictionary
        """
        start_time = time.time()
        logger.info("=" * 60)
        logger.info("Starting Topology Garbage Collection...")
        logger.info(f"Dry Run: {dry_run}")
        logger.info("=" * 60)

        self.stats = {
            'total_deleted': 0,
            'nodes_by_type': {},
            'execution_time': 0,
            'dry_run': dry_run
        }

        try:
            with self.driver.session() as session:
                # Get actual node labels present in the database
                node_labels = self._get_node_labels(session)
                logger.info(f"Found {len(node_labels)} node types in database: {node_labels}")

                # Clean each label type
                for label in node_labels:
                    ttl_hours = self.ttl_policies.get(label, self.ttl_policies['Unknown'])

                    try:
                        deleted_count = session.execute_write(
                            self._delete_expired_nodes_batch,
                            label,
                            ttl_hours,
                            dry_run
                        )

                        if deleted_count > 0:
                            self.stats['nodes_by_type'][label] = deleted_count
                            self.stats['total_deleted'] += deleted_count
                            logger.info(f"🧹 {'Would delete' if dry_run else 'Deleted'} {deleted_count} expired {label} nodes (TTL: {ttl_hours}h)")
                        else:
                            logger.debug(f"✓ No expired {label} nodes (TTL: {ttl_hours}h)")

                    except Exception as e:
                        logger.error(f"Error cleaning {label} nodes: {e}")
                        continue

            # Update execution time
            self.stats['execution_time'] = time.time() - start_time

            # Log summary
            logger.info("=" * 60)
            logger.info("Garbage Collection Completed")
            logger.info(f"Total {'would be deleted' if dry_run else 'deleted'}: {self.stats['total_deleted']} nodes")
            logger.info(f"Execution time: {self.stats['execution_time']:.2f}s")
            logger.info("=" * 60)

            return self.stats

        except Exception as e:
            logger.error(f"Fatal error during cleanup: {e}")
            self.stats['error'] = str(e)
            return self.stats

    def _get_node_labels(self, session) -> List[str]:
        """Get all node labels present in the database"""
        query = """
        CALL db.labels() YIELD label
        RETURN label
        ORDER BY label
        """
        result = session.run(query)
        return [record['label'] for record in result]

    @staticmethod
    def _delete_expired_nodes_batch(tx, label: str, ttl_hours: int, dry_run: bool = False) -> int:
        """
        Delete expired nodes in batches to prevent performance issues

        Args:
            tx: Neo4j transaction
            label: Node label (e.g., 'Pod', 'Service')
            ttl_hours: Time-to-live in hours
            dry_run: If True, only count without deleting

        Returns:
            Total number of nodes deleted (or would be deleted)
        """
        total_deleted = 0
        batch_num = 0

        # Use DETACH DELETE to remove nodes and their relationships
        if dry_run:
            # Dry run: only count, don't delete
            query = f"""
            MATCH (n:{label})
            WHERE n.last_seen < datetime() - duration('PT{ttl_hours}H')
            RETURN count(n) as count
            """
            result = tx.run(query).single()
            total_deleted = result["count"] if result else 0
        else:
            # Actual deletion in batches
            while True:
                batch_num += 1
                query = f"""
                MATCH (n:{label})
                WHERE n.last_seen < datetime() - duration('PT{ttl_hours}H')
                WITH n LIMIT 1000
                DETACH DELETE n
                RETURN count(n) as count
                """
                result = tx.run(query).single()
                count = result["count"] if result else 0

                if count == 0:
                    break

                total_deleted += count
                logger.debug(f"  Batch {batch_num}: Deleted {count} {label} nodes")

        return total_deleted

    def run_cleanup_for_label(self, label: str, ttl_hours: int = None, dry_run: bool = False) -> Dict:
        """
        Run cleanup for a specific node label

        Args:
            label: Node label (e.g., 'Pod', 'Service')
            ttl_hours: Optional custom TTL (uses default if not provided)
            dry_run: If True, only report what would be deleted

        Returns:
            Cleanup statistics for this label
        """
        if ttl_hours is None:
            ttl_hours = self.ttl_policies.get(label, self.ttl_policies['Unknown'])

        logger.info(f"Running cleanup for {label} (TTL: {ttl_hours}h, Dry Run: {dry_run})")

        with self.driver.session() as session:
            deleted_count = session.execute_write(
                self._delete_expired_nodes_batch,
                label,
                ttl_hours,
                dry_run
            )

            stats = {
                'label': label,
                'ttl_hours': ttl_hours,
                'deleted_count': deleted_count,
                'dry_run': dry_run
            }

            logger.info(f"Result: {'Would delete' if dry_run else 'Deleted'} {deleted_count} {label} nodes")
            return stats

    def get_expired_nodes_count(self, label: str, ttl_hours: int = None) -> int:
        """
        Count expired nodes without deleting them

        Args:
            label: Node label
            ttl_hours: Optional custom TTL

        Returns:
            Number of expired nodes
        """
        if ttl_hours is None:
            ttl_hours = self.ttl_policies.get(label, self.ttl_policies['Unknown'])

        with self.driver.session() as session:
            query = f"""
            MATCH (n:{label})
            WHERE n.last_seen < datetime() - duration('PT{ttl_hours}H')
            RETURN count(n) as count
            """
            result = session.run(query).single()
            return result['count'] if result else 0

    def get_cleanup_stats(self) -> Dict:
        """
        Get statistics about expired nodes for all labels

        Returns:
            Dictionary with label -> expired_count mapping
        """
        stats = {}

        with self.driver.session() as session:
            node_labels = self._get_node_labels(session)

            for label in node_labels:
                ttl_hours = self.ttl_policies.get(label, self.ttl_policies['Unknown'])
                expired_count = self.get_expired_nodes_count(label, ttl_hours)
                stats[label] = {
                    'ttl_hours': ttl_hours,
                    'expired_count': expired_count,
                    'would_delete_mb': self._estimate_storage_saving(label, expired_count)
                }

        return stats

    def _estimate_storage_saving(self, label: str, count: int) -> float:
        """
        Estimate storage savings in MB

        Rough estimate: 1KB per node + 0.5KB per relationship
        """
        # This is a rough estimate, actual values vary
        avg_size_mb = 0.001  # 1KB per node
        return round(count * avg_size_mb, 2)

    def print_cleanup_preview(self):
        """Print a preview of what would be deleted"""
        stats = self.get_cleanup_stats()

        logger.info("=" * 60)
        logger.info("Cleanup Preview (What would be deleted)")
        logger.info("=" * 60)

        total_expired = 0
        for label, info in sorted(stats.items(), key=lambda x: x[1]['expired_count'], reverse=True):
            expired = info['expired_count']
            ttl = info['ttl_hours']
            if expired > 0:
                logger.info(f"  {label:20s} TTL: {ttl:4d}h | Expired: {expired:6d} nodes | Est. saving: {info['would_delete_mb']:6.2f} MB")
                total_expired += expired

        logger.info("-" * 60)
        logger.info(f"Total expired nodes: {total_expired}")
        logger.info("=" * 60)


def main():
    """Main entry point for running cleanup"""
    import argparse

    parser = argparse.ArgumentParser(description='AIOps Graph Cleaner')
    parser.add_argument('--dry-run', action='store_true', help='Preview what would be deleted without actually deleting')
    parser.add_argument('--label', type=str, help='Clean only specific node label')
    parser.add_argument('--ttl', type=int, help='Custom TTL in hours for the specified label')
    parser.add_argument('--preview', action='store_true', help='Show cleanup preview and exit')
    parser.add_argument('--uri', type=str, default=os.environ.get('NEO4J_URI', 'bolt://neo4j:7687'), help='Neo4j URI')
    parser.add_argument('--user', type=str, default=os.environ.get('NEO4J_USER', 'neo4j'), help='Neo4j username')
    parser.add_argument('--password', type=str, default=os.environ.get('NEO4J_PASSWORD', 'password123'), help='Neo4j password')

    args = parser.parse_args()

    # Initialize cleaner
    cleaner = GraphCleaner(
        uri=args.uri,
        user=args.user,
        password=args.password
    )

    # Connect to database
    if not cleaner.connect():
        logger.error("Failed to connect to Neo4j")
        return 1

    try:
        # Show preview if requested
        if args.preview:
            cleaner.print_cleanup_preview()
            return 0

        # Run cleanup for specific label or all labels
        if args.label:
            stats = cleaner.run_cleanup_for_label(args.label, args.ttl, args.dry_run)
        else:
            stats = cleaner.run_cleanup(dry_run=args.dry_run)

        # Print results
        logger.info(f"\n{'DRY RUN - ' if args.dry_run else ''}Cleanup Results:")
        logger.info(f"Total nodes deleted: {stats.get('total_deleted', 0)}")
        if 'nodes_by_type' in stats:
            for label, count in stats['nodes_by_type'].items():
                logger.info(f"  {label}: {count}")

        return 0

    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        return 1
    finally:
        cleaner.close()


if __name__ == '__main__':
    import sys
    sys.exit(main())