# --- Variables ---


# --- Feature ---

devpod:
	devpod up . --ide codium --provider docker --recreate

run-nodes:
	uv run dora build dataflow.yml --uv
	uv run dora run dataflow.yml --uv

code-map: ## Export project structure to JSON
	uv run python3 libs/code_mapper.py --to-json

##@ Maintenance
clean: ## Remove python caches and temporary files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache .venv .ruff_cache .mypy_cache
	@# Remove legacy VS Code Snap environment injections that break devpod/devbox sessions
	-sed -i '/snap\/code/d' ~/.profile ~/.bashrc ~/.bash_aliases 2>/dev/null

nuke: clean ## ☢️  Wipe EVERYTHING
	@echo "Nuking system..."
	@docker stop $$(docker ps -aq) 2>/dev/null || true
	@docker rm $$(docker ps -aq) 2>/dev/null || true
	@docker volume rm $$(docker volume ls -q) 2>/dev/null || true
	@docker system prune -af --volumes
	@echo "✅ Reset complete."

#  Automatically collect all targets with descriptions for .PHONY
ALL_TARGETS := $(shell grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | cut -d: -f1)

.PHONY: $(ALL_TARGETS)