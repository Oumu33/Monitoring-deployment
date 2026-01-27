import os
import yaml
import json
from neo4j import GraphDatabase
import time
import logging

# --- Configuration ---
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password123")
DEVICES_FILE = "/etc/topology/devices.yml"
TOPOLOGY_FILE = "/data/topology/topology.json"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Edge Criticality Weights ---
# 定义不同关系的"致命程度" (0.0 - 1.0)
EDGE_WEIGHTS = {
    'PHYSICAL': 1.0,    # HOSTED_ON (Pod -> Node) - 物理依赖，生死与共
    'SYNC_CALL': 0.9,   # RPC/REST (Service -> Service) - 同步强依赖
    'CONFIG': 0.8,      # MOUNTS (Pod -> ConfigMap) - 配置依赖，启动必需
    'ASYNC_CALL': 0.5,  # MQ/PubSub (Service -> Kafka) - 异步弱依赖，可缓冲
    'SIDECAR': 0.2,     # Logging/Metrics (Service -> Fluentd) - 辅助功能
    'UNKNOWN': 0.5      # 默认兜底策略
}

# 关键端口特征库 (用于推断同步/异步)
PORT_SIGNATURES = {
    'SYNC': [80, 443, 8080, 8443, 3306, 5432, 6379, 27017, 9200],  # Web, MySQL, Redis, MongoDB, ES
    'ASYNC': [9092, 9093, 9094, 5672, 1883, 61616, 4222],           # Kafka, RabbitMQ, MQTT, Artemis
}

# 数据库/存储特征关键词
DATABASE_KEYWORDS = ['mysql', 'postgres', 'redis', 'mongodb', 'elasticsearch', 'cassandra', 'influxdb']

# 消息队列特征关键词
MQ_KEYWORDS = ['kafka', 'rabbitmq', 'activemq', 'pulsar', 'nats', 'mqtt', 'redis-stream']

class GraphBuilder:
    def __init__(self, uri, user, password):
        self._driver = None
        self.uri = uri
        self.user = user
        self.password = password
        self.connect()

    def connect(self):
        """Establishes connection to the Neo4j database."""
        for i in range(10): # Retry connection
            try:
                self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
                self._driver.verify_connectivity()
                logging.info("Successfully connected to Neo4j.")
                return
            except Exception as e:
                logging.warning(f"Connection to Neo4j failed: {e}. Retrying in 10 seconds... ({i+1}/10)")
                time.sleep(10)
        logging.error("Could not connect to Neo4j after multiple retries. Exiting.")
        exit(1)


    def close(self):
        """Closes the database connection."""
        if self._driver is not None:
            self._driver.close()
            logging.info("Neo4j connection closed.")

    def run_query(self, query, parameters=None):
        """Runs a Cypher query."""
        with self._driver.session() as session:
            result = session.run(query, parameters)
            return [record for record in result]

    def setup_constraints(self):
        """Sets up unique constraints on node properties."""
        logging.info("Setting up database constraints...")
        query = "CREATE CONSTRAINT IF NOT EXISTS FOR (d:Device) REQUIRE d.name IS UNIQUE"
        self.run_query(query)
        logging.info("Constraint 'Device.name' is unique' ensured.")

    def import_devices(self):
        """Imports devices from a YAML file into Neo4j."""
        logging.info(f"Importing devices from {DEVICES_FILE}...")
        try:
            with open(DEVICES_FILE, 'r') as f:
                devices = yaml.safe_load(f)
        except FileNotFoundError:
            logging.error(f"Device file not found at {DEVICES_FILE}. Skipping device import.")
            return

        for device_name, properties in devices.get('devices', {}).items():
            device_type = properties.get('type', 'Unknown')
            query = (
                "MERGE (d:Device {name: $name}) "
                "SET d.ip = $ip, "
                "    d.type = $type, "
                "    d.site = $site, "
                "    d.last_seen = datetime(), "
                "    d.valid_from = CASE WHEN d.valid_from IS NULL THEN datetime() ELSE d.valid_from END"
            )
            parameters = {
                'name': device_name,
                'ip': properties.get('ip'),
                'type': device_type,
                'site': properties.get('site')
            }
            self.run_query(query, parameters)
            logging.info(f"Merged device node: {device_name} (type: {device_type})")

    def _calculate_criticality(self, rel_type, source_props, target_props):
        """
        启发式计算边权重

        根据关系类型、端口、节点名称等多维度信息智能推断边的致命程度。

        Args:
            rel_type: 关系类型 (e.g., 'CONNECTS_TO', 'HOSTED_ON')
            source_props: 源节点属性
            target_props: 目标节点属性

        Returns:
            float (0.0 - 1.0) - 边的权重，越高表示依赖越强
        """
        # 1. 物理层依赖 (最高优先级)
        if rel_type == 'HOSTED_ON':
            return EDGE_WEIGHTS['PHYSICAL']

        # 2. 配置/存储挂载
        if rel_type == 'MOUNTS':
            return EDGE_WEIGHTS['CONFIG']

        # 3. 辅助 Sidecar (通过名称判断)
        # 如果目标是 fluentd, filebeat, promtail, istio-proxy 等
        target_name = target_props.get('name', '').lower()
        source_name = source_props.get('name', '').lower()

        if any(s in target_name for s in ['fluentd', 'filebeat', 'promtail', 'loki', 'otel-collector']):
            return EDGE_WEIGHTS['SIDECAR']

        # 检查源是否是 sidecar (istio-proxy, envoy)
        if any(s in source_name for s in ['istio-proxy', 'envoy', 'sidecar']):
            return EDGE_WEIGHTS['SIDECAR']

        # 4. 网络调用 (CONNECTS_TO) - 核心逻辑
        if rel_type == 'CONNECTS_TO':
            # 获取端口信息
            source_port = int(source_props.get('port', source_props.get('source_port', 0)))
            target_port = int(target_props.get('port', target_props.get('target_port', 0)))

            # 规则 A: 基于端口判断
            # 优先使用目标端口
            port_to_check = target_port if target_port > 0 else source_port

            if port_to_check > 0:
                # 检查是否是数据库/存储端口 (同步强依赖)
                if port_to_check in PORT_SIGNATURES['SYNC']:
                    return EDGE_WEIGHTS['SYNC_CALL']

                # 检查是否是消息队列端口 (异步弱依赖)
                if port_to_check in PORT_SIGNATURES['ASYNC']:
                    return EDGE_WEIGHTS['ASYNC_CALL']

            # 规则 B: 基于节点名称/类型判断
            target_type = target_props.get('type', '').lower()

            # 数据库/存储 -> 同步强依赖
            if any(db in target_name or db in target_type for db in DATABASE_KEYWORDS):
                return EDGE_WEIGHTS['SYNC_CALL']

            # 消息队列 -> 异步弱依赖
            if any(mq in target_name or mq in target_type for mq in MQ_KEYWORDS):
                return EDGE_WEIGHTS['ASYNC_CALL']

            # 规则 C: 默认策略
            # 如果目标设备类型是 'router' 或 'switch' (网络设备)，视为中等依赖
            if target_type in ['router', 'switch', 'firewall']:
                return 0.7

            # 默认视为同步调用 (宁可误判为强依赖，不可漏判)
            return EDGE_WEIGHTS['SYNC_CALL']

        # 5. 未知关系类型
        return EDGE_WEIGHTS['UNKNOWN']

    def import_topology(self):
        """Imports topology relationships from a JSON file with intelligent criticality calculation."""
        logging.info(f"Importing topology from {TOPOLOGY_FILE}...")
        try:
            with open(TOPOLOGY_FILE, 'r') as f:
                topology_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            logging.warning(f"Topology file not found or invalid at {TOPOLOGY_FILE}. Skipping topology import.")
            return

        for edge in topology_data.get('edges', []):
            source_device = edge.get('source')
            target_device = edge.get('target')
            source_port = edge.get('source_port')
            target_port = edge.get('target_port')

            if not all([source_device, target_device, source_port, target_port]):
                logging.warning(f"Skipping incomplete edge data: {edge}")
                continue

            # 🔥 智能计算边权重
            # 获取源和目标设备的属性用于推断
            source_props = {'name': source_device, 'port': source_port}
            target_props = {'name': target_device, 'port': target_port}

            # 尝试从 devices.yml 获取更多属性
            try:
                with open(DEVICES_FILE, 'r') as f:
                    devices = yaml.safe_load(f)
                    if source_device in devices.get('devices', {}):
                        source_props.update(devices['devices'][source_device])
                    if target_device in devices.get('devices', {}):
                        target_props.update(devices['devices'][target_device])
            except Exception as e:
                logging.debug(f"Could not load device properties for criticality calculation: {e}")

            # 计算权重
            criticality = self._calculate_criticality('CONNECTS_TO', source_props, target_props)

            # 构建查询并注入权重
            query = (
                "MATCH (a:Device {name: $source_device}) "
                "MATCH (b:Device {name: $target_device}) "
                "MERGE (a)-[r:CONNECTS_TO]->(b) "
                "SET r.source_port = $source_port, "
                "    r.target_port = $target_port, "
                "    r.criticality = $criticality, "
                "    r.last_seen = datetime()"
            )
            parameters = {
                'source_device': source_device,
                'target_device': target_device,
                'source_port': source_port,
                'target_port': target_port,
                'criticality': criticality
            }

            self.run_query(query, parameters)

            # 根据权重记录不同的日志级别
            if criticality >= 0.9:
                logging.info(f"Merged CRITICAL relationship: {source_device}({source_port}) -> {target_device}({target_port}) [criticality: {criticality}]")
            elif criticality >= 0.7:
                logging.info(f"Merged HIGH relationship: {source_device}({source_port}) -> {target_device}({target_port}) [criticality: {criticality}]")
            else:
                logging.debug(f"Merged relationship: {source_device}({source_port}) -> {target_device}({target_port}) [criticality: {criticality}]")

if __name__ == "__main__":
    logging.info("Starting AIOps Graph Builder...")
    builder = GraphBuilder(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    builder.setup_constraints()
    builder.import_devices()
    builder.import_topology()
    builder.close()
    logging.info("Graph building process finished.")
