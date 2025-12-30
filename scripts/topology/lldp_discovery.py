#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLDP 拓扑自动发现脚本
功能：
1. 通过 SNMP 采集所有网络设备的 LLDP 邻居信息
2. 生成设备连接关系图
3. 自动更新 Prometheus 标签（拓扑关系）
4. 生成拓扑可视化数据
"""

import json
import yaml
import time
import logging
from datetime import datetime
from collections import defaultdict
from pysnmp.hlapi import *

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LLDPDiscovery:
    """LLDP 拓扑发现类"""

    def __init__(self, config_file='/etc/topology/devices.yml'):
        """初始化"""
        self.config_file = config_file
        self.devices = []
        self.topology = {
            'nodes': {},      # 设备节点
            'edges': [],      # 连接关系
            'updated': None   # 更新时间
        }
        self.load_config()

    def load_config(self):
        """加载设备配置"""
        try:
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f)
                self.devices = config.get('devices', [])
            logger.info(f"加载了 {len(self.devices)} 个设备配置")
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            self.devices = []

    def snmp_walk(self, device, oid):
        """SNMP Walk 查询"""
        results = []

        try:
            iterator = nextCmd(
                SnmpEngine(),
                CommunityData(device.get('snmp_community', 'public')),
                UdpTransportTarget((device['host'], device.get('snmp_port', 161)), timeout=5, retries=1),
                ContextData(),
                ObjectType(ObjectIdentity(oid)),
                lexicographicMode=False
            )

            for errorIndication, errorStatus, errorIndex, varBinds in iterator:
                if errorIndication:
                    logger.error(f"{device['name']} SNMP 错误: {errorIndication}")
                    break
                elif errorStatus:
                    logger.error(f"{device['name']} SNMP 错误: {errorStatus}")
                    break
                else:
                    for varBind in varBinds:
                        results.append(varBind)
        except Exception as e:
            logger.error(f"{device['name']} SNMP 查询失败: {e}")

        return results

    def get_lldp_neighbors(self, device):
        """获取设备的 LLDP 邻居信息"""
        # LLDP MIB OIDs
        LLDP_REM_CHASSIS_ID = '1.0.8802.1.1.2.1.4.1.1.5'      # 远端设备 Chassis ID
        LLDP_REM_PORT_ID = '1.0.8802.1.1.2.1.4.1.1.7'         # 远端端口 ID
        LLDP_REM_SYS_NAME = '1.0.8802.1.1.2.1.4.1.1.9'        # 远端系统名称
        LLDP_REM_PORT_DESC = '1.0.8802.1.1.2.1.4.1.1.8'       # 远端端口描述
        LLDP_LOC_PORT_DESC = '1.0.8802.1.1.2.1.3.7.1.4'       # 本地端口描述

        neighbors = []

        # 获取远端系统名称
        logger.info(f"正在采集 {device['name']} 的 LLDP 邻居...")
        rem_sys_names = self.snmp_walk(device, LLDP_REM_SYS_NAME)

        for varBind in rem_sys_names:
            oid_str = str(varBind[0])
            remote_name = str(varBind[1])

            # 从 OID 中提取索引（时间戳.本地端口.远端索引）
            # 例如: 1.0.8802.1.1.2.1.4.1.1.9.0.12.456 -> 0.12.456
            parts = oid_str.split('.')
            if len(parts) >= 15:
                time_mark = parts[-3]
                local_port_num = parts[-2]
                remote_index = parts[-1]

                # 构造其他 OID 来获取详细信息
                index_suffix = f"{time_mark}.{local_port_num}.{remote_index}"

                # 获取本地端口描述
                local_port_oid = f"{LLDP_LOC_PORT_DESC}.{local_port_num}"
                local_port_desc = self.snmp_get(device, local_port_oid)

                # 获取远端端口 ID
                remote_port_oid = f"{LLDP_REM_PORT_ID}.{index_suffix}"
                remote_port = self.snmp_get(device, remote_port_oid)

                neighbor = {
                    'local_device': device['name'],
                    'local_port': local_port_desc or f"Port-{local_port_num}",
                    'remote_device': remote_name,
                    'remote_port': remote_port or 'Unknown',
                    'timestamp': datetime.now().isoformat()
                }

                neighbors.append(neighbor)
                logger.debug(f"  发现邻居: {neighbor}")

        logger.info(f"{device['name']} 发现 {len(neighbors)} 个 LLDP 邻居")
        return neighbors

    def snmp_get(self, device, oid):
        """SNMP Get 查询"""
        try:
            iterator = getCmd(
                SnmpEngine(),
                CommunityData(device.get('snmp_community', 'public')),
                UdpTransportTarget((device['host'], device.get('snmp_port', 161)), timeout=3, retries=1),
                ContextData(),
                ObjectType(ObjectIdentity(oid))
            )

            errorIndication, errorStatus, errorIndex, varBinds = next(iterator)

            if errorIndication or errorStatus:
                return None
            else:
                return str(varBinds[0][1]) if varBinds else None
        except:
            return None

    def discover_topology(self):
        """发现整体拓扑"""
        logger.info("=" * 60)
        logger.info("开始 LLDP 拓扑发现...")
        logger.info("=" * 60)

        all_neighbors = []

        # 遍历所有设备采集 LLDP 信息
        for device in self.devices:
            neighbors = self.get_lldp_neighbors(device)
            all_neighbors.extend(neighbors)

            # 添加设备节点
            if device['name'] not in self.topology['nodes']:
                self.topology['nodes'][device['name']] = {
                    'name': device['name'],
                    'host': device['host'],
                    'type': device.get('type', 'switch'),
                    'tier': device.get('tier', 'unknown'),
                    'location': device.get('location', 'unknown'),
                    'vendor': device.get('vendor', 'unknown')
                }

        # 去重和标准化连接关系
        seen_edges = set()
        for neighbor in all_neighbors:
            # 创建边（无向图，确保不重复）
            edge_key = tuple(sorted([neighbor['local_device'], neighbor['remote_device']]))

            if edge_key not in seen_edges:
                seen_edges.add(edge_key)

                self.topology['edges'].append({
                    'source': neighbor['local_device'],
                    'target': neighbor['remote_device'],
                    'source_port': neighbor['local_port'],
                    'target_port': neighbor['remote_port']
                })

                # 添加远端设备节点（如果不存在）
                if neighbor['remote_device'] not in self.topology['nodes']:
                    self.topology['nodes'][neighbor['remote_device']] = {
                        'name': neighbor['remote_device'],
                        'type': 'unknown',
                        'tier': 'unknown'
                    }

        self.topology['updated'] = datetime.now().isoformat()

        logger.info("=" * 60)
        logger.info(f"拓扑发现完成！")
        logger.info(f"  设备数量: {len(self.topology['nodes'])}")
        logger.info(f"  连接数量: {len(self.topology['edges'])}")
        logger.info("=" * 60)

        return self.topology

    def calculate_tiers(self):
        """计算网络层级（核心、汇聚、接入）"""
        # 基于连接数量推断层级
        connections = defaultdict(int)

        for edge in self.topology['edges']:
            connections[edge['source']] += 1
            connections[edge['target']] += 1

        # 简单的层级推断逻辑
        for device_name, node in self.topology['nodes'].items():
            if node.get('tier') == 'unknown':
                conn_count = connections[device_name]

                if conn_count >= 10:
                    node['tier'] = 'core'
                elif conn_count >= 3:
                    node['tier'] = 'aggregation'
                else:
                    node['tier'] = 'access'

        logger.info("层级计算完成")

    def save_topology(self, output_file='/data/topology/topology.json'):
        """保存拓扑数据"""
        try:
            with open(output_file, 'w') as f:
                json.dump(self.topology, f, indent=2, ensure_ascii=False)
            logger.info(f"拓扑数据已保存到: {output_file}")
        except Exception as e:
            logger.error(f"保存拓扑数据失败: {e}")

    def generate_prometheus_labels(self, output_dir='/etc/prometheus/targets'):
        """生成 Prometheus 标签文件（按设备类型分类的文件服务发现格式）"""
        # 按设备类型分类
        switches = []   # 交换机/路由器 → SNMP
        servers = []    # 服务器 → node_exporter

        for device_name, node in self.topology['nodes'].items():
            # 找到该设备连接的交换机
            connected_switches = []
            connected_ports = []

            for edge in self.topology['edges']:
                if edge['source'] == device_name:
                    connected_switches.append(edge['target'])
                    connected_ports.append(edge['source_port'])
                elif edge['target'] == device_name:
                    connected_switches.append(edge['source'])
                    connected_ports.append(edge['target_port'])

            # 生成标签（统一的标签集）
            labels = {
                'device_name': device_name,
                'device_type': node.get('type', 'unknown'),
                'device_tier': node.get('tier', 'unknown'),
                'device_location': node.get('location', 'unknown'),
                'device_vendor': node.get('vendor', 'unknown'),
                'topology_discovered': 'true'
            }

            # 添加连接信息（统一命名）
            if connected_switches:
                labels['connected_switch'] = connected_switches[0]
                labels['connected_switches'] = ','.join(connected_switches)

            if connected_ports:
                labels['connected_switch_port'] = connected_ports[0]

            # 根据设备类型生成不同格式的 targets
            if 'host' not in node:
                continue

            device_type = node.get('type', 'unknown')

            # 交换机/路由器 → SNMP Exporter（裸 IP）
            if device_type in ['switch', 'router', 'firewall']:
                target_entry = {
                    'targets': [node['host']],  # SNMP 用裸 IP
                    'labels': labels
                }
                switches.append(target_entry)

            # 服务器 → Node Exporter（IP:端口）
            elif device_type in ['server', 'host', 'vm']:
                target_entry = {
                    'targets': [f"{node['host']}:9100"],
                    'labels': labels
                }
                servers.append(target_entry)

        # 保存交换机配置（用于 SNMP）
        switches_file = f"{output_dir}/topology-switches.json"
        try:
            with open(switches_file, 'w') as f:
                json.dump(switches, f, indent=2, ensure_ascii=False)
            logger.info(f"交换机拓扑标签已生成: {switches_file}")
            logger.info(f"  包含 {len(switches)} 个交换机")
        except Exception as e:
            logger.error(f"生成交换机标签文件失败: {e}")

        # 保存服务器配置（用于 Node Exporter）
        servers_file = f"{output_dir}/topology-servers.json"
        try:
            with open(servers_file, 'w') as f:
                json.dump(servers, f, indent=2, ensure_ascii=False)
            logger.info(f"服务器拓扑标签已生成: {servers_file}")
            logger.info(f"  包含 {len(servers)} 个服务器")
        except Exception as e:
            logger.error(f"生成服务器标签文件失败: {e}")

    def generate_telegraf_labels(self, output_file='/data/topology/telegraf-labels.json'):
        """生成 Telegraf 标签映射文件（hostname → labels）"""
        # Telegraf 使用主机名作为 key
        label_map = {}

        for device_name, node in self.topology['nodes'].items():
            # 找到该设备连接的交换机
            connected_switches = []
            connected_ports = []

            for edge in self.topology['edges']:
                if edge['source'] == device_name:
                    connected_switches.append(edge['target'])
                    connected_ports.append(edge['source_port'])
                elif edge['target'] == device_name:
                    connected_switches.append(edge['source'])
                    connected_ports.append(edge['target_port'])

            # 生成标签（与其他方式一致）
            labels = {
                'device_name': device_name,
                'device_type': node.get('type', 'unknown'),
                'device_tier': node.get('tier', 'unknown'),
                'device_location': node.get('location', 'unknown'),
                'device_vendor': node.get('vendor', 'unknown'),
                'topology_discovered': 'true'
            }

            if connected_switches:
                labels['connected_switch'] = connected_switches[0]
                labels['connected_switches'] = ','.join(connected_switches)

            if connected_ports:
                labels['connected_switch_port'] = connected_ports[0]

            # 使用设备名和 host 作为 key（支持多种匹配）
            if 'host' in node:
                # 使用 IP 地址作为 key
                label_map[node['host']] = labels
                # 也使用设备名作为 key（支持 hostname 匹配）
                label_map[device_name] = labels
                # 支持 FQDN（如果有）
                label_map[f"{device_name}.local"] = labels

        # 保存标签映射
        try:
            with open(output_file, 'w') as f:
                json.dump(label_map, f, indent=2, ensure_ascii=False)
            logger.info(f"Telegraf 标签映射已生成: {output_file}")
            logger.info(f"  包含 {len(label_map)} 个映射条目")
        except Exception as e:
            logger.error(f"生成 Telegraf 标签映射失败: {e}")

    def generate_grafana_graph(self, output_file='/data/topology/graph.json'):
        """生成 Grafana Node Graph 数据"""
        # Grafana Node Graph 需要的数据格式
        graph_data = {
            'nodes': [],
            'edges': []
        }

        # 节点数据
        for device_name, node in self.topology['nodes'].items():
            graph_node = {
                'id': device_name,
                'title': device_name,
                'mainStat': node.get('tier', 'unknown'),
                'secondaryStat': node.get('type', 'unknown'),
                'arc__success': 0.8,  # 成功率（可以从实际指标获取）
                'detail__role': node.get('tier', 'unknown')
            }
            graph_data['nodes'].append(graph_node)

        # 边数据
        for edge in self.topology['edges']:
            graph_edge = {
                'id': f"{edge['source']}-{edge['target']}",
                'source': edge['source'],
                'target': edge['target'],
                'mainStat': f"{edge['source_port']} <-> {edge['target_port']}"
            }
            graph_data['edges'].append(graph_edge)

        try:
            with open(output_file, 'w') as f:
                json.dump(graph_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Grafana 图数据已生成: {output_file}")
        except Exception as e:
            logger.error(f"生成 Grafana 图数据失败: {e}")

def main():
    """主函数"""
    discovery = LLDPDiscovery('/etc/topology/devices.yml')

    # 发现拓扑
    discovery.discover_topology()

    # 计算层级
    discovery.calculate_tiers()

    # 保存拓扑数据
    discovery.save_topology('/data/topology/topology.json')

    # 生成 Prometheus 标签（按设备类型分类）
    discovery.generate_prometheus_labels('/etc/prometheus/targets')

    # 生成 Telegraf 标签映射
    discovery.generate_telegraf_labels('/data/topology/telegraf-labels.json')

    # 生成 Grafana 图数据
    discovery.generate_grafana_graph('/data/topology/graph.json')

    logger.info("所有任务完成！")

if __name__ == '__main__':
    main()
