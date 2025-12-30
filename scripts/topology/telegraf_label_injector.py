#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegraf Processor - 拓扑标签注入
功能：读取拓扑标签映射，为 Telegraf metrics 添加拓扑标签
协议：Telegraf execd processor (InfluxDB Line Protocol)
"""

import sys
import json
import logging
import os
from datetime import datetime

# 配置日志（输出到 stderr，不影响 stdout 的 metrics）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

class TopologyLabelInjector:
    """拓扑标签注入器"""

    def __init__(self, label_file='/data/topology/telegraf-labels.json'):
        self.label_file = label_file
        self.label_map = {}
        self.last_load_time = 0
        self.reload_interval = 60  # 每 60 秒重新加载一次

    def load_labels(self):
        """加载标签映射"""
        try:
            if os.path.exists(self.label_file):
                with open(self.label_file, 'r') as f:
                    self.label_map = json.load(f)
                logger.info(f"加载标签映射: {len(self.label_map)} 个条目")
                self.last_load_time = datetime.now().timestamp()
                return True
            else:
                logger.warning(f"标签文件不存在: {self.label_file}")
                return False
        except Exception as e:
            logger.error(f"加载标签映射失败: {e}")
            return False

    def should_reload(self):
        """检查是否需要重新加载"""
        now = datetime.now().timestamp()
        return (now - self.last_load_time) > self.reload_interval

    def parse_line_protocol(self, line):
        """解析 InfluxDB Line Protocol"""
        # 格式：measurement,tag1=value1,tag2=value2 field1=value1,field2=value2 timestamp
        line = line.strip()
        if not line or line.startswith('#'):
            return None

        try:
            # 分割 measurement+tags 和 fields
            parts = line.split(' ', 2)
            if len(parts) < 2:
                return None

            measurement_tags = parts[0]
            fields = parts[1]
            timestamp = parts[2] if len(parts) == 3 else ''

            # 分割 measurement 和 tags
            measurement_parts = measurement_tags.split(',', 1)
            measurement = measurement_parts[0]
            tags_str = measurement_parts[1] if len(measurement_parts) > 1 else ''

            # 解析 tags
            tags = {}
            if tags_str:
                for tag in tags_str.split(','):
                    if '=' in tag:
                        k, v = tag.split('=', 1)
                        tags[k] = v

            return {
                'measurement': measurement,
                'tags': tags,
                'fields': fields,
                'timestamp': timestamp
            }
        except Exception as e:
            logger.error(f"解析 line protocol 失败: {line}, 错误: {e}")
            return None

    def find_labels(self, tags):
        """根据 tags 查找对应的拓扑标签"""
        # 尝试多种匹配方式
        match_keys = [
            tags.get('esxi_host'),           # VMware ESXi
            tags.get('host'),                # 通用 host
            tags.get('vcenter'),             # vCenter
            tags.get('source'),              # source
            tags.get('hostname'),            # hostname
            tags.get('instance'),            # instance
        ]

        # 尝试匹配
        for key in match_keys:
            if key and key in self.label_map:
                return self.label_map[key]

        return None

    def inject_labels(self, metric_data):
        """注入拓扑标签"""
        if not metric_data:
            return None

        # 查找标签
        topology_labels = self.find_labels(metric_data['tags'])
        if not topology_labels:
            return metric_data  # 没有找到标签，返回原始数据

        # 注入标签
        metric_data['tags'].update(topology_labels)
        return metric_data

    def build_line_protocol(self, metric_data):
        """重新构建 InfluxDB Line Protocol"""
        if not metric_data:
            return None

        # 构建 tags 字符串
        tags_str = ','.join([f"{k}={v}" for k, v in sorted(metric_data['tags'].items())])

        # 构建完整行
        line = f"{metric_data['measurement']},{tags_str} {metric_data['fields']}"
        if metric_data['timestamp']:
            line += f" {metric_data['timestamp']}"

        return line

    def process_line(self, line):
        """处理单行 metric"""
        # 解析
        metric_data = self.parse_line_protocol(line)
        if not metric_data:
            return line  # 解析失败，返回原始行

        # 注入标签
        metric_data = self.inject_labels(metric_data)

        # 重新构建
        new_line = self.build_line_protocol(metric_data)
        return new_line if new_line else line


def main():
    """主函数"""
    label_file = os.environ.get('TOPOLOGY_LABELS_FILE', '/data/topology/telegraf-labels.json')

    logger.info("=" * 60)
    logger.info("Telegraf Topology Label Injector 启动")
    logger.info(f"标签文件: {label_file}")
    logger.info("=" * 60)

    injector = TopologyLabelInjector(label_file)

    # 初始加载
    if not injector.load_labels():
        logger.warning("初始标签加载失败，将继续运行")

    # 从 stdin 读取 metrics，处理后输出到 stdout
    try:
        for line in sys.stdin:
            # 定期重新加载标签
            if injector.should_reload():
                injector.load_labels()

            # 处理并输出
            processed_line = injector.process_line(line)
            if processed_line:
                print(processed_line)
                sys.stdout.flush()  # 确保立即输出

    except KeyboardInterrupt:
        logger.info("收到停止信号，正在关闭...")
    except Exception as e:
        logger.error(f"处理过程中发生错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
