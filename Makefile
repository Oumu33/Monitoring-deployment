.PHONY: help setup start stop restart status logs health backup restore clean update

# 默认目标
.DEFAULT_GOAL := help

# 颜色输出
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m

##@ 帮助

help: ## 显示帮助信息
	@echo ""
	@echo "$(BLUE)VictoriaMetrics 监控系统 - 操作命令$(NC)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf ""} /^[a-zA-Z_-]+:.*?##/ { printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(YELLOW)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
	@echo ""

##@ 部署管理

setup: ## 初始化部署（首次安装）
	@echo "$(BLUE)开始初始化部署...$(NC)"
	@./scripts/setup.sh

start: ## 启动所有服务
	@echo "$(BLUE)启动监控服务...$(NC)"
	@docker-compose up -d
	@echo "$(GREEN)服务启动完成$(NC)"
	@make status

stop: ## 停止所有服务
	@echo "$(BLUE)停止监控服务...$(NC)"
	@docker-compose down
	@echo "$(GREEN)服务已停止$(NC)"

restart: ## 重启所有服务
	@echo "$(BLUE)重启监控服务...$(NC)"
	@docker-compose restart
	@echo "$(GREEN)服务重启完成$(NC)"

restart-vm: ## 重启 VictoriaMetrics
	@docker-compose restart victoriametrics
	@echo "$(GREEN)VictoriaMetrics 已重启$(NC)"

restart-vmagent: ## 重启 vmagent
	@docker-compose restart vmagent
	@echo "$(GREEN)vmagent 已重启$(NC)"

restart-vmalert: ## 重启 vmalert
	@docker-compose restart vmalert
	@echo "$(GREEN)vmalert 已重启$(NC)"

restart-grafana: ## 重启 Grafana
	@docker-compose restart grafana
	@echo "$(GREEN)Grafana 已重启$(NC)"

restart-alertmanager: ## 重启 Alertmanager
	@docker-compose restart alertmanager
	@echo "$(GREEN)Alertmanager 已重启$(NC)"

##@ 状态监控

status: ## 查看服务状态
	@echo "$(BLUE)服务运行状态:$(NC)"
	@docker-compose ps

health: ## 执行健康检查
	@./scripts/health-check.sh

logs: ## 查看所有服务日志
	@docker-compose logs -f --tail=100

logs-vm: ## 查看 VictoriaMetrics 日志
	@docker-compose logs -f --tail=100 victoriametrics

logs-vmagent: ## 查看 vmagent 日志
	@docker-compose logs -f --tail=100 vmagent

logs-vmalert: ## 查看 vmalert 日志
	@docker-compose logs -f --tail=100 vmalert

logs-grafana: ## 查看 Grafana 日志
	@docker-compose logs -f --tail=100 grafana

logs-alertmanager: ## 查看 Alertmanager 日志
	@docker-compose logs -f --tail=100 alertmanager

##@ 备份恢复

backup: ## 创建完整备份
	@./scripts/backup.sh

restore: ## 从备份恢复（需要指定备份目录: make restore BACKUP_DIR=./backup/20240101_120000）
	@if [ -z "$(BACKUP_DIR)" ]; then \
		echo "$(YELLOW)请指定备份目录: make restore BACKUP_DIR=./backup/20240101_120000$(NC)"; \
		exit 1; \
	fi
	@./scripts/restore.sh $(BACKUP_DIR)

##@ 配置管理

config-check: ## 检查配置文件语法
	@echo "$(BLUE)检查 docker-compose 配置...$(NC)"
	@docker-compose config > /dev/null && echo "$(GREEN)✓ Docker Compose 配置正确$(NC)"
	@echo "$(BLUE)检查 Prometheus 配置...$(NC)"
	@docker run --rm -v $(PWD)/config/vmagent:/config prom/prometheus:latest promtool check config /config/prometheus.yml && echo "$(GREEN)✓ Prometheus 配置正确$(NC)"

reload-vmagent: ## 重新加载 vmagent 配置（不重启）
	@echo "$(BLUE)重新加载 vmagent 配置...$(NC)"
	@curl -X POST http://localhost:8429/-/reload || make restart-vmagent
	@echo "$(GREEN)配置已重新加载$(NC)"

reload-vmalert: ## 重新加载 vmalert 配置（不重启）
	@echo "$(BLUE)重新加载 vmalert 配置...$(NC)"
	@curl -X POST http://localhost:8880/-/reload || make restart-vmalert
	@echo "$(GREEN)配置已重新加载$(NC)"

reload-alertmanager: ## 重新加载 Alertmanager 配置（不重启）
	@echo "$(BLUE)重新加载 Alertmanager 配置...$(NC)"
	@curl -X POST http://localhost:9093/-/reload || make restart-alertmanager
	@echo "$(GREEN)配置已重新加载$(NC)"

##@ 数据管理

clean-data: ## 清理所有监控数据（危险操作！）
	@echo "$(YELLOW)警告: 这将删除所有监控数据！$(NC)"
	@read -p "确认删除? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		make stop; \
		docker volume rm monitoring-deployment_vmdata monitoring-deployment_vmagentdata monitoring-deployment_grafana-data monitoring-deployment_alertmanager-data 2>/dev/null || true; \
		echo "$(GREEN)数据已清理$(NC)"; \
	else \
		echo "$(BLUE)操作已取消$(NC)"; \
	fi

update-images: ## 更新所有 Docker 镜像
	@echo "$(BLUE)更新 Docker 镜像...$(NC)"
	@docker-compose pull
	@echo "$(GREEN)镜像更新完成，请执行 make restart 重启服务$(NC)"

##@ 访问服务

open-grafana: ## 在浏览器打开 Grafana
	@echo "$(BLUE)打开 Grafana...$(NC)"
	@xdg-open http://localhost:3000 2>/dev/null || open http://localhost:3000 2>/dev/null || echo "请访问: http://localhost:3000"

open-vm: ## 在浏览器打开 VictoriaMetrics
	@echo "$(BLUE)打开 VictoriaMetrics...$(NC)"
	@xdg-open http://localhost:8428 2>/dev/null || open http://localhost:8428 2>/dev/null || echo "请访问: http://localhost:8428"

open-vmalert: ## 在浏览器打开 vmalert
	@echo "$(BLUE)打开 vmalert...$(NC)"
	@xdg-open http://localhost:8880 2>/dev/null || open http://localhost:8880 2>/dev/null || echo "请访问: http://localhost:8880"

open-alertmanager: ## 在浏览器打开 Alertmanager
	@echo "$(BLUE)打开 Alertmanager...$(NC)"
	@xdg-open http://localhost:9093 2>/dev/null || open http://localhost:9093 2>/dev/null || echo "请访问: http://localhost:9093"

##@ 测试工具

test-alert: ## 发送测试告警
	@echo "$(BLUE)发送测试告警到 Alertmanager...$(NC)"
	@curl -s -XPOST -H "Content-Type: application/json" -d '[{"labels":{"alertname":"TestAlert","severity":"warning","instance":"test"},"annotations":{"summary":"这是一条测试告警","description":"用于测试告警通知功能"}}]' http://localhost:9093/api/v1/alerts
	@echo ""
	@echo "$(GREEN)测试告警已发送，请检查通知渠道$(NC)"

show-targets: ## 显示所有采集目标状态
	@echo "$(BLUE)vmagent 采集目标状态:$(NC)"
	@curl -s http://localhost:8429/targets | grep -o '"health":"[^"]*"' | sort | uniq -c || echo "无法获取目标状态"

show-alerts: ## 显示当前触发的告警
	@echo "$(BLUE)当前触发的告警:$(NC)"
	@curl -s http://localhost:8880/api/v1/alerts | jq -r '.data.alerts[] | select(.state=="firing") | "\(.labels.alertname) - \(.labels.instance)"' || echo "没有触发的告警"

show-metrics-count: ## 显示指标数量
	@echo "$(BLUE)时间序列统计:$(NC)"
	@curl -s http://localhost:8428/api/v1/status/tsdb | jq '.data.totalSeries' || echo "无法获取指标数"

##@ 开发工具

shell-vm: ## 进入 VictoriaMetrics 容器
	@docker exec -it victoriametrics sh

shell-vmagent: ## 进入 vmagent 容器
	@docker exec -it vmagent sh

shell-grafana: ## 进入 Grafana 容器
	@docker exec -it grafana sh

download-snmp-config: ## 下载官方 SNMP Exporter 配置
	@echo "$(BLUE)下载 SNMP Exporter 配置...$(NC)"
	@wget -q -O config/snmp-exporter/snmp.yml https://github.com/prometheus/snmp_exporter/releases/latest/download/snmp.yml
	@echo "$(GREEN)下载完成$(NC)"

##@ 清理操作

clean: ## 清理临时文件和日志
	@echo "$(BLUE)清理临时文件...$(NC)"
	@find . -name "*.log" -type f -delete
	@find . -name "*.tmp" -type f -delete
	@find . -name "*~" -type f -delete
	@echo "$(GREEN)清理完成$(NC)"

prune: ## 清理未使用的 Docker 资源
	@echo "$(BLUE)清理未使用的 Docker 资源...$(NC)"
	@docker system prune -f
	@echo "$(GREEN)清理完成$(NC)"

uninstall: ## 完全卸载（删除所有数据和配置）
	@echo "$(YELLOW)警告: 这将删除所有服务、数据和配置！$(NC)"
	@read -p "确认卸载? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		make stop; \
		docker volume rm monitoring-deployment_vmdata monitoring-deployment_vmagentdata monitoring-deployment_grafana-data monitoring-deployment_alertmanager-data 2>/dev/null || true; \
		docker network rm monitoring-deployment_monitoring 2>/dev/null || true; \
		echo "$(GREEN)卸载完成$(NC)"; \
	else \
		echo "$(BLUE)操作已取消$(NC)"; \
	fi
