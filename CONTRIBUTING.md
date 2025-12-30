# 🤝 贡献指南 (Contributing Guide)

感谢您对 **Enterprise Infrastructure Observability Platform** 的关注！我们欢迎所有形式的贡献。

[English](#english) | [中文](#中文)

---

## 中文

### 📋 目录

- [行为准则](#行为准则)
- [我能贡献什么](#我能贡献什么)
- [开发环境设置](#开发环境设置)
- [提交指南](#提交指南)
- [Pull Request 流程](#pull-request-流程)
- [代码规范](#代码规范)
- [文档规范](#文档规范)
- [社区支持](#社区支持)

---

### 行为准则

本项目遵循 [贡献者公约](https://www.contributor-covenant.org/zh-cn/version/2/1/code_of_conduct/)。参与本项目即表示您同意遵守其条款。

**核心原则：**
- 尊重所有贡献者
- 接受建设性批评
- 专注于对社区最有利的事情
- 展现对其他社区成员的同理心

---

### 我能贡献什么

#### 🐛 报告 Bug

**在提交 Bug 前，请确认：**
1. 搜索 [现有 Issues](https://github.com/YOUR-USERNAME/monitoring-platform/issues) 确保问题未被报告
2. 使用最新版本测试问题是否仍然存在
3. 收集足够的信息（日志、配置、环境信息）

**Bug 报告应包含：**
```markdown
**Bug 描述**
清晰简洁地描述 Bug

**复现步骤**
1. 执行 '...'
2. 点击 '...'
3. 看到错误

**预期行为**
应该发生什么

**实际行为**
实际发生了什么

**环境信息**
- OS: [例如 Ubuntu 22.04]
- Docker: [例如 20.10.21]
- Docker Compose: [例如 2.12.2]

**日志输出**
```bash
粘贴相关日志
```

**截图**
如有必要，添加截图

**附加信息**
其他相关信息
```

#### 💡 建议新功能

**功能建议应包含：**
- **问题描述**：当前有什么问题或限制
- **建议方案**：您希望如何解决
- **替代方案**：您考虑过的其他方案
- **使用场景**：谁会使用这个功能，在什么场景下

#### 📝 改进文档

文档改进永远欢迎！包括：
- 修复拼写错误或语法错误
- 添加缺失的文档
- 改进现有文档的清晰度
- 添加示例和教程
- 翻译文档

#### ✨ 贡献代码

**适合新贡献者的任务：**
- 标记为 `good first issue` 的 Issues
- 文档改进
- 添加测试用例
- 修复小 Bug

**高级贡献：**
- 新的 Exporter 集成
- 性能优化
- 新功能开发
- 架构改进

---

### 开发环境设置

#### 前置要求

- Git 2.x+
- Docker 20.10+
- Docker Compose 2.0+
- Python 3.8+ (用于脚本开发)
- 文本编辑器或 IDE

#### 克隆仓库

```bash
# 1. Fork 本仓库到您的 GitHub 账号

# 2. 克隆您的 Fork
git clone https://github.com/YOUR-USERNAME/monitoring-platform.git
cd monitoring-platform

# 3. 添加上游远程仓库
git remote add upstream https://github.com/ORIGINAL-OWNER/monitoring-platform.git

# 4. 验证远程仓库
git remote -v
```

#### 本地开发环境

```bash
# 1. 复制示例配置
cp .env.example .env

# 2. 启动服务
docker-compose up -d

# 3. 查看日志
docker-compose logs -f

# 4. 访问服务
# Grafana: http://localhost:3000
# VictoriaMetrics: http://localhost:8428
# Alertmanager: http://localhost:9093
```

#### Python 开发环境

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 运行测试
python -m pytest tests/
```

---

### 提交指南

#### 创建特性分支

```bash
# 确保主分支是最新的
git checkout main
git pull upstream main

# 创建新分支
git checkout -b feature/your-feature-name
# 或
git checkout -b fix/bug-description
```

#### 提交消息规范

我们使用 [Conventional Commits](https://www.conventionalcommits.org/zh-hans/) 规范：

```
<类型>(<范围>): <简短描述>

<详细描述>

<页脚>
```

**类型：**
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 重构（既不是新功能也不是 Bug 修复）
- `perf`: 性能优化
- `test`: 添加测试
- `chore`: 构建过程或辅助工具的变动

**示例：**

```bash
feat(topology): 添加 LLDP 自动发现功能

- 实现 SNMP LLDP 数据采集
- 自动生成网络拓扑图
- 支持设备层级自动计算

Closes #123
```

```bash
fix(alertmanager): 修复核心交换机告警抑制规则

修复当核心交换机故障时，接入交换机告警未被正确抑制的问题。

问题原因：标签匹配规则中 device_tier 字段名错误
解决方案：将 tier 改为 device_tier

Fixes #456
```

---

### Pull Request 流程

#### 1. 准备您的更改

```bash
# 运行测试
docker-compose down
docker-compose up -d
docker-compose ps  # 确保所有服务正常

# 检查代码格式（Python）
black scripts/
flake8 scripts/

# 提交更改
git add .
git commit -m "feat: 您的提交消息"
```

#### 2. 推送到您的 Fork

```bash
git push origin feature/your-feature-name
```

#### 3. 创建 Pull Request

1. 访问您的 Fork 页面
2. 点击 "Compare & pull request"
3. 填写 PR 模板：

```markdown
## 更改描述
清晰描述您的更改内容

## 更改类型
- [ ] Bug 修复
- [ ] 新功能
- [ ] 文档更新
- [ ] 性能优化
- [ ] 代码重构
- [ ] 其他（请说明）

## 测试
- [ ] 本地测试通过
- [ ] 添加了新的测试用例（如适用）
- [ ] 所有服务启动正常
- [ ] 文档已更新（如适用）

## 相关 Issue
Closes #(issue 编号)

## 截图（如适用）
添加截图说明您的更改

## 检查清单
- [ ] 代码遵循项目规范
- [ ] 提交消息遵循 Conventional Commits
- [ ] 文档已更新
- [ ] 没有引入新的警告
```

#### 4. Code Review

- 项目维护者会审查您的 PR
- 可能会要求修改
- 修改后推送到同一分支会自动更新 PR
- 批准后会被合并

---

### 代码规范

#### Python 代码规范

**遵循 PEP 8 规范：**

```python
# Good
def discover_topology(devices, interval=300):
    """
    发现网络拓扑结构

    Args:
        devices (list): 设备列表
        interval (int): 发现间隔（秒）

    Returns:
        dict: 拓扑数据
    """
    topology = {}
    for device in devices:
        # 采集 LLDP 数据
        lldp_data = snmp_get_lldp(device)
        topology[device['name']] = lldp_data

    return topology

# Bad
def discover(d,i=300):
    t={}
    for x in d:
        t[x['name']]=snmp_get_lldp(x)
    return t
```

**使用工具格式化：**

```bash
# 安装工具
pip install black flake8 isort

# 格式化代码
black scripts/
isort scripts/

# 检查代码质量
flake8 scripts/
```

#### Docker 配置规范

```yaml
# Good - 清晰的注释和组织
services:
  # VictoriaMetrics - 时序数据库
  victoriametrics:
    image: victoriametrics/victoria-metrics:latest
    container_name: victoriametrics
    ports:
      - "8428:8428"
    volumes:
      - vmdata:/storage
    command:
      - "--storageDataPath=/storage"
      - "--httpListenAddr=:8428"
      - "--retentionPeriod=12"  # 数据保留12个月
    restart: unless-stopped
    networks:
      - monitoring
```

#### 配置文件规范

**YAML 文件：**
- 使用 2 空格缩进
- 添加清晰的注释
- 按逻辑分组配置

**示例：**

```yaml
# ===== 全局配置 =====
global:
  scrape_interval: 15s      # 默认采集间隔
  evaluation_interval: 15s  # 默认评估间隔

# ===== 告警配置 =====
alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']

# ===== 采集任务 =====
scrape_configs:
  # Linux 主机监控
  - job_name: 'node-exporter'
    scrape_interval: 15s
    static_configs:
      - targets: ['192.168.1.10:9100']
        labels:
          env: 'production'
          role: 'web'
```

---

### 文档规范

#### Markdown 文档

**结构要求：**
- 使用清晰的标题层级（H1 → H2 → H3）
- 添加目录（对于长文档）
- 使用代码块指定语言
- 添加示例和截图

**示例：**

````markdown
# 文档标题

## 目录

- [安装](#安装)
- [配置](#配置)
- [使用](#使用)

## 安装

说明文字...

```bash
# 命令示例
docker-compose up -d
```

## 配置

配置步骤...

| 参数 | 说明 | 默认值 |
|------|------|--------|
| interval | 采集间隔 | 15s |
````

#### 注释规范

**Python 注释：**

```python
def function_name(param1, param2):
    """
    一句话功能描述

    详细说明（可选）

    Args:
        param1 (type): 参数1说明
        param2 (type): 参数2说明

    Returns:
        type: 返回值说明

    Raises:
        ExceptionType: 异常说明

    Example:
        >>> function_name('value1', 'value2')
        'result'
    """
    pass
```

**YAML 注释：**

```yaml
# ===== 主配置段 =====
key: value  # 行内说明

# 多行说明：
# 第一行
# 第二行
complex_config:
  option1: value1
  option2: value2
```

---

### 社区支持

#### 获取帮助

- **GitHub Issues**: [提交问题](https://github.com/YOUR-USERNAME/monitoring-platform/issues)
- **GitHub Discussions**: [参与讨论](https://github.com/YOUR-USERNAME/monitoring-platform/discussions)
- **文档**: 查看 [docs/](docs/) 目录

#### 联系方式

- **维护者**: 在 GitHub 上 @ 提到维护者
- **安全问题**: 请私下报告（不要公开 Issue）

---

## English

### 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Code Standards](#code-standards)
- [Documentation Standards](#documentation-standards)
- [Community Support](#community-support)

---

### Code of Conduct

This project follows the [Contributor Covenant](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).

**Core Principles:**
- Respect all contributors
- Accept constructive criticism
- Focus on what's best for the community
- Show empathy towards other community members

---

### How Can I Contribute

#### 🐛 Reporting Bugs

**Before submitting a bug:**
1. Search [existing issues](https://github.com/YOUR-USERNAME/monitoring-platform/issues)
2. Test with the latest version
3. Collect relevant information (logs, config, environment)

**Bug reports should include:**
- Clear bug description
- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment information
- Log output
- Screenshots (if applicable)

#### 💡 Suggesting Features

Feature suggestions should include:
- Problem description
- Proposed solution
- Alternative solutions
- Use cases

#### 📝 Improving Documentation

Documentation improvements are always welcome:
- Fix typos or grammar
- Add missing documentation
- Improve clarity
- Add examples and tutorials
- Translate documentation

#### ✨ Contributing Code

**Good first tasks:**
- Issues marked `good first issue`
- Documentation improvements
- Adding test cases
- Fixing small bugs

**Advanced contributions:**
- New exporter integrations
- Performance optimizations
- New features
- Architecture improvements

---

### Development Setup

#### Prerequisites

- Git 2.x+
- Docker 20.10+
- Docker Compose 2.0+
- Python 3.8+
- Text editor or IDE

#### Clone Repository

```bash
# 1. Fork the repository

# 2. Clone your fork
git clone https://github.com/YOUR-USERNAME/monitoring-platform.git
cd monitoring-platform

# 3. Add upstream remote
git remote add upstream https://github.com/ORIGINAL-OWNER/monitoring-platform.git

# 4. Verify remotes
git remote -v
```

#### Local Development

```bash
# 1. Copy example config
cp .env.example .env

# 2. Start services
docker-compose up -d

# 3. View logs
docker-compose logs -f

# 4. Access services
# Grafana: http://localhost:3000
# VictoriaMetrics: http://localhost:8428
# Alertmanager: http://localhost:9093
```

---

### Commit Guidelines

We use [Conventional Commits](https://www.conventionalcommits.org/):

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code style
- `refactor`: Code refactoring
- `perf`: Performance optimization
- `test`: Tests
- `chore`: Build/tooling

**Example:**

```bash
feat(topology): add LLDP auto-discovery

- Implement SNMP LLDP data collection
- Auto-generate network topology
- Support automatic tier calculation

Closes #123
```

---

### Pull Request Process

1. Create feature branch
2. Make your changes
3. Run tests
4. Push to your fork
5. Create Pull Request
6. Wait for review
7. Address feedback
8. Get merged!

---

### Code Standards

- Follow PEP 8 for Python
- Use consistent formatting
- Add clear comments
- Write meaningful commit messages
- Update documentation

---

### Documentation Standards

- Use clear heading hierarchy
- Add table of contents for long docs
- Specify language in code blocks
- Add examples and screenshots
- Keep it concise and clear

---

### Community Support

#### Getting Help

- **GitHub Issues**: [Submit issue](https://github.com/YOUR-USERNAME/monitoring-platform/issues)
- **GitHub Discussions**: [Join discussion](https://github.com/YOUR-USERNAME/monitoring-platform/discussions)
- **Documentation**: Check [docs/](docs/) directory

#### Contact

- **Maintainers**: @ mention on GitHub
- **Security Issues**: Report privately

---

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

## 🙏 Thank You!

Thank you for contributing to this project! Every contribution, no matter how small, makes a difference.

---

<div align="center">

**Made with ❤️ by the Community**

[⬆ Back to Top](#-贡献指南-contributing-guide)

</div>
