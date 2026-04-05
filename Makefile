PYTHON ?= /Users/robert/arkham/.venv/bin/python
OPENAPI_DIR := /Users/robert/arkham/docs/openapi
OPENAPI_EXPORTER := /Users/robert/arkham/infra/scripts/export_gateway_openapi.py

.PHONY: openapi-export openapi-serve

openapi-export:
	$(PYTHON) $(OPENAPI_EXPORTER)

openapi-serve:
	cd $(OPENAPI_DIR) && $(PYTHON) -m http.server 8080
