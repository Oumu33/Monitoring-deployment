#!/usr/bin/env python3
"""
AIOps Identity Mapper

Provides unified entity identification across heterogeneous data sources:
- VictoriaMetrics (Prometheus format)
- Loki
- Neo4j Topology

URN Format: urn:aiops:{entity_type}:{namespace}:{name}

Entity Types:
- k8s:node
- k8s:pod
- k8s:service
- network:switch
- network:router
- server:physical
- server:vm
"""

import re
import json
import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EntityType(Enum):
    """Entity type enumeration"""
    K8S_NODE = "k8s:node"
    K8S_POD = "k8s:pod"
    K8S_SERVICE = "k8s:service"
    NETWORK_SWITCH = "network:switch"
    NETWORK_ROUTER = "network:router"
    SERVER_PHYSICAL = "server:physical"
    SERVER_VM = "server:vm"
    UNKNOWN = "unknown"


@dataclass
class EntityMetadata:
    """Entity metadata"""
    urn: str
    entity_type: EntityType
    namespace: str
    name: str
    labels: Dict[str, str]
    aliases: Dict[str, str]  # Alternative identifiers (IP, hostname, etc.)


class IdentityMapper:
    """
    Unified entity identification mapper

    Converts heterogeneous identifiers to unified URNs and provides
    reverse lookups for different data sources.
    """

    def __init__(self, redis_client=None):
        """
        Initialize Identity Mapper

        Args:
            redis_client: Optional Redis client for caching mappings
        """
        self.redis_client = redis_client
        self._cache_enabled = redis_client is not None

        # Mapping cache in memory
        self._urn_to_entity = {}
        self._ip_to_urn = {}
        self._hostname_to_urn = {}

        # Pre-compile regex patterns
        self._patterns = {
            'prometheus_instance': re.compile(r'^([^:]+):(\d+)$'),
            'k8s_pod': re.compile(r'^([a-z0-9-]+)-([a-z0-9]{5,10})-([a-z0-9]{5})$'),
            'ip_address': re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'),
        }

        logger.info("Identity Mapper initialized")

    # ==================== URN Generation ====================

    def generate_urn(self, entity_type: EntityType, namespace: str, name: str) -> str:
        """
        Generate unified URN for an entity

        Args:
            entity_type: Type of entity
            namespace: Namespace or cluster name
            name: Entity name

        Returns:
            Unified URN string
        """
        return f"urn:aiops:{entity_type.value}:{namespace}:{name}"

    def parse_urn(self, urn: str) -> Optional[Tuple[EntityType, str, str]]:
        """
        Parse URN string into components

        URN Format: urn:aiops:{entity_type}:{namespace}:{name}
        Example: urn:aiops:k8s:node:production:k8s-node-01

        Args:
            urn: URN string

        Returns:
            Tuple of (entity_type, namespace, name) or None if invalid
        """
        try:
            parts = urn.split(':')
            if len(parts) < 4 or parts[0] != 'urn' or parts[1] != 'aiops':
                return None

            # Entity type is the combination of parts 2 and 3 (e.g., "k8s:node")
            entity_type_str = f"{parts[2]}:{parts[3]}"

            # Everything after the first 4 parts is the name
            # Namespace is part 4, name is parts[5:] joined by ':'
            if len(parts) >= 6:
                namespace = parts[4]
                name = ':'.join(parts[5:])
            else:
                # Fallback for simple cases
                namespace = 'default'
                name = parts[4] if len(parts) > 4 else 'unknown'

            entity_type = EntityType(entity_type_str)
            return (entity_type, namespace, name)

        except (ValueError, IndexError) as e:
            logger.warning(f"Invalid URN format: {urn} - Error: {e}")
            return None

    # ==================== Prometheus Mapping ====================

    def resolve_prometheus_instance(self, instance: str, labels: Dict[str, str]) -> EntityMetadata:
        """
        Resolve Prometheus instance label to unified URN

        Args:
            instance: Prometheus instance label (e.g., "10.1.1.2:9100" or "k8s-node-01")
            labels: Additional Prometheus labels

        Returns:
            EntityMetadata with unified URN
        """
        # Try to extract IP or hostname
        match = self._patterns['prometheus_instance'].match(instance)
        if match:
            identifier = match.group(1)  # IP or hostname
        else:
            identifier = instance

        # Determine entity type from labels
        entity_type = self._infer_entity_type_from_labels(labels)

        # Determine namespace
        namespace = labels.get('namespace', labels.get('cluster', 'default'))

        # Determine name - prioritize explicit labels over instance identifier
        name = identifier  # Default to the instance identifier

        if entity_type == EntityType.K8S_POD:
            name = labels.get('pod', labels.get('pod_name', identifier))
        elif entity_type == EntityType.K8S_NODE:
            # For node_exporter, prioritize the 'node' label if available
            name = labels.get('node', labels.get('nodename', identifier))
        elif entity_type == EntityType.K8S_SERVICE:
            name = labels.get('service', labels.get('service_name', identifier))
        elif entity_type == EntityType.SERVER_PHYSICAL:
            # For physical servers, try to use hostname or nodename
            name = labels.get('hostname', labels.get('nodename', identifier))

        # Generate URN
        urn = self.generate_urn(entity_type, namespace, name)

        # Build metadata
        metadata = EntityMetadata(
            urn=urn,
            entity_type=entity_type,
            namespace=namespace,
            name=name,
            labels=labels,
            aliases={
                'prometheus_instance': instance,
                'identifier': identifier
            }
        )

        # Add IP if available
        if self._patterns['ip_address'].match(identifier):
            metadata.aliases['ip'] = identifier

        # Add hostname if available
        if 'hostname' in labels:
            metadata.aliases['hostname'] = labels['hostname']

        # Add node name if available
        if 'node' in labels:
            metadata.aliases['node'] = labels['node']

        # Cache the mapping
        self._cache_mapping(metadata)

        logger.info(f"Resolved Prometheus instance '{instance}' to URN '{urn}'")
        return metadata

    def _infer_entity_type_from_labels(self, labels: Dict[str, str]) -> EntityType:
        """Infer entity type from Prometheus labels"""
        # Check for K8s pod labels
        if 'pod' in labels or 'pod_name' in labels:
            return EntityType.K8S_POD

        # Check for K8s node labels
        if 'node' in labels:
            return EntityType.K8S_NODE

        # Check for node_exporter job
        job = labels.get('job', '').lower()
        if job.startswith('node_exporter') or 'node-exporter' in job:
            return EntityType.K8S_NODE

        # Check for K8s service labels
        if 'service' in labels or 'service_name' in labels:
            return EntityType.K8S_SERVICE

        # Check for network device labels
        if 'device' in labels or 'switch' in job or 'router' in job:
            return EntityType.NETWORK_SWITCH

        # Default to physical server
        return EntityType.SERVER_PHYSICAL

    # ==================== Loki Mapping ====================

    def resolve_loki_stream(self, stream_labels: Dict[str, str]) -> EntityMetadata:
        """
        Resolve Loki stream labels to unified URN

        Args:
            stream_labels: Loki stream labels

        Returns:
            EntityMetadata with unified URN
        """
        # Extract instance or hostname
        instance = stream_labels.get('instance', stream_labels.get('hostname', 'unknown'))
        namespace = stream_labels.get('namespace', stream_labels.get('cluster', 'default'))
        pod = stream_labels.get('pod', stream_labels.get('pod_name', ''))
        node = stream_labels.get('node', '')

        # Determine entity type
        if pod:
            entity_type = EntityType.K8S_POD
            name = pod
        elif node:
            entity_type = EntityType.K8S_NODE
            name = node
        else:
            entity_type = EntityType.SERVER_PHYSICAL
            name = instance

        # Generate URN
        urn = self.generate_urn(entity_type, namespace, name)

        # Build metadata
        metadata = EntityMetadata(
            urn=urn,
            entity_type=entity_type,
            namespace=namespace,
            name=name,
            labels=stream_labels,
            aliases={
                'loki_instance': instance,
                'stream_labels': json.dumps(stream_labels)
            }
        )

        # Add IP if available
        if 'ip' in stream_labels:
            metadata.aliases['ip'] = stream_labels['ip']

        # Cache the mapping
        self._cache_mapping(metadata)

        logger.info(f"Resolved Loki stream to URN '{urn}'")
        return metadata

    # ==================== Topology (Neo4j) Mapping ====================

    def resolve_topology_node(self, node_data: Dict[str, str]) -> EntityMetadata:
        """
        Resolve Neo4j topology node to unified URN

        Args:
            node_data: Neo4j node properties

        Returns:
            EntityMetadata with unified URN
        """
        name = node_data.get('name', node_data.get('id', 'unknown'))
        node_type = node_data.get('type', node_data.get('device_type', 'unknown'))
        ip = node_data.get('ip', '')
        namespace = node_data.get('namespace', node_data.get('site', 'default'))

        # Map node_type to EntityType
        entity_type_map = {
            'switch': EntityType.NETWORK_SWITCH,
            'router': EntityType.NETWORK_ROUTER,
            'node': EntityType.K8S_NODE,
            'pod': EntityType.K8S_POD,
            'service': EntityType.K8S_SERVICE,
            'server': EntityType.SERVER_PHYSICAL,
            'vm': EntityType.SERVER_VM,
        }

        entity_type = entity_type_map.get(node_type.lower(), EntityType.UNKNOWN)

        # Generate URN
        urn = self.generate_urn(entity_type, namespace, name)

        # Build metadata
        metadata = EntityMetadata(
            urn=urn,
            entity_type=entity_type,
            namespace=namespace,
            name=name,
            labels=node_data,
            aliases={
                'neo4j_name': name,
                'neo4j_type': node_type
            }
        )

        # Add IP if available
        if ip:
            metadata.aliases['ip'] = ip

        # Cache the mapping
        self._cache_mapping(metadata)

        logger.info(f"Resolved Neo4j node to URN '{urn}'")
        return metadata

    # ==================== Reverse Lookups ====================

    def urn_to_ip(self, urn: str) -> Optional[str]:
        """Get IP address from URN"""
        metadata = self._get_metadata(urn)
        return metadata.aliases.get('ip') if metadata else None

    def ip_to_urn(self, ip: str) -> Optional[str]:
        """Get URN from IP address"""
        return self._ip_to_urn.get(ip)

    def hostname_to_urn(self, hostname: str) -> Optional[str]:
        """Get URN from hostname"""
        return self._hostname_to_urn.get(hostname)

    def urn_to_neo4j_query(self, urn: str) -> Dict:
        """
        Convert URN to Neo4j query parameters

        Returns:
            Dict with 'match' and 'where' clauses
        """
        parsed = self.parse_urn(urn)
        if not parsed:
            return {'match': 'MATCH (n)', 'where': 'WHERE 1=0', 'params': {}}

        entity_type, namespace, name = parsed

        # Build query based on entity type
        if entity_type == EntityType.K8S_NODE:
            match_clause = "MATCH (n:Node)"
            where_clause = "WHERE n.name = $name AND n.namespace = $namespace"
        elif entity_type == EntityType.K8S_POD:
            match_clause = "MATCH (n:Pod)"
            where_clause = "WHERE n.name = $name AND n.namespace = $namespace"
        elif entity_type == EntityType.NETWORK_SWITCH:
            match_clause = "MATCH (n:Device)"
            where_clause = "WHERE n.name = $name AND n.type = 'switch'"
        else:
            match_clause = "MATCH (n:Device)"
            where_clause = "WHERE n.name = $name"

        return {
            'match': match_clause,
            'where': where_clause,
            'params': {
                'name': name,
                'namespace': namespace
            }
        }

    # ==================== Caching ====================

    def _cache_mapping(self, metadata: EntityMetadata):
        """Cache entity mapping"""
        # In-memory cache
        self._urn_to_entity[metadata.urn] = metadata

        # IP to URN mapping
        if 'ip' in metadata.aliases:
            self._ip_to_urn[metadata.aliases['ip']] = metadata.urn

        # Hostname to URN mapping
        if 'hostname' in metadata.aliases:
            self._hostname_to_urn[metadata.aliases['hostname']] = metadata.urn

        # Redis cache
        if self._cache_enabled and self.redis_client:
            try:
                # Store entity metadata
                key = f"entity:{metadata.urn}"
                self.redis_client.setex(
                    key,
                    3600,  # 1 hour TTL
                    json.dumps({
                        'urn': metadata.urn,
                        'entity_type': metadata.entity_type.value,
                        'namespace': metadata.namespace,
                        'name': metadata.name,
                        'aliases': metadata.aliases
                    })
                )

                # Store reverse mappings
                if 'ip' in metadata.aliases:
                    ip_key = f"entity:ip:{metadata.aliases['ip']}"
                    self.redis_client.setex(ip_key, 3600, metadata.urn)

                if 'hostname' in metadata.aliases:
                    host_key = f"entity:host:{metadata.aliases['hostname']}"
                    self.redis_client.setex(host_key, 3600, metadata.urn)

            except Exception as e:
                logger.error(f"Failed to cache mapping in Redis: {e}")

    def _get_metadata(self, urn: str) -> Optional[EntityMetadata]:
        """Get entity metadata from cache"""
        # Try in-memory cache first
        if urn in self._urn_to_entity:
            return self._urn_to_entity[urn]

        # Try Redis cache
        if self._cache_enabled and self.redis_client:
            try:
                key = f"entity:{urn}"
                data = self.redis_client.get(key)
                if data:
                    entity_data = json.loads(data)
                    metadata = EntityMetadata(
                        urn=entity_data['urn'],
                        entity_type=EntityType(entity_data['entity_type']),
                        namespace=entity_data['namespace'],
                        name=entity_data['name'],
                        labels={},
                        aliases=entity_data['aliases']
                    )
                    # Update in-memory cache
                    self._urn_to_entity[urn] = metadata
                    return metadata
            except Exception as e:
                logger.error(f"Failed to get metadata from Redis: {e}")

        return None

    # ==================== Batch Operations ====================

    def batch_resolve_prometheus(self, metrics_list: list) -> list:
        """
        Batch resolve multiple Prometheus metrics

        Args:
            metrics_list: List of metric dictionaries with 'labels' field

        Returns:
            List of EntityMetadata objects
        """
        results = []
        for metric in metrics_list:
            labels = metric.get('labels', {})
            instance = labels.get('instance', labels.get('hostname', 'unknown'))
            metadata = self.resolve_prometheus_instance(instance, labels)
            results.append(metadata)
        return results

    def batch_resolve_loki(self, streams_list: list) -> list:
        """
        Batch resolve multiple Loki streams

        Args:
            streams_list: List of stream label dictionaries

        Returns:
            List of EntityMetadata objects
        """
        results = []
        for stream in streams_list:
            metadata = self.resolve_loki_stream(stream)
            results.append(metadata)
        return results

    # ==================== Statistics ====================

    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        return {
            'urn_count': len(self._urn_to_entity),
            'ip_mapping_count': len(self._ip_to_urn),
            'hostname_mapping_count': len(self._hostname_to_urn),
            'redis_enabled': self._cache_enabled
        }

    def clear_cache(self):
        """Clear all caches"""
        self._urn_to_entity.clear()
        self._ip_to_urn.clear()
        self._hostname_to_urn.clear()
        logger.info("Identity Mapper cache cleared")


# ==================== Example Usage ====================

if __name__ == '__main__':
    import redis

    # Initialize with Redis
    redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
    mapper = IdentityMapper(redis_client=redis_client)

    # Example 1: Resolve Prometheus instance
    prometheus_labels = {
        'instance': '10.1.1.2:9100',
        'job': 'node_exporter',
        'cluster': 'production',
        'namespace': 'default'
    }
    entity1 = mapper.resolve_prometheus_instance('10.1.1.2:9100', prometheus_labels)
    print(f"Prometheus URN: {entity1.urn}")

    # Example 2: Resolve Loki stream
    loki_labels = {
        'instance': 'k8s-node-01',
        'namespace': 'production',
        'pod': 'api-server-7d8f9c2b4-k4j5m',
        'node': 'k8s-node-01'
    }
    entity2 = mapper.resolve_loki_stream(loki_labels)
    print(f"Loki URN: {entity2.urn}")

    # Example 3: Resolve Neo4j node
    neo4j_node = {
        'name': 'core-switch-01',
        'type': 'switch',
        'ip': '10.1.1.1',
        'site': 'datacenter-1'
    }
    entity3 = mapper.resolve_topology_node(neo4j_node)
    print(f"Neo4j URN: {entity3.urn}")

    # Example 4: Reverse lookup
    print(f"IP 10.1.1.1 -> URN: {mapper.ip_to_urn('10.1.1.1')}")

    # Example 5: Neo4j query generation
    query_params = mapper.urn_to_neo4j_query(entity3.urn)
    print(f"Neo4j Query: {query_params['match']} {query_params['where']}")

    # Cache stats
    print(f"Cache stats: {mapper.get_cache_stats()}")