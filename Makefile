PWD=$$(pwd)
SCRIPT_DIR=$(shell cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJ_ROOT=$(SCRIPT_DIR)
TOOLS_DIR=$(PROJ_ROOT)/tools

all: dev

.PHONY:
init:
	cd "$(PROJ_ROOT)/docs-gen" && npm install

.PHONY:
dev:
	cd "$(PROJ_ROOT)/docs-gen" && npm run dev


.PHONY:
build:
	cd "$(PROJ_ROOT)/docs-gen" && npm run build

.PHONY:
clean:
	git clean -fdx
