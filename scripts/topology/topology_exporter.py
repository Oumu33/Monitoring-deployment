#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Topology Exporter - 将拓扑数据暴露为 Prometheus 指标
功能：读取 topology.json 和 metrics.json，生成拓扑和自身指标
"""

import json
import time
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
import os

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TopologyExporter:
    """拓扑指标导出器"""

    def __init__(self, topology_file='/data/topology/topology.json', metrics_file='/data/topology/metrics.json'):
        self.topology_file = topology_file
        self.metrics_file = metrics_file
        self.topology = {'nodes': {}, 'edges': [], 'updated': None}
        self.discovery_metrics = {}
        self.metrics = ""
        self.last_load_time = 0
        self.reload_interval = 60  # 每 60 秒重新加载一次

    def load_topology(self):
        """加载拓扑数据"""
        try:
            if os.path.exists(self.topology_file):
                with open(self.topology_file, 'r') as f:
                    self.topology = json.load(f)
                logger.info(f"加载拓扑数据: {len(self.topology.get('nodes', {}))} 个节点, "
                           f"{len(self.topology.get('edges', []))} 条连接")
                self.last_load_time = time.time()
                return True
            else:
                logger.warning(f"拓扑文件不存在: {self.topology_file}")
                return False
        except Exception as e:
            logger.error(f"加载拓扑数据失败: {e}")
            return False

    def load_metrics(self):
        """加载自身指标"""
        try:
            if os.path.exists(self.metrics_file):
                with open(self.metrics_file, 'r') as f:
                    self.discovery_metrics = json.load(f)
                logger.debug(f"加载自身指标: {self.discovery_metrics}")
                return True
            else:
                logger.warning(f"自身指标文件不存在: {self.metrics_file}")
                return False
        except Exception as e:
            logger.error(f"加载自身指标失败: {e}")
            return False

    def generate_metrics(self):
        """生成 Prometheus 格式的指标"""
        # 检查是否需要重新加载
        if time.time() - self.last_load_time > self.reload_interval:
            self.load_topology()
            self.load_metrics()

        metrics = []

        # ========== 拓扑指标 ==========
        # HELP 和 TYPE 声明
        metrics.append("# HELP topology_device_info Network device topology information")
        metrics.append("# TYPE topology_device_info gauge")

        # 设备节点指标
        for device_name, node in self.topology.get('nodes', {}).items():
            labels = {
                'device_name': device_name,
                'device_type': node.get('type', 'unknown'),
                'device_tier': node.get('tier', 'unknown'),
                'device_location': node.get('location', 'unknown'),
                'device_vendor': node.get('vendor', 'unknown'),
                'device_host': node.get('host', 'unknown')
            }

            # 生成标签字符串
            label_str = ','.join([f'{k}="{v}"' for k, v in labels.items()])
            metrics.append(f"topology_device_info{{{label_str}}} 1")

        # 连接关系指标
        metrics.append("")
        metrics.append("# HELP topology_connection Network device connections")
        metrics.append("# TYPE topology_connection gauge")

        for edge in self.topology.get('edges', []):
            labels = {
                'source_device': edge.get('source', 'unknown'),
                'target_device': edge.get('target', 'unknown'),
                'source_port': edge.get('source_port', 'unknown'),
                'target_port': edge.get('target_port', 'unknown'),
                'protocol': edge.get('protocol', 'unknown')
            }

            label_str = ','.join([f'{k}="{v}"' for k, v in labels.items()])
            metrics.append(f"topology_connection{{{label_str}}} 1")

        # 拓扑统计指标
        metrics.append("")
        metrics.append("# HELP topology_devices_total Total number of devices")
        metrics.append("# TYPE topology_devices_total gauge")
        metrics.append(f"topology_devices_total {len(self.topology.get('nodes', {}))}")

        metrics.append("")
        metrics.append("# HELP topology_connections_total Total number of connections")
        metrics.append("# TYPE topology_connections_total gauge")
        metrics.append(f"topology_connections_total {len(self.topology.get('edges', []))}")

        # ========== 自身指标 ==========
        metrics.append("")
        metrics.append("# HELP topology_discovery_duration_seconds Discovery duration in seconds")
        metrics.append("# TYPE topology_discovery_duration_seconds gauge")
        metrics.append(f"topology_discovery_duration_seconds {self.discovery_metrics.get('discovery_duration_seconds', 0)}")

        metrics.append("")
        metrics.append("# HELP topology_devices_discovered Total devices discovered")
        metrics.append("# TYPE topology_devices_discovered gauge")
        metrics.append(f"topology_devices_discovered {self.discovery_metrics.get('devices_discovered', 0)}")

        metrics.append("")
        metrics.append("# HELP topology_devices_failed Total devices failed")
        metrics.append("# TYPE topology_devices_failed gauge")
        metrics.append(f"topology_devices_failed {self.discovery_metrics.get('devices_failed', 0)}")

        metrics.append("")
        metrics.append("# HELP topology_lldp_neighbors Total LLDP neighbors")
        metrics.append("# TYPE topology_lldp_neighbors gauge")
        metrics.append(f"topology_lldp_neighbors {self.discovery_metrics.get('lldp_neighbors', 0)}")

        metrics.append("")
        metrics.append("# HELP topology_cdp_neighbors Total CDP neighbors")
        metrics.append("# TYPE topology_cdp_neighbors gauge")
        metrics.append(f"topology_cdp_neighbors {self.discovery_metrics.get('cdp_neighbors', 0)}")

        metrics.append("")
        metrics.append("# HELP topology_ndp_neighbors Total NDP neighbors")
        metrics.append("# TYPE topology_ndp_neighbors gauge")
        metrics.append(f"topology_ndp_neighbors {self.discovery_metrics.get('ndp_neighbors', 0)}")

        metrics.append("")
        metrics.append("# HELP topology_lnp_neighbors Total LNP neighbors")
        metrics.append("# TYPE topology_lnp_neighbors gauge")
        metrics.append(f"topology_lnp_neighbors {self.discovery_metrics.get('lnp_neighbors', 0)}")

        metrics.append("")
        metrics.append("# HELP topology_snmp_errors Total SNMP errors")
        metrics.append("# TYPE topology_snmp_errors counter")
        metrics.append(f"topology_snmp_errors {self.discovery_metrics.get('snmp_errors', 0)}")

        metrics.append("")
        metrics.append("# HELP topology_lacp_links Total LACP aggregation links")
        metrics.append("# TYPE topology_lacp_links gauge")
        metrics.append(f"topology_lacp_links {self.discovery_metrics.get('lacp_links', 0)}")

        metrics.append("")
        metrics.append("# HELP topology_loops_detected Total network loops detected")
        metrics.append("# TYPE topology_loops_detected gauge")
        metrics.append(f"topology_loops_detected {self.discovery_metrics.get('loops_detected', 0)}")

        metrics.append("")
        metrics.append("# HELP topology_topology_changes Total topology changes detected")
        metrics.append("# TYPE topology_topology_changes gauge")
        metrics.append(f"topology_topology_changes {self.discovery_metrics.get('topology_changes', 0)}")

        # 计算成功率
        total = self.discovery_metrics.get('devices_discovered', 0) + self.discovery_metrics.get('devices_failed', 0)
        success_rate = (self.discovery_metrics.get('devices_discovered', 0) / total * 100) if total > 0 else 0
        
        metrics.append("")
        metrics.append("# HELP topology_discovery_success_rate Discovery success rate percentage")
        metrics.append("# TYPE topology_discovery_success_rate gauge")
        metrics.append(f"topology_discovery_success_rate {success_rate:.2f}")

        self.metrics = '\n'.join(metrics)
        return self.metrics

    def health_check(self):
        """健康检查"""
        return {
            'status': 'healthy',
            'topology_updated': self.topology.get('updated'),
            'nodes': len(self.topology.get('nodes', {})),
            'edges': len(self.topology.get('edges', {}))
        }

class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理器"""

    def __init__(self, exporter, *args, **kwargs):
        self.exporter = exporter
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """处理 GET 请求"""
        if self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            metrics = self.exporter.generate_metrics()
            self.wfile.write(metrics.encode('utf-8'))
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            health = self.exporter.health_check()
            self.wfile.write(json.dumps(health).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """禁用默认日志"""
        pass

def start_exporter(exporter, port=9700):
    """启动 HTTP 服务器"""
    server_address = ('', port)
    
    def handler(*args, **kwargs):
        MetricsHandler(exporter, *args, **kwargs)
    
    httpd = HTTPServer(server_address, handler)
    logger.info(f"Topology Exporter 启动在端口 {port}")
    logger.info(f"  指标端点: http://localhost:{port}/metrics")
    logger.info(f"  健康检查: http://localhost:{port}/health")
    httpd.serve_forever()

def main():
    """主函数"""
    exporter = TopologyExporter(
        topology_file='/data/topology/topology.json',
        metrics_file='/data/topology/metrics.json'
    )
    
    # 启动 HTTP 服务器
    server_thread = Thread(target=start_exporter, args=(exporter, 9700), daemon=True)
    server_thread.start()
    
    # 保持运行
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Topology Exporter 停止")

if __name__ == '__main__':
    main()
