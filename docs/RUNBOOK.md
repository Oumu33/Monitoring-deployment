# 监控告警处理手册（Runbook）

## 📖 文档说明

本文档提供所有监控告警的标准化处理流程。每个告警都包含：
- 告警说明
- 影响范围
- 可能原因
- 排查步骤
- 解决方案
- 预防措施

**更新日期**: 2025-12-27

---

## 目录

### 主机监控告警
- [主机宕机 (HostDown)](#主机宕机-hostdown)
- [CPU 使用率过高 (HighCPU)](#cpu-使用率过高-highcpu)
- [内存使用率过高 (HighMemory)](#内存使用率过高-highmemory)
- [磁盘空间不足 (DiskSpaceLow)](#磁盘空间不足-diskspacelow)
- [磁盘 I/O 等待过高 (HighDiskIOWait)](#磁盘-io-等待过高-highdiskiowait)
- [系统负载过高 (HighSystemLoad)](#系统负载过高-highsystemload)
- [网络接口下线 (NetworkInterfaceDown)](#网络接口下线-networkinterfacedown)

### VMware 虚拟化告警
- [虚拟机宕机 (VMDown)](#虚拟机宕机-vmdown)
- [虚拟机 CPU/内存过高 (VMHighCPU/VMHighMemory)](#虚拟机-cpu内存过高)
- [ESXi 主机资源过高 (ESXiHighCPU/ESXiHighMemory)](#esxi-主机资源过高)
- [数据存储空间不足 (DatastoreLowSpace)](#数据存储空间不足-datastorelowspace)

### 网络设备告警
- [SNMP 设备不可达 (SNMPDeviceDown)](#snmp-设备不可达-snmpdevicedown)
- [网络接口下线 (InterfaceDown)](#网络接口下线-interfacedown)
- [接口错误率过高 (HighInterfaceErrors)](#接口错误率过高-highinterfaceerrors)
- [接口流量过高 (HighInterfaceTraffic)](#接口流量过高-highinterfacetraffic)

### 服务可用性告警
- [网站宕机 (WebsiteDown)](#网站宕机-websitedown)
- [网站响应缓慢 (WebsiteSlow)](#网站响应缓慢-websiteslow)
- [SSL 证书过期 (SSLCertificateExpiring)](#ssl-证书过期-sslcertificateexpiring)
- [TCP 端口不可用 (TCPPortDown)](#tcp-端口不可用-tcpportdown)

### 监控系统告警
- [VictoriaMetrics 宕机 (VictoriaMetricsDown)](#victoriametrics-宕机)
- [vmagent 宕机 (VMAgentDown)](#vmagent-宕机)
- [vmalert 宕机 (VMAlertDown)](#vmalert-宕机)

---

## 主机监控告警

### 主机宕机 (HostDown)

#### 告警说明
主机无法通过 Node Exporter 采集到监控数据，可能已宕机。

#### 影响范围
- **严重程度**: 🔴 Critical (P0)
- **影响**: 该主机上所有服务不可用
- **SLA影响**: 高

#### 可能原因
1. 主机关机或重启
2. 网络不可达
3. Node Exporter 进程崩溃
4. 防火墙阻止

#### 排查步骤

**第 1 步：检查网络连通性**
```bash
# Ping 测试
ping -c 4 <host_ip>

# 如果 Ping 不通，检查路由
traceroute <host_ip>

# 检查本地防火墙
sudo iptables -L -n | grep <host_ip>
```

**第 2 步：检查主机状态**
```bash
# 如果能 SSH 登录
ssh <host_ip>

# 检查系统负载
uptime

# 查看系统日志
sudo journalctl -xe | tail -50

# 检查最近重启记录
last reboot
```

**第 3 步：检查 Node Exporter**
```bash
# 检查服务状态
sudo systemctl status node_exporter

# 查看日志
sudo journalctl -u node_exporter -n 50

# 检查端口监听
sudo netstat -tuln | grep 9100
```

#### 解决方案

**情况 1：主机关机**
```bash
# 通过 IPMI/iLO/iDRAC 开机
ipmitool -I lanplus -H <ipmi_ip> -U admin -P password power on

# 或者物理开机
```

**情况 2：Node Exporter 崩溃**
```bash
# 重启服务
sudo systemctl restart node_exporter

# 检查状态
sudo systemctl status node_exporter

# 设置自动启动
sudo systemctl enable node_exporter
```

**情况 3：防火墙阻止**
```bash
# 允许 9100 端口
sudo firewall-cmd --permanent --add-port=9100/tcp
sudo firewall-cmd --reload

# 或者 iptables
sudo iptables -A INPUT -p tcp --dport 9100 -j ACCEPT
sudo iptables-save > /etc/sysconfig/iptables
```

#### 预防措施
- ✅ 配置主机自动重启（硬件故障后）
- ✅ 配置 Node Exporter systemd 自动重启
- ✅ 设置硬件监控（温度、风扇）
- ✅ 定期检查磁盘健康状态

---

### CPU 使用率过高 (HighCPU)

#### 告警说明
主机 CPU 使用率持续超过阈值。
- Warning: CPU > 85%（持续 5 分钟）
- Critical: CPU > 95%（持续 3 分钟）

#### 影响范围
- **严重程度**: ⚠️ Warning (P2) / 🔴 Critical (P1)
- **影响**: 服务响应变慢，可能导致超时
- **SLA影响**: 中到高

#### 可能原因
1. 业务流量突增
2. 进程异常（死循环、CPU 密集计算）
3. 恶意进程（挖矿、攻击）
4. 资源配置不足

#### 排查步骤

**第 1 步：查看 CPU 占用进程**
```bash
# 实时查看 CPU 占用（推荐）
htop

# 或使用 top
top -c

# 按 CPU 使用率排序
ps aux --sort=-%cpu | head -20

# 查看 CPU 核心使用情况
mpstat -P ALL 1 5
```

**第 2 步：查看系统负载**
```bash
# 查看 1/5/15 分钟负载
uptime

# 查看负载详情
w

# 查看运行队列
vmstat 1 5
```

**第 3 步：检查是否有异常进程**
```bash
# 查找长时间运行的进程
ps -eo pid,ppid,cmd,%cpu,%mem,etime --sort=-%cpu | head -20

# 查看进程线程
top -H -p <pid>

# 查看进程打开的文件
lsof -p <pid>
```

**第 4 步：检查是否有僵尸进程**
```bash
# 查看僵尸进程
ps aux | grep 'Z'

# 统计僵尸进程数量
ps aux | awk '$8=="Z" {print}' | wc -l
```

#### 解决方案

**情况 1：正常业务高峰**
```bash
# 查看业务指标（如 QPS、连接数）
# 如果是业务高峰，考虑扩容或优化

# 临时措施：降低非关键服务优先级
renice +10 <pid>
```

**情况 2：异常进程占用**
```bash
# 先记录进程信息
ps -ef | grep <pid>
lsof -p <pid>

# 杀死进程（优雅关闭）
kill <pid>

# 等待 10 秒后强制杀死
kill -9 <pid>

# 检查进程是否重启
ps aux | grep <process_name>
```

**情况 3：应用程序性能问题**
```bash
# Java 应用：查看线程堆栈
jstack <pid> > jstack.log

# 分析 CPU 占用最高的线程
top -H -p <pid>

# Python 应用：使用 py-spy
py-spy top --pid <pid>
```

**情况 4：资源不足（长期解决）**
- 垂直扩容：增加 CPU 核心数
- 水平扩容：添加更多服务器
- 优化应用代码
- 启用缓存

#### 预防措施
- ✅ 设置 CPU 资源限制（cgroups）
- ✅ 配置自动扩容策略
- ✅ 定期性能测试和压力测试
- ✅ 应用性能分析和优化
- ✅ 监控业务指标趋势

---

### 内存使用率过高 (HighMemory)

#### 告警说明
主机内存使用率持续超过阈值。
- Warning: 内存 > 85%（持续 5 分钟）
- Critical: 内存 > 95%（持续 2 分钟）

#### 影响范围
- **严重程度**: ⚠️ Warning (P2) / 🔴 Critical (P0)
- **影响**: 可能触发 OOM Killer，导致进程被杀死
- **SLA影响**: 高

#### 可能原因
1. 应用内存泄漏
2. 缓存占用过多
3. 业务负载增加
4. 内存配置不足

#### 排查步骤

**第 1 步：查看内存使用情况**
```bash
# 查看内存概览
free -h

# 详细内存信息
cat /proc/meminfo

# 查看内存使用趋势
vmstat 1 5
```

**第 2 步：查找占用内存最多的进程**
```bash
# 按内存使用率排序
ps aux --sort=-%mem | head -20

# 查看进程内存详情
pmap -x <pid>

# 查看进程内存映射
cat /proc/<pid>/smaps | grep -i rss | awk '{sum+=$2} END {print sum/1024 " MB"}'
```

**第 3 步：检查缓存和缓冲区**
```bash
# 查看缓存使用
cat /proc/meminfo | grep -E "Cached|Buffers"

# 查看 slab 缓存
slabtop

# 查看共享内存
ipcs -m
```

**第 4 步：检查 OOM Killer 日志**
```bash
# 查看是否有进程被 OOM 杀死
dmesg | grep -i "out of memory"
dmesg | grep -i "killed process"

# 查看系统日志
grep -i "out of memory" /var/log/messages
```

#### 解决方案

**情况 1：缓存占用过多（临时措施）**
```bash
# 注意：这会影响性能，谨慎操作！
# 仅清理 PageCache
sync && echo 1 > /proc/sys/vm/drop_caches

# 清理 dentries 和 inodes
sync && echo 2 > /proc/sys/vm/drop_caches

# 清理所有缓存
sync && echo 3 > /proc/sys/vm/drop_caches
```

**情况 2：应用内存泄漏**
```bash
# Java 应用：生成堆转储
jmap -dump:format=b,file=heap.hprof <pid>

# 分析堆转储（需要工具）
# 使用 Eclipse MAT 或 jhat

# 临时措施：重启应用
systemctl restart <service>
```

**情况 3：进程占用内存过多**
```bash
# 记录进程信息
ps -ef | grep <pid>

# 优雅重启
systemctl restart <service>

# 或者杀死进程
kill -9 <pid>
```

**情况 4：内存不足（长期解决）**
- 增加物理内存
- 优化应用内存使用
- 启用 swap（临时缓解）
- 分离服务到不同主机

#### 预防措施
- ✅ 设置内存资源限制（cgroups）
- ✅ 配置应用堆内存限制
- ✅ 定期重启内存密集型应用
- ✅ 监控内存增长趋势
- ✅ 进行内存泄漏测试

---

### 磁盘空间不足 (DiskSpaceLow)

#### 告警说明
文件系统剩余空间不足。
- Warning: 剩余 < 15%（持续 5 分钟）
- Critical: 剩余 < 5%（持续 1 分钟）

#### 影响范围
- **严重程度**: ⚠️ Warning (P2) / 🔴 Critical (P0)
- **影响**: 无法写入文件，服务可能崩溃
- **SLA影响**: 高

#### 可能原因
1. 日志文件过大
2. 临时文件未清理
3. 数据增长过快
4. 磁盘配置不足

#### 排查步骤

**第 1 步：查看磁盘使用情况**
```bash
# 查看所有文件系统
df -h

# 查看 inode 使用情况
df -i

# 查看特定挂载点
df -h /data
```

**第 2 步：查找大文件和目录**
```bash
# 查找根目录下最大的目录（TOP 10）
du -sh /* 2>/dev/null | sort -rh | head -10

# 查找最大的文件（大于 100MB）
find / -type f -size +100M -exec ls -lh {} \; 2>/dev/null | sort -k5 -rh | head -20

# 查找特定目录下的大文件
find /var/log -type f -size +50M -exec ls -lh {} \;
```

**第 3 步：检查日志文件**
```bash
# 查看 systemd 日志大小
journalctl --disk-usage

# 查看所有日志文件大小
du -sh /var/log/*

# 查找最大的日志文件
find /var/log -type f -exec ls -lh {} \; | sort -k5 -rh | head -10
```

**第 4 步：检查已删除但未释放的文件**
```bash
# 查看被删除但进程仍然打开的文件
lsof | grep deleted

# 查看占用空间
lsof | grep deleted | awk '{sum+=$7} END {print sum/1024/1024 " MB"}'
```

#### 解决方案

**情况 1：日志文件过大**
```bash
# 清理 systemd 日志（保留最近 7 天）
journalctl --vacuum-time=7d

# 或按大小清理（保留 500MB）
journalctl --vacuum-size=500M

# 清理应用日志
find /var/log -name "*.log" -mtime +30 -delete
find /var/log -name "*.gz" -mtime +30 -delete

# 压缩旧日志
find /var/log -name "*.log" -mtime +7 -exec gzip {} \;
```

**情况 2：临时文件过多**
```bash
# 清理 /tmp（注意：可能影响运行中的应用）
find /tmp -type f -mtime +7 -delete

# 清理 yum/dnf 缓存
yum clean all

# 清理 apt 缓存
apt-get clean
apt-get autoclean
```

**情况 3：Docker 占用空间**
```bash
# 查看 Docker 空间使用
docker system df

# 清理未使用的镜像
docker image prune -a

# 清理未使用的容器
docker container prune

# 清理未使用的卷
docker volume prune

# 一键清理所有未使用资源
docker system prune -a --volumes
```

**情况 4：已删除文件未释放**
```bash
# 重启占用已删除文件的进程
# 先找到进程
lsof | grep deleted | awk '{print $2}' | sort -u

# 重启对应服务
systemctl restart <service>
```

**情况 5：扩容磁盘（长期解决）**
```bash
# 在线扩容（LVM）
lvextend -L +50G /dev/mapper/vg-lv
resize2fs /dev/mapper/vg-lv

# 或者 XFS
xfs_growfs /data

# 添加新磁盘并迁移数据
```

#### 预防措施
- ✅ 配置日志轮转（logrotate）
- ✅ 设置日志自动清理策略
- ✅ 监控磁盘使用趋势
- ✅ 定期清理临时文件
- ✅ 使用独立磁盘存储日志和数据

---

### 磁盘 I/O 等待过高 (HighDiskIOWait)

#### 告警说明
磁盘 I/O 等待时间过高，CPU 等待 I/O 完成的时间超过阈值。

#### 影响范围
- **严重程度**: ⚠️ Warning (P2)
- **影响**: 系统响应变慢，应用性能下降
- **SLA影响**: 中

#### 可能原因
1. 磁盘性能不足
2. 大量读写操作
3. 磁盘故障或老化
4. RAID 重建

#### 排查步骤

**第 1 步：查看 I/O 统计**
```bash
# 查看 I/O 等待
vmstat 1 5

# 查看磁盘 I/O 详情
iostat -x 1 5

# 查看每个磁盘的 I/O
iostat -xd 1 5
```

**第 2 步：查找占用 I/O 的进程**
```bash
# 安装 iotop（如果没有）
yum install iotop  # CentOS/RHEL
apt-get install iotop  # Debian/Ubuntu

# 实时查看 I/O 占用
iotop -o

# 查看进程 I/O 统计
pidstat -d 1 5
```

**第 3 步：检查磁盘健康**
```bash
# 查看磁盘 SMART 信息
smartctl -a /dev/sda

# 查看磁盘错误
dmesg | grep -i error
dmesg | grep -i "I/O error"
```

**第 4 步：检查文件系统**
```bash
# 查看文件系统挂载选项
mount | grep /data

# 检查文件系统错误
fsck -n /dev/sda1
```

#### 解决方案

**情况 1：应用程序 I/O 密集**
```bash
# 优化应用 I/O 行为
# - 启用缓存
# - 批量写入
# - 异步 I/O

# 调整进程 I/O 优先级
ionice -c2 -n7 -p <pid>

# 限制进程 I/O（cgroups）
cgcreate -g blkio:/limit-io
echo "<pid>" > /sys/fs/cgroup/blkio/limit-io/tasks
echo "8:0 1048576" > /sys/fs/cgroup/blkio/limit-io/blkio.throttle.read_bps_device
```

**情况 2：文件系统优化**
```bash
# 启用 noatime 挂载选项（减少写入）
mount -o remount,noatime /data

# 永久修改 /etc/fstab
/dev/sda1  /data  ext4  noatime,nodiratime  0  2
```

**情况 3：磁盘性能不足**
- 升级到 SSD
- 使用 RAID 0/10 提升性能
- 分离数据到多个磁盘

#### 预防措施
- ✅ 使用高性能磁盘（SSD/NVMe）
- ✅ 优化应用 I/O 模式
- ✅ 启用文件系统缓存
- ✅ 定期检查磁盘健康
- ✅ 监控 I/O 使用趋势

---

### 系统负载过高 (HighSystemLoad)

#### 告警说明
系统 15 分钟平均负载过高。
- Warning: 负载 > CPU核心数 * 1.5
- Critical: 负载 > CPU核心数 * 2.5

#### 影响范围
- **严重程度**: ⚠️ Warning (P2) / 🔴 Critical (P1)
- **影响**: 系统响应变慢，可能无响应
- **SLA影响**: 中到高

#### 排查步骤

**第 1 步：查看负载详情**
```bash
# 查看负载和运行进程数
uptime
w

# 查看详细负载信息
cat /proc/loadavg

# 查看运行队列
vmstat 1 5
```

**第 2 步：判断负载类型**
```bash
# 查看 CPU、内存、I/O 状态
vmstat 1 5

# 如果 wa（I/O等待）高 → I/O 密集
# 如果 sy（系统）高 → 系统调用频繁
# 如果 us（用户）高 → CPU 密集
```

**第 3 步：查找高负载进程**
```bash
# 查看所有进程
top -c

# 按 CPU 排序
ps aux --sort=-%cpu | head -20

# 查看进程状态
ps -eo pid,ppid,cmd,stat,wchan --sort=-pcpu | head -20

# 查看不可中断睡眠进程（D状态）
ps aux | awk '$8=="D" {print}'
```

#### 解决方案
参考 CPU、内存、I/O 相关章节的解决方案。

---

### 网络接口下线 (NetworkInterfaceDown)

#### 告警说明
物理网络接口状态为 DOWN。

#### 影响范围
- **严重程度**: ⚠️ Warning (P2)
- **影响**: 该接口的网络连接中断
- **SLA影响**: 中

#### 排查步骤

**第 1 步：检查接口状态**
```bash
# 查看所有接口
ip link show

# 查看特定接口
ip link show eth0

# 查看接口详细信息
ethtool eth0

# 查看接口统计
ip -s link show eth0
```

**第 2 步：检查物理连接**
```bash
# 检查网线是否插好
ethtool eth0 | grep "Link detected"

# 查看接口速率和双工
ethtool eth0 | grep -E "Speed|Duplex"

# 检查接口错误
netstat -i
```

#### 解决方案

**情况 1：接口被手动关闭**
```bash
# 启动接口
ip link set eth0 up

# 或使用 ifconfig
ifconfig eth0 up

# 永久启用（修改配置文件）
# CentOS/RHEL: /etc/sysconfig/network-scripts/ifcfg-eth0
ONBOOT=yes

# Ubuntu/Debian: /etc/network/interfaces
auto eth0
```

**情况 2：物理连接问题**
- 检查网线是否插好
- 更换网线
- 检查交换机端口状态
- 检查光模块（如果是光纤）

---

## VMware 虚拟化告警

### 虚拟机宕机 (VMDown)

#### 告警说明
虚拟机电源状态为关机（powerstate = 0）。

#### 影响范围
- **严重程度**: 🔴 Critical (P1)
- **影响**: 虚拟机上的服务不可用
- **SLA影响**: 高

#### 可能原因
1. 手动关机
2. ESXi 主机故障
3. 电源管理策略触发
4. VM 自动关机脚本

#### 排查步骤

**第 1 步：登录 vCenter 检查**
```
1. 打开 vSphere Client
2. 找到对应虚拟机
3. 查看电源状态
4. 查看事件日志（Events标签）
```

**第 2 步：检查 ESXi 主机状态**
```bash
# 通过 CLI 检查
ssh root@<esxi_ip>

# 查看 VM 列表
vim-cmd vmsvc/getallvms

# 查看 VM 电源状态
vim-cmd vmsvc/power.getstate <vmid>

# 查看 ESXi 日志
tail -100 /var/log/vmware/hostd.log
```

#### 解决方案

**情况 1：计划内关机**
```
确认是否为维护窗口，无需操作
```

**情况 2：意外关机，需要启动**
```
vCenter 操作：
1. 右键虚拟机
2. Power → Power On
3. 等待虚拟机启动
4. 检查服务是否正常
```

**通过 CLI 启动**：
```bash
# SSH 到 ESXi
ssh root@<esxi_ip>

# 启动虚拟机
vim-cmd vmsvc/power.on <vmid>

# 查看启动状态
vim-cmd vmsvc/power.getstate <vmid>
```

#### 预防措施
- ✅ 配置 HA（High Availability）
- ✅ 配置 DRS（Distributed Resource Scheduler）
- ✅ 设置 VM 重启策略
- ✅ 监控 ESXi 主机健康状态

---

### 虚拟机 CPU/内存过高

#### 告警说明
虚拟机资源使用率持续过高。
- Warning: CPU/内存 > 80%
- Critical: CPU/内存 > 95%

#### 排查步骤

**第 1 步：vCenter 检查**
```
1. 打开 vSphere Client
2. 选择虚拟机 → Performance 标签
3. 查看 CPU/内存使用趋势
4. 检查是否有资源竞争
```

**第 2 步：检查虚拟机内部**
```bash
# SSH 登录虚拟机
ssh user@vm_ip

# 查看进程（参考主机监控章节）
top -c
ps aux --sort=-%cpu
ps aux --sort=-%mem
```

#### 解决方案

**情况 1：资源配置不足**
```
vCenter 操作：
1. 右键虚拟机 → Edit Settings
2. 增加 vCPU 数量（可能需要重启）
3. 增加内存大小（可能需要重启）
4. 保存配置
```

**情况 2：应用程序问题**
- 参考主机监控章节的解决方案
- 优化应用程序
- 重启服务

---

### ESXi 主机资源过高

#### 告警说明
ESXi 主机 CPU/内存使用率过高。
- Warning: > 80%
- Critical: > 95%

#### 影响范围
- **严重程度**: 🔴 Critical (P0)
- **影响**: 所有虚拟机性能下降
- **SLA影响**: 非常高

#### 排查步骤

**第 1 步：vCenter 检查**
```
1. 打开 vSphere Client
2. 选择 ESXi 主机 → Performance
3. 查看资源使用情况
4. 查看 VM 列表和资源分配
```

**第 2 步：识别高负载 VM**
```
1. 在 ESXi 主机视图中
2. 切换到 VMs 标签
3. 按 CPU/内存使用率排序
4. 识别占用资源最多的 VM
```

#### 解决方案

**情况 1：VM 分布不均**
```
使用 vMotion 迁移 VM：
1. 右键高负载 VM
2. Migrate → Change compute resource only
3. 选择负载较低的 ESXi 主机
4. 完成迁移
```

**情况 2：启用 DRS**
```
1. 配置 DRS 集群
2. 设置为 Fully Automated
3. DRS 会自动平衡负载
```

**情况 3：扩容集群**
- 添加新的 ESXi 主机到集群
- 迁移部分 VM 到新主机

---

### 数据存储空间不足 (DatastoreLowSpace)

#### 告警说明
数据存储剩余空间不足。
- Warning: > 80% 已使用
- Critical: > 90% 已使用

#### 影响范围
- **严重程度**: 🔴 Critical (P0)
- **影响**: 无法创建快照、VM无法写入
- **SLA影响**: 非常高

#### 可能原因
1. VM 磁盘增长
2. 快照过多
3. 日志文件过大
4. 存储配置不足

#### 排查步骤

**第 1 步：vCenter 检查**
```
1. 打开 vSphere Client
2. Storage → Datastores
3. 查看使用率
4. 切换到 VMs 标签查看占用最多的 VM
```

**第 2 步：检查快照**
```
1. 选择数据存储
2. 查看 Snapshot Manager
3. 识别大快照文件
```

#### 解决方案

**情况 1：快照过多**
```
删除不需要的快照：
1. 右键 VM → Snapshots → Manage Snapshots
2. 选择不需要的快照
3. Delete / Delete All
4. 等待快照合并完成（可能需要较长时间）
```

**情况 2：VM 磁盘过大**
```
清理或迁移 VM：
1. 登录 VM 清理不需要的文件
2. 或迁移 VM 到其他数据存储
3. Storage vMotion
```

**情况 3：扩容数据存储**
```
- 添加新 LUN 到数据存储
- 扩展现有 LUN
- 创建新数据存储
```

#### 预防措施
- ✅ 定期清理快照
- ✅ 监控存储增长趋势
- ✅ 设置快照保留策略
- ✅ 使用精简置备（Thin Provisioning）

---

## 网络设备告警

### SNMP 设备不可达 (SNMPDeviceDown)

#### 告警说明
无法通过 SNMP 采集设备数据。

#### 影响范围
- **严重程度**: 🔴 Critical (P0)
- **影响**: 设备可能宕机或网络不可达
- **SLA影响**: 高

#### 可能原因
1. 设备宕机
2. 网络不可达
3. SNMP 配置错误
4. 防火墙阻止

#### 排查步骤

**第 1 步：检查网络连通性**
```bash
# Ping 设备
ping -c 4 <device_ip>

# Traceroute
traceroute <device_ip>

# 检查 SNMP 端口
nmap -p 161 <device_ip>
```

**第 2 步：测试 SNMP 连接**
```bash
# 手动 SNMP 查询
snmpwalk -v2c -c public <device_ip> system

# 如果失败，检查 community string
snmpwalk -v2c -c <community> <device_ip> sysDescr
```

**第 3 步：登录设备检查**
```bash
# SSH 登录交换机
ssh admin@<device_ip>

# 检查 SNMP 配置
show snmp

# 检查 ACL 配置
show access-lists
```

#### 解决方案

**情况 1：设备宕机**
- 检查设备电源
- 检查设备状态指示灯
- 重启设备

**情况 2：SNMP 配置错误**
```
# 配置 SNMP（Cisco 示例）
enable
configure terminal
snmp-server community public RO
end
write memory
```

**情况 3：防火墙阻止**
```
# 允许 SNMP 流量（防火墙配置）
# 开放 UDP 161 端口
```

---

### 网络接口下线 (InterfaceDown)

#### 告警说明
交换机/路由器接口状态为 DOWN（ifOperStatus = 2）。

#### 影响范围
- **严重程度**: ⚠️ Warning (P2)
- **影响**: 该接口的网络连接中断
- **SLA影响**: 中

#### 排查步骤

**第 1 步：登录设备检查**
```bash
# Cisco 设备
ssh admin@<device_ip>
show interface status
show interface <interface_name>

# 查看接口详细信息
show interface GigabitEthernet0/1

# 查看接口错误
show interface GigabitEthernet0/1 | include error
```

**第 2 步：检查物理连接**
```
1. 检查网线是否插好
2. 检查对端设备状态
3. 更换网线测试
4. 检查端口指示灯
```

#### 解决方案

**情况 1：接口被手动关闭**
```
# Cisco 设备
enable
configure terminal
interface GigabitEthernet0/1
no shutdown
end
write memory
```

**情况 2：物理连接问题**
- 更换网线
- 更换光模块
- 检查对端设备

---

### 接口错误率过高 (HighInterfaceErrors)

#### 告警说明
接口输入/输出错误包数量持续增加。

#### 影响范围
- **严重程度**: ⚠️ Warning (P2)
- **影响**: 网络性能下降，丢包
- **SLA影响**: 中

#### 可能原因
1. 网线质量差
2. 光模块故障
3. 接口硬件故障
4. 速率/双工模式不匹配

#### 排查步骤

**第 1 步：查看错误详情**
```bash
# Cisco 设备
show interface GigabitEthernet0/1 | include error
show interface counters errors

# 查看 CRC 错误
show interface GigabitEthernet0/1 | include CRC
```

**第 2 步：检查速率和双工**
```bash
# 查看接口速率和双工
show interface GigabitEthernet0/1 status

# 查看协商状态
show interface GigabitEthernet0/1 | include duplex
```

#### 解决方案

**情况 1：速率/双工不匹配**
```
# 设置为自动协商
interface GigabitEthernet0/1
duplex auto
speed auto
end
write memory

# 或强制设置
interface GigabitEthernet0/1
duplex full
speed 1000
end
write memory
```

**情况 2：物理层问题**
- 更换网线（使用高质量线缆）
- 更换光模块
- 清洁光纤接头
- 检查接口硬件

---

### 接口流量过高 (HighInterfaceTraffic)

#### 告警说明
接口流量使用率超过 80%。

#### 影响范围
- **严重程度**: ⚠️ Warning (P2)
- **影响**: 网络拥塞，延迟增加
- **SLA影响**: 中

#### 可能原因
1. 业务流量增长
2. 异常流量（攻击、广播风暴）
3. 带宽配置不足

#### 排查步骤

**第 1 步：查看流量详情**
```bash
# Cisco 设备
show interface GigabitEthernet0/1
show interface GigabitEthernet0/1 | include rate

# 查看流量统计
show interface counters
```

**第 2 步：分析流量来源**
```bash
# 使用 NetFlow/sFlow
show ip flow top-talkers

# 或使用 SPAN 抓包分析
```

#### 解决方案

**情况 1：正常业务增长**
- 升级接口带宽
- 添加链路聚合（Port Channel）
- 部署负载均衡

**情况 2：异常流量**
- 查找流量源头
- 配置 ACL 限制
- 启用流量整形（QoS）

---

## 服务可用性告警

### 网站宕机 (WebsiteDown)

#### 告警说明
网站无法访问，HTTP 探测失败。

#### 影响范围
- **严重程度**: 🔴 Critical (P0)
- **影响**: 用户无法访问网站
- **SLA影响**: 非常高

#### 可能原因
1. Web 服务宕机
2. 应用程序错误
3. 网络不可达
4. DNS 解析失败

#### 排查步骤

**第 1 步：本地测试**
```bash
# 浏览器访问
# 打开浏览器访问 URL

# 命令行测试
curl -I https://www.company.com

# 测试 DNS 解析
nslookup www.company.com
dig www.company.com
```

**第 2 步：检查 Web 服务**
```bash
# SSH 登录 Web 服务器
ssh user@webserver

# 检查 Nginx/Apache 状态
systemctl status nginx
systemctl status apache2

# 查看日志
tail -100 /var/log/nginx/error.log
```

**第 3 步：检查端口监听**
```bash
# 检查端口
netstat -tuln | grep :80
netstat -tuln | grep :443

# 测试端口连通性
telnet webserver 80
nc -zv webserver 80
```

#### 解决方案

**情况 1：Web 服务宕机**
```bash
# 重启服务
systemctl restart nginx

# 检查配置
nginx -t

# 查看错误日志
journalctl -u nginx -n 50
```

**情况 2：应用程序错误**
```bash
# 查看应用日志
tail -100 /var/log/app/error.log

# 重启应用
systemctl restart app

# 检查进程
ps aux | grep app
```

**情况 3：防火墙问题**
```bash
# 检查防火墙规则
iptables -L -n
firewall-cmd --list-all

# 允许 HTTP/HTTPS
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --reload
```

---

### 网站响应缓慢 (WebsiteSlow)

#### 告警说明
网站响应时间超过阈值。
- Warning: > 2秒
- Critical: > 5秒

#### 影响范围
- **严重程度**: ⚠️ Warning (P2) / 🔴 Critical (P1)
- **影响**: 用户体验差
- **SLA影响**: 中到高

#### 可能原因
1. 服务器负载过高
2. 数据库查询慢
3. 网络延迟
4. 缓存失效

#### 排查步骤

**第 1 步：测试响应时间**
```bash
# 使用 curl 测试
curl -o /dev/null -s -w "Time: %{time_total}s\n" https://www.company.com

# 详细时间分解
curl -o /dev/null -s -w "\
DNS: %{time_namelookup}s\n\
Connect: %{time_connect}s\n\
SSL: %{time_appconnect}s\n\
Transfer: %{time_starttransfer}s\n\
Total: %{time_total}s\n" https://www.company.com
```

**第 2 步：检查服务器负载**
```bash
# 参考主机监控章节
top
vmstat 1 5
iostat -x 1 5
```

**第 3 步：检查数据库**
```bash
# MySQL 慢查询日志
tail -100 /var/log/mysql/mysql-slow.log

# 查看当前查询
mysql -e "SHOW PROCESSLIST;"

# 查看慢查询数量
mysql -e "SHOW STATUS LIKE 'Slow_queries';"
```

#### 解决方案

**情况 1：服务器负载高**
- 参考主机监控章节
- 扩容服务器
- 启用负载均衡

**情况 2：数据库慢查询**
```bash
# 优化查询
# 添加索引
# 优化表结构
# 启用查询缓存
```

**情况 3：启用缓存**
```bash
# Nginx 启用缓存
# Redis 缓存热点数据
# CDN 加速静态资源
```

---

### SSL 证书过期 (SSLCertificateExpiring)

#### 告警说明
SSL 证书即将过期。
- Warning: 剩余 < 30 天
- Critical: 剩余 < 7 天

#### 影响范围
- **严重程度**: ⚠️ Warning (P2) / 🔴 Critical (P0)
- **影响**: 证书过期后网站不可访问
- **SLA影响**: 非常高

#### 可能原因
1. 忘记续期
2. 自动续期失败

#### 排查步骤

**第 1 步：检查证书有效期**
```bash
# 在线检查
echo | openssl s_client -connect www.company.com:443 2>/dev/null | openssl x509 -noout -dates

# 查看剩余天数
echo | openssl s_client -connect www.company.com:443 2>/dev/null | \
  openssl x509 -noout -enddate | cut -d= -f2

# 详细证书信息
echo | openssl s_client -connect www.company.com:443 2>/dev/null | openssl x509 -noout -text
```

**第 2 步：检查服务器证书文件**
```bash
# 检查证书文件
openssl x509 -in /etc/ssl/certs/server.crt -noout -dates

# 检查私钥匹配
openssl x509 -in server.crt -noout -modulus | openssl md5
openssl rsa -in server.key -noout -modulus | openssl md5
```

#### 解决方案

**情况 1：续期证书（Let's Encrypt）**
```bash
# 手动续期
certbot renew

# 强制续期
certbot renew --force-renewal

# 测试续期（不实际续期）
certbot renew --dry-run

# 检查自动续期定时任务
systemctl list-timers | grep certbot
```

**情况 2：续期证书（商业证书）**
```
1. 联系证书提供商
2. 生成 CSR
3. 提交续期申请
4. 下载新证书
5. 部署新证书
```

**第 3 步：部署新证书**
```bash
# 备份旧证书
cp /etc/ssl/certs/server.crt /etc/ssl/certs/server.crt.old

# 复制新证书
cp new-cert.crt /etc/ssl/certs/server.crt

# 重启 Web 服务
systemctl restart nginx

# 验证新证书
echo | openssl s_client -connect www.company.com:443 2>/dev/null | openssl x509 -noout -dates
```

#### 预防措施
- ✅ 配置自动续期（Let's Encrypt）
- ✅ 设置证书过期提醒（30天、7天）
- ✅ 使用证书管理工具
- ✅ 定期检查证书状态

---

### TCP 端口不可用 (TCPPortDown)

#### 告警说明
TCP 端口无法连接。

#### 影响范围
- **严重程度**: 🔴 Critical (P1)
- **影响**: 服务不可用
- **SLA影响**: 高

#### 可能原因
1. 服务未启动
2. 端口被占用
3. 防火墙阻止
4. 进程崩溃

#### 排查步骤

**第 1 步：测试端口连通性**
```bash
# Telnet 测试
telnet <host> <port>

# Netcat 测试
nc -zv <host> <port>

# Nmap 扫描
nmap -p <port> <host>
```

**第 2 步：检查端口监听**
```bash
# 检查端口监听
netstat -tuln | grep <port>
ss -tuln | grep <port>

# 查看进程
lsof -i :<port>
```

**第 3 步：检查服务状态**
```bash
# 检查服务
systemctl status <service>

# 查看日志
journalctl -u <service> -n 50
```

#### 解决方案

**情况 1：服务未启动**
```bash
# 启动服务
systemctl start <service>

# 检查状态
systemctl status <service>

# 设置自动启动
systemctl enable <service>
```

**情况 2：端口被占用**
```bash
# 查找占用端口的进程
lsof -i :<port>

# 杀死进程
kill -9 <pid>

# 重启服务
systemctl restart <service>
```

**情况 3：防火墙阻止**
```bash
# 检查防火墙
iptables -L -n | grep <port>
firewall-cmd --list-all

# 允许端口
firewall-cmd --permanent --add-port=<port>/tcp
firewall-cmd --reload
```

---

## 监控系统告警

### VictoriaMetrics 宕机

#### 告警说明
VictoriaMetrics 时序数据库服务宕机。

#### 影响范围
- **严重程度**: 🔴 Critical (P0)
- **影响**: 整个监控系统停止工作
- **SLA影响**: 非常高

#### 排查步骤

**第 1 步：检查容器状态**
```bash
# 查看容器
docker ps -a | grep victoriametrics

# 查看日志
docker logs victoriametrics --tail 100

# 查看资源使用
docker stats victoriametrics --no-stream
```

**第 2 步：检查磁盘空间**
```bash
# 检查数据目录
df -h | grep victoria

# 检查 inode
df -i
```

#### 解决方案

**情况 1：容器崩溃**
```bash
# 重启容器
docker-compose restart victoriametrics

# 查看日志
docker logs -f victoriametrics

# 如果无法启动，查看错误
docker logs victoriametrics 2>&1 | tail -50
```

**情况 2：磁盘空间不足**
```bash
# 清理旧数据
# 或扩容磁盘

# 临时措施：调整保留期
docker-compose down
# 修改 docker-compose.yaml 中的 --retentionPeriod
docker-compose up -d
```

**情况 3：配置错误**
```bash
# 检查配置
docker-compose config

# 重新部署
docker-compose up -d victoriametrics
```

---

### vmagent 宕机

#### 告警说明
vmagent 采集服务宕机。

#### 影响范围
- **严重程度**: 🔴 Critical (P0)
- **影响**: 监控数据无法采集
- **SLA影响**: 非常高

#### 排查步骤

**第 1 步：检查容器**
```bash
# 查看容器状态
docker ps -a | grep vmagent

# 查看日志
docker logs vmagent --tail 100
```

**第 2 步：检查配置文件**
```bash
# 验证配置
docker exec vmagent cat /etc/prometheus/prometheus.yml

# 检查语法（如果有 promtool）
promtool check config prometheus.yml
```

#### 解决方案

**情况 1：配置文件错误**
```bash
# 修正配置文件
vim config/vmagent/prometheus.yml

# 重启服务
docker-compose restart vmagent

# 查看日志确认
docker logs -f vmagent
```

**情况 2：连接 VictoriaMetrics 失败**
```bash
# 检查网络
docker network inspect monitoring

# 重启 vmagent
docker-compose restart vmagent
```

---

### vmalert 宕机

#### 告警说明
vmalert 告警引擎宕机。

#### 影响范围
- **严重程度**: 🔴 Critical (P0)
- **影响**: 无法发送告警通知
- **SLA影响**: 非常高

#### 排查步骤
```bash
# 查看容器
docker ps -a | grep vmalert

# 查看日志
docker logs vmalert --tail 100

# 检查告警规则
ls -lh config/vmalert/alerts/
```

#### 解决方案

**情况 1：告警规则语法错误**
```bash
# 修正规则文件
vim config/vmalert/alerts/*.yml

# 重启服务
docker-compose restart vmalert

# 查看日志
docker logs -f vmalert
```

**情况 2：连接失败**
```bash
# 重启 vmalert
docker-compose restart vmalert

# 检查 VictoriaMetrics 和 Alertmanager 状态
docker ps | grep -E "victoriametrics|alertmanager"
```

---

## 📞 升级流程

### 告警优先级处理时间

| 优先级 | 响应时间 | 开始处理 | 解决时间目标 |
|-------|---------|---------|------------|
| **P0** | 立即（5分钟内） | 15分钟内 | 1小时 |
| **P1** | 15分钟内 | 30分钟内 | 4小时 |
| **P2** | 30分钟内 | 2小时内 | 24小时 |
| **P3** | 24小时内 | 48小时内 | 1周 |

### 升级路径

```
告警触发 → 值班工程师（15分钟）→ 团队负责人（30分钟）→ 技术总监（1小时）
```

---

## 📚 附录

### 常用命令速查

**系统信息**
```bash
# 系统版本
cat /etc/os-release

# 内核版本
uname -r

# 系统启动时间
uptime

# CPU 信息
lscpu

# 内存信息
free -h

# 磁盘信息
lsblk
```

**进程管理**
```bash
# 查看所有进程
ps aux

# 查看进程树
pstree

# 杀死进程
kill <pid>
kill -9 <pid>  # 强制杀死
killall <process_name>

# 查看进程详情
cat /proc/<pid>/status
```

**网络命令**
```bash
# 网络接口
ip addr show
ip link show

# 路由表
ip route show

# 网络连接
netstat -tuln
ss -tuln

# DNS 查询
nslookup <domain>
dig <domain>
host <domain>

# 抓包
tcpdump -i eth0 port 80
```

**Docker 命令**
```bash
# 查看容器
docker ps -a

# 查看日志
docker logs <container>
docker logs -f <container>  # 实时查看

# 进入容器
docker exec -it <container> bash

# 重启容器
docker restart <container>

# 查看资源使用
docker stats

# 清理资源
docker system prune -a
```

### 联系方式

| 团队 | 邮箱 | 电话 | 负责范围 |
|-----|------|------|---------|
| 运维团队 | ops@example.com | 123-456-7890 | 主机、网络 |
| VMware 团队 | vmware@example.com | 123-456-7891 | 虚拟化 |
| 网络团队 | network@example.com | 123-456-7892 | 网络设备 |
| 安全团队 | security@example.com | 123-456-7893 | 安全告警 |
| 监控团队 | monitoring@example.com | 123-456-7894 | 监控系统 |

---

**文档维护**
- 负责人：监控团队
- 更新频率：每季度或重大变更后
- 反馈渠道：monitoring@example.com

**版本历史**
- v1.0 (2025-12-27): 初始版本
