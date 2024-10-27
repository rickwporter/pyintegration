python_cmd ?= python3

#################
# Targets
#################
default: help

lint: ## Check code formatting
	$(python_cmd) -m flake8

delint: ## Fix formatting
	black .

clean: ## Remove build/run artifacts
	rm -rf *.log

test: ## Runs the example test code
	$(python_cmd) integration_test.py

help: ## This message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
