#!/bin/bash
set -euo pipefail

DOCKER_HOST_PORT=${DOCKER_HOST_PORT:-8000}

PYLON_DOCKER_IMAGE_NAME=${PYLON_DOCKER_IMAGE_NAME:-bittensor_pylon:latest}

nox -s build-docker -- -t "$PYLON_DOCKER_IMAGE_NAME"

docker run --rm \
  --env-file .env \
  -v "$HOME/.bittensor:/root/.bittensor" \
  -p "$DOCKER_HOST_PORT:8000" \
  "$PYLON_DOCKER_IMAGE_NAME" "$@"
