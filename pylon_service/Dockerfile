# Use official Python image as base
FROM python:3.12-slim

WORKDIR /app

# install system and Rust build dependencies
RUN apt-get update && apt-get install -y git curl build-essential pkg-config libssl-dev

RUN curl https://sh.rustup.rs -sSf | sh -s -- -y --profile minimal
ENV PATH="/root/.cargo/bin:/app/pylon_service/.venv/bin:${PATH}"
ENV TZ=UTC

# copy packages (build context should be repository root)
COPY pylon_commons ./pylon_commons
COPY pylon_service ./pylon_service

# install uv and dependencies
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /bin/
RUN cd pylon_service && /bin/uv sync --no-dev

EXPOSE 8000
CMD ["pylon_service/.venv/bin/python", "-m", "pylon_service.uvicorn_entrypoint"]
