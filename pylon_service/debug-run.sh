#!/bin/bash

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
pushd "$script_dir" >/dev/null || exit 1
trap 'popd >/dev/null' EXIT

PYLON_DEBUG=true uv run python -m pylon_service.uvicorn_entrypoint "$@"
