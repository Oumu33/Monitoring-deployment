# AIOps Graph Schema Design

## Overview

This document defines the unified graph schema for AIOps topology management, supporting Kubernetes workloads, network infrastructure, and physical servers.

## URN Naming Convention

All entities are identified using unified URNs:
```
urn:aiops:{entity_type}:{namespace}:{name}
```

### Entity Types

| Type | URN Format | Example | Description |
|------|------------|---------|-------------|
| `k8s:node` | `urn:aiops:k8s:node:{namespace}:{name}` | `urn:aiops:k8s:node:production:k8s-node-01` | Kubernetes node |
| `k8s:pod` | `urn:aiops:k8s:pod:{namespace}:{name}` | `urn:aiops:k8s:pod:production:api-server-7d8f9c2b4` | Kubernetes pod |
| `k8s:service` | `urn:aiops:k8s:service:{namespace}:{name}` | `urn:aiops:k8s:service:production:api-service` | Kubernetes service |
| `network:switch` | `urn:aiops:network:switch:{site}:{name}` | `urn:aiops:network:switch:dc1:core-switch-01` | Network switch |
| `network:router` | `urn:aiops:network:router:{site}:{name}` | `urn:aiops:network:router:dc1:edge-router-01` | Network router |
| `server:physical` | `urn:aiops:server:physical:{site}:{name}` | `urn:aiops:server:physical:dc1:server-01` | Physical server |
| `server:vm` | `urn:aiops:server:vm:{site}:{name}` | `urn:aiops:server:vm:dc1:vm-web-01` | Virtual machine |

## Node Labels (Cypher)

### 1. Kubernetes Nodes

```
(:Node {
    urn: string,                          # Unique identifier
    name: string,                         # Node name
    namespace: string,                    # Cluster/namespace
    ip: string,                           # Primary IP address
    hostname: string,                     # Hostname
    labels: map<string, string>,          # K8s labels
    capacity_cpu: int,                    # CPU cores
    capacity_memory: int,                 # Memory in GB
    status: string,                       # Ready/NotReady/Unknown
    kubelet_version: string,              # Kubernetes version
    valid_from: datetime,                 # Valid from timestamp
    valid_to: datetime,                   # Valid to timestamp (nullable)
    last_updated: datetime                # Last update timestamp
})
```

### 2. Kubernetes Pods

```
(:Pod {
    urn: string,                          # Unique identifier
    name: string,                         # Pod name
    namespace: string,                    # Namespace
    ip: string,                           # Pod IP
    host_ip: string,                      # Host node IP
    node_name: string,                    # Host node name
    containers: list<string>,             # Container names
    status: string,                       # Running/Pending/Failed/Succeeded
    phase: string,                        # Pod phase
    restart_count: int,                   # Total restart count
    valid_from: datetime,                 # Valid from timestamp
    valid_to: datetime,                   # Valid to timestamp (nullable)
    last_updated: datetime                # Last update timestamp
})
```

### 3. Kubernetes Services

```
(:Service {
    urn: string,                          # Unique identifier
    name: string,                         # Service name
    namespace: string,                    # Namespace
    cluster_ip: string,                   # Cluster IP
    type: string,                         # ClusterIP/NodePort/LoadBalancer
    ports: list<map>,                     # Service ports
    selector: map<string, string>,        # Pod selector
    valid_from: datetime,                 # Valid from timestamp
    valid_to: datetime,                   # Valid to timestamp (nullable)
    last_updated: datetime                # Last update timestamp
})
```

### 4. Network Devices

```
(:Device {
    urn: string,                          # Unique identifier
    name: string,                         # Device name
    type: string,                         # switch/router/firewall
    vendor: string,                       # Cisco/Juniper/Arista
    model: string,                        # Model number
    ip: string,                           # Management IP
    site: string,                         # Datacenter/site location
    rack: string,                         # Rack location
    status: string,                       # online/offline/degraded
    capacity_bandwidth: int,              # Bandwidth in Gbps
    valid_from: datetime,                 # Valid from timestamp
    valid_to: datetime,                   # Valid to timestamp (nullable)
    last_updated: datetime                # Last update timestamp
})
```

### 5. Physical Servers

```
(:Server {
    urn: string,                          # Unique identifier
    name: string,                         # Server name
    type: string,                         # physical/vm
    ip: string,                           # Primary IP
    hostname: string,                     # Hostname
    site: string,                         # Datacenter/site
    rack: string,                         # Rack location
    cpu_cores: int,                       # CPU cores
    memory_gb: int,                       # Memory in GB
    disk_gb: int,                         # Disk capacity in GB
    os_type: string,                      # OS type
    os_version: string,                   # OS version
    status: string,                       # online/offline/maintenance
    valid_from: datetime,                 # Valid from timestamp
    valid_to: datetime,                   # Valid to timestamp (nullable)
    last_updated: datetime                # Last update timestamp
})
```

## Relationship Types (Cypher)

### 1. HOSTS (Node hosts Pod)

```
(:Node)-[:HOSTS {
    created_at: datetime,
    last_updated: datetime
}]->(:Pod)
```

### 2. RUNS_ON (Pod runs on Node)

```
(:Pod)-[:RUNS_ON {
    created_at: datetime,
    last_updated: datetime
}]->(:Node)
```

### 3. EXPOSES (Service exposes Pod)

```
(:Service)-[:EXPOSES {
    port: int,
    target_port: int,
    protocol: string,                     # TCP/UDP
    created_at: datetime,
    last_updated: datetime
}]->(:Pod)
```

### 4. CONNECTS_TO (Network connectivity)

```
(:Device)-[:CONNECTS_TO {
    source_port: string,                  # Source interface/port
    target_port: string,                  # Target interface/port
    criticality: float,                   # 0.0-1.0, dependency strength
    bandwidth_mbps: int,                  # Link bandwidth
    latency_ms: float,                    # Expected latency
    created_at: datetime,
    last_updated: datetime
}]->(:Device)
```

### 5. DEPENDS_ON (Service dependency)

```
(:Service)-[:DEPENDS_ON {
    type: string,                         # http/tcp/rpc
    criticality: float,                   # 0.0-1.0, dependency strength
    created_at: datetime,
    last_updated: datetime
}]->(:Service)
```

### 6. ROUTES_TO (Routing path)

```
(:Device)-[:ROUTES_TO {
    next_hop_ip: string,
    route_metric: int,
    created_at: datetime,
    last_updated: datetime
}]->(:Device)
```

## Edge Criticality Weights

### Overview

Edge criticality weights measure the "fatalness" of dependencies between entities. A higher weight (closer to 1.0) indicates a stronger dependency where the failure of the target will immediately impact the source.

### Weight Scale

| Weight | Severity | Description | Example |
|--------|----------|-------------|---------|
| 1.0 | CRITICAL | Physical dependency, life-or-death | Pod running on Node |
| 0.9 | HIGH | Synchronous strong dependency | REST/RPC calls to Database |
| 0.8 | MEDIUM-HIGH | Configuration dependency, startup required | Pod mounting ConfigMap |
| 0.7 | MEDIUM | Network infrastructure dependency | Service connecting to Router |
| 0.5 | MEDIUM-LOW | Default dependency, moderate impact | Default service-to-service calls |
| 0.2 | LOW | Auxiliary dependency, minimal impact | Logging sidecar connections |

### Predefined Weight Categories

| Category | Weight | Relationship Types | Use Cases |
|----------|--------|-------------------|-----------|
| `PHYSICAL` | 1.0 | HOSTED_ON | Pod → Node, Container → Pod |
| `SYNC_CALL` | 0.9 | CALLS, CONNECTS_TO | Service → Database, API → API |
| `CONFIG` | 0.8 | MOUNTS | Pod → ConfigMap, Pod → Secret |
| `ASYNC_CALL` | 0.5 | CALLS (async) | Service → Kafka, Service → RabbitMQ |
| `SIDECAR` | 0.2 | CONNECTS_TO | Service → Fluentd, Service → Istio-Proxy |
| `UNKNOWN` | 0.5 | Any | Fallback for unknown dependencies |

### Intelligent Weight Calculation

The system uses a heuristic function to calculate edge criticality based on multiple factors:

#### 1. Port-Based Detection

**Synchronous (Strong Dependency) Ports:**
- Web: 80, 443, 8080, 8443
- Databases: 3306 (MySQL), 5432 (PostgreSQL), 6379 (Redis), 27017 (MongoDB), 9200 (Elasticsearch)

**Asynchronous (Weak Dependency) Ports:**
- Message Queues: 9092, 9093, 9094 (Kafka), 5672 (RabbitMQ), 1883 (MQTT), 61616 (ActiveMQ)

#### 2. Name-Based Detection

**Database/Storage Keywords:**
- mysql, postgres, redis, mongodb, elasticsearch, cassandra, influxdb
- Result: Weight = 0.9 (SYNC_CALL)

**Message Queue Keywords:**
- kafka, rabbitmq, activemq, pulsar, nats, mqtt, redis-stream
- Result: Weight = 0.5 (ASYNC_CALL)

**Sidecar Keywords:**
- fluentd, filebeat, promtail, loki, otel-collector, istio-proxy, envoy
- Result: Weight = 0.2 (SIDECAR)

#### 3. Type-Based Detection

**Physical Dependency:**
- Relation: HOSTED_ON
- Result: Weight = 1.0 (PHYSICAL)

**Network Infrastructure:**
- Type: router, switch, firewall
- Result: Weight = 0.7 (MEDIUM)

### Query Examples

#### Find High Criticality Paths

```cypher
MATCH path = (start:Device)-[:CONNECTS_TO*1..3]->(end:Device)
WHERE ALL(rel IN relationships(path) WHERE rel.criticality >= 0.9)
RETURN path, 
       reduce(total = 0.0, rel IN relationships(path) | total + rel.criticality) AS total_criticality
ORDER BY total_criticality DESC
LIMIT 10
```

#### Find Weak Dependencies (Sidecars)

```cypher
MATCH (a:Device)-[r:CONNECTS_TO]->(b:Device)
WHERE r.criticality < 0.5
RETURN a.name AS source, b.name AS target, r.criticality
ORDER BY r.criticality ASC
```

#### Filter by Criticality Threshold

```cypher
MATCH (a:Device)-[r:CONNECTS_TO]->(b:Device)
WHERE r.criticality >= 0.8
RETURN a.name, r.criticality, b.name
```

#### Calculate Risk Score

```cypher
MATCH (service:Device)-[r:CONNECTS_TO]->(dependency:Device)
WHERE service.type = 'Service'
RETURN service.name AS service,
       dependency.name AS dependency,
       r.criticality * dependency.failure_probability AS risk_score
ORDER BY risk_score DESC
```

### Best Practices

1. **Prefer Strong Dependencies**: When in doubt, assign a higher weight (0.9) rather than a lower one. It's better to over-prioritize than miss a critical dependency.

2. **Sidecar Detection**: Always check for sidecar patterns in node names (fluentd, istio-proxy, etc.) as they should have low criticality.

3. **Port Priority**: Port-based detection takes precedence over name-based detection for network relationships.

4. **Network Infrastructure**: Routers and switches should have medium criticality (0.7) - important but not as critical as databases.

5. **Monitor Weights**: Periodically review edge criticality values and adjust heuristic rules based on real-world incident patterns.

### Update Strategy

When updating edge weights:
- Use `ON CREATE SET` to only set weight on new relationships
- Use `SET` to update existing relationships if business logic changes
- Always include `last_seen` timestamp for TTL cleanup

Example Cypher:
```cypher
MERGE (a:Device {name: $source})-[r:CONNECTS_TO]->(b:Device {name: $target})
SET r.criticality = $calculated_weight,
    r.last_seen = datetime()
```

## Example Graph Structure

```
Kubernetes Namespace: production

┌─────────────────────────────────────────────────────────────┐
│                        Service: api-service                  │
│                  urn:aiops:k8s:service:production:api       │
└─────────────────────────────────────────────────────────────┘
                                │
                                │ EXPOSES (criticality: 1.0)
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                       Pod: api-server-7d8f9c2b4             │
│              urn:aiops:k8s:pod:production:api-server        │
└─────────────────────────────────────────────────────────────┘
                                │
                                │ RUNS_ON
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                       Node: k8s-node-01                      │
│               urn:aiops:k8s:node:production:k8s-node-01     │
└─────────────────────────────────────────────────────────────┘
                                │
                                │ CONNECTS_TO (criticality: 0.9)
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                     Device: core-switch-01                  │
│           urn:aiops:network:switch:dc1:core-switch-01       │
└─────────────────────────────────────────────────────────────┘
                                │
                                │ CONNECTS_TO (criticality: 0.8)
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                    Device: db-server-01                      │
│            urn:aiops:server:physical:dc1:db-server-01       │
└─────────────────────────────────────────────────────────────┘
```

## Query Patterns

### Find all downstream services for a node

```cypher
MATCH (start:Node {urn: $start_urn})
MATCH (start)<-[:RUNS_ON]-(pod:Pod)
MATCH (pod)<-[:EXPOSES]-(service:Service)
RETURN service.urn, service.name, service.namespace
```

### Find critical path with high criticality

```cypher
MATCH path = (start:Device {urn: $start_urn})-[:CONNECTS_TO*1..3]->(end:Device)
WHERE ALL(rel IN relationships(path) WHERE rel.criticality > 0.7)
RETURN path, reduce(weight = 0.0, rel IN relationships(path) | weight + rel.criticality) AS total_criticality
ORDER BY total_criticality DESC
LIMIT 10
```

### Time-travel query (historical topology)

```cypher
MATCH (n:Pod)
WHERE n.urn = $pod_urn
  AND n.valid_from <= $timestamp
  AND (n.valid_to IS NULL OR n.valid_to > $timestamp)
RETURN n
```

### Find dependencies with TTL expiration

```cypher
MATCH (n:Pod)
WHERE n.last_updated < datetime() - duration('PT24H')
RETURN n.urn, n.name, n.last_updated
```

## TTL (Time-To-Live) Policies

| Entity Type | TTL | Cleanup Strategy |
|-------------|-----|------------------|
| Pod | 24 hours after deletion | Mark as deleted, keep for 24h for audit |
| Service | 7 days after deletion | Mark as deleted, keep for 7d |
| Node | Never (unless decommissioned) | Keep until explicitly deleted |
| Network Device | Never | Keep unless decommissioned |
| Server | Never | Keep unless decommissioned |

### TTL Implementation

```cypher
// Mark entity as deleted (soft delete)
MATCH (n:Pod {urn: $urn})
SET n.valid_to = datetime(),
    n.status = 'Deleted',
    n.last_updated = datetime()

// Hard delete expired entities (cleanup job)
MATCH (n:Pod)
WHERE n.valid_to < datetime() - duration('PT24H')
DETACH DELETE n
```

## Indexes and Constraints

```cypher
// Unique constraints
CREATE CONSTRAINT IF NOT EXISTS FOR (n:Node) REQUIRE n.urn IS UNIQUE
CREATE CONSTRAINT IF NOT EXISTS FOR (p:Pod) REQUIRE p.urn IS UNIQUE
CREATE CONSTRAINT IF NOT EXISTS FOR (s:Service) REQUIRE s.urn IS UNIQUE
CREATE CONSTRAINT IF NOT EXISTS FOR (d:Device) REQUIRE d.urn IS UNIQUE
CREATE CONSTRAINT IF NOT EXISTS FOR (sv:Server) REQUIRE sv.urn IS UNIQUE

// Performance indexes
CREATE INDEX IF NOT EXISTS FOR (n:Node) ON (n.name, n.namespace)
CREATE INDEX IF NOT EXISTS FOR (p:Pod) ON (p.namespace, p.status)
CREATE INDEX IF NOT EXISTS FOR (d:Device) ON (d.ip)
CREATE INDEX IF NOT EXISTS FOR (d:Device) ON (d.type, d.site)
CREATE INDEX IF NOT EXISTS FOR (d:Device) ON (d.valid_from, d.valid_to)
```

## Best Practices

1. **Always use URNs** for entity identification instead of IP addresses or hostnames
2. **Implement soft deletes** using `valid_to` timestamp for audit trails
3. **Set criticality weights** on relationships to prioritize root cause analysis
4. **Batch updates** to reduce database load during topology changes
5. **Cache common queries** (e.g., device neighbors) in Redis
6. **Use time-travel queries** for troubleshooting historical issues
7. **Implement TTL cleanup jobs** to prevent graph explosion
8. **Monitor query performance** and add indexes as needed

## Migration Guide

### From IP-based to URN-based schema

```cypher
// Step 1: Add URN field
MATCH (d:Device)
WHERE d.urn IS NULL
SET d.urn = 'urn:aiops:network:switch:' + d.site + ':' + d.name

// Step 2: Create unique constraint (will fail if duplicates exist)
CREATE CONSTRAINT IF NOT EXISTS FOR (d:Device) REQUIRE d.urn IS UNIQUE

// Step 3: Add validity timestamps
MATCH (d:Device)
WHERE d.valid_from IS NULL
SET d.valid_from = datetime(),
    d.last_updated = datetime()

// Step 4: Add criticality to relationships
MATCH ()-[r:CONNECTS_TO]->()
WHERE r.criticality IS NULL
SET r.criticality = 0.5  // Default to medium criticality
```

## References

- Neo4j Cypher Manual: https://neo4j.com/docs/cypher-manual/
- Identity Mapper Implementation: `/opt/Monitoring-deployment-main/scripts/aiops/identity_mapper.py`
- Graph Builder Script: `/opt/Monitoring-deployment-main/scripts/aiops/graph_builder.py`