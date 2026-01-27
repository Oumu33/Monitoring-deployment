#!/usr/bin/env python3
"""
Simple integration test for Identity Mapper
"""

import sys
sys.path.insert(0, '/opt/Monitoring-deployment-main/scripts/aiops')

from identity_mapper import IdentityMapper, EntityType

def test_simple_integration():
    """Test simple integration scenario"""
    mapper = IdentityMapper()

    # Scenario: Prometheus metrics from node_exporter
    prometheus_labels = {
        'instance': '10.1.1.2:9100',
        'job': 'node_exporter',
        'cluster': 'production',
        'namespace': 'default',
        'node': 'k8s-node-01'  # This is the key label
    }
    metric_entity = mapper.resolve_prometheus_instance('10.1.1.2:9100', prometheus_labels)

    print(f"Prometheus entity: {metric_entity.urn}")
    print(f"  Name: {metric_entity.name}")
    print(f"  Type: {metric_entity.entity_type.value}")
    print(f"  Aliases: {metric_entity.aliases}")

    # Loki logs from the same node
    loki_labels = {
        'instance': 'k8s-node-01',
        'namespace': 'default',
        'node': 'k8s-node-01'
    }
    log_entity = mapper.resolve_loki_stream(loki_labels)

    print(f"\nLoki entity: {log_entity.urn}")
    print(f"  Name: {log_entity.name}")
    print(f"  Type: {log_entity.entity_type.value}")

    # Neo4j topology node
    neo4j_node = {
        'name': 'k8s-node-01',
        'type': 'node',
        'ip': '10.1.1.2',
        'namespace': 'default'
    }
    topology_entity = mapper.resolve_topology_node(neo4j_node)

    print(f"\nTopology entity: {topology_entity.urn}")
    print(f"  Name: {topology_entity.name}")
    print(f"  Type: {topology_entity.entity_type.value}")

    # Verify all entities map to the same URN
    if metric_entity.urn == log_entity.urn == topology_entity.urn:
        print("\n✓ SUCCESS: All entities map to the same URN!")
        print(f"  Unified URN: {metric_entity.urn}")
        return True
    else:
        print("\n✗ FAILED: Entities have different URNs")
        print(f"  Metric URN: {metric_entity.urn}")
        print(f"  Log URN: {log_entity.urn}")
        print(f"  Topology URN: {topology_entity.urn}")
        return False

if __name__ == '__main__':
    success = test_simple_integration()
    sys.exit(0 if success else 1)
