#!/bin/sh

set -e

exec poetry run uvicorn \
	--host 0.0.0.0 \
	--port 5000 \
	--reload \
	sudoku_as_a_service.main:app
