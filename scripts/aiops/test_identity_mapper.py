#!/usr/bin/env python3
"""
Test script for Identity Mapper

Validates:
1. URN generation and parsing
2. Prometheus instance resolution
3. Loki stream resolution
4. Neo4j node resolution
5. Reverse lookups (IP -> URN, Hostname -> URN)
6. Neo4j query generation
7. Batch operations
8. Caching
"""

import sys
import json
import logging
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, '/opt/Monitoring-deployment-main/scripts/aiops')

from identity_mapper import IdentityMapper, EntityType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestRunner:
    """Test runner for Identity Mapper"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []

    def run_test(self, test_name: str, test_func):
        """Run a single test"""
        try:
            logger.info(f"Running test: {test_name}")
            test_func()
            self.passed += 1
            self.tests.append({'name': test_name, 'status': 'PASSED'})
            logger.info(f"✓ {test_name} PASSED")
        except Exception as e:
            self.failed += 1
            self.tests.append({'name': test_name, 'status': 'FAILED', 'error': str(e)})
            logger.error(f"✗ {test_name} FAILED: {e}")
            raise

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Total: {self.passed + self.failed}")
        print(f"Passed: {self.passed} ✓")
        print(f"Failed: {self.failed} ✗")
        print("=" * 60)

        if self.failed > 0:
            print("\nFailed Tests:")
            for test in self.tests:
                if test['status'] == 'FAILED':
                    print(f"  ✗ {test['name']}: {test['error']}")


# ==================== Test Cases ====================

def test_urn_generation():
    """Test URN generation"""
    mapper = IdentityMapper()

    urn1 = mapper.generate_urn(EntityType.K8S_NODE, 'production', 'k8s-node-01')
    assert urn1 == 'urn:aiops:k8s:node:production:k8s-node-01', f"Expected 'urn:aiops:k8s:node:production:k8s-node-01', got '{urn1}'"

    urn2 = mapper.generate_urn(EntityType.NETWORK_SWITCH, 'dc1', 'core-switch-01')
    assert urn2 == 'urn:aiops:network:switch:dc1:core-switch-01', f"Expected 'urn:aiops:network:switch:dc1:core-switch-01', got '{urn2}'"

    logger.info(f"Generated URNs: {urn1}, {urn2}")


def test_urn_parsing():
    """Test URN parsing"""
    mapper = IdentityMapper()

    urn = 'urn:aiops:k8s:pod:production:api-server-7d8f9c2b4'
    parsed = mapper.parse_urn(urn)

    assert parsed is not None, "Failed to parse valid URN"
    entity_type, namespace, name = parsed
    assert entity_type == EntityType.K8S_POD, f"Expected K8S_POD, got {entity_type}"
    assert namespace == 'production', f"Expected 'production', got '{namespace}'"
    assert name == 'api-server-7d8f9c2b4', f"Expected 'api-server-7d8f9c2b4', got '{name}'"

    logger.info(f"Parsed URN: entity_type={entity_type}, namespace={namespace}, name={name}")


def test_prometheus_resolution():
    """Test Prometheus instance resolution"""
    mapper = IdentityMapper()

    # Test 1: Node exporter with IP
    labels = {
        'instance': '10.1.1.2:9100',
        'job': 'node_exporter',
        'cluster': 'production',
        'namespace': 'default'
    }
    metadata = mapper.resolve_prometheus_instance('10.1.1.2:9100', labels)

    assert metadata is not None, "Failed to resolve Prometheus instance"
    assert metadata.urn is not None, "URN is None"
    assert metadata.entity_type == EntityType.K8S_NODE, f"Expected K8S_NODE, got {metadata.entity_type}"
    assert 'ip' in metadata.aliases, "IP not in aliases"
    assert metadata.aliases['ip'] == '10.1.1.2', f"Expected IP '10.1.1.2', got '{metadata.aliases['ip']}'"

    logger.info(f"Resolved Prometheus instance: URN={metadata.urn}, Entity Type={metadata.entity_type.value}")

    # Test 2: Pod with hostname
    labels2 = {
        'instance': 'api-server-pod',
        'job': 'kubernetes-pods',
        'namespace': 'production',
        'pod': 'api-server-7d8f9c2b4',
        'pod_name': 'api-server-7d8f9c2b4'
    }
    metadata2 = mapper.resolve_prometheus_instance('api-server-pod', labels2)

    assert metadata2.entity_type == EntityType.K8S_POD, f"Expected K8S_POD, got {metadata2.entity_type}"
    assert metadata2.name == 'api-server-7d8f9c2b4', f"Expected name 'api-server-7d8f9c2b4', got '{metadata2.name}'"

    logger.info(f"Resolved Pod: URN={metadata2.urn}")


def test_loki_resolution():
    """Test Loki stream resolution"""
    mapper = IdentityMapper()

    labels = {
        'instance': 'k8s-node-01',
        'namespace': 'production',
        'pod': 'api-server-7d8f9c2b4-k4j5m',
        'node': 'k8s-node-01',
        'job': 'kubernetes-pods'
    }
    metadata = mapper.resolve_loki_stream(labels)

    assert metadata is not None, "Failed to resolve Loki stream"
    assert metadata.urn is not None, "URN is None"
    assert metadata.entity_type == EntityType.K8S_POD, f"Expected K8S_POD, got {metadata.entity_type}"
    assert metadata.name == 'api-server-7d8f9c2b4-k4j5m', f"Expected pod name 'api-server-7d8f9c2b4-k4j5m', got '{metadata.name}'"

    logger.info(f"Resolved Loki stream: URN={metadata.urn}")


def test_topology_resolution():
    """Test Neo4j topology node resolution"""
    mapper = IdentityMapper()

    node_data = {
        'name': 'core-switch-01',
        'type': 'switch',
        'ip': '10.1.1.1',
        'site': 'datacenter-1',
        'vendor': 'Cisco'
    }
    metadata = mapper.resolve_topology_node(node_data)

    assert metadata is not None, "Failed to resolve topology node"
    assert metadata.urn is not None, "URN is None"
    assert metadata.entity_type == EntityType.NETWORK_SWITCH, f"Expected NETWORK_SWITCH, got {metadata.entity_type}"
    assert 'ip' in metadata.aliases, "IP not in aliases"
    assert metadata.aliases['ip'] == '10.1.1.1', f"Expected IP '10.1.1.1', got '{metadata.aliases['ip']}'"

    logger.info(f"Resolved topology node: URN={metadata.urn}")


def test_reverse_lookups():
    """Test reverse lookups (IP -> URN, Hostname -> URN)"""
    mapper = IdentityMapper()

    # Create entity with IP
    labels = {
        'instance': '10.1.1.2:9100',
        'hostname': 'k8s-node-01',
        'namespace': 'default'
    }
    metadata = mapper.resolve_prometheus_instance('10.1.1.2:9100', labels)

    # Test IP lookup
    urn_from_ip = mapper.ip_to_urn('10.1.1.2')
    assert urn_from_ip == metadata.urn, f"Expected URN '{metadata.urn}', got '{urn_from_ip}'"

    # Test hostname lookup
    urn_from_hostname = mapper.hostname_to_urn('k8s-node-01')
    assert urn_from_hostname == metadata.urn, f"Expected URN '{metadata.urn}', got '{urn_from_hostname}'"

    # Test URN to IP
    ip_from_urn = mapper.urn_to_ip(metadata.urn)
    assert ip_from_urn == '10.1.1.2', f"Expected IP '10.1.1.2', got '{ip_from_urn}'"

    logger.info(f"Reverse lookups: IP->URN='{urn_from_ip}', Hostname->URN='{urn_from_hostname}', URN->IP='{ip_from_urn}'")


def test_neo4j_query_generation():
    """Test Neo4j query generation from URN"""
    mapper = IdentityMapper()

    # Test K8S node query
    urn = 'urn:aiops:k8s:node:production:k8s-node-01'
    query_params = mapper.urn_to_neo4j_query(urn)

    assert query_params['match'] == 'MATCH (n:Node)', f"Expected 'MATCH (n:Node)', got '{query_params['match']}'"
    assert 'WHERE n.name = $name' in query_params['where'], "WHERE clause missing"
    assert query_params['params']['name'] == 'k8s-node-01', f"Expected name 'k8s-node-01', got '{query_params['params']['name']}'"

    logger.info(f"Neo4j query: {query_params['match']} {query_params['where']}")

    # Test network switch query
    urn2 = 'urn:aiops:network:switch:dc1:core-switch-01'
    query_params2 = mapper.urn_to_neo4j_query(urn2)

    assert query_params2['match'] == 'MATCH (n:Device)', f"Expected 'MATCH (n:Device)', got '{query_params2['match']}'"
    assert "n.type = 'switch'" in query_params2['where'], "Switch type filter missing"

    logger.info(f"Neo4j query 2: {query_params2['match']} {query_params2['where']}")


def test_batch_operations():
    """Test batch operations"""
    mapper = IdentityMapper()

    # Test batch Prometheus resolution
    metrics_list = [
        {'labels': {'instance': '10.1.1.2:9100', 'namespace': 'default'}},
        {'labels': {'instance': '10.1.1.3:9100', 'namespace': 'default'}},
        {'labels': {'instance': 'api-server-pod', 'namespace': 'production', 'pod': 'api-server-1'}}
    ]

    results = mapper.batch_resolve_prometheus(metrics_list)

    assert len(results) == 3, f"Expected 3 results, got {len(results)}"
    assert all(m.urn is not None for m in results), "Some URNs are None"

    logger.info(f"Batch resolved {len(results)} Prometheus metrics")

    # Test batch Loki resolution
    streams_list = [
        {'instance': 'k8s-node-01', 'namespace': 'production', 'pod': 'api-server-1'},
        {'instance': 'k8s-node-02', 'namespace': 'production', 'pod': 'db-server-1'}
    ]

    results2 = mapper.batch_resolve_loki(streams_list)

    assert len(results2) == 2, f"Expected 2 results, got {len(results2)}"
    assert all(m.urn is not None for m in results2), "Some URNs are None"

    logger.info(f"Batch resolved {len(results2)} Loki streams")


def test_caching():
    """Test caching functionality"""
    mapper = IdentityMapper()

    # Create entity
    labels = {
        'instance': '10.1.1.5:9100',
        'hostname': 'test-server',
        'namespace': 'test'
    }
    metadata = mapper.resolve_prometheus_instance('10.1.1.5:9100', labels)

    # Check cache stats
    stats = mapper.get_cache_stats()
    assert stats['urn_count'] >= 1, "Cache should have at least 1 URN"
    assert stats['ip_mapping_count'] >= 1, "Cache should have at least 1 IP mapping"
    assert stats['hostname_mapping_count'] >= 1, "Cache should have at least 1 hostname mapping"

    logger.info(f"Cache stats: {json.dumps(stats, indent=2)}")

    # Clear cache
    mapper.clear_cache()
    stats_after_clear = mapper.get_cache_stats()
    assert stats_after_clear['urn_count'] == 0, "Cache should be empty after clear"
    assert stats_after_clear['ip_mapping_count'] == 0, "IP mappings should be empty after clear"

    logger.info("Cache cleared successfully")


def test_integration_scenario():
    """Test integration scenario: Metrics -> Logs -> Topology"""
    mapper = IdentityMapper()

    # Step 1: Prometheus metric comes in
    prometheus_labels = {
        'instance': '10.1.1.2:9100',
        'job': 'node_exporter',
        'cluster': 'production',
        'namespace': 'default'
    }
    metric_entity = mapper.resolve_prometheus_instance('10.1.1.2:9100', prometheus_labels)

    logger.info(f"Step 1 - Prometheus entity: {metric_entity.urn}")

    # Step 2: Loki logs come in for the same instance
    loki_labels = {
        'instance': '10.1.1.2',
        'namespace': 'default',
        'node': 'k8s-node-01'
    }
    log_entity = mapper.resolve_loki_stream(loki_labels)

    logger.info(f"Step 2 - Loki entity: {log_entity.urn}")

    # Step 3: Neo4j topology node
    neo4j_node = {
        'name': 'k8s-node-01',
        'type': 'node',
        'ip': '10.1.1.2',
        'namespace': 'default'
    }
    topology_entity = mapper.resolve_topology_node(neo4j_node)

    logger.info(f"Step 3 - Topology entity: {topology_entity.urn}")

    # Verify all entities map to the same URN
    assert metric_entity.urn == log_entity.urn == topology_entity.urn, \
        f"Entities should have the same URN: metric={metric_entity.urn}, log={log_entity.urn}, topology={topology_entity.urn}"

    logger.info("✓ All three entities map to the same URN - Integration successful!")


# ==================== Main Test Runner ====================

def main():
    """Main test runner"""
    print("=" * 60)
    print("Identity Mapper Test Suite")
    print("=" * 60)
    print()

    runner = TestRunner()

    # Run all tests
    runner.run_test("URN Generation", test_urn_generation)
    runner.run_test("URN Parsing", test_urn_parsing)
    runner.run_test("Prometheus Resolution", test_prometheus_resolution)
    runner.run_test("Loki Resolution", test_loki_resolution)
    runner.run_test("Topology Resolution", test_topology_resolution)
    runner.run_test("Reverse Lookups", test_reverse_lookups)
    runner.run_test("Neo4j Query Generation", test_neo4j_query_generation)
    runner.run_test("Batch Operations", test_batch_operations)
    runner.run_test("Caching", test_caching)
    runner.run_test("Integration Scenario", test_integration_scenario)

    # Print summary
    runner.print_summary()

    # Exit with appropriate code
    sys.exit(0 if runner.failed == 0 else 1)


if __name__ == '__main__':
    main()