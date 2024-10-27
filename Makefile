.PHONY = default
.PHONY += build
.PHONY += lint
.PHONY += install
.PHONY += help

python_cmd ?= python3
python_install_cmd ?= $(python_cmd) -m pip install --user --upgrade

example_dir := example

#################
# Targets
#################
default: install

lint: ## Check code formatting
	$(python_cmd) -m flake8

delint: ## Attempt to fix formatting issues
	black .

install: ## Install the pyintegration package
	$(python_install_cmd) -e .

build: ## Builds the package for installation
	$(python_cmd) -m build

clean: ## Remove build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf pyintegration.egg-info/

test: ## Runs the example test code
	make -C $(example_dir) $@

help: ## This message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
