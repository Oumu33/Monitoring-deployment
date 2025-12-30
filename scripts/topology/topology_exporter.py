#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Topology Exporter - 将拓扑数据暴露为 Prometheus 指标
功能：读取 topology.json，生成 topology_device_info 和 topology_connection 指标
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

    def __init__(self, topology_file='/data/topology/topology.json'):
        self.topology_file = topology_file
        self.topology = {'nodes': {}, 'edges': [], 'updated': None}
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

    def generate_metrics(self):
        """生成 Prometheus 格式的指标"""
        # 检查是否需要重新加载
        if time.time() - self.last_load_time > self.reload_interval:
            self.load_topology()

        metrics = []

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
                'target_port': edge.get('target_port', 'unknown')
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

        # 按层级统计
        tier_counts = {}
        for node in self.topology.get('nodes', {}).values():
            tier = node.get('tier', 'unknown')
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        metrics.append("")
        metrics.append("# HELP topology_devices_by_tier Devices grouped by network tier")
        metrics.append("# TYPE topology_devices_by_tier gauge")
        for tier, count in tier_counts.items():
            metrics.append(f'topology_devices_by_tier{{tier="{tier}"}} {count}')

        # 最后更新时间
        if self.topology.get('updated'):
            metrics.append("")
            metrics.append("# HELP topology_last_update_timestamp Last topology update timestamp")
            metrics.append("# TYPE topology_last_update_timestamp gauge")
            metrics.append(f"topology_last_update_timestamp {int(self.last_load_time)}")

        self.metrics = '\n'.join(metrics) + '\n'
        return self.metrics


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理器"""

    exporter = None  # 将由外部设置

    def do_GET(self):
        """处理 GET 请求"""
        if self.path == '/metrics':
            metrics = self.exporter.generate_metrics()
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(metrics.encode('utf-8'))
        elif self.path == '/health' or self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK\n')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """禁用默认日志"""
        pass


def main():
    """主函数"""
    port = int(os.environ.get('EXPORTER_PORT', 9700))
    topology_file = os.environ.get('TOPOLOGY_FILE', '/data/topology/topology.json')

    logger.info("=" * 60)
    logger.info("Topology Exporter 启动")
    logger.info(f"监听端口: {port}")
    logger.info(f"拓扑文件: {topology_file}")
    logger.info("=" * 60)

    # 创建 exporter
    exporter = TopologyExporter(topology_file)

    # 初始加载
    if not exporter.load_topology():
        logger.warning("初始拓扑加载失败，将使用空拓扑")

    # 设置全局 exporter
    MetricsHandler.exporter = exporter

    # 启动 HTTP 服务器
    server = HTTPServer(('0.0.0.0', port), MetricsHandler)
    logger.info(f"✓ Topology Exporter 就绪，访问 http://localhost:{port}/metrics")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("收到停止信号，正在关闭...")
        server.shutdown()


if __name__ == '__main__':
    main()
