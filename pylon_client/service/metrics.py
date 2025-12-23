from __future__ import annotations

import functools
import inspect
import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from time import perf_counter
from typing import Any, TypeVar, cast

from prometheus_client import Counter, Histogram
from prometheus_client.metrics import MetricWrapperBase

logger = logging.getLogger(__name__)


class UseMethodName:
    """Sentinel type indicating the decorator should use the function name."""


AsyncCallableT = TypeVar("AsyncCallableT", bound=Callable[..., Awaitable[Any]])
USE_METHOD_NAME = UseMethodName()


class MetricsConfigurationError(Exception):
    """Raised when metrics label configuration is invalid."""


class LabelSource(ABC):
    """
    Label sources define how to extract values for Prometheus metric labels
    from method calls. Each source type knows how to extract values from
    different locations (attributes, parameters, or static values).
    """

    @abstractmethod
    def extract(self, label_name: str, self_obj: object | None, method_params: dict[str, Any]) -> str:
        """
        Extract label value from the method call context.

        Args:
            label_name: Name of the label being extracted (for error messages)
            self_obj: The instance object (self) if method is bound, None otherwise
            method_params: Dictionary of method parameter names to their values

        Returns:
            String value for the label

        Raises:
            MetricsConfigurationError: When value cannot be extracted
        """


class Static(LabelSource):
    """Static label value that never changes."""

    def __init__(self, value: str):
        self.value = value

    def extract(self, label_name: str, self_obj: object | None, method_params: dict[str, Any]) -> str:
        return self.value


class Param(LabelSource):
    """Extract label value from method parameter."""

    def __init__(self, name: str):
        self.name = name

    def extract(self, label_name: str, self_obj: object | None, method_params: dict[str, Any]) -> str:
        if self.name not in method_params:
            raise MetricsConfigurationError(
                f"Parameter '{self.name}' not found in method signature for label '{label_name}'"
            )
        value = method_params[self.name]
        return str(value) if value is not None else "unknown"


class Attr(LabelSource):
    """Extract label value from instance attribute (self.attribute)."""

    def __init__(self, name: str):
        self.name = name

    def extract(self, label_name: str, self_obj: object | None, method_params: dict[str, Any]) -> str:
        if self_obj is None:
            raise MetricsConfigurationError(
                f"Cannot extract attribute '{self.name}' for label '{label_name}' - no self object"
            )
        if not hasattr(self_obj, self.name):
            raise MetricsConfigurationError(
                f"Attribute '{self.name}' not found on {type(self_obj).__name__} for label '{label_name}'"
            )
        value = getattr(self_obj, self.name)
        return str(value) if value is not None else "unknown"


class MetricsContext:
    """
    Context for tracking metrics during operation execution.
    """

    def __init__(self, initial_labels: dict[str, str] | None = None):
        self.labels = initial_labels.copy() if initial_labels else {}

    def set_label(self, key: str, value: str) -> None:
        """Set or update a label that will be included in metrics."""
        self.labels[key] = value

    def get_all_labels(self) -> dict[str, str]:
        """Get all labels for metrics recording."""
        return self.labels


bittensor_operation_duration = Histogram(
    "pylon_bittensor_operation_duration_seconds",
    """Duration of Bittensor operations in seconds.

    Labels:
        operation: Name of the operation (e.g., get_block, get_neurons, commit_weights).
        status: Operation outcome ("success" or "error").
              Set automatically by _track_operation_context based on exception presence.
        uri: Bittensor network URI.
        netuid: Subnet identifier.
        hotkey: Wallet hotkey (ss58) performing the operation.
    """,
    ["operation", "status", "uri", "netuid", "hotkey"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0),
)

bittensor_fallback_total = Counter(
    "pylon_bittensor_fallback_total",
    """Total number of archive client fallback events.

    Labels:
        reason: Reason for fallback (e.g., "unknown_block", "stale_block").
              See pylon_client.service.bittensor.client.FallbackReason for details.
        operation: Name of the operation that triggered fallback.
        hotkey: Wallet hotkey (ss58) performing the operation.
    """,
    ["reason", "operation", "hotkey"],
)

# ApplyWeights metrics
apply_weights_job_duration = Histogram(
    "pylon_apply_weights_job_duration_seconds",
    """Duration of entire ApplyWeights job execution (outer ``run_job`` wrapper).

    Labels:
        operation: Name of the operation (``run_job``).
        status: Operation outcome ("success" or "error").
              Set automatically by _track_operation_context based on exception presence.
        netuid: Subnet identifier for multi-net deployments.
        hotkey: Wallet hotkey (ss58) used by the client submitting weights.
    """,
    ["operation", "status", "netuid", "hotkey"],
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0, 1200.0),
)

apply_weights_attempt_duration = Histogram(
    "pylon_apply_weights_attempt_duration_seconds",
    """Duration of individual `_apply_weights` attempts.

    Labels:
        operation: Name of the inner coroutine (``_apply_weights``).
        status: Outcome of the attempt ("success" or "error").
              Set automatically by _track_operation_context based on exception presence.
        netuid: Subnet identifier.
        hotkey: Wallet hotkey (ss58) used by the client submitting weights.
    """,
    ["operation", "status", "netuid", "hotkey"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0),
)


def track_operation(
    duration_metric: Histogram,
    operation_name: str | UseMethodName = USE_METHOD_NAME,
    labels: dict[str, LabelSource] | None = None,
    *,
    inject_context: str | None = None,
):
    """
    Operation tracking decorator.

    This decorator:
    1. Extracts initial labels from method parameters/attributes
    2. Creates a MetricsContext and optionally injects it as a parameter
    3. Allows dynamic label setting during execution via the context
    4. Records duration histogram with all labels when operation completes

    The histogram automatically includes a "status" label ("success" or "error") to track
    operation outcomes.

    Args:
        duration_metric: Prometheus Histogram for operation duration (must include "status" label)
        operation_name: Custom operation name. If not provided, uses method name.
        labels: Label extraction configuration. Maps label names to LabelSource objects.
            Example:
                {
                    "uri": Attr("uri"),           # Extract from self.uri
                    "hotkey": Attr("_hotkey"),    # Extract from self._hotkey
                    "netuid": Param("netuid"),    # Extract from netuid parameter
                    "env": Static("production"),  # Static value
                }
        inject_context: Parameter name to inject MetricsContext into. If None, no injection.
    """

    def decorator(func: AsyncCallableT) -> AsyncCallableT:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # We bind the original call to inspect parameters/attributes for label extraction.
            sig = inspect.signature(func)
            bound_args = sig.bind_partial(*args, **kwargs)
            bound_args.apply_defaults()

            self_obj = args[0] if args else None
            op_name = func.__name__ if isinstance(operation_name, UseMethodName) else operation_name
            extracted_labels = _extract_labels(labels or {}, self_obj, bound_args.arguments)

            context = MetricsContext(extracted_labels)

            call_kwargs = dict(kwargs)
            if inject_context:
                if inject_context in call_kwargs:
                    raise ValueError(f"Parameter '{inject_context}' already exists in function call")
                call_kwargs[inject_context] = context

            async with _track_operation_context(op_name, context, duration_metric):
                return await func(*args, **call_kwargs)

        return cast(AsyncCallableT, wrapper)

    return decorator


def _extract_labels(
    label_config: dict[str, LabelSource],
    self_obj: object | None,
    method_params: dict[str, Any],
) -> dict[str, str]:
    """
    Extract labels using LabelSource objects.

    Args:
        label_config: Mapping of label names to LabelSource objects
        self_obj: Instance object (self) if available
        method_params: Dictionary of method parameter names to values

    Returns:
        Dictionary of label names to extracted string values

    Raises:
        MetricsConfigurationError: When label extraction fails or configuration is invalid
    """
    extracted = {}

    for label_name, source in label_config.items():
        if not isinstance(source, LabelSource):
            raise MetricsConfigurationError(
                f"Label '{label_name}' must be a LabelSource instance (Static, Param, or Attr), "
                f"got {type(source).__name__}"
            )
        extracted[label_name] = source.extract(label_name, self_obj, method_params)

    return extracted


def _prepare_metric_labels(
    metric: MetricWrapperBase, context_labels: dict[str, str], required_labels: dict[str, str]
) -> dict[str, str]:
    """
    Prepare labels for metric recording with validation and auto-filling missing labels.

    Args:
        metric: The Prometheus metric (Histogram or Counter)
        context_labels: Labels from MetricsContext
        required_labels: Labels that must be added (e.g., operation, status)

    Returns:
        Complete label dict ready for metric recording with missing labels set to "N/A"

    Raises:
        MetricsConfigurationError: If a configured label is not expected by the metric
    """
    expected_label_names = set(metric._labelnames)
    all_labels = {**context_labels, **required_labels}

    # Check for unexpected labels - this indicates misconfiguration
    unexpected = set(all_labels.keys()) - expected_label_names
    if unexpected:
        raise MetricsConfigurationError(
            f"Labels {unexpected} are not expected by metric '{metric._name}'. Expected: {expected_label_names}"
        )

    # Fill missing labels with N/A
    result = {}
    for label_name in expected_label_names:
        result[label_name] = all_labels.get(label_name, "N/A")

    return result


@asynccontextmanager
async def _track_operation_context(operation: str, context: MetricsContext, duration_metric: Histogram):
    """Track operation duration with histogram using the provided metrics context.

    Records duration with status label ("success" or "error"). Error count can be
    derived from histogram bucket counts with status="error".
    """
    start_time = perf_counter()
    status = "success"

    try:
        yield
    except Exception:
        status = "error"
        raise
    finally:
        # Record duration histogram with status label
        duration_labels = _prepare_metric_labels(
            duration_metric, context.get_all_labels(), {"operation": operation, "status": status}
        )
        duration = perf_counter() - start_time
        duration_metric.labels(**duration_labels).observe(duration)
