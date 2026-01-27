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
            query = (
                "MERGE (d:Device {name: $name}) "
                "SET d.ip = $ip, d.type = $type, d.site = $site"
            )
            parameters = {
                'name': device_name,
                'ip': properties.get('ip'),
                'type': properties.get('type'),
                'site': properties.get('site')
            }
            self.run_query(query, parameters)
            logging.info(f"Merged device node: {device_name}")

    def import_topology(self):
        """Imports topology relationships from a JSON file."""
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

            query = (
                "MATCH (a:Device {name: $source_device}) "
                "MATCH (b:Device {name: $target_device}) "
                "MERGE (a)-[r:CONNECTS_TO]->(b) "
                "SET r.source_port = $source_port, r.target_port = $target_port"
            )
            parameters = {
                'source_device': source_device,
                'target_device': target_device,
                'source_port': source_port,
                'target_port': target_port,
            }
            self.run_query(query, parameters)
            logging.info(f"Merged relationship: {source_device}({source_port}) -> {target_device}({target_port})")

if __name__ == "__main__":
    logging.info("Starting AIOps Graph Builder...")
    builder = GraphBuilder(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    builder.setup_constraints()
    builder.import_devices()
    builder.import_topology()
    builder.close()
    logging.info("Graph building process finished.")
