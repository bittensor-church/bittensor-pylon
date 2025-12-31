# Pylon

This document covers the usage, configuration, deployment, and observability of Pylon.

## Access Modes

Pylon supports two access patterns:

### Open Access

Open access mode can be used to query the subtensor without presenting any hotkey.
It gives access to subtensor data like neurons or hyperparams,
but does not allow write operations.

Open access endpoints may require authentication via `open_access_token`,
depending on service configuration.

Open access endpoints follow the pattern `/api/v1/subnet/{netuid}/...` and do not require
an identity. See the full list at `/schema/swagger` when the service is running.

### Identity Access

Identity is a combination of a Bittensor wallet and a subnet.
Identities are named and defined in the Pylon configuration.
Each identity is protected by its own secret token.

When authenticated with an identity token, Pylon uses the wallet defined in the identity
to perform all operations on the associated subnet.

Identity endpoints follow the pattern `/api/v1/identity/{identity_name}/subnet/{netuid}/...`.
See the full list at `/schema/swagger` when the service is running.

> **Note:** Output of respective open-access and identity endpoints may differ slightly,
> as data can depend on the hotkey presented. For example, axon info may differ when using DDOS shield.

## Configuration

All configuration is done via environment variables with the `PYLON_` prefix.
We recommend creating a `.env` file and passing it to the Docker container using `--env-file .env`.

### Core Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `PYLON_BITTENSOR_NETWORK` | Bittensor network (e.g., `finney` or `ws://mylocalchain:9944`) | `finney` |
| `PYLON_BITTENSOR_ARCHIVE_NETWORK` | Archive network for historical data | `archive` |
| `PYLON_BITTENSOR_ARCHIVE_BLOCKS_CUTOFF` | Blocks threshold for switching to archive network | `300` |
| `PYLON_BITTENSOR_WALLET_PATH` | Path to wallet directory inside the container | `/root/.bittensor/wallets` |

### Access Control

| Variable | Description | Default |
|----------|-------------|---------|
| `PYLON_OPEN_ACCESS_TOKEN` | Token for open access endpoints (empty = no auth required) | `""` |
| `PYLON_IDENTITIES` | JSON list of identity names to configure | `[]` |

### Identity Configuration

For each identity listed in `PYLON_IDENTITIES`, configure these variables
(replace `{NAME}` with uppercase identity name):

| Variable | Description |
|----------|-------------|
| `PYLON_ID_{NAME}_WALLET_NAME` | Wallet name (coldkey) |
| `PYLON_ID_{NAME}_HOTKEY_NAME` | Hotkey name |
| `PYLON_ID_{NAME}_NETUID` | Subnet UID |
| `PYLON_ID_{NAME}_TOKEN` | Authentication token for this identity |

**Example:**

```bash
# .env
PYLON_IDENTITIES=["sn1", "sn2"]

# Identity: sn1
PYLON_ID_SN1_WALLET_NAME=sn1_wallet
PYLON_ID_SN1_HOTKEY_NAME=sn1_hotkey
PYLON_ID_SN1_NETUID=1
PYLON_ID_SN1_TOKEN=8GOqUEjyTuYXER790bm8LpSmOIDuPvbr

# Identity: sn2
PYLON_ID_SN2_WALLET_NAME=sn2_wallet
PYLON_ID_SN2_HOTKEY_NAME=sn2_hotkey
PYLON_ID_SN2_NETUID=2
PYLON_ID_SN2_TOKEN=IEYAWl9rPQAMTV0hqAKAaQtEYqqKws5z
```

### Retry Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `PYLON_WEIGHTS_RETRY_ATTEMPTS` | Max retry attempts for weight submission | `200` |
| `PYLON_WEIGHTS_RETRY_DELAY_SECONDS` | Delay between retries in seconds | `1` |
| `PYLON_COMMITMENT_RETRY_ATTEMPTS` | Max retry attempts for commitment submission | `10` |
| `PYLON_COMMITMENT_RETRY_DELAY_SECONDS` | Delay between commitment retries in seconds | `1` |

### Monitoring

| Variable | Description | Default |
|----------|-------------|---------|
| `PYLON_METRICS_TOKEN` | Token for `/metrics` endpoint (empty = 403 Forbidden) | `""` |
| `PYLON_SENTRY_DSN` | Sentry DSN for error tracking | `""` |
| `PYLON_SENTRY_ENVIRONMENT` | Sentry environment name | `production` |

## Deployment

The recommended way to run Pylon is via Docker.
The official image is available on
[Docker Hub](https://hub.docker.com/r/backenddevelopersltd/bittensor-pylon).
Make sure your `.env` file and wallet directory are accessible to the container.

### Docker

```bash
docker pull backenddevelopersltd/bittensor-pylon:latest
docker run -d \
    --env-file .env \
    -v ~/.bittensor/wallets/:/root/.bittensor/wallets \
    backenddevelopersltd/bittensor-pylon:latest
```

### Docker Compose

Create a `docker-compose.yaml` file:

```yaml
services:
  pylon:
    image: backenddevelopersltd/bittensor-pylon:latest
    restart: unless-stopped
    env_file: ./.env
    volumes:
      - ~/.bittensor/wallets/:/root/.bittensor/wallets
```

Run with:

```bash
docker compose up -d
```

## Versioning

API endpoints are versioned to ensure backward compatibility. If breaking changes need to be
introduced to an endpoint, a new version of that endpoint will be created while the old version
remains unchanged. This allows us to deploy seemingly breaking changes without bumping up the image
major version and therefore not breaking existing clients. The aim of this is to support older clients,
providing them fixes and improvements, without maintaining separate branches.

Current newest API version: `v1` (endpoints under `/api/v1/...`)

## Observability

### Prometheus Metrics

The service exposes Prometheus metrics at `/metrics` endpoint,
protected with Bearer token authentication.

**Configuration:**

```bash
PYLON_METRICS_TOKEN=your-secure-metrics-token
```

**Access:**

```bash
curl http://localhost:8000/metrics -H "Authorization: Bearer your-secure-metrics-token"
```

**Available Metrics:**

*HTTP API Metrics:*

| Metric | Type | Description |
|--------|------|-------------|
| `pylon_requests_total` | Counter | Total number of HTTP requests |
| `pylon_request_duration_seconds` | Histogram | HTTP request duration |
| `pylon_requests_in_progress` | Gauge | HTTP requests currently being processed |

All HTTP metrics include labels: `method`, `path`, `status_code`, `app_name`.

*Bittensor Operations Metrics:*

| Metric | Type | Description |
|--------|------|-------------|
| `pylon_bittensor_operation_duration_seconds` | Histogram | Duration of Bittensor operations |
| `pylon_bittensor_fallback_total` | Counter | Archive client fallback events |

Labels: `operation`, `status`, `uri`, `netuid`, `hotkey`, `reason`.

*ApplyWeights Job Metrics:*

| Metric | Type | Description |
|--------|------|-------------|
| `pylon_apply_weights_job_duration_seconds` | Histogram | Duration of entire ApplyWeights job |
| `pylon_apply_weights_attempt_duration_seconds` | Histogram | Duration of individual weight attempts |

Labels: `operation`, `status`, `netuid`, `hotkey`.

*Python Runtime Metrics:*
Standard Python process metrics are also exposed: memory usage, CPU time,
garbage collection stats, and file descriptors.

> **Tip:** Set `PROMETHEUS_DISABLE_CREATED_SERIES=True` to disable automatic `*_created`
> gauge metrics and reduce metrics output.
