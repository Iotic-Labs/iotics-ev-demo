CMD ?= src/conf.py

VENV_DIR=venv
PYTHON=${VENV_DIR}/bin/python
SRC_DIR = ./src
EXT_PROTO_DIR = ./ext
# directories where you want to clone your proto buffers
EXT_GOOGLE_PROTO_DIR = ${EXT_PROTO_DIR}/google
EXT_IOTICS_PROTO_DIR = ${EXT_PROTO_DIR}/iotics
EXT_IOTICS_PROTO_API_DIR = $(EXT_IOTICS_PROTO_DIR)/proto/iotics/api
# for each directory we clone separately

SEED=~/.config/.tutorial-ev-chargers.seed
#SEED=.ev-demo.prod.seed

USER_SEED_FILE ?= ${SEED}
IOTICS_UK_NAME ?= demo-user
AGENT_SEED_FILE ?= ${SEED}
IOTICS_AK_NAME ?= demo-agent
IOTICS_USER_NAME ?= demo-agent
IOTICS_AGENT_NAME ?= demo-agent
IOTICS_HOST_PORT ?= 9090
CONF_NAME ?= $(shell echo ${IOTICS_HOST_PORT} | cut -d . -f 1)

PWD=$(shell pwd)

export PIP_CERT=${SSL_CERT_FILE}
export USER_SEED_FILE
export AGENT_SEED_FILE
export IOTICS_HOST_PORT
export IOTICS_AK_NAME
export IOTICS_AGENT_NAME
export IOTICS_UK_NAME

check-conf:
	venv/bin/python \
	src/conf.py

#serve: write-js-conf
serve:
	${PYTHON} -m http.server -d src/js 9090

run-demo:
	${PYTHON} ${CMD} -e demo.iotics.space

run-demo2:
	${PYTHON} ${CMD} -e demo2.iotics.space

setup:
	python3 -mvenv ${VENV_DIR}
	${VENV_DIR}/bin/pip install -U pip setuptools
	${VENV_DIR}/bin/pip install -e .
# for GRPC
	${VENV_DIR}/bin/pip install grpcio grpcio-tools grpcio-status timeloop

run-publisher:
	${PYTHON} src/twin_manager.py

run-observer:
	${PYTHON} src/analytics.py

run-subscriber:
	${PYTHON} src/subscriber.py

cleanup:
	${PYTHON} src/cleanup.py

showvars:
	@echo USER_SEED_FILE=${USER_SEED_FILE}
	@echo AGENT_SEED_FILE=${AGENT_SEED_FILE}
	@echo IOTICS_HOST_PORT=${IOTICS_HOST_PORT}
	@echo IOTICS_AK_NAME=${IOTICS_AK_NAME}
	@echo IOTICS_UK_NAME=${IOTICS_UK_NAME}
	@echo IOTICS_AGENT_NAME=${IOTICS_AGENT_NAME}
	@echo IOTICS_USER_NAME=${IOTICS_USER_NAME}


define CONF_TEMPLATE
{
    "${CONF_NAME}": {
        "endpoint": "${IOTICS_HOST_PORT}",
        "userName": "${IOTICS_UK_NAME}",
        "userSeed": "$(shell cat ${USER_SEED_FILE})",
        "agentName": "${IOTICS_AK_NAME}",
        "agentSeed": "$(shell cat ${AGENT_SEED_FILE})"
    }
}
endef
export CONF_TEMPLATE


check-env:
ifndef IOTICS_HOST_PORT
	$(error IOTICS_HOST_PORT not set)
endif

write-js-conf: check-env
	@echo $$CONF_TEMPLATE > src/js/conf.json

docker-build: write-js-conf
	@docker build \
		--target builder \
		--build-arg PIP_INDEX_URL=${PIP_INDEX_URL} \
		-t iotics-ev-charger-tutorial \
		.

docker-run-publisher:
	docker run \
		-it --rm --name ev-publisher \
		--network host \
		-e USER_SEED_FILE=${USER_SEED_FILE} \
		-e AGENT_SEED_FILE=${AGENT_SEED_FILE} \
		-e IOTICS_HOST_PORT=${IOTICS_HOST_PORT} \
		-e IOTICS_AK_NAME=${IOTICS_AK_NAME} \
		-e IOTICS_AGENT_NAME=${IOTICS_AGENT_NAME} \
		-e IOTICS_UK_NAME=${IOTICS_UK_NAME} \
		iotics-ev-charger-tutorial

### GRPC additions

$(EXT_GOOGLE_PROTO_DIR):
	@mkdir -p $(EXT_GOOGLE_PROTO_DIR)
	@git clone https://github.com/googleapis/googleapis.git $(EXT_GOOGLE_PROTO_DIR)

$(EXT_IOTICS_PROTO_DIR):
	@mkdir -p $(EXT_IOTICS_PROTO_DIR)
	@git clone https://github.com/Iotic-Labs/api.git $(EXT_IOTICS_PROTO_DIR)

.PHONY: gen
.PHONY: clone

# deletes the generated source code
clean:
	rm -rf $(SRC_DIR)/google/*
	rm -rf $(SRC_DIR)/iotics/*
	mkdir -p $(SRC_DIR)/google/rpc

# cleans the root directory of the cloned repos - don't do it that often cos googleapi is huge
clean-proto:
	@rm -rf ${EXT_PROTO_DIR}

# clone conditionally to the existence of the APIs and fetch latest
clone: | $(EXT_GOOGLE_PROTO_DIR) ${EXT_IOTICS_PROTO_DIR}
	@echo CLONED
	@cd $(EXT_GOOGLE_PROTO_DIR) && git pull
	@cd $(EXT_IOTICS_PROTO_DIR) && git pull

gen-iotics:
#	proto buffer compiler
	@echo "Compiling IOTICS protos"
	@for name in $(EXT_IOTICS_PROTO_API_DIR)/*.proto ; do \
		echo "Compiling $${name}" ; \
		python -m grpc_tools.protoc -I$(EXT_GOOGLE_PROTO_DIR):$(EXT_IOTICS_PROTO_DIR)/proto/:$(EXT_IOTICS_PROTO_API_DIR) --python_out=$(SRC_DIR) --grpc_python_out=$(SRC_DIR) $${name} ; \
	done

gen-google:
	@echo "Compiling google protos"
	@python -m grpc_tools.protoc -I$(EXT_GOOGLE_PROTO_DIR) --python_out=$(SRC_DIR) --grpc_python_out=$(SRC_DIR) $(EXT_GOOGLE_PROTO_DIR)/google/rpc/status.proto

gen: clone clean gen-iotics gen-google