# Tabys Analytics Makefile
# Quick commands for analytics operations

.PHONY: help seed seed-docker stats stats-docker clean-analytics reset-analytics docker-up docker-down docker-logs docker-rebuild

help: ## Show this help message
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║         TABYS Analytics - Available Commands               ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "Analytics Commands:"
	@echo "  make seed            - Seed analytics data (Docker)"
	@echo "  make stats           - View analytics statistics (Docker)"
	@echo "  make clean-analytics - Clear all analytics data"
	@echo "  make reset-analytics - Reset and reseed analytics"
	@echo ""
	@echo "Docker Commands:"
	@echo "  make docker-up       - Start Docker services"
	@echo "  make docker-down     - Stop Docker services"
	@echo "  make docker-logs     - View API logs"
	@echo "  make docker-rebuild  - Rebuild and restart containers"
	@echo ""
	@echo "Database Commands:"
	@echo "  make db-shell        - Open PostgreSQL shell"
	@echo "  make db-backup       - Backup database"
	@echo "  make db-stats        - View database statistics"
	@echo ""

seed: docker-up ## Seed analytics data in Docker
	@echo "🚀 Seeding analytics data..."
	@docker-compose exec api python seed_analytics.py

seed-docker: ## Run seed script with confirmation
	@./seed_analytics_docker.sh

stats: ## View analytics statistics
	@docker-compose exec api python view_analytics_stats.py

stats-local: ## View analytics statistics locally
	@python view_analytics_stats.py

clean-analytics: ## Clear all analytics data
	@echo "⚠️  This will delete all analytics data!"
	@read -p "Continue? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	@echo "Clearing analytics data..."
	@docker-compose exec -T postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "TRUNCATE TABLE user_activities CASCADE;"
	@docker-compose exec -T postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "TRUNCATE TABLE login_history CASCADE;"
	@docker-compose exec -T postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "TRUNCATE TABLE system_events CASCADE;"
	@echo "✅ Analytics data cleared"

reset-analytics: clean-analytics seed ## Reset and reseed all analytics
	@echo "✅ Analytics reset complete"

docker-up: ## Start Docker services
	@echo "🐳 Starting Docker services..."
	@docker-compose up -d
	@echo "✅ Services started"

docker-down: ## Stop Docker services
	@echo "🛑 Stopping Docker services..."
	@docker-compose down
	@echo "✅ Services stopped"

docker-logs: ## View API container logs
	@docker-compose logs -f api

docker-rebuild: ## Rebuild and restart containers
	@echo "🔨 Rebuilding containers..."
	@docker-compose down
	@docker-compose build --no-cache
	@docker-compose up -d
	@echo "✅ Rebuild complete"

db-shell: ## Open PostgreSQL shell
	@docker-compose exec postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB}

db-backup: ## Backup database
	@echo "💾 Creating database backup..."
	@mkdir -p ./backups
	@docker-compose exec -T postgres pg_dump -U ${POSTGRES_USER} ${POSTGRES_DB} > ./backups/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "✅ Backup created in ./backups/"

db-stats: ## View database statistics
	@echo "📊 Database Statistics:"
	@docker-compose exec -T postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "\
		SELECT \
			'users_2026_12' as table_name, COUNT(*) as count FROM users_2026_12 \
		UNION ALL \
		SELECT 'user_activities', COUNT(*) FROM user_activities \
		UNION ALL \
		SELECT 'login_history', COUNT(*) FROM login_history \
		UNION ALL \
		SELECT 'system_events', COUNT(*) FROM system_events;"

open-analytics: ## Open analytics dashboard in browser
	@open http://localhost:3001/kz/admin/analytics

open-docs: ## Open API docs in browser
	@open http://localhost:8000/docs

test-api: ## Test analytics API endpoint
	@curl -s http://localhost:8000/api/v2/admin/analytics/dashboard?period=month | jq '.'
